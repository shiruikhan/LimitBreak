"""utils/db_core.py — Infraestrutura compartilhada do LimitBreak.

Contém:
  - Conexão psycopg2 (get_connection, _db_params)
  - Helpers de fuso BRT (_today_brt, _brt_day_bounds, etc.)
  - Streak de treino (_unique_workout_days_brt, _compute_streak_from_days)
  - Constantes e helpers de stats/natures/IV/EV de Pokémon
  - Helper de inserção de user_pokemon (_insert_user_pokemon)
  - Helpers de sprite (sprite_img_tag, hq_sprite_url, get_image_as_base64)
  - Constante _LOOT_VITAMINS (usada em loja, treino e missões)

Não importa de nenhum outro módulo db_*.
"""

import os
import base64
import random
import datetime
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()

# ── Timezone e helpers BRT ────────────────────────────────────────────────────

_BRT = datetime.timezone(datetime.timedelta(hours=-3))


def _today_brt() -> datetime.date:
    return datetime.datetime.now(tz=_BRT).date()


def _brt_day_bounds(day: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Returns the inclusive/exclusive TIMESTAMPTZ bounds for one BRT day."""
    start = datetime.datetime.combine(day, datetime.time.min, tzinfo=_BRT)
    return start, start + datetime.timedelta(days=1)


def _brt_date_range_bounds(
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Returns [start, end) TIMESTAMPTZ bounds for an inclusive BRT date range."""
    start_ts, _ = _brt_day_bounds(start_date)
    _, end_ts = _brt_day_bounds(end_date)
    return start_ts, end_ts


def _brt_month_bounds(year: int, month: int) -> tuple[datetime.datetime, datetime.datetime]:
    """Returns [start, end) TIMESTAMPTZ bounds for a BRT calendar month."""
    start_date = datetime.date(year, month, 1)
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    start_ts, _ = _brt_day_bounds(start_date)
    end_ts = datetime.datetime.combine(next_month, datetime.time.min, tzinfo=_BRT)
    return start_ts, end_ts


def _to_brt_date(ts: datetime.datetime | None) -> datetime.date | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    return ts.astimezone(_BRT).date()


def _unique_workout_days_brt(cur, user_id: str) -> list[datetime.date]:
    """Returns unique workout days in BRT ordered from newest to oldest.

    A janela de 400 dias é suficiente para qualquer streak realista e evita
    full-sequential-scans em usuários com centenas de sessões registradas.
    """
    cur.execute("""
        SELECT completed_at
        FROM workout_logs
        WHERE user_id = %s
          AND completed_at > NOW() - INTERVAL '400 days'
        ORDER BY completed_at DESC;
    """, (user_id,))

    days: list[datetime.date] = []
    seen: set[datetime.date] = set()
    for (completed_at,) in cur.fetchall():
        day = _to_brt_date(completed_at)
        if day and day not in seen:
            seen.add(day)
            days.append(day)
    return days


def _compute_streak_from_days(days: list[datetime.date], start_day: datetime.date | None = None) -> int:
    if not days:
        return 0
    streak = 0
    check_day = start_day or _today_brt()
    for day in days:
        if day == check_day:
            streak += 1
            check_day -= datetime.timedelta(days=1)
        elif day < check_day:
            break
    return streak


# ── Conexão psycopg2 ──────────────────────────────────────────────────────────

_DB_PARAMS: dict | None = None


def _db_params() -> dict:
    """Carrega parâmetros de conexão.

    Prioridade:
      1. st.secrets["database"]  — Streamlit Cloud (ou secrets.toml local)
      2. Variáveis de ambiente   — arquivo .env para desenvolvimento local
    """
    global _DB_PARAMS
    if _DB_PARAMS is None:
        try:
            db = st.secrets["database"]
            _DB_PARAMS = dict(
                host=db["host"],
                port=int(db["port"]),
                dbname=db["name"],
                user=db["user"],
                password=db["password"],
            )
        except (KeyError, FileNotFoundError):
            # Fallback: .env local
            _DB_PARAMS = dict(
                host=os.getenv("host"),
                port=os.getenv("port"),
                dbname=os.getenv("database"),
                user=os.getenv("user"),
                password=os.getenv("password"),
            )
    return _DB_PARAMS


def _new_conn():
    return psycopg2.connect(**_db_params())


def get_connection():
    """Returns a live psycopg2 connection stored per Streamlit session.
    Reconnects automatically if the server closed the connection.
    """
    conn = st.session_state.get("_db_conn")
    if conn is None or conn.closed != 0:
        st.session_state._db_conn = _new_conn()
        return st.session_state._db_conn
    # Roll back any aborted transaction so the connection is reusable
    if conn.status != psycopg2.extensions.STATUS_READY:
        try:
            conn.rollback()
        except Exception:
            st.session_state._db_conn = _new_conn()
    return st.session_state._db_conn


# ── Column name helpers ───────────────────────────────────────────────────────

def _workout_days_sheet_fk() -> str:
    return "sheet_id"


def _workout_day_exercises_day_fk() -> str:
    return "day_id"


# ── Constantes de Pokémon ─────────────────────────────────────────────────────

_STAT_ORDER = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")
_NEUTRAL_NATURES = {"hardy", "docile", "serious", "bashful", "quirky"}
_NATURE_EFFECTS = {
    "lonely": ("attack", "defense"),
    "brave": ("attack", "speed"),
    "adamant": ("attack", "sp_attack"),
    "naughty": ("attack", "sp_defense"),
    "bold": ("defense", "attack"),
    "relaxed": ("defense", "speed"),
    "impish": ("defense", "sp_attack"),
    "lax": ("defense", "sp_defense"),
    "timid": ("speed", "attack"),
    "hasty": ("speed", "defense"),
    "jolly": ("speed", "sp_attack"),
    "naive": ("speed", "sp_defense"),
    "modest": ("sp_attack", "attack"),
    "mild": ("sp_attack", "defense"),
    "quiet": ("sp_attack", "speed"),
    "rash": ("sp_attack", "sp_defense"),
    "calm": ("sp_defense", "attack"),
    "gentle": ("sp_defense", "defense"),
    "sassy": ("sp_defense", "speed"),
    "careful": ("sp_defense", "sp_attack"),
}
_STAT_LABELS = {
    "hp": "HP",
    "attack": "ATK",
    "defense": "DEF",
    "sp_attack": "Sp. Atk",
    "sp_defense": "Sp. Def",
    "speed": "SPD",
}
_ALL_NATURES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)


# ── Helpers de stat / nature ──────────────────────────────────────────────────

def _pokemon_stat_value(
    base: int,
    level: int,
    *,
    iv: int = 0,
    ev: int = 0,
    nature: float = 1.0,
    is_hp: bool = False,
) -> int:
    """Calcula um stat usando a fórmula padrão de Pokémon.

    Quando IV/EV/Nature não estiverem presentes ou preenchidos, usa valores
    neutros como fallback para manter compatibilidade.
    """
    level = max(1, min(level, 100))
    base = max(0, base or 0)
    iv = max(0, iv or 0)
    ev = max(0, ev or 0)
    scaled = ((2 * base + iv + (ev // 4)) * level) // 100
    if is_hp:
        return max(1, scaled + level + 10)
    return max(1, int((scaled + 5) * nature))


def _build_pokemon_stats(
    bases: tuple | list,
    level: int,
    *,
    ivs: dict | None = None,
    evs: dict | None = None,
    nature_modifiers: dict | None = None,
    flat_boosts: dict | None = None,
) -> list[int]:
    """Monta os seis stats finais na ordem usada por user_pokemon."""
    ivs = ivs or {}
    evs = evs or {}
    nature_modifiers = nature_modifiers or {}
    flat_boosts = flat_boosts or {}

    values = []
    for i, stat in enumerate(_STAT_ORDER):
        values.append(
            _pokemon_stat_value(
                bases[i] or 0,
                level,
                iv=ivs.get(stat, 0),
                ev=evs.get(stat, 0),
                nature=nature_modifiers.get(stat, 1.0),
                is_hp=(stat == "hp"),
            ) + flat_boosts.get(stat, 0)
        )
    return values


def _get_species_bases(cur, species_id: int):
    cur.execute("""
        SELECT base_hp, base_attack, base_defense,
               base_sp_attack, base_sp_defense, base_speed
        FROM pokemon_species WHERE id = %s;
    """, (species_id,))
    return cur.fetchone()


def _random_ivs() -> dict:
    return {stat: random.randint(0, 31) for stat in _STAT_ORDER}


def _random_evs() -> dict:
    remaining = 510
    evs = {}
    for stat in random.sample(list(_STAT_ORDER), len(_STAT_ORDER)):
        max_for_stat = min(252, remaining)
        value = random.randint(0, max_for_stat // 4) * 4
        evs[stat] = value
        remaining -= value
    return evs


def _random_nature() -> str:
    return random.choice(_ALL_NATURES)


def _nature_payload(nature_name: str | None) -> dict | None:
    if not nature_name:
        return None

    slug = str(nature_name).strip().lower()
    if not slug:
        return None

    boosted = nerfed = None
    boosted_nerfed = _NATURE_EFFECTS.get(slug)
    if boosted_nerfed:
        boosted, nerfed = boosted_nerfed

    is_neutral = slug in _NEUTRAL_NATURES or not boosted_nerfed
    boosted_label = _STAT_LABELS.get(boosted) if boosted else None
    nerfed_label = _STAT_LABELS.get(nerfed) if nerfed else None

    return {
        "name": slug.capitalize(),
        "slug": slug,
        "is_neutral": is_neutral,
        "boosted_stat": boosted,
        "boosted_label": boosted_label,
        "nerfed_stat": nerfed,
        "nerfed_label": nerfed_label,
        "summary": "Neutral" if is_neutral else f"+{boosted_label} / -{nerfed_label}",
    }


def _nature_modifiers(nature_name: str | None) -> dict:
    modifiers = {stat: 1.0 for stat in _STAT_ORDER}
    payload = _nature_payload(nature_name)
    if not payload or payload["is_neutral"]:
        return modifiers

    boosted = payload["boosted_stat"]
    nerfed = payload["nerfed_stat"]
    modifiers[boosted] = 1.1
    modifiers[nerfed] = 0.9
    return modifiers


def _nature_select_sql(table_alias: str = "up") -> str:
    return f"{table_alias}.nature AS nature"


def _load_pokemon_genetics(cur, user_pokemon_id: int) -> tuple[dict, dict, dict]:
    cur.execute("""
        SELECT iv_hp, iv_attack, iv_defense, iv_sp_attack, iv_sp_defense, iv_speed,
               ev_hp, ev_attack, ev_defense, ev_sp_attack, ev_sp_defense, ev_speed,
               nature
        FROM user_pokemon
        WHERE id = %s;
    """, (user_pokemon_id,))
    row = cur.fetchone()
    if not row:
        return {}, {}, _nature_modifiers(None)

    ivs = {stat: row[i] or 0 for i, stat in enumerate(_STAT_ORDER)}
    evs = {stat: row[i + len(_STAT_ORDER)] or 0 for i, stat in enumerate(_STAT_ORDER)}
    nature_mods = _nature_modifiers(row[-1])
    return ivs, evs, nature_mods


def _stored_user_pokemon_stats(cur, user_pokemon_id: int) -> list[int] | None:
    cur.execute("""
        SELECT stat_hp, stat_attack, stat_defense,
               stat_sp_attack, stat_sp_defense, stat_speed
        FROM user_pokemon
        WHERE id = %s;
    """, (user_pokemon_id,))
    row = cur.fetchone()
    return list(row) if row else None


def _flat_stat_boosts(cur, user_pokemon_id: int) -> dict:
    boosts = {stat: 0 for stat in _STAT_ORDER}
    cur.execute("""
        SELECT stat, COALESCE(SUM(delta), 0)
        FROM user_pokemon_stat_boosts
        WHERE user_pokemon_id = %s
        GROUP BY stat;
    """, (user_pokemon_id,))
    for stat, total in cur.fetchall():
        if stat in boosts:
            boosts[stat] = total or 0
    return boosts


def _expected_user_pokemon_stats(
    cur,
    user_pokemon_id: int,
    *,
    species_id: int | None = None,
    level: int | None = None,
) -> list[int] | None:
    if species_id is None or level is None:
        cur.execute("""
            SELECT species_id, level
            FROM user_pokemon
            WHERE id = %s;
        """, (user_pokemon_id,))
        row = cur.fetchone()
        if not row:
            return None
        if species_id is None:
            species_id = row[0]
        if level is None:
            level = row[1]

    bases = _get_species_bases(cur, species_id)
    if not bases:
        return None

    ivs, evs, nature_mods = _load_pokemon_genetics(cur, user_pokemon_id)
    return _build_pokemon_stats(
        bases,
        level,
        ivs=ivs,
        evs=evs,
        nature_modifiers=nature_mods,
        flat_boosts=_flat_stat_boosts(cur, user_pokemon_id),
    )


def _sync_user_pokemon_stats(
    cur,
    user_pokemon_id: int,
    *,
    species_id: int | None = None,
    level: int | None = None,
) -> bool:
    """Regrava stat_* usando a espécie atual como fonte única de verdade."""
    expected = _expected_user_pokemon_stats(
        cur,
        user_pokemon_id,
        species_id=species_id,
        level=level,
    )
    if expected is None:
        return False

    stored = _stored_user_pokemon_stats(cur, user_pokemon_id)
    if stored == expected:
        return False

    set_parts = ", ".join(f"stat_{stat} = %s" for stat in _STAT_ORDER)
    cur.execute(
        f"UPDATE user_pokemon SET {set_parts} WHERE id = %s;",
        expected + [user_pokemon_id],
    )
    return True


def _audit_and_sync_user_team_stats(cur, user_id: str) -> list[int]:
    """Audita a equipe ativa do usuário e corrige quaisquer stats divergentes."""
    cur.execute("""
        SELECT up.id
        FROM user_team ut
        JOIN user_pokemon up ON up.id = ut.user_pokemon_id
        WHERE ut.user_id = %s
        ORDER BY ut.slot ASC;
    """, (user_id,))
    changed_ids = []
    for (user_pokemon_id,) in cur.fetchall():
        if _sync_user_pokemon_stats(cur, user_pokemon_id):
            changed_ids.append(user_pokemon_id)
    return changed_ids


def _insert_user_pokemon(
    cur,
    user_id: str,
    species_id: int,
    *,
    level: int,
    xp: int = 0,
    is_shiny: bool = False,
) -> int | None:
    """Insere um Pokémon com stats calculados pela fórmula canônica."""
    bases = _get_species_bases(cur, species_id)
    if not bases:
        return None

    ivs = _random_ivs()
    evs = _random_evs()
    nature = _random_nature()
    nature_mods = _nature_modifiers(nature)
    stats = _build_pokemon_stats(
        bases, level, ivs=ivs, evs=evs, nature_modifiers=nature_mods
    )
    cur.execute("""
        INSERT INTO user_pokemon (
            user_id, species_id, level, xp, is_shiny,
            iv_hp, iv_attack, iv_defense, iv_sp_attack, iv_sp_defense, iv_speed,
            ev_hp, ev_attack, ev_defense, ev_sp_attack, ev_sp_defense, ev_speed,
            nature,
            stat_hp, stat_attack, stat_defense,
            stat_sp_attack, stat_sp_defense, stat_speed
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s,
            %s, %s, %s, %s, %s, %s
        )
        RETURNING id;
    """, (
        user_id, species_id, level, xp, is_shiny,
        ivs["hp"], ivs["attack"], ivs["defense"], ivs["sp_attack"], ivs["sp_defense"], ivs["speed"],
        evs["hp"], evs["attack"], evs["defense"], evs["sp_attack"], evs["sp_defense"], evs["speed"],
        nature,
        *stats,
    ))
    row = cur.fetchone()
    return row[0] if row else None


# ── Sprite helpers ─────────────────────────────────────────────────────────────

# URL base do repo público de assets (HybridShivam/Pokemon)
_GITHUB_ASSETS_CDN = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master"


def _asset_fallback_url(path: str) -> str | None:
    norm = path.replace("\\", "/")
    if "assets/" not in norm:
        return None
    rel = norm.split("assets/", 1)[1]
    return f"{_GITHUB_ASSETS_CDN}/assets/{rel}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_image_as_base64(path: str) -> str | None:
    """Converte um asset local em base64.

    O objetivo deste helper e atender apenas casos legados de arquivos locais.
    Para URLs HTTP/S use `sprite_img_tag()` ou `st.image(url)` para deixar o
    browser lidar com cache e carregamento.
    """
    try:
        if path.startswith(("http://", "https://")):
            return None

        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except FileNotFoundError:
            return None

    except Exception:
        return None


def sprite_img_tag(
    sprite_url: str | None,
    width: int = 80,
    extra_style: str = "",
) -> str:
    """Gera tag <img> para um sprite de Pokémon de forma eficiente.

    Para URLs HTTP (Supabase Storage ou outro CDN público) usa o src diretamente,
    evitando download + base64 no servidor Python e aproveitando o cache do browser.
    Para caminhos locais faz fallback via get_image_as_base64().

    Retorna string vazia se não conseguir resolver a imagem.
    """
    if not sprite_url:
        return ""

    style_attr = f' style="{extra_style}"' if extra_style else ""

    if sprite_url.startswith(("http://", "https://")):
        return f'<img src="{sprite_url}" width="{width}"{style_attr}>'

    fallback_url = _asset_fallback_url(sprite_url)
    if fallback_url:
        return f'<img src="{fallback_url}" width="{width}"{style_attr}>'

    # Caminho local — converte para base64
    b64 = get_image_as_base64(sprite_url)
    if b64:
        return f'<img src="data:image/png;base64,{b64}" width="{width}"{style_attr}>'
    return ""


def hq_sprite_url(sprite_url: str) -> str:
    """Converte qualquer URL de sprite para a versão HQ (official artwork).

    - Supabase normal/XXXX.png → hq/XXXX.png
    - Supabase shiny/XXXX.png  → hq-shiny/XXXX.png
    - Formas regionais (ex.: 0026-Alola.png) não têm HQ — retorna URL original.
    - URLs genéricas: troca /images/ por /imagesHQ/
    - Caminhos locais: idem
    """
    if not sprite_url:
        return sprite_url
    if "supabase" in sprite_url and "/pokemon-sprites/" in sprite_url:
        filename = sprite_url.rsplit("/", 1)[-1]
        stem = filename.rsplit(".", 1)[0]
        if "-" in stem:  # forma regional — sem HQ disponível
            return sprite_url
        if "/shiny/" in sprite_url:
            return sprite_url.replace("/shiny/", "/hq-shiny/")
        if "/normal/" in sprite_url:
            return sprite_url.replace("/normal/", "/hq/")
    if sprite_url.startswith("http"):
        return sprite_url.replace("/images/", "/imagesHQ/")
    return sprite_url.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")


# ── Constante de loot compartilhada ──────────────────────────────────────────
# Usada em: loja (open_loot_box), treino (pickup ability), missões (claim_mission_reward)

_LOOT_VITAMINS = ["hp-up", "protein", "iron", "calcium", "zinc", "carbos"]
