import os
import base64
import random
import datetime
import calendar as cal_module
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_BRT = datetime.timezone(datetime.timedelta(hours=-3))

def _today_brt() -> datetime.date:
    return datetime.datetime.now(tz=_BRT).date()

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


def _table_has_column(table_name: str, column_name: str) -> bool:
    """Checks column existence to stay compatible with small schema drifts."""
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s
                  AND column_name = %s
                LIMIT 1;
                """,
                (table_name, column_name),
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def _first_existing_column(table_name: str, *column_names: str) -> str | None:
    """Returns the first existing column name from the provided candidates."""
    for column_name in column_names:
        if _table_has_column(table_name, column_name):
            return column_name
    return None


_STAT_ORDER = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")
_GENETIC_COLUMNS = (
    "iv_hp", "iv_attack", "iv_defense", "iv_sp_attack", "iv_sp_defense", "iv_speed",
    "ev_hp", "ev_attack", "ev_defense", "ev_sp_attack", "ev_sp_defense", "ev_speed",
    "nature",
)
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


def _has_genetic_columns(cur) -> bool:
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_name = 'user_pokemon'
          AND table_schema = ANY(current_schemas(false))
          AND column_name = ANY(%s);
    """, (list(_GENETIC_COLUMNS),))
    return cur.fetchone()[0] == len(_GENETIC_COLUMNS)


def _nature_select_sql(cur, table_alias: str = "up") -> str:
    return f"{table_alias}.nature AS nature" if _has_genetic_columns(cur) else "NULL AS nature"


def _load_pokemon_genetics(cur, user_pokemon_id: int) -> tuple[dict, dict, dict]:
    if not _has_genetic_columns(cur):
        return {}, {}, _nature_modifiers(None)

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

    if _has_genetic_columns(cur):
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
    else:
        stats = _build_pokemon_stats(bases, level)
        cur.execute("""
            INSERT INTO user_pokemon (
                user_id, species_id, level, xp, is_shiny,
                stat_hp, stat_attack, stat_defense,
                stat_sp_attack, stat_sp_defense, stat_speed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (user_id, species_id, level, xp, is_shiny, *stats))
    row = cur.fetchone()
    return row[0] if row else None


# URL base do repo público de assets (HybridShivam/Pokemon)
_GITHUB_ASSETS_CDN = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master"


@st.cache_data(show_spinner=False)
def get_image_as_base64(path: str) -> str | None:
    """Converte uma imagem em base64.

    Aceita:
    - Caminho local (dev): tenta abrir o arquivo
    - URL http/https: faz GET e converte
    - Caminho local não encontrado: faz fallback automático para o CDN
      público do HybridShivam/Pokemon no GitHub (Streamlit Cloud)
    """
    import requests as _req

    try:
        # ── 1. URL remota explícita ───────────────────────────────────────────
        if path.startswith(("http://", "https://")):
            r = _req.get(path, timeout=10)
            return base64.b64encode(r.content).decode() if r.status_code == 200 else None

        # ── 2. Arquivo local ──────────────────────────────────────────────────
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except FileNotFoundError:
            pass

        # ── 3. Fallback: GitHub CDN (produção no Streamlit Cloud) ─────────────
        # Transforma qualquer caminho local que contenha "assets/" em URL remota.
        # Ex.: C:\...\src\Pokemon\assets\images\0001.png
        #   →  https://raw.githubusercontent.com/.../assets/images/0001.png
        norm = path.replace("\\", "/")
        if "assets/" in norm:
            rel = norm.split("assets/", 1)[1]
            r = _req.get(f"{_GITHUB_ASSETS_CDN}/assets/{rel}", timeout=10)
            return base64.b64encode(r.content).decode() if r.status_code == 200 else None

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

    # Caminho local — converte para base64
    b64 = get_image_as_base64(sprite_url)
    if b64:
        return f'<img src="data:image/png;base64,{b64}" width="{width}"{style_attr}>'
    return ""


# ── Pokédex queries ────────────────────────────────────────────────────────────

@st.cache_data
def get_all_pokemon() -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("SELECT id, name FROM pokemon_species ORDER BY id;")
        return cur.fetchall()


@st.cache_data
def get_all_pokemon_with_types() -> list[dict]:
    """Retorna todos os 1.025 Pokémon com tipos e sprite — cacheado globalmente."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.sprite_url,
                   t1.name AS type1, t1.slug AS type1_slug,
                   t2.name AS type2, t2.slug AS type2_slug
            FROM pokemon_species p
            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
            LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
            ORDER BY p.id;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "name": r[1], "sprite_url": r[2],
                "type1": r[3], "type1_slug": r[4],
                "type2": r[5], "type2_slug": r[6],
            }
            for r in rows
        ]


@st.cache_data(show_spinner=False)
def get_pokemon_details(pokemon_id: int) -> tuple | None:
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url,
                   t1.name AS type1, t2.name AS type2, p.base_experience,
                   p.base_hp, p.base_attack, p.base_defense,
                   p.base_sp_attack, p.base_sp_defense, p.base_speed
            FROM pokemon_species p
            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
            LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
            WHERE p.id = %s;
        """, (pokemon_id,))
        return cur.fetchone()


@st.cache_data(ttl=3600, show_spinner=False)
def get_pokemon_moves(pokemon_id: int) -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT m.name, sm.level_learned_at, m.damage_class,
                   t.name AS type_name, m.power, m.accuracy
            FROM pokemon_moves m
            JOIN pokemon_species_moves sm ON m.id = sm.move_id
            LEFT JOIN pokemon_types t ON m.type_id = t.id
            WHERE sm.species_id = %s AND sm.learn_method = 'level-up'
            ORDER BY sm.level_learned_at ASC;
        """, (pokemon_id,))
        return cur.fetchall()


@st.cache_data(ttl=3600, show_spinner=False)
def get_full_evolution_chain(pokemon_id: int) -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("""
            WITH RECURSIVE ancestors AS (
                SELECT from_species_id AS id
                FROM pokemon_evolutions WHERE to_species_id = %(id)s
                UNION
                SELECT e.from_species_id
                FROM pokemon_evolutions e
                INNER JOIN ancestors a ON e.to_species_id = a.id
            ),
            base_pokemon AS (
                SELECT id FROM ancestors
                UNION
                SELECT %(id)s
                ORDER BY id ASC LIMIT 1
            ),
            full_chain AS (
                SELECT e.from_species_id, e.to_species_id, e.min_level, e.trigger_name, e.item_name
                FROM pokemon_evolutions e
                WHERE e.from_species_id = (SELECT id FROM base_pokemon)
                UNION
                SELECT e.from_species_id, e.to_species_id, e.min_level, e.trigger_name, e.item_name
                FROM pokemon_evolutions e
                INNER JOIN full_chain fc ON e.from_species_id = fc.to_species_id
            )
            SELECT fc.from_species_id, p1.name,
                   fc.to_species_id, p2.name,
                   fc.min_level, fc.trigger_name, fc.item_name,
                   p1.sprite_url, p2.sprite_url
            FROM full_chain fc
            JOIN pokemon_species p1 ON fc.from_species_id = p1.id
            JOIN pokemon_species p2 ON fc.to_species_id = p2.id;
        """, {"id": pokemon_id})
        return cur.fetchall()


# ── User / team queries ────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict | None:
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT id, username, coins, starter_pokemon_id
                FROM user_profiles WHERE id = %s;
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "username": row[1], "coins": row[2], "starter_pokemon_id": row[3]}
    except Exception:
        return None


def create_user_profile(user_id: str, username: str, starter_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profiles (id, username, starter_pokemon_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (user_id, username, starter_id))

            up_id = _insert_user_pokemon(cur, user_id, starter_id, level=1, xp=0)
            if up_id is None:
                raise ValueError("Espécie inicial não encontrada para calcular stats.")

            # Put starter in team slot 1
            cur.execute("""
                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                VALUES (%s, 1, %s)
                ON CONFLICT (user_id, slot) DO UPDATE SET user_pokemon_id = EXCLUDED.user_pokemon_id;
            """, (user_id, up_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e


def get_user_team(user_id: str) -> list[dict]:
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            if _audit_and_sync_user_team_stats(cur, user_id):
                conn.commit()
            nature_select = _nature_select_sql(cur)
            cur.execute(f"""
                SELECT ut.slot, up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp, t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       p.base_hp, p.base_attack, p.base_defense,
                       p.base_sp_attack, p.base_sp_defense, p.base_speed,
                       {nature_select},
                       p.ability_slug,
                       up.is_shiny, p.sprite_shiny_url
                FROM user_team ut
                JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                JOIN pokemon_species p ON up.species_id = p.id
                LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
                WHERE ut.user_id = %s
                ORDER BY ut.slot ASC;
            """, (user_id,))
            rows = cur.fetchall()
            return [
                {
                    "slot": r[0], "user_pokemon_id": r[1], "species_id": r[2],
                    "name": r[3], "sprite_url": r[4], "level": r[5], "xp": r[6],
                    "type1": r[7], "type2": r[8],
                    "stat_hp": r[9],  "stat_attack": r[10], "stat_defense": r[11],
                    "stat_sp_attack": r[12], "stat_sp_defense": r[13], "stat_speed": r[14],
                    "base_hp": r[15], "base_attack": r[16], "base_defense": r[17],
                    "base_sp_attack": r[18], "base_sp_defense": r[19], "base_speed": r[20],
                    "nature_name": r[21],
                    "nature": _nature_payload(r[21]),
                    "ability_slug": r[22] if len(r) > 22 else None,
                    "is_shiny": bool(r[23]) if len(r) > 23 else False,
                    "sprite_shiny_url": r[24] if len(r) > 24 else None,
                }
                for r in rows
            ]
    except Exception:
        return []


def get_user_pokemon_ids(user_id: str) -> set[int]:
    """Returns set of species_id that the user owns."""
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                "SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s;",
                (user_id,)
            )
            return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def capture_pokemon(user_id: str, species_id: int) -> bool:
    """Adds Pokémon to user collection and team (if slot available). Returns True on success."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            up_id = _insert_user_pokemon(cur, user_id, species_id, level=1, xp=0)
            if up_id is None:
                raise ValueError("Espécie não encontrada para calcular stats.")

            # Fill first available team slot (1-6)
            cur.execute("""
                SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;
            """, (user_id,))
            used = {r[0] for r in cur.fetchall()}
            free = next((s for s in range(1, 7) if s not in used), None)
            if free:
                cur.execute("""
                    INSERT INTO user_team (user_id, slot, user_pokemon_id)
                    VALUES (%s, %s, %s);
                """, (user_id, free, up_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def get_user_bench(user_id: str) -> list[dict]:
    """Retorna todos os user_pokemon do usuário que NÃO estão na equipe ativa."""
    try:
        with get_connection().cursor() as cur:
            nature_select = _nature_select_sql(cur)
            cur.execute(f"""
                SELECT up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp,
                       t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       {nature_select},
                       up.is_shiny, p.sprite_shiny_url
                FROM user_pokemon up
                JOIN pokemon_species p  ON up.species_id = p.id
                LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
                WHERE up.user_id = %s
                  AND up.id NOT IN (
                      SELECT user_pokemon_id FROM user_team WHERE user_id = %s
                  )
                ORDER BY up.level DESC, up.id DESC;
            """, (user_id, user_id))
            rows = cur.fetchall()
            return [
                {
                    "user_pokemon_id": r[0], "species_id": r[1],
                    "name": r[2], "sprite_url": r[3],
                    "level": r[4], "xp": r[5],
                    "type1": r[6], "type2": r[7],
                    "stat_hp": r[8],  "stat_attack": r[9],  "stat_defense": r[10],
                    "stat_sp_attack": r[11], "stat_sp_defense": r[12], "stat_speed": r[13],
                    "nature_name": r[14],
                    "nature": _nature_payload(r[14]),
                    "is_shiny": bool(r[15]) if len(r) > 15 else False,
                    "sprite_shiny_url": r[16] if len(r) > 16 else None,
                }
                for r in rows
            ]
    except Exception:
        return []


def add_to_team(user_id: str, user_pokemon_id: int) -> tuple[bool, str]:
    """Adiciona um Pokémon do banco ao primeiro slot livre da equipe.

    Retorna (True, mensagem) ou (False, mensagem de erro).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verifica se o Pokémon pertence ao usuário e não está na equipe
            cur.execute(
                "SELECT id FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            if not cur.fetchone():
                return False, "Pokémon não encontrado."

            cur.execute(
                "SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;",
                (user_id,)
            )
            occupied = {r[0] for r in cur.fetchall()}
            free_slot = next((s for s in range(1, 7) if s not in occupied), None)
            if free_slot is None:
                return False, "A equipe já está cheia (6/6)."

            cur.execute("""
                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, slot) DO UPDATE SET user_pokemon_id = EXCLUDED.user_pokemon_id;
            """, (user_id, free_slot, user_pokemon_id))
        conn.commit()
        return True, f"Pokémon adicionado ao slot {free_slot}!"
    except Exception as e:
        conn.rollback()
        return False, str(e)


def set_team_slot(user_id: str, slot: int, user_pokemon_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, slot) DO UPDATE SET user_pokemon_id = EXCLUDED.user_pokemon_id;
            """, (user_id, slot, user_pokemon_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def remove_from_team(user_id: str, slot: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_team WHERE user_id = %s AND slot = %s;",
                (user_id, slot)
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def swap_team_slots(user_id: str, slot_a: int, slot_b: int) -> bool:
    """Swaps two team slots using a temporary slot to avoid PK conflicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s FOR UPDATE;",
                (user_id, slot_a)
            )
            row_a = cur.fetchone()
            cur.execute(
                "SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s FOR UPDATE;",
                (user_id, slot_b)
            )
            row_b = cur.fetchone()

            if not row_b:
                return False

            if not row_a:
                # slot_a is empty — just move slot_b into it
                cur.execute(
                    "UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=%s;",
                    (slot_a, user_id, slot_b)
                )
            else:
                # Swap via temp slot 99
                cur.execute("UPDATE user_team SET slot=99 WHERE user_id=%s AND slot=%s;", (user_id, slot_a))
                cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=%s;", (slot_a, user_id, slot_b))
                cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=99;", (slot_b, user_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


# ── Move management ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_available_moves(species_id: int, level: int) -> list[dict]:
    """All level-up moves the Pokémon can know at its current level."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT m.id, m.name, sm.level_learned_at, m.damage_class,
                       t.name AS type_name, m.power, m.accuracy
                FROM pokemon_moves m
                JOIN pokemon_species_moves sm ON m.id = sm.move_id
                LEFT JOIN pokemon_types t ON m.type_id = t.id
                WHERE sm.species_id = %s
                  AND sm.learn_method = 'level-up'
                  AND sm.level_learned_at <= %s
                ORDER BY sm.level_learned_at ASC;
            """, (species_id, level))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0], "name": r[1], "level_learned_at": r[2],
                    "damage_class": r[3], "type_name": r[4],
                    "power": r[5], "accuracy": r[6],
                }
                for r in rows
            ]
    except Exception:
        return []


def get_active_moves(user_pokemon_id: int) -> list[dict]:
    """The 4 equipped moves for a user's Pokémon, ordered by slot."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT upm.slot, m.id, m.name, m.damage_class,
                       t.name AS type_name, m.power, m.accuracy
                FROM user_pokemon_moves upm
                JOIN pokemon_moves m ON upm.move_id = m.id
                LEFT JOIN pokemon_types t ON m.type_id = t.id
                WHERE upm.user_pokemon_id = %s
                ORDER BY upm.slot;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            return [
                {
                    "slot": r[0], "id": r[1], "name": r[2],
                    "damage_class": r[3], "type_name": r[4],
                    "power": r[5], "accuracy": r[6],
                }
                for r in rows
            ]
    except Exception:
        return []


def equip_move(user_pokemon_id: int, slot: int, move_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_pokemon_moves (user_pokemon_id, slot, move_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_pokemon_id, slot)
                DO UPDATE SET move_id = EXCLUDED.move_id;
            """, (user_pokemon_id, slot, move_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def unequip_move(user_pokemon_id: int, slot: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_pokemon_moves WHERE user_pokemon_id = %s AND slot = %s;",
                (user_pokemon_id, slot),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


# ── Stat boosts (itens da loja) ────────────────────────────────────────────────

# Stats válidos — usados como whitelist antes de interpolar no nome da coluna
_VALID_STATS = frozenset({"hp", "attack", "defense", "sp_attack", "sp_defense", "speed"})
_MAX_STAT_BOOSTS_PER_STAT = 5  # vitaminas por stat por Pokémon


def apply_stat_boost(user_pokemon_id: int, stat: str, delta: int, source_item: str) -> bool:
    """Aplica um boost permanente a um stat do Pokémon do usuário.

    Registra o histórico em user_pokemon_stat_boosts e atualiza o valor
    efetivo em user_pokemon.stat_<stat> — tudo na mesma transação.

    Args:
        user_pokemon_id: ID do user_pokemon a ser modificado.
        stat:            Nome do stat ('hp', 'attack', 'defense',
                         'sp_attack', 'sp_defense', 'speed').
        delta:           Variação (positiva para buff, negativa para nerf).
        source_item:     Nome do item que causou a alteração (ex: 'HP Up').

    Returns:
        True em caso de sucesso, False em caso de erro.
    """
    if stat not in _VALID_STATS:
        raise ValueError(f"Stat inválido: '{stat}'. Válidos: {sorted(_VALID_STATS)}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Limite de vitaminas por stat
            cur.execute("""
                SELECT COUNT(*) FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s AND stat = %s AND delta > 0;
            """, (user_pokemon_id, stat))
            if cur.fetchone()[0] >= _MAX_STAT_BOOSTS_PER_STAT:
                return False

            # Registra o boost no histórico auditável
            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, delta, source_item))

            # Atualiza o valor efetivo (stat é validado pela whitelist acima — seguro interpolar)
            cur.execute(f"""
                UPDATE user_pokemon
                SET stat_{stat} = COALESCE(stat_{stat}, 0) + %s
                WHERE id = %s;
            """, (delta, user_pokemon_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def get_stat_boosts(user_pokemon_id: int) -> list[dict]:
    """Retorna o histórico completo de boosts de um Pokémon, do mais antigo ao mais recente."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT id, stat, delta, source_item, applied_at
                FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s
                ORDER BY applied_at ASC;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "stat": r[1],
                    "delta": r[2],
                    "source_item": r[3],
                    "applied_at": r[4],
                }
                for r in rows
            ]
    except Exception:
        return []


def get_stat_boost_summary(user_pokemon_id: int) -> dict:
    """Retorna o total acumulado de boosts por stat para um Pokémon.

    Exemplo de retorno:
        {'hp': 20, 'attack': 10, 'defense': 0, ...}
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT stat, COALESCE(SUM(delta), 0) AS total
                FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s
                GROUP BY stat;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            summary = {s: 0 for s in _VALID_STATS}
            for stat, total in rows:
                summary[stat] = total
            return summary
    except Exception:
        return {s: 0 for s in _VALID_STATS}


def get_team_stat_boost_counts(user_id: str) -> dict:
    """Retorna contagem de aplicações de vitamina por stat para todos os membros da equipe.

    Retorna {user_pokemon_id: {stat: count}}.
    Uma única query — usada por equipe.py para exibir o indicador de cap.
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT usb.user_pokemon_id, usb.stat, COUNT(*) AS cnt
                FROM user_pokemon_stat_boosts usb
                JOIN user_team ut ON ut.user_pokemon_id = usb.user_pokemon_id
                WHERE ut.user_id = %s
                GROUP BY usb.user_pokemon_id, usb.stat
            """, (user_id,))
            result: dict = {}
            for up_id, stat, cnt in cur.fetchall():
                if up_id not in result:
                    result[up_id] = {}
                result[up_id][stat] = cnt
            return result
    except Exception:
        return {}




# ── Loja ──────────────────────────────────────────────────────────────────────

@st.cache_data
def get_shop_items() -> list[dict]:
    """Retorna o catálogo completo da loja — cacheado globalmente."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT id, slug, name, description, category,
                   price, effect_stat, effect_value, icon
            FROM shop_items
            ORDER BY category, price;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "slug": r[1], "name": r[2], "description": r[3],
                "category": r[4], "price": r[5], "effect_stat": r[6],
                "effect_value": r[7], "icon": r[8],
            }
            for r in rows
        ]


def get_user_inventory(user_id: str) -> dict[int, int]:
    """Retorna {item_id: quantity} para os itens que o usuário possui (quantity > 0)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT item_id, quantity FROM user_inventory
                WHERE user_id = %s AND quantity > 0;
            """, (user_id,))
            return {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        return {}


_LOOT_BOX_ITEM = {
    "slug": "loot-box",
    "name": "Loot Box",
    "description": "Abra na Mochila para receber uma recompensa aleatoria.",
    "category": "other",
    "price": 1,
    "icon": "🎁",
}


def _add_inventory_item(cur, user_id: str, item_id: int, quantity: int = 1) -> None:
    """Adiciona quantidade ao inventario do usuario dentro da transacao atual."""
    cur.execute("""
        INSERT INTO user_inventory (user_id, item_id, quantity)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, item_id)
        DO UPDATE SET quantity = user_inventory.quantity + EXCLUDED.quantity;
    """, (user_id, item_id, quantity))


def _ensure_loot_box_item(cur) -> tuple[int, str]:
    """Garante que a Loot Box exista em shop_items e retorna (id, name)."""
    cur.execute("SELECT id, name FROM shop_items WHERE slug = %s;", (_LOOT_BOX_ITEM["slug"],))
    row = cur.fetchone()
    if row:
        return row[0], row[1]

    cur.execute("""
        INSERT INTO shop_items (slug, name, description, category, price, effect_stat, effect_value, icon)
        VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s)
        RETURNING id, name;
    """, (
        _LOOT_BOX_ITEM["slug"],
        _LOOT_BOX_ITEM["name"],
        _LOOT_BOX_ITEM["description"],
        _LOOT_BOX_ITEM["category"],
        _LOOT_BOX_ITEM["price"],
        _LOOT_BOX_ITEM["icon"],
    ))
    get_shop_items.clear()
    row = cur.fetchone()
    return row[0], row[1]


def _grant_loot_box(cur, user_id: str, count: int = 1) -> dict:
    """Entrega loot boxes ao inventario do usuario dentro da transacao atual."""
    item_id, item_name = _ensure_loot_box_item(cur)
    _add_inventory_item(cur, user_id, item_id, count)
    label = f"{count}x {item_name}" if count != 1 else f"1x {item_name}"
    return {
        "type": "loot_box",
        "slug": _LOOT_BOX_ITEM["slug"],
        "name": item_name,
        "label": label,
        "rarity": "common",
        "count": count,
    }


def buy_item(user_id: str, item_id: int) -> tuple[bool, str]:
    """Compra um item: debita moedas e adiciona ao inventário.

    XP Share não vai ao inventário — ativa/estende o efeito diretamente.

    Returns:
        (True, mensagem_sucesso) ou (False, mensagem_erro)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, price, slug FROM shop_items WHERE id = %s;", (item_id,))
            row = cur.fetchone()
            if not row:
                return False, "Item não encontrado."
            item_name, price, slug = row
            if slug == _LOOT_BOX_ITEM["slug"]:
                return False, "Este item não pode ser comprado na loja."

            # Saldo do usuário (FOR UPDATE trava a linha contra compras simultâneas)
            cur.execute(
                "SELECT coins FROM user_profiles WHERE id = %s FOR UPDATE;",
                (user_id,)
            )
            profile = cur.fetchone()
            if not profile:
                return False, "Perfil não encontrado."
            if profile[0] < price:
                return False, f"Moedas insuficientes. Você tem {profile[0]} 🪙, precisa de {price} 🪙."

            # Debita moedas
            cur.execute(
                "UPDATE user_profiles SET coins = coins - %s WHERE id = %s;",
                (price, user_id)
            )

            if slug == "xp-share":
                # XP Share: ativa/estende direto, não entra no inventário
                _extend_xp_share(cur, user_id)
                conn.commit()
                return True, f"📡 **{item_name}** ativado! +15 dias adicionados ao efeito."

            # Demais itens: adiciona ao inventário (upsert)
            cur.execute("""
                INSERT INTO user_inventory (user_id, item_id, quantity)
                VALUES (%s, %s, 1)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = user_inventory.quantity + 1;
            """, (user_id, item_id))

        conn.commit()
        return True, f"**{item_name}** comprado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao comprar: {e}"


def use_stat_item(user_id: str, item_id: int, user_pokemon_id: int) -> tuple[bool, str]:
    """Usa uma vitamina de stat em um Pokémon da equipe do usuário.

    Debita 1 unidade do inventário, aplica o boost e registra o histórico
    em user_pokemon_stat_boosts — tudo na mesma transação.

    Returns:
        (True, mensagem_sucesso) ou (False, mensagem_erro)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Detalhes do item
            cur.execute("""
                SELECT name, category, effect_stat, effect_value
                FROM shop_items WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            iname, category, stat, value = item
            if category != "stat_boost" or not stat or not value:
                return False, "Este item não pode ser usado diretamente."
            if stat not in _VALID_STATS:
                return False, "Stat inválido."

            # Verifica ownership do Pokémon
            cur.execute(
                "SELECT id FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            if not cur.fetchone():
                return False, "Pokémon não encontrado na sua coleção."

            # Verifica limite de boosts por stat
            cur.execute("""
                SELECT COUNT(*) FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s AND stat = %s AND delta > 0;
            """, (user_pokemon_id, stat))
            if cur.fetchone()[0] >= _MAX_STAT_BOOSTS_PER_STAT:
                stat_label = {
                    "hp": "HP", "attack": "Ataque", "defense": "Defesa",
                    "sp_attack": "Atq. Especial", "sp_defense": "Def. Especial",
                    "speed": "Velocidade",
                }.get(stat, stat)
                return False, f"Este Pokémon já atingiu o limite de {_MAX_STAT_BOOSTS_PER_STAT} vitaminas de {stat_label}."

            # Verifica inventário (FOR UPDATE trava contra uso duplo)
            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            # Debita inventário
            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

            # Registra histórico do boost
            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, value, iname))

            # Aplica no stat efetivo (stat validado pela whitelist acima)
            cur.execute(f"""
                UPDATE user_pokemon
                SET stat_{stat} = COALESCE(stat_{stat}, 0) + %s
                WHERE id = %s;
            """, (value, user_pokemon_id))

        conn.commit()
        stat_label = {
            "hp": "HP", "attack": "Ataque", "defense": "Defesa",
            "sp_attack": "Atq. Especial", "sp_defense": "Def. Especial", "speed": "Velocidade",
        }.get(stat, stat)
        return True, f"+{value} {stat_label} aplicado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao usar item: {e}"


def use_xp_share_item(user_id: str, item_id: int) -> tuple[bool, str]:
    """Ativa um XP Share que esteja guardado no inventario do usuario."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, slug, category
                FROM shop_items
                WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."

            item_name, slug, category = item
            if slug != "xp-share" or category != "other":
                return False, "Este item não pode ser ativado aqui."

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            cur.execute("""
                UPDATE user_inventory
                SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))
            _extend_xp_share(cur, user_id)

        conn.commit()
        return True, f"📡 **{item_name}** ativado! +15 dias adicionados ao efeito."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao ativar item: {e}"


def use_nature_mint(user_id: str, item_id: int, user_pokemon_id: int, new_nature: str) -> tuple[bool, str]:
    """Troca a natureza de um Pokémon. Consome 1 Nature Mint do inventário."""
    if new_nature not in _ALL_NATURES:
        return False, "Natureza inválida."
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, category, slug FROM shop_items WHERE id = %s;", (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            iname, category, slug = item
            if category != "nature_mint" and slug != "nature-mint":
                return False, "Este item não pode ser usado aqui."

            cur.execute(
                "SELECT nature FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return False, "Pokémon não encontrado na sua coleção."
            current_nature = (row[0] or "").capitalize()
            if current_nature == new_nature:
                return False, f"Este Pokémon já tem a natureza {new_nature}."

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))
            cur.execute(
                "UPDATE user_pokemon SET nature = %s WHERE id = %s;",
                (new_nature, user_pokemon_id),
            )
            _sync_user_pokemon_stats(cur, user_pokemon_id)

        conn.commit()
        return True, f"Natureza alterada para **{new_nature}** com sucesso! 🌿"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao usar Nature Mint: {e}"


def open_loot_box(user_id: str, item_id: int) -> tuple[bool, str, dict | None]:
    """Consome 1 Loot Box do inventario e aplica o premio sorteado."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM shop_items
                WHERE id = %s AND slug = %s;
            """, (item_id, _LOOT_BOX_ITEM["slug"]))
            item = cur.fetchone()
            if not item:
                return False, "Loot Box não encontrada.", None

            _, item_name = item
            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui nenhuma Loot Box.", None

            cur.execute("""
                UPDATE user_inventory
                SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

            loot = _roll_loot_box(cur, user_id)

        conn.commit()

        if loot["type"] == "xp":
            try:
                with get_connection().cursor() as cur2:
                    cur2.execute(
                        "SELECT user_pokemon_id FROM user_team WHERE user_id = %s AND slot = 1",
                        (user_id,),
                    )
                    slot1 = cur2.fetchone()
                if slot1:
                    xp_result = award_xp(slot1[0], loot["amount"], "loot_box_open")
                    loot["xp_result"] = xp_result
                    if xp_result.get("error"):
                        return False, f"Loot Box aberta, mas houve erro ao aplicar o XP: {xp_result['error']}", loot
                else:
                    loot["xp_result"] = {"error": "Sem Pokémon no slot 1 para receber o XP."}
                    return False, "Loot Box aberta, mas você não tem Pokémon no slot 1 para receber o XP.", loot
            except Exception as e:
                loot["xp_result"] = {"error": str(e)}
                return False, f"Loot Box aberta, mas houve erro ao aplicar o XP: {e}", loot

        return True, f"🎁 **{item_name}** aberta com sucesso! Recompensa: {loot['label']}", loot
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao abrir Loot Box: {e}", None


# ── Calendário / Check-in ──────────────────────────────────────────────────────

def get_monthly_checkins(user_id: str, year: int, month: int) -> dict:
    """Retorna dados de check-in do mês para renderizar o calendário.

    Returns:
        {
            day_number: {
                "streak": int,
                "coins": int,
                "bonus_item": bool,       # ganhou XP Share
                "spawned_species_id": int | None,
            }
        }
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT
                    EXTRACT(DAY FROM checked_date)::int AS day,
                    streak,
                    coins_earned,
                    bonus_item_id IS NOT NULL AS has_bonus,
                    spawned_species_id
                FROM user_checkins
                WHERE user_id = %s
                  AND EXTRACT(YEAR  FROM checked_date) = %s
                  AND EXTRACT(MONTH FROM checked_date) = %s;
            """, (user_id, year, month))
            return {
                r[0]: {
                    "streak": r[1],
                    "coins": r[2],
                    "bonus_item": r[3],
                    "spawned_species_id": r[4],
                }
                for r in cur.fetchall()
            }
    except Exception:
        return {}


def get_checkin_streak(user_id: str) -> int:
    """Retorna o streak atual (dias consecutivos até hoje ou ontem)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT checked_date, streak
                FROM user_checkins
                WHERE user_id = %s
                ORDER BY checked_date DESC
                LIMIT 1;
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return 0
            last_date, last_streak = row
            today     = _today_brt()
            yesterday = today - datetime.timedelta(days=1)
            if last_date in (today, yesterday):
                return last_streak
            return 0
    except Exception:
        return 0


def do_checkin(user_id: str) -> dict:
    """Executa o check-in diário do usuário.

    Regras:
    - 1 moeda por dia (UNIQUE constraint bloqueia duplicatas)
    - Dia 15 e último dia do mês: +1 XP Share
    - Streak múltiplo de 3: 25% de chance de capturar um Pokémon
      aleatório que o usuário ainda não possui (nível 5)

    Returns:
        {
            "success":       bool,
            "already_done":  bool,
            "streak":        int,
            "coins_earned":  int,
            "bonus_xp_share": bool,
            "spawn_rolled":  bool,   # True se o dado foi lançado
            "spawned": {id, name, sprite_url, type1} | None,
        }
    """
    conn    = get_connection()
    today   = _today_brt()
    result  = {
        "success": False, "already_done": False,
        "streak": 0, "coins_earned": 0,
        "bonus_xp_share": False, "spawn_rolled": False, "spawned": None,
    }

    try:
        with conn.cursor() as cur:

            # ── Streak ────────────────────────────────────────────────────────
            yesterday = today - datetime.timedelta(days=1)
            cur.execute("""
                SELECT checked_date, streak FROM user_checkins
                WHERE user_id = %s ORDER BY checked_date DESC LIMIT 1;
            """, (user_id,))
            last = cur.fetchone()
            if last and last[0] == yesterday:
                streak = last[1] + 1
            else:
                streak = 1

            # ── Bonus de meio/fim de mês? ─────────────────────────────────────
            last_day      = cal_module.monthrange(today.year, today.month)[1]
            is_bonus_day  = today.day in (15, last_day)
            bonus_item_id = None
            if is_bonus_day:
                cur.execute("SELECT id FROM shop_items WHERE slug = 'xp-share';")
                row = cur.fetchone()
                bonus_item_id = row[0] if row else None

            # ── INSERT check-in (UNIQUE bloqueia duplicata) ───────────────────
            try:
                cur.execute("""
                    INSERT INTO user_checkins
                        (user_id, checked_date, streak, coins_earned, bonus_item_id)
                    VALUES (%s, %s, %s, 1, %s);
                """, (user_id, today, streak, bonus_item_id))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                result["already_done"] = True
                return result

            # ── +1 moeda ──────────────────────────────────────────────────────
            cur.execute(
                "UPDATE user_profiles SET coins = coins + 1 WHERE id = %s;",
                (user_id,)
            )

            # ── XP Share nos dias especiais ───────────────────────────────────
            if bonus_item_id:
                _extend_xp_share(cur, user_id)
                result["bonus_xp_share"] = True

            # ── Spawn em múltiplo de 3 ────────────────────────────────────────
            spawned_species_id = None
            if streak % 3 == 0:
                result["spawn_rolled"] = True
                if random.random() < 0.25:
                    spawned_species_id = _pick_spawn_species(cur, user_id)
                    if spawned_species_id is not None:
                        checkin_shiny = _shiny_roll(streak)

                        # Captura o Pokémon (nível 5, fórmula padrão)
                        up_id = _insert_user_pokemon(
                            cur,
                            user_id,
                            spawned_species_id,
                            level=5,
                            xp=0,
                            is_shiny=checkin_shiny,
                        )
                        if up_id is None:
                            raise ValueError("Espécie spawnada não encontrada para calcular stats.")

                        # Slot de equipe livre, se houver
                        cur.execute(
                            "SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;",
                            (user_id,)
                        )
                        used = {r[0] for r in cur.fetchall()}
                        free = next((s for s in range(1, 7) if s not in used), None)
                        if free:
                            cur.execute("""
                                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                                VALUES (%s, %s, %s);
                            """, (user_id, free, up_id))

                        # Atualiza o registro do check-in com o spawn
                        cur.execute("""
                            UPDATE user_checkins SET spawned_species_id = %s
                            WHERE user_id = %s AND checked_date = %s;
                        """, (spawned_species_id, user_id, today))

                        # Busca dados do Pokémon para o resultado
                        cur.execute("""
                            SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url,
                                   t1.name AS type1
                            FROM pokemon_species p
                            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                            WHERE p.id = %s;
                        """, (spawned_species_id,))
                        pdata = cur.fetchone()
                        if pdata:
                            sprite = (pdata[3] if checkin_shiny and pdata[3] else pdata[2])
                            result["spawned"] = {
                                "id": pdata[0], "name": pdata[1],
                                "sprite_url": sprite, "type1": pdata[4],
                                "is_shiny": checkin_shiny,
                            }

        conn.commit()
        result.update({
            "success": True,
            "streak":  streak,
            "coins_earned": 1,
        })

        # ── +10 XP para o Pokémon principal (slot 1) ──────────────────────────
        # Feito após o commit do check-in para manter transações independentes.
        # Quando o módulo de treinos estiver integrado, o XP virá de lá;
        # o check-in apenas garante um pequeno progresso diário.
        xp_result = None
        try:
            with get_connection().cursor() as cur2:
                cur2.execute("""
                    SELECT up.id FROM user_team ut
                    JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                    WHERE ut.user_id = %s AND ut.slot = 1;
                """, (user_id,))
                main_row = cur2.fetchone()
            if main_row:
                xp_result = award_xp(main_row[0], 10, "check-in")
        except Exception:
            pass  # XP é bônus — falha silenciosa para não cancelar o check-in
        result["xp_result"] = xp_result

        return result

    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result


# ── XP, level-up e evolução ────────────────────────────────────────────────────

def _recalc_stats_for_level(
    cur, user_pokemon_id: int, species_id: int, level: int
) -> None:
    """Recalcula stat_* com a fórmula padrão de Pokémon + boosts planos.

    Deve ser chamada após level-ups e evoluções para manter os stats
    individuais em sincronia com o nível atual e a espécie atual.
    """
    _sync_user_pokemon_stats(
        cur,
        user_pokemon_id,
        species_id=species_id,
        level=level,
    )


def _recalc_stats_on_evolution(cur, user_pokemon_id: int) -> None:
    """Força recálculo completo após evolução usando a nova espécie persistida."""
    _sync_user_pokemon_stats(cur, user_pokemon_id)


def get_xp_share_status(user_id: str) -> dict:
    """Retorna o status do XP Share do usuário.

    Returns:
        {"active": bool, "expires_at": datetime | None, "days_left": int}
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                "SELECT xp_share_expires_at FROM user_profiles WHERE id = %s;",
                (user_id,)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return {"active": False, "expires_at": None, "days_left": 0}
            expires_at = row[0]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
            now    = datetime.datetime.now(tz=_BRT)
            active = expires_at > now
            days_left = max(0, (expires_at.date() - _today_brt()).days) if active else 0
            return {"active": active, "expires_at": expires_at, "days_left": days_left}
    except Exception:
        return {"active": False, "expires_at": None, "days_left": 0}


def _extend_xp_share(cur, user_id: str) -> None:
    """Estende (ou inicia) o XP Share em +15 dias dentro de uma transação aberta."""
    cur.execute("""
        UPDATE user_profiles
        SET xp_share_expires_at =
            GREATEST(COALESCE(xp_share_expires_at, NOW()), NOW())
            + INTERVAL '15 days'
        WHERE id = %s;
    """, (user_id,))


def _distribute_xp_share(user_id: str, main_pokemon_id: int, amount: int, source: str) -> list:
    """Distribui XP (30%) para os demais membros da equipe via XP Share.

    Retorna lista de {name, xp, user_pokemon_id} para exibição no log.
    """
    distributed = []
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ut.user_pokemon_id, ps.name
                FROM user_team ut
                JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                JOIN pokemon_species ps ON up.species_id = ps.id
                WHERE ut.user_id = %s AND ut.user_pokemon_id != %s
                ORDER BY ut.slot;
            """, (user_id, main_pokemon_id))
            others = [(r[0], r[1]) for r in cur.fetchall()]
        for pid, name in others:
            award_xp(pid, amount, source, _distributing=True)
            distributed.append({"name": name, "xp": amount, "user_pokemon_id": pid})
    except Exception:
        pass
    return distributed


def award_xp(user_pokemon_id: int, amount: int, source: str = "xp",
             _distributing: bool = False) -> dict:
    """Concede XP a um Pokémon, processando level-ups e evoluções automáticas.

    Se XP Share estiver ativo e _distributing=False, distribui 30% do XP
    para os demais membros da equipe automaticamente.

    Ponto de integração para o módulo de treinos:
        award_xp(user_pokemon_id, xp_amount, "exercise")

    Args:
        user_pokemon_id: ID do user_pokemon que receberá o XP.
        amount:          Quantidade de XP a conceder (positivo).
        source:          Origem do XP ("check-in", "exercise", "battle", etc.).
        _distributing:   Uso interno — evita recursão no XP Share.

    Returns:
        {
            "levels_gained": int,
            "old_level":     int,
            "new_level":     int,
            "new_xp":        int,
            "evolutions":    list[{from_name, to_name, to_id, sprite_url}],
            "error":         str | None,
        }
    """
    result = {
        "levels_gained": 0,
        "old_level": 0,
        "new_level": 0,
        "new_xp": 0,
        "evolutions": [],
        "xp_share_distributed": [],
        "error": None,
    }
    if amount <= 0:
        return result

    conn = get_connection()
    user_id = None
    try:
        with conn.cursor() as cur:
            # Estado atual (FOR UPDATE garante consistência em acessos simultâneos)
            cur.execute("""
                SELECT level, xp, species_id, user_id
                FROM user_pokemon WHERE id = %s FOR UPDATE;
            """, (user_pokemon_id,))
            row = cur.fetchone()
            if not row:
                result["error"] = "Pokémon não encontrado."
                return result

            level, xp, species_id, user_id = row
            result["old_level"] = level
            xp += amount

            # ── Loop de level-up ──────────────────────────────────────────────
            # Fórmula: level * 100 XP para o próximo nível. Cap: nível 100.
            _BYPASS_LEVEL = 36
            while xp >= level * 100 and level < 100:
                xp    -= level * 100
                level += 1
                result["levels_gained"] += 1

                # Verifica evolução por nível (limite de 3 por chamada).
                # Triggers não-padrão (trade, spin, three-critical-hits, take-damage,
                # agile/strong-style-move, recoil-damage, tower-*, other) disparam
                # no nível 36 como bypass. 'use-item' e 'shed' são tratados à parte.
                if len(result["evolutions"]) < 3:
                    cur.execute("""
                        SELECT e.to_species_id, p2.name, p2.sprite_url,
                               p1.name AS from_name
                        FROM pokemon_evolutions e
                        JOIN pokemon_species p2 ON e.to_species_id = p2.id
                        JOIN pokemon_species p1 ON e.from_species_id = p1.id
                        WHERE e.from_species_id = %s
                          AND (
                              (e.trigger_name = 'level-up' AND e.min_level <= %s)
                              OR (e.trigger_name NOT IN ('level-up', 'use-item', 'shed')
                                  AND %s >= %s)
                          )
                        ORDER BY e.min_level DESC NULLS LAST
                        LIMIT 1;
                    """, (species_id, level, level, _BYPASS_LEVEL))
                    evo = cur.fetchone()
                    if evo:
                        to_id, to_name, to_sprite, from_name = evo
                        result["evolutions"].append({
                            "from_name":  from_name,
                            "to_name":    to_name,
                            "to_id":      to_id,
                            "sprite_url": to_sprite,
                        })

                        # Shed mechanic: se a pré-evolução tem uma entrada 'shed',
                        # spawna o Pokémon companheiro se a equipe tiver slot livre.
                        cur.execute("""
                            SELECT e2.to_species_id, p2.name, p2.sprite_url
                            FROM pokemon_evolutions e2
                            JOIN pokemon_species p2 ON e2.to_species_id = p2.id
                            WHERE e2.from_species_id = %s AND e2.trigger_name = 'shed';
                        """, (species_id,))
                        shed_row = cur.fetchone()
                        if shed_row and user_id:
                            shed_id, shed_name, shed_sprite = shed_row
                            cur.execute(
                                "SELECT COUNT(*) FROM user_team WHERE user_id = %s;",
                                (user_id,)
                            )
                            if cur.fetchone()[0] < 6:
                                shed_up_id = _insert_user_pokemon(
                                    cur, user_id, shed_id, level=level, xp=0
                                )
                                if shed_up_id is None:
                                    raise ValueError(
                                        "Espécie de evolução complementar não encontrada."
                                    )
                                cur.execute(
                                    "SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;",
                                    (user_id,)
                                )
                                used_slots = {r[0] for r in cur.fetchall()}
                                free_slot = next(
                                    (s for s in range(1, 7) if s not in used_slots), None
                                )
                                if free_slot:
                                    cur.execute("""
                                        INSERT INTO user_team (user_id, slot, user_pokemon_id)
                                        VALUES (%s, %s, %s);
                                    """, (user_id, free_slot, shed_up_id))
                                result["evolutions"].append({
                                    "from_name":  from_name,
                                    "to_name":    shed_name,
                                    "to_id":      shed_id,
                                    "sprite_url": shed_sprite,
                                    "shed":       True,
                                })

                        species_id = to_id  # próxima iteração usa a nova espécie

            # Ao atingir o cap: congela XP em 0
            if level >= 100:
                level = 100
                xp = 0

            # ── Persiste level, xp e espécie ─────────────────────────────────
            cur.execute("""
                UPDATE user_pokemon
                SET level = %s, xp = %s, species_id = %s
                WHERE id = %s;
            """, (level, xp, species_id, user_pokemon_id))

            # ── Recalcula stats por nível e/ou evolução ──────────────────────
            if result["evolutions"]:
                # Após persistir a espécie evoluída, recalcula a partir dela.
                _recalc_stats_on_evolution(cur, user_pokemon_id)
            elif result["levels_gained"] > 0:
                # Sem evolução, mas subiu de nível → escala stats pela fórmula
                _recalc_stats_for_level(cur, user_pokemon_id, species_id, level)

        conn.commit()
        result["new_level"] = level
        result["new_xp"]    = xp

        # ── Distribuição via XP Share (só para chamada original) ──────────────
        if not _distributing and user_id:
            status = get_xp_share_status(user_id)
            if status["active"]:
                share_amount = max(1, int(amount * 0.30))
                result["xp_share_distributed"] = _distribute_xp_share(
                    user_id, user_pokemon_id, share_amount, source
                )

        return result

    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result


def get_stone_targets(user_id: str, stone_slug: str) -> list[dict]:
    """Retorna os Pokémon do usuário que podem evoluir com a pedra especificada.

    Inclui Pokémon da equipe e da coleção completa.
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT up.id, up.species_id, p1.name AS from_name,
                       e.to_species_id, p2.name AS to_name, p2.sprite_url,
                       up.level,
                       EXISTS(
                           SELECT 1 FROM user_team ut
                           WHERE ut.user_pokemon_id = up.id
                       ) AS in_team
                FROM user_pokemon up
                JOIN pokemon_species p1 ON up.species_id = p1.id
                JOIN pokemon_evolutions e
                     ON e.from_species_id = up.species_id
                    AND e.trigger_name    = 'use-item'
                    AND e.item_name       = %s
                JOIN pokemon_species p2 ON e.to_species_id = p2.id
                WHERE up.user_id = %s
                ORDER BY in_team DESC, up.id;
            """, (stone_slug, user_id))
            return [
                {
                    "user_pokemon_id": r[0],
                    "species_id":      r[1],
                    "from_name":       r[2],
                    "to_species_id":   r[3],
                    "to_name":         r[4],
                    "sprite_url":      r[5],
                    "level":           r[6],
                    "in_team":         r[7],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def evolve_with_stone(user_id: str, item_id: int, user_pokemon_id: int) -> tuple[bool, str, dict]:
    """Evolui um Pokémon usando uma pedra do inventário do usuário.

    Debita a pedra, atualiza species_id e recalcula stats em uma
    única transação.

    Returns:
        (success, message, evolution_data)
        evolution_data: {from_name, to_name, to_id, sprite_url} ou {}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Dados do item (pedra de evolução)
            cur.execute(
                "SELECT slug, name FROM shop_items WHERE id = %s AND category = 'stone';",
                (item_id,)
            )
            item_row = cur.fetchone()
            if not item_row:
                return False, "Item não encontrado ou não é uma pedra de evolução.", {}
            stone_slug, stone_name = item_row

            # Verifica ownership e inventário
            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, f"Você não possui {stone_name}.", {}

            # Verifica ownership do Pokémon e carrega nível atual
            cur.execute(
                "SELECT species_id, level FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            poke_row = cur.fetchone()
            if not poke_row:
                return False, "Pokémon não encontrado na sua coleção.", {}
            current_species, poke_level = poke_row

            # Verifica se esta pedra evolui este Pokémon
            cur.execute("""
                SELECT e.to_species_id, p1.name, p2.name, p2.sprite_url
                FROM pokemon_evolutions e
                JOIN pokemon_species p1 ON e.from_species_id = p1.id
                JOIN pokemon_species p2 ON e.to_species_id   = p2.id
                WHERE e.from_species_id = %s
                  AND e.trigger_name    = 'use-item'
                  AND e.item_name       = %s
                LIMIT 1;
            """, (current_species, stone_slug))
            evo_row = cur.fetchone()
            if not evo_row:
                return False, "Este Pokémon não evolui com essa pedra.", {}

            to_id, from_name, to_name, to_sprite = evo_row

            # Aplica evolução
            cur.execute(
                "UPDATE user_pokemon SET species_id = %s WHERE id = %s;",
                (to_id, user_pokemon_id)
            )
            # A evolução passa a usar o bloco de base stats da nova espécie.
            _recalc_stats_on_evolution(cur, user_pokemon_id)

            # Debita pedra do inventário
            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

        conn.commit()
        evo_data = {
            "from_name":  from_name,
            "to_name":    to_name,
            "to_id":      to_id,
            "sprite_url": to_sprite,
        }
        return True, f"{from_name} evoluiu para {to_name}!", evo_data

    except Exception as e:
        conn.rollback()
        return False, f"Erro ao evoluir: {e}", {}


# ──────────────────────────────────────────────────────────────────────────────
# Batalhas
# ──────────────────────────────────────────────────────────────────────────────

_MAX_BATTLES_PER_DAY = 3
_MAX_TURNS = 50
_WIN_COINS = 1
_WIN_XP = 30
_LOSS_XP = 10


def _pokemon_max_hp(stat_hp: int, level: int) -> int:
    # stat_hp já está pré-computado pela fórmula Pokémon escalada por nível
    # (floor(2 × base × level / 100) + level + 10 + vitaminas).
    # Retorna diretamente — sem re-escalar.
    return max(1, stat_hp)


# Type chart: _TYPE_CHART[move_type_id][defender_type_id] = multiplier (omitidos = 1.0)
_TYPE_CHART = {
    1:  {6: 0.5, 8: 0,   9: 0.5},
    2:  {1: 2,   3: 0.5, 4: 0.5, 6: 2,   7: 0.5, 8: 0,   9: 2,   14: 0.5, 15: 2,  17: 2,  18: 0.5},
    3:  {2: 2,   6: 0.5, 7: 2,   9: 0.5, 12: 2,  13: 0.5},
    4:  {4: 0.5, 5: 0.5, 6: 0.5, 8: 0.5, 9: 0,   12: 2,  18: 2},
    5:  {3: 0,   6: 2,   7: 0.5, 9: 2,   10: 2,  12: 0.5, 13: 0},
    6:  {2: 0.5, 3: 2,   5: 0.5, 7: 2,   9: 0.5, 10: 2,  15: 2},
    7:  {2: 0.5, 3: 0.5, 4: 0.5, 8: 0.5, 9: 0.5, 10: 0.5, 12: 2, 14: 2,  17: 2,  18: 0.5},
    8:  {1: 0,   8: 2,   14: 2,  17: 0.5},
    9:  {6: 2,   9: 0.5, 10: 0.5, 11: 0.5, 13: 0.5, 15: 2,  18: 2},
    10: {6: 0.5, 7: 2,   9: 2,   10: 0.5, 11: 0.5, 12: 2,  15: 2,  16: 0.5},
    11: {5: 2,   6: 2,   10: 2,  11: 0.5, 12: 0.5, 16: 0.5},
    12: {3: 0.5, 4: 0.5, 5: 2,   6: 2,   7: 0.5,  9: 0.5,  10: 0.5, 11: 2, 12: 0.5, 16: 0.5},
    13: {3: 2,   5: 0,   9: 0.5, 11: 2,  12: 0.5, 13: 0.5, 16: 0.5},
    14: {2: 2,   4: 2,   9: 0.5, 14: 0.5, 17: 0},
    15: {3: 2,   5: 2,   9: 0.5, 10: 0.5, 11: 0.5, 12: 2,  15: 0.5, 16: 2},
    16: {9: 0.5, 16: 2,  18: 0},
    17: {2: 0.5, 8: 2,   14: 2,  17: 0.5, 18: 0.5},
    18: {2: 2,   4: 0.5, 9: 0.5, 10: 0.5, 16: 2,  17: 2},
}

_CRIT_CHANCE = 1 / 24   # Gen 6+ (~4.2%)
_CRIT_MULT   = 1.5


def _type_effectiveness(move_type_id, defender_types: tuple) -> float:
    if not move_type_id:
        return 1.0
    chart = _TYPE_CHART.get(move_type_id, {})
    mult = 1.0
    for dt in defender_types:
        if dt:
            mult *= chart.get(dt, 1.0)
    return mult


def _calc_damage(atk_stat: int, def_stat: int, power: int, level: int,
                 move_type_id=None, attacker_types=(), defender_types=()) -> dict:
    """
    Fórmula oficial Pokémon com modificadores:
      base = ((2L/5+2) × Poder × A/D) / 50 + 2
      × STAB (1.5 se tipo do move == tipo do atacante)
      × Efetividade (0.25 / 0.5 / 1 / 2 / 4)
      × Crítico (1.5, chance 1/24)
      × Roll aleatório (0.85–1.0)
    """
    if not power:
        return {"damage": 0, "critical": False, "effectiveness": 1.0, "stab": False}

    stab = move_type_id in attacker_types if move_type_id else False
    effectiveness = _type_effectiveness(move_type_id, defender_types)
    critical = random.random() < _CRIT_CHANCE

    base = ((2 * level / 5 + 2) * power * (atk_stat / max(1, def_stat))) / 50 + 2
    dmg  = base
    dmg *= 1.5 if stab else 1.0
    dmg *= effectiveness
    dmg *= _CRIT_MULT if critical else 1.0
    dmg *= random.uniform(0.85, 1.0)

    return {
        "damage":        max(1, int(dmg)) if effectiveness > 0 else 0,
        "critical":      critical,
        "effectiveness": effectiveness,
        "stab":          stab,
    }


def _best_move(moves: list) -> dict:
    """Oponente usa o move de maior power disponível; fallback para Investida."""
    _tackle = {"name": "Investida", "power": 40, "damage_class": "physical", "id": None, "type_id": 1}
    if not moves:
        return _tackle
    pool = [m for m in moves if m["damage_class"] in ("physical", "special") and m["power"]]
    if not pool:
        return _tackle
    return max(pool, key=lambda m: m["power"])


def get_battle_opponents(user_id: str) -> list:
    """Retorna outros usuários que têm Pokémon no slot 1, com dados do Pokémon."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT up.username, ut.user_id, up2.level, ps.name, ps.sprite_url
        FROM user_team ut
        JOIN user_profiles up  ON ut.user_id = up.id
        JOIN user_pokemon up2  ON ut.user_pokemon_id = up2.id
        JOIN pokemon_species ps ON up2.species_id = ps.id
        WHERE ut.slot = 1
          AND ut.user_id != %s
        ORDER BY up.username;
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    return [
        {"username": r[0], "user_id": str(r[1]), "level": r[2],
         "pokemon_name": r[3], "sprite_url": r[4]}
        for r in rows
    ]


def get_daily_battle_count(user_id: str) -> int:
    """Quantidade de batalhas iniciadas hoje (como desafiante)."""
    conn = get_connection()
    cur = conn.cursor()
    today = _today_brt()
    cur.execute("""
        SELECT COUNT(*) FROM user_battles
        WHERE challenger_id = %s
          AND battled_at AT TIME ZONE 'America/Sao_Paulo' >= %s::date
          AND battled_at AT TIME ZONE 'America/Sao_Paulo' <  %s::date + INTERVAL '1 day';
    """, (user_id, today, today))
    count = cur.fetchone()[0]
    cur.close()
    return count


def start_battle(challenger_id: str, opponent_id: str) -> dict:
    """
    Inicia batalha interativa: verifica limite diário, carrega pokémon e moves.
    Retorna estado inicial da batalha para ser mantido em session_state.
    Não persiste nada no banco — apenas finalize_battle() persiste.
    """
    if get_daily_battle_count(challenger_id) >= _MAX_BATTLES_PER_DAY:
        return {"error": f"Limite de {_MAX_BATTLES_PER_DAY} batalhas por dia atingido."}

    conn = get_connection()
    cur = conn.cursor()
    try:
        if _audit_and_sync_user_team_stats(cur, challenger_id):
            conn.commit()
        if opponent_id != challenger_id and _audit_and_sync_user_team_stats(cur, opponent_id):
            conn.commit()

        def _load_fighter(uid):
            cur.execute("""
                SELECT up.id, up.level,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       ps.name, ps.sprite_url, ps.type1_id, ps.type2_id
                FROM user_team ut
                JOIN user_pokemon up  ON ut.user_pokemon_id = up.id
                JOIN pokemon_species ps ON up.species_id = ps.id
                WHERE ut.user_id = %s AND ut.slot = 1;
            """, (uid,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0], "level": row[1],
                "stat_hp": row[2], "stat_attack": row[3], "stat_defense": row[4],
                "stat_sp_attack": row[5], "stat_sp_defense": row[6], "stat_speed": row[7],
                "name": row[8], "sprite_url": row[9],
                "type1_id": row[10], "type2_id": row[11],
            }

        def _load_moves(pokemon_id):
            cur.execute("""
                SELECT pm.name, pm.power, pm.damage_class, pm.id, pm.type_id
                FROM user_pokemon_moves upm
                JOIN pokemon_moves pm ON upm.move_id = pm.id
                WHERE upm.user_pokemon_id = %s
                ORDER BY upm.slot;
            """, (pokemon_id,))
            return [{"name": r[0], "power": r[1] or 0, "damage_class": r[2],
                     "id": r[3], "type_id": r[4]}
                    for r in cur.fetchall()]

        ch = _load_fighter(challenger_id)
        op = _load_fighter(opponent_id)
        if not ch:
            return {"error": "Você não tem Pokémon no slot 1 da equipe."}
        if not op:
            return {"error": "Oponente não tem Pokémon na equipe."}

        ch_moves = _load_moves(ch["id"])
        op_moves = _load_moves(op["id"])
        _tackle = {"name": "Investida", "power": 40, "damage_class": "physical", "id": None, "type_id": 1}
        if not any(m["power"] for m in ch_moves):
            ch_moves = [_tackle]
        if not any(m["power"] for m in op_moves):
            op_moves = [_tackle]

        ch_max_hp = _pokemon_max_hp(ch["stat_hp"], ch["level"])
        op_max_hp = _pokemon_max_hp(op["stat_hp"], op["level"])

        return {
            "challenger_id": challenger_id,
            "opponent_id":   opponent_id,
            "ch":  {**ch, "max_hp": ch_max_hp, "hp": ch_max_hp, "moves": ch_moves},
            "op":  {**op, "max_hp": op_max_hp, "hp": op_max_hp, "moves": op_moves},
            "turns":    [],
            "turn_num": 0,
            "finished": False,
            "result":   None,
            "winner_id": None,
        }
    finally:
        cur.close()


def finalize_battle(state: dict) -> dict:
    """
    Persiste batalha concluída no banco e concede XP/moedas.
    Recebe o state retornado por start_battle (com turns preenchidos).
    """
    challenger_id = state["challenger_id"]
    opponent_id   = state["opponent_id"]
    ch = state["ch"]
    op = state["op"]
    result    = state["result"]
    winner_id = state["winner_id"]
    turns     = state["turns"]

    ch_xp  = _WIN_XP if result == "challenger_win" else _LOSS_XP
    op_xp  = _WIN_XP if result == "opponent_win"   else _LOSS_XP
    coins  = _WIN_COINS if winner_id else 0

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_battles
                (challenger_id, opponent_id, challenger_pokemon_id, opponent_pokemon_id,
                 winner_id, result, challenger_xp_earned, opponent_xp_earned,
                 coins_earned, turn_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (challenger_id, opponent_id, ch["id"], op["id"],
              winner_id, result, ch_xp, op_xp, coins, len(turns)))
        battle_id = cur.fetchone()[0]

        for t in turns:
            cur.execute("""
                INSERT INTO user_battle_turns
                    (battle_id, turn_number, attacker_pokemon_id,
                     move_name, move_power, damage,
                     challenger_hp_remaining, opponent_hp_remaining)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (battle_id, t["turn"], t["attacker_id"],
                  t["move_name"], t["move_power"], t["damage"],
                  t["ch_hp"], t["op_hp"]))

        if winner_id:
            cur.execute(
                "UPDATE user_profiles SET coins = coins + %s WHERE id = %s;",
                (coins, winner_id)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()

    ch_xp_result = award_xp(ch["id"], ch_xp, "battle")
    op_xp_result = award_xp(op["id"], op_xp, "battle")

    return {
        "battle_id":    battle_id,
        "result":       result,
        "winner_id":    winner_id,
        "ch_xp_result": ch_xp_result,
        "op_xp_result": op_xp_result,
        "coins_earned": coins,
        "ch_xp":        ch_xp,
        "op_xp":        op_xp,
    }


def get_battle_history(user_id: str, limit: int = 20) -> list:
    """Retorna as últimas batalhas em que o usuário participou."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            b.id, b.result, b.winner_id,
            b.challenger_id, pc.username AS challenger_name,
            b.opponent_id,  po.username AS opponent_name,
            ps_ch.name AS ch_pokemon, ps_op.name AS op_pokemon,
            b.challenger_xp_earned, b.opponent_xp_earned,
            b.coins_earned, b.turn_count, b.battled_at
        FROM user_battles b
        JOIN user_profiles pc  ON b.challenger_id = pc.id
        JOIN user_profiles po  ON b.opponent_id   = po.id
        JOIN user_pokemon up_ch ON b.challenger_pokemon_id = up_ch.id
        JOIN user_pokemon up_op ON b.opponent_pokemon_id   = up_op.id
        JOIN pokemon_species ps_ch ON up_ch.species_id = ps_ch.id
        JOIN pokemon_species ps_op ON up_op.species_id = ps_op.id
        WHERE b.challenger_id = %s OR b.opponent_id = %s
        ORDER BY b.battled_at DESC
        LIMIT %s;
    """, (user_id, user_id, limit))
    rows = cur.fetchall()
    cur.close()
    cols = ["id", "result", "winner_id",
            "challenger_id", "challenger_name",
            "opponent_id", "opponent_name",
            "ch_pokemon", "op_pokemon",
            "ch_xp", "op_xp", "coins", "turn_count", "battled_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_battle_detail(battle_id: int) -> list:
    """Retorna todos os turnos de uma batalha."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT turn_number, attacker_pokemon_id, move_name, move_power,
               damage, challenger_hp_remaining, opponent_hp_remaining
        FROM user_battle_turns
        WHERE battle_id = %s
        ORDER BY turn_number, id;
    """, (battle_id,))
    rows = cur.fetchall()
    cur.close()
    cols = ["turn", "attacker_id", "move_name", "move_power",
            "damage", "ch_hp", "op_hp"]
    return [dict(zip(cols, r)) for r in rows]


# ── Exercícios e treino ────────────────────────────────────────────────────────

_EXERCISE_XP_DAILY_CAP = 300
_FIRST_WORKOUT_BONUS_XP = 50
_EXERCISE_REP_XP_DIVISOR = 2
_EXERCISE_WEIGHT_XP_DIVISOR = 20
_MAX_DAILY_SPAWNS = 1
_EXERCISE_SPAWN_CHANCE = 0.25

# body_parts (campo de exercises) → slugs de tipo Pokémon para spawn temático.
# Cada body_part pode mapear para múltiplos tipos; o spawn usa a lista agregada
# de todos os exercícios da sessão, priorizando os tipos mais frequentes.
_BODY_PART_TYPES: dict[str, list[str]] = {
    "Peitoral":            ["fighting", "normal"],
    "Braços":              ["fighting", "poison"],
    "Bíceps":              ["fighting", "poison"],
    "Tríceps":             ["fighting", "poison"],
    "Antebraços":          ["normal",   "fighting"],
    "Costas":              ["dark",     "flying"],
    "Costas Superiores":   ["dark",     "flying"],
    "Latíssimo":           ["dark",     "flying"],
    "Coluna":              ["rock",     "ground"],
    "Ombros":              ["flying",   "psychic"],
    "Deltoides":           ["flying",   "psychic"],
    "Elevador da Escápula":["flying",   "steel"],
    "Trapézio":            ["rock",     "normal"],
    "Coxas":               ["ground",   "fighting"],
    "Pernas":              ["ground",   "rock"],
    "Cintura":             ["steel",    "rock"],
    "Pescoço":             ["rock",     "normal"],
    "Cardio":              ["water",    "electric"],
}


def _ranked_spawn_types(exercises: list[dict], bp_map: dict[int, list[str]]) -> list[str]:
    """Returns type slugs ordered by how frequently they appear across the session's body parts."""
    type_counts: dict[str, int] = {}
    for ex in exercises:
        for bp in bp_map.get(ex["exercise_id"], []):
            for t in _BODY_PART_TYPES.get(bp, []):
                type_counts[t] = type_counts.get(t, 0) + 1
    return sorted(type_counts, key=lambda t: type_counts[t], reverse=True)


@st.cache_data(ttl=3600)
def get_muscle_groups() -> list[dict]:
    """Grupos musculares com imagem anatômica."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("SELECT id, name, image_url FROM muscle_groups ORDER BY name;")
            return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in cur.fetchall()]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_exercises(body_part: str | None = None) -> list[dict]:
    """Catálogo de exercícios, opcionalmente filtrado por body_part."""
    try:
        with get_connection().cursor() as cur:
            if body_part:
                cur.execute("""
                    SELECT id, name, name_pt, target_muscles, body_parts, equipments, gif_url
                    FROM exercises
                    WHERE %s = ANY(body_parts)
                    ORDER BY COALESCE(name_pt, name);
                """, (body_part,))
            else:
                cur.execute("""
                    SELECT id, name, name_pt, target_muscles, body_parts, equipments, gif_url
                    FROM exercises
                    ORDER BY COALESCE(name_pt, name);
                """)
            return [
                {
                    "id": r[0], "name": r[1], "name_pt": r[2],
                    "target_muscles": r[3], "body_parts": r[4],
                    "equipments": r[5], "gif_url": r[6],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_distinct_body_parts() -> list[str]:
    """Lista de body_parts distintos presentes nos exercícios."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT DISTINCT unnest(body_parts) AS bp
                FROM exercises
                ORDER BY bp;
            """)
            return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def get_workout_days(user_id: str) -> list[dict]:
    """Dias do plano de treino ativo do usuário com contagem de exercícios."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT wd.id, wd.name, wd.day_order,
                       ws.name AS sheet_name,
                       COUNT(wde.id) AS exercise_count
                FROM workout_sheets ws
                JOIN workout_days wd ON wd.sheet_id = ws.id
                LEFT JOIN workout_day_exercises wde ON wde.day_id = wd.id
                WHERE ws.user_id = %s AND ws.is_active = TRUE
                GROUP BY wd.id, wd.name, wd.day_order, ws.name
                ORDER BY wd.day_order;
            """, (user_id,))
            return [
                {
                    "id": str(r[0]), "name": r[1], "day_order": r[2],
                    "sheet_name": r[3], "exercise_count": r[4],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def get_day_exercises(day_id: str) -> list[dict]:
    """Exercícios prescritos para um dia do plano de treino."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT e.id, COALESCE(e.name_pt, e.name) AS display_name,
                       e.target_muscles, e.body_parts, e.gif_url,
                       wde.sets, wde.reps, wde.rest_seconds, wde.notes,
                       wde.exercise_order
                FROM workout_day_exercises wde
                JOIN exercises e ON e.id = wde.exercise_id
                WHERE wde.day_id = %s
                ORDER BY wde.exercise_order;
            """, (day_id,))
            return [
                {
                    "id": r[0], "name": r[1],
                    "target_muscles": r[2], "body_parts": r[3], "gif_url": r[4],
                    "prescribed_sets": r[5], "prescribed_reps": r[6],
                    "rest_seconds": r[7], "notes": r[8], "order": r[9],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def get_daily_xp_from_exercise(user_id: str) -> int:
    """XP ganho por exercício hoje (usado para verificar o cap diário)."""
    today = _today_brt()
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0)
                FROM workout_logs
                WHERE user_id = %s
                  AND completed_at AT TIME ZONE 'America/Sao_Paulo' >= %s::date
                  AND completed_at AT TIME ZONE 'America/Sao_Paulo' <  %s::date + INTERVAL '1 day';
            """, (user_id, today, today))
            return cur.fetchone()[0]
    except Exception:
        return 0


def get_workout_streak(user_id: str) -> int:
    """Dias consecutivos com pelo menos um treino registrado."""
    today = _today_brt()
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    (completed_at AT TIME ZONE 'America/Sao_Paulo')::date AS d
                FROM workout_logs
                WHERE user_id = %s
                ORDER BY d DESC;
            """, (user_id,))
            days = [r[0] for r in cur.fetchall()]
        if not days:
            return 0
        streak = 0
        check = today
        for d in days:
            if d == check:
                streak += 1
                check -= datetime.timedelta(days=1)
            elif d < check:
                break
        return streak
    except Exception:
        return 0


def get_workout_history(user_id: str, limit: int = 10) -> list[dict]:
    """Últimas sessões de treino com contagem de exercícios e XP ganho."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT wl.id, wl.completed_at, wl.xp_earned,
                       wl.spawned_species_id, wl.duration_minutes,
                       wd.name AS day_name,
                       COUNT(el.id) AS exercise_count
                FROM workout_logs wl
                LEFT JOIN workout_days wd ON wl.day_id = wd.id
                LEFT JOIN exercise_logs el ON el.workout_log_id = wl.id
                WHERE wl.user_id = %s
                GROUP BY wl.id, wl.completed_at, wl.xp_earned,
                         wl.spawned_species_id, wl.duration_minutes, wd.name
                ORDER BY wl.completed_at DESC
                LIMIT %s;
            """, (user_id, limit))
            return [
                {
                    "id": str(r[0]), "completed_at": r[1], "xp_earned": r[2],
                    "spawned_species_id": r[3], "duration_minutes": r[4],
                    "day_name": r[5], "exercise_count": r[6],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def _calc_exercise_xp(exercises: list[dict]) -> int:
    """XP bruto de uma sessão: CEIL(reps / 2) + FLOOR(weight_kg / 20) por set.

    A curva foi reduzida para que um treino completo avance o Pokémon de forma
    consistente sem estourar o cap diário em poucos exercícios.
    """
    total = 0
    for ex in exercises:
        for s in ex.get("sets_data", []):
            reps   = int(s.get("reps") or 0)
            weight = float(s.get("weight") or 0)
            rep_xp = (reps + (_EXERCISE_REP_XP_DIVISOR - 1)) // _EXERCISE_REP_XP_DIVISOR
            weight_xp = int(weight / _EXERCISE_WEIGHT_XP_DIVISOR)
            total += rep_xp + weight_xp
    return max(0, total)


def _shiny_roll(streak: int) -> bool:
    """Retorna True com probabilidade crescente baseada no streak."""
    if streak >= 60:
        odds = 8
    elif streak >= 30:
        odds = 16
    elif streak >= 15:
        odds = 32
    elif streak >= 7:
        odds = 64
    else:
        odds = 128
    return random.random() < (1 / odds)


# Weighted spawn tiers — legendary/mythical are excluded via is_spawnable=FALSE in DB.
# Weights are relative; uncommon ~3× rarer than common, rare ~10× rarer.
_SPAWN_TIER_WEIGHTS: dict[str, int] = {
    "common":   60,
    "uncommon": 30,
    "rare":      9,
}


def _pick_spawn_species(
    cur,
    user_id: str,
    type_slug: str | None = None,
) -> int | None:
    """Picks a spawnable species_id using weighted tier sampling.

    Tries typed filter first (if type_slug given), falls back to any type.
    Returns species_id or None if pool exhausted.
    """
    tiers = list(_SPAWN_TIER_WEIGHTS.keys())
    weights = [_SPAWN_TIER_WEIGHTS[t] for t in tiers]

    # Shuffle tier order by weighted random pick (sample without replacement)
    tier_order: list[str] = random.choices(tiers, weights=weights, k=len(tiers))
    # Deduplicate while preserving weighted order
    seen: set[str] = set()
    tier_order = [t for t in tier_order if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]

    def _query(tier: str, with_type: bool) -> int | None:
        base_filter = """
            ps.is_spawnable = TRUE
            AND ps.rarity_tier = %s
            AND ps.id NOT IN (
                SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
            )
        """
        if with_type:
            cur.execute(f"""
                SELECT ps.id
                FROM pokemon_species ps
                JOIN pokemon_types pt1 ON ps.type1_id = pt1.id
                WHERE {base_filter}
                  AND (pt1.slug = %s
                       OR EXISTS (
                           SELECT 1 FROM pokemon_types pt2
                           WHERE pt2.id = ps.type2_id AND pt2.slug = %s
                       ))
                ORDER BY RANDOM() LIMIT 1;
            """, (tier, user_id, type_slug, type_slug))
        else:
            cur.execute(f"""
                SELECT ps.id FROM pokemon_species ps
                WHERE {base_filter}
                ORDER BY RANDOM() LIMIT 1;
            """, (tier, user_id))
        row = cur.fetchone()
        return row[0] if row else None

    # Try each tier in weighted order, typed first then untyped fallback
    for tier in tier_order:
        if type_slug:
            sid = _query(tier, with_type=True)
            if sid:
                return sid
        sid = _query(tier, with_type=False)
        if sid:
            return sid

    return None


def _spawn_multi_typed(cur, user_id: str, candidate_types: list[str], is_shiny: bool = False):
    """Tries candidate_types in order, falls back to untyped. Returns (species_id, info) or (None, None)."""
    for type_slug in candidate_types:
        sid = _pick_spawn_species(cur, user_id, type_slug)
        if sid:
            break
    else:
        sid = _pick_spawn_species(cur, user_id, None)

    if sid is None:
        return None, None

    up_id = _insert_user_pokemon(cur, user_id, sid, level=5, xp=0, is_shiny=is_shiny)
    if up_id is None:
        raise ValueError("Espécie sorteada não encontrada para calcular stats.")

    cur.execute("SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;", (user_id,))
    used = {r[0] for r in cur.fetchall()}
    free = next((s for s in range(1, 7) if s not in used), None)
    if free:
        cur.execute(
            "INSERT INTO user_team (user_id, slot, user_pokemon_id) VALUES (%s, %s, %s);",
            (user_id, free, up_id)
        )

    cur.execute("""
        SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url, t.name AS type1
        FROM pokemon_species p
        LEFT JOIN pokemon_types t ON p.type1_id = t.id
        WHERE p.id = %s;
    """, (sid,))
    pdata = cur.fetchone()
    sprite = (pdata[3] if is_shiny and pdata[3] else pdata[2])
    return sid, {"id": pdata[0], "name": pdata[1], "sprite_url": sprite,
                 "type1": pdata[4], "is_shiny": is_shiny}


def _spawn_typed(cur, user_id: str, type_slug: str | None = None, is_shiny: bool = False):
    """Captura um Pokémon não capturado (tipo opcional) dentro de uma transação aberta.

    Tenta primeiro com filtro de tipo; se não encontrar, usa qualquer espécie.
    Retorna (species_id, {id, name, sprite_url, type1, is_shiny}) ou (None, None).
    """
    species_id = _pick_spawn_species(cur, user_id, type_slug)
    if species_id is None:
        return None, None

    up_id = _insert_user_pokemon(
        cur, user_id, species_id, level=5, xp=0, is_shiny=is_shiny
    )
    if up_id is None:
        raise ValueError("Espécie sorteada não encontrada para calcular stats.")

    cur.execute("SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;", (user_id,))
    used = {r[0] for r in cur.fetchall()}
    free = next((s for s in range(1, 7) if s not in used), None)
    if free:
        cur.execute(
            "INSERT INTO user_team (user_id, slot, user_pokemon_id) VALUES (%s, %s, %s);",
            (user_id, free, up_id)
        )

    cur.execute("""
        SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url, t.name AS type1
        FROM pokemon_species p
        LEFT JOIN pokemon_types t ON p.type1_id = t.id
        WHERE p.id = %s;
    """, (species_id,))
    pdata = cur.fetchone()
    sprite = (pdata[3] if is_shiny and pdata[3] else pdata[2])
    return species_id, {
        "id": pdata[0], "name": pdata[1], "sprite_url": sprite,
        "type1": pdata[4], "is_shiny": is_shiny,
    }


_PR_XP_BONUS       = 50   # XP awarded per personal record
_PR_MAX_PER_SESSION = 3   # cap on how many PR bonuses can fire in one session

# Egg system (Release 2A)
_EGG_MILESTONES: dict[int, str] = {25: "uncommon", 50: "rare", 100: "rare"}
_EGG_WORKOUTS_TO_HATCH: dict[str, int] = {"common": 5, "uncommon": 8, "rare": 12}


def _get_exercise_bests(cur, user_id: str, exercise_ids: list[int]) -> dict[int, tuple[float, int]]:
    """Returns {exercise_id: (best_weight, best_reps_at_best_weight)} from historical logs.

    Only considers sessions before the current one (caller inserts before comparing).
    The tuple represents the user's personal best: highest weight ever lifted for that
    exercise, and the highest rep count achieved at that exact weight.
    """
    if not exercise_ids:
        return {}
    cur.execute("""
        SELECT el.exercise_id,
               MAX((s->>'weight')::float)                       AS best_weight,
               MAX((s->>'reps')::int)                           AS best_reps
        FROM exercise_logs el
        JOIN workout_logs wl ON wl.id = el.workout_log_id
        JOIN LATERAL jsonb_array_elements(el.sets_data) AS s ON true
        WHERE wl.user_id = %s
          AND el.exercise_id = ANY(%s)
          AND (s->>'weight') IS NOT NULL
          AND (s->>'reps') IS NOT NULL
        GROUP BY el.exercise_id, (s->>'weight')::float
        ORDER BY el.exercise_id, best_weight DESC;
    """, (user_id, exercise_ids))
    # For each exercise keep the row with the highest weight (first row due to ORDER BY)
    bests: dict[int, tuple[float, int]] = {}
    for eid, bw, br in cur.fetchall():
        if eid not in bests:
            bests[eid] = (float(bw), int(br))
    return bests


def _detect_prs(
    exercises: list[dict],
    historical_bests: dict[int, tuple[float, int]],
    exercise_names: dict[int, str],
) -> list[dict]:
    """Compares current session sets against historical bests.

    Returns a list of PR dicts (at most one per exercise):
      {exercise_id, exercise_name, old_weight, new_weight, new_reps}

    PR rules:
    - Primary: any set's weight exceeds the previous best weight.
    - Tie-break: same weight, more reps than previous best at that weight.
    """
    prs: list[dict] = []
    seen: set[int] = set()
    for ex in exercises:
        eid = ex["exercise_id"]
        if eid in seen:
            continue
        sets_data = ex.get("sets_data") or []
        if not sets_data:
            continue
        cur_best_w = max((float(s.get("weight") or 0) for s in sets_data), default=0.0)
        cur_best_r = max(
            (int(s.get("reps") or 0) for s in sets_data if float(s.get("weight") or 0) == cur_best_w),
            default=0,
        )
        if cur_best_w <= 0:
            continue

        old_w, old_r = historical_bests.get(eid, (0.0, 0))

        is_pr = (cur_best_w > old_w) or (cur_best_w == old_w and cur_best_r > old_r)
        if is_pr:
            prs.append({
                "exercise_id":   eid,
                "exercise_name": exercise_names.get(eid, f"Exercício #{eid}"),
                "old_weight":    old_w,
                "new_weight":    cur_best_w,
                "new_reps":      cur_best_r,
            })
            seen.add(eid)
    return prs


def get_user_eggs(user_id: str) -> list[dict]:
    """Returns all pending (unhatched) eggs for a user, oldest first.

    Includes species_id/name/sprite_url for spoiler-toggle in ovos.py.
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ue.id, ue.rarity, ue.workouts_to_hatch, ue.workouts_done,
                       ue.received_at, ue.species_id,
                       ps.name AS species_name, ps.sprite_url
                FROM user_eggs ue
                LEFT JOIN pokemon_species ps ON ps.id = ue.species_id
                WHERE ue.user_id = %s AND ue.hatched_at IS NULL
                ORDER BY ue.received_at;
            """, (user_id,))
            return [
                {
                    "id": r[0], "rarity": r[1],
                    "workouts_to_hatch": r[2], "workouts_done": r[3],
                    "received_at": r[4],
                    "species_id": r[5],
                    "species_name": r[6],
                    "sprite_url": r[7],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def _pick_egg_species(cur, user_id: str, rarity: str) -> int | None:
    """Picks a random spawnable species the user doesn't own yet, matching rarity tier."""
    cur.execute("""
        SELECT ps.id FROM pokemon_species ps
        WHERE ps.is_spawnable = TRUE
          AND ps.rarity_tier = %s
          AND ps.id NOT IN (
              SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
          )
        ORDER BY RANDOM() LIMIT 1;
    """, (rarity, user_id))
    row = cur.fetchone()
    return row[0] if row else None


def _grant_eggs_if_milestone(cur, user_id: str, workout_count: int) -> list[dict]:
    """Grants one egg if workout_count is exactly a milestone. Returns list of granted egg dicts."""
    rarity = _EGG_MILESTONES.get(workout_count)
    if not rarity:
        return []
    species_id = _pick_egg_species(cur, user_id, rarity)
    if species_id is None:
        species_id = _pick_egg_species(cur, user_id, "common")
    if species_id is None:
        return []
    workouts_to_hatch = _EGG_WORKOUTS_TO_HATCH[rarity]
    cur.execute("""
        INSERT INTO user_eggs (user_id, species_id, rarity, workouts_to_hatch)
        VALUES (%s, %s, %s, %s);
    """, (user_id, species_id, rarity, workouts_to_hatch))
    return [{"rarity": rarity, "workouts_to_hatch": workouts_to_hatch}]


def _advance_and_hatch_eggs(cur, user_id: str) -> list[dict]:
    """Increments workouts_done for all pending eggs; hatches any that are ready.

    Returns list of hatched egg dicts: {species_id, name, sprite_url, type1, rarity}.
    """
    cur.execute("""
        UPDATE user_eggs
        SET workouts_done = workouts_done + 1
        WHERE user_id = %s AND hatched_at IS NULL
        RETURNING id, species_id, rarity, workouts_done, workouts_to_hatch;
    """, (user_id,))
    updated = cur.fetchall()

    hatched: list[dict] = []
    for egg_id, species_id, rarity, done, to_hatch in updated:
        if done < to_hatch:
            continue
        up_id = _insert_user_pokemon(cur, user_id, species_id, level=5, xp=0, is_shiny=False)
        if up_id is None:
            continue
        cur.execute("SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;", (user_id,))
        used = {r[0] for r in cur.fetchall()}
        free = next((s for s in range(1, 7) if s not in used), None)
        if free:
            cur.execute(
                "INSERT INTO user_team (user_id, slot, user_pokemon_id) VALUES (%s, %s, %s);",
                (user_id, free, up_id)
            )
        cur.execute("UPDATE user_eggs SET hatched_at = now() WHERE id = %s;", (egg_id,))
        cur.execute("""
            SELECT ps.name, ps.sprite_url, pt.name AS type1
            FROM pokemon_species ps
            LEFT JOIN pokemon_types pt ON pt.id = ps.type1_id
            WHERE ps.id = %s;
        """, (species_id,))
        row = cur.fetchone()
        if row:
            hatched.append({
                "species_id": species_id,
                "name": row[0],
                "sprite_url": row[1],
                "type1": row[2],
                "rarity": rarity,
            })
    return hatched


def _get_slot1_ability(user_id: str) -> str | None:
    """Returns the ability_slug of the Pokémon in slot 1, or None."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ps.ability_slug
                FROM user_team ut
                JOIN user_pokemon up ON up.id = ut.user_pokemon_id
                JOIN pokemon_species ps ON ps.id = up.species_id
                WHERE ut.user_id = %s AND ut.slot = 1;
            """, (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def do_exercise_event(
    user_id: str,
    exercises: list[dict],
    day_id: str | None = None,
) -> dict:
    """Registra uma sessão de treino e concede XP ao Pokémon do slot 1.

    Args:
        user_id:   UUID do usuário (deve existir em auth.users / user_profiles).
        exercises: [{"exercise_id": int,
                     "sets_data":   [{"reps": int, "weight": float}],
                     "notes":       str | None}]
        day_id:    UUID do workout_day prescrito (None = treino livre).

    Returns:
        {xp_earned, capped, spawn_rolled, spawned, xp_result, error}
    """
    import json as _json

    result = {
        "xp_earned":    0,
        "capped":       False,
        "spawn_rolled": False,
        "spawned":      [],
        "spawn_context": None,
        "xp_result":    None,
        "milestone":    None,
        "milestone_xp": 0,
        "streak":       0,
        "prs":          [],
        "eggs_granted": [],
        "eggs_hatched": [],
        "ability_effects": None,
        "error":        None,
    }

    if not exercises:
        result["error"] = "Nenhum exercício informado."
        return result

    from utils.abilities import apply_blaze as _apply_blaze
    slot1_ability = _get_slot1_ability(user_id)
    _abilfx: dict = {}

    raw_xp = _calc_exercise_xp(exercises)
    # Release 3A — blaze boosts XP on high-intensity sessions before cap calculation
    if slot1_ability == "blaze" and raw_xp >= 200:
        boosted = _apply_blaze(raw_xp)
        _abilfx["blaze_xp_before"] = raw_xp
        _abilfx["blaze_xp_after"] = boosted
        raw_xp = boosted

    if raw_xp <= 0:
        result["error"] = "Nenhuma série registrada."
        return result

    already_today = get_daily_xp_from_exercise(user_id)
    remaining     = max(0, _EXERCISE_XP_DAILY_CAP - already_today)
    xp_to_award   = min(raw_xp, remaining)

    if xp_to_award < raw_xp:
        result["capped"] = True

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Primeiro treino? (antes do INSERT)
            cur.execute("SELECT COUNT(*) FROM workout_logs WHERE user_id = %s;", (user_id,))
            _pre_insert_count = cur.fetchone()[0]
            is_first_workout = _pre_insert_count == 0

            # Busca body_parts e nomes dos exercícios (spawn affinity + PR names)
            ex_ids = [ex["exercise_id"] for ex in exercises]
            cur.execute(
                "SELECT id, body_parts, COALESCE(name_pt, name) FROM exercises WHERE id = ANY(%s);",
                (ex_ids,)
            )
            ex_rows = cur.fetchall()
            bp_map       = {r[0]: (r[1] or []) for r in ex_rows}
            ex_name_map  = {r[0]: r[2] for r in ex_rows}

            # Session-wide types used only for milestone forced spawns
            candidate_types = _ranked_spawn_types(exercises, bp_map)
            if slot1_ability == "pressure" and candidate_types:
                candidate_types = [candidate_types[0]]
                _abilfx["pressure_type"] = candidate_types[0]

            # Detecta PRs antes do INSERT (histórico exclui sessão atual)
            historical_bests = _get_exercise_bests(cur, user_id, ex_ids)

            # Insere sessão
            cur.execute("""
                INSERT INTO workout_logs (user_id, day_id, xp_earned)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (user_id, day_id, xp_to_award))
            wl_id = cur.fetchone()[0]

            # Insere logs por exercício
            for ex in exercises:
                cur.execute("""
                    INSERT INTO exercise_logs (workout_log_id, exercise_id, sets_data, notes)
                    VALUES (%s, %s, %s::jsonb, %s);
                """, (wl_id, ex["exercise_id"],
                      _json.dumps(ex.get("sets_data", [])),
                      ex.get("notes")))

            # Streak pós-insert (inclui a sessão recém inserida)
            cur.execute("""
                SELECT DISTINCT (completed_at AT TIME ZONE 'America/Sao_Paulo')::date AS d
                FROM workout_logs WHERE user_id = %s ORDER BY d DESC;
            """, (user_id,))
            streak_days = [r[0] for r in cur.fetchall()]
            new_streak = 0
            check_day = _today_brt()
            for d in streak_days:
                if d == check_day:
                    new_streak += 1
                    check_day -= datetime.timedelta(days=1)
                elif d < check_day:
                    break
            result["streak"] = new_streak

            # Milestone
            force_spawn = False
            force_shiny = False
            if is_first_workout:
                result["milestone"] = "first_workout"
            if new_streak >= 30 and new_streak % 30 == 0:
                force_spawn = True
                force_shiny = True
                if result["milestone"] != "first_workout":
                    result["milestone"] = f"streak_{new_streak}"
            elif new_streak >= 7 and new_streak % 7 == 0:
                force_spawn = True
                if result["milestone"] != "first_workout":
                    result["milestone"] = f"streak_{new_streak}"

            # ── Per-exercise spawn with daily cap ─────────────────────────────
            # Count spawns granted in earlier sessions today.
            # Each workout_log records at most one spawned_species_id, so this
            # is a slight undercount when a prior session yielded multiple spawns,
            # making the cap mildly lenient on multi-session days.
            cur.execute("""
                SELECT COUNT(*) FROM workout_logs
                WHERE user_id = %s
                  AND (completed_at AT TIME ZONE 'America/Sao_Paulo')::date
                      = (NOW() AT TIME ZONE 'America/Sao_Paulo')::date
                  AND id != %s
                  AND spawned_species_id IS NOT NULL;
            """, (user_id, wl_id))
            prior_spawns = int(cur.fetchone()[0])
            spawn_budget = max(0, _MAX_DAILY_SPAWNS - prior_spawns)
            session_spawns = 0

            # Milestone forced spawn consumes a budget slot first
            if force_spawn and spawn_budget > 0:
                try:
                    roll_shiny = force_shiny or _shiny_roll(new_streak)
                    species_id, spawn_info = _spawn_multi_typed(
                        cur, user_id, candidate_types, is_shiny=roll_shiny
                    )
                    if species_id:
                        result["spawn_rolled"] = True
                        result["spawned"].append(spawn_info)
                        session_spawns += 1
                        cur.execute(
                            "UPDATE workout_logs SET spawned_species_id = %s WHERE id = %s;",
                            (species_id, wl_id)
                        )
                except Exception:
                    pass

            # Single session-level spawn roll (25% chance for the whole session)
            if session_spawns < spawn_budget and random.random() < _EXERCISE_SPAWN_CHANCE:
                session_types = candidate_types
                if slot1_ability == "pressure" and session_types:
                    session_types = [session_types[0]]
                try:
                    roll_shiny = _shiny_roll(new_streak)
                    species_id, spawn_info = _spawn_multi_typed(
                        cur, user_id, session_types, is_shiny=roll_shiny
                    )
                    # compound-eyes: one reroll on failure
                    if species_id is None and slot1_ability == "compound-eyes":
                        species_id, spawn_info = _spawn_multi_typed(
                            cur, user_id, session_types, is_shiny=roll_shiny
                        )
                        if species_id:
                            _abilfx["compound_eyes_rerolled"] = True
                    if species_id:
                        result["spawn_rolled"] = True
                        result["spawned"].append(spawn_info)
                        session_spawns += 1
                        if not force_spawn:
                            cur.execute(
                                "UPDATE workout_logs SET spawned_species_id = %s WHERE id = %s;",
                                (species_id, wl_id)
                            )
                except Exception:
                    pass

            # Release 2A — egg system: grant milestone eggs + advance all pending
            _post_workout_count = _pre_insert_count + 1
            try:
                result["eggs_granted"] = _grant_eggs_if_milestone(cur, user_id, _post_workout_count)
                result["eggs_hatched"] = _advance_and_hatch_eggs(cur, user_id)
            except Exception:
                result["eggs_granted"] = []
                result["eggs_hatched"] = []

        conn.commit()
        result["xp_earned"] = xp_to_award

        # Release 3A — pickup: 10% chance for a bonus vitamin after commit
        if slot1_ability == "pickup" and random.random() < 0.10:
            try:
                pickup_slug = random.choice(_LOOT_VITAMINS)
                _conn_pk = get_connection()
                with _conn_pk.cursor() as _c:
                    _c.execute("SELECT id FROM shop_items WHERE slug = %s;", (pickup_slug,))
                    _row = _c.fetchone()
                    if _row:
                        _add_inventory_item(_c, user_id, _row[0])
                _conn_pk.commit()
                _abilfx["pickup_item"] = pickup_slug
            except Exception:
                pass

        # XP para o Pokémon slot 1 — transação separada após commit
        slot1_id = None
        try:
            with get_connection().cursor() as cur2:
                cur2.execute("""
                    SELECT ut.user_pokemon_id FROM user_team ut
                    WHERE ut.user_id = %s AND ut.slot = 1;
                """, (user_id,))
                row = cur2.fetchone()
            if row:
                slot1_id = row[0]
                if xp_to_award > 0:
                    result["xp_result"] = award_xp(slot1_id, xp_to_award, "exercise")
        except Exception:
            pass

        # Release 3A — synchronize: award +15% extra XP to team members who received XP Share
        if slot1_ability == "synchronize" and slot1_id and xp_to_award > 0:
            sync_bonus = int(xp_to_award * 0.15)
            if sync_bonus > 0 and result.get("xp_result"):
                shared = result["xp_result"].get("xp_share_distributed", [])
                if shared:
                    for entry in shared:
                        try:
                            award_xp(entry["user_pokemon_id"], sync_bonus,
                                     "synchronize_bonus", _distributing=True)
                        except Exception:
                            pass
                    _abilfx["synchronize_bonus_xp"] = sync_bonus

        # Detecta PRs e concede bônus de XP (fora do cap diário, máx _PR_MAX_PER_SESSION)
        detected_prs = _detect_prs(exercises, historical_bests, ex_name_map)
        capped_prs   = detected_prs[:_PR_MAX_PER_SESSION]
        result["prs"] = capped_prs
        if capped_prs and slot1_id:
            try:
                pr_xp_total = len(capped_prs) * _PR_XP_BONUS
                pr_res = award_xp(slot1_id, pr_xp_total, "pr_bonus", _distributing=True)
                result["milestone_xp"] = result.get("milestone_xp", 0) + pr_xp_total
                if result["xp_result"] and not result["xp_result"].get("error"):
                    result["xp_result"]["levels_gained"] = (
                        result["xp_result"].get("levels_gained", 0)
                        + pr_res.get("levels_gained", 0)
                    )
                    result["xp_result"]["new_level"] = pr_res.get("new_level", result["xp_result"].get("new_level"))
                    result["xp_result"]["new_xp"]    = pr_res.get("new_xp",    result["xp_result"].get("new_xp"))
                    evos = result["xp_result"].get("evolutions", [])
                    evos.extend(pr_res.get("evolutions", []))
                    result["xp_result"]["evolutions"] = evos
                else:
                    result["xp_result"] = pr_res
            except Exception:
                pass

        # Bônus de primeiro treino (+50 XP fora do cap diário)
        if is_first_workout and slot1_id:
            try:
                bonus_res = award_xp(slot1_id, _FIRST_WORKOUT_BONUS_XP, "first_workout_bonus", _distributing=True)
                result["milestone_xp"] = _FIRST_WORKOUT_BONUS_XP
                if result["xp_result"] and not result["xp_result"].get("error"):
                    result["xp_result"]["levels_gained"] = (
                        result["xp_result"].get("levels_gained", 0)
                        + bonus_res.get("levels_gained", 0)
                    )
                    result["xp_result"]["new_level"] = bonus_res.get("new_level", result["xp_result"].get("new_level"))
                    result["xp_result"]["new_xp"]    = bonus_res.get("new_xp",    result["xp_result"].get("new_xp"))
                    evos = result["xp_result"].get("evolutions", [])
                    evos.extend(bonus_res.get("evolutions", []))
                    result["xp_result"]["evolutions"] = evos
                else:
                    result["xp_result"] = bonus_res
            except Exception:
                pass

        if _abilfx and slot1_ability:
            result["ability_effects"] = {"slug": slot1_ability, **_abilfx}

        return result

    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result


# ── Workout Builder — write helpers ──────────────────────────────────────────

def get_workout_sheets(user_id: str) -> list[dict]:
    """Sheets owned by the user with day count."""
    try:
        day_sheet_fk = _first_existing_column("workout_days", "sheet_id", "workout_sheet_id")
        if day_sheet_fk is None:
            return []
        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT ws.id, ws.name, COUNT(wd.id) AS day_count
                FROM workout_sheets ws
                LEFT JOIN workout_days wd ON wd.{day_sheet_fk} = ws.id
                WHERE ws.user_id = %s
                GROUP BY ws.id, ws.name
                ORDER BY ws.name;
            """, (user_id,))
            rows = cur.fetchall()
        return [{"id": str(r[0]), "name": r[1], "day_count": r[2]} for r in rows]
    except Exception:
        return []


def create_workout_sheet(
    user_id: str,
    name: str,
    created_by: str | None = None,
) -> tuple[str | None, str | None]:
    """INSERT into workout_sheets; returns (new_uuid, None) or (None, error_msg)."""
    try:
        conn = get_connection()
        actor_id = created_by or user_id
        has_created_by = _table_has_column("workout_sheets", "created_by")
        with conn.cursor() as cur:
            if has_created_by:
                cur.execute(
                    """
                    INSERT INTO workout_sheets (user_id, created_by, name)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, actor_id, name.strip()),
                )
            else:
                cur.execute(
                    "INSERT INTO workout_sheets (user_id, name) VALUES (%s, %s) RETURNING id;",
                    (user_id, name.strip()),
                )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id), None
    except Exception as e:
        if "conn" in locals():
            conn.rollback()
        return None, str(e)


def update_workout_sheet(user_id: str, sheet_id: str, name: str) -> tuple[bool, str | None]:
    """Updates the routine name; returns (True, None) or (False, error_msg)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            if _table_has_column("workout_sheets", "updated_at"):
                cur.execute(
                    """
                    UPDATE workout_sheets
                    SET name = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (name.strip(), sheet_id, user_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE workout_sheets
                    SET name = %s
                    WHERE id = %s AND user_id = %s;
                    """,
                    (name.strip(), sheet_id, user_id),
                )
            if cur.rowcount == 0:
                conn.rollback()
                return False, "Rotina não encontrada para este usuário."
        conn.commit()
        return True, None
    except Exception as e:
        if "conn" in locals():
            conn.rollback()
        return False, str(e)


def delete_workout_sheet(sheet_id: str) -> tuple[bool, str | None]:
    """DELETE a sheet with all its days and exercises."""
    try:
        conn = get_connection()
        sheet_fk = _first_existing_column("workout_days", "sheet_id", "workout_sheet_id")
        day_fk = _first_existing_column("workout_day_exercises", "day_id", "workout_day_id")
        with conn.cursor() as cur:
            if sheet_fk:
                # Nullify workout_logs.day_id to avoid FK violation
                cur.execute(f"""
                    UPDATE workout_logs SET day_id = NULL
                    WHERE day_id IN (
                        SELECT id FROM workout_days WHERE {sheet_fk} = %s
                    );
                """, (sheet_id,))
                if day_fk:
                    cur.execute(f"""
                        DELETE FROM workout_day_exercises
                        WHERE {day_fk} IN (
                            SELECT id FROM workout_days WHERE {sheet_fk} = %s
                        );
                    """, (sheet_id,))
                cur.execute(f"DELETE FROM workout_days WHERE {sheet_fk} = %s;", (sheet_id,))
            cur.execute("DELETE FROM workout_sheets WHERE id = %s;", (sheet_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def create_workout_day(sheet_id: str, name: str) -> tuple[str | None, str | None]:
    """INSERT into workout_days; returns (new_uuid, None) or (None, error_msg)."""
    try:
        conn = get_connection()
        sheet_fk = _first_existing_column("workout_days", "sheet_id", "workout_sheet_id")
        if sheet_fk is None:
            return None, "Nenhuma coluna de vínculo de rotina foi encontrada em workout_days."
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO workout_days ({sheet_fk}, name) VALUES (%s, %s) RETURNING id;",
                (sheet_id, name.strip()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id), None
    except Exception as e:
        get_connection().rollback()
        return None, str(e)


def delete_workout_day(day_id: str) -> tuple[bool, str | None]:
    """DELETE a day with all its exercises."""
    try:
        conn = get_connection()
        day_fk = _first_existing_column("workout_day_exercises", "day_id", "workout_day_id")
        with conn.cursor() as cur:
            cur.execute("UPDATE workout_logs SET day_id = NULL WHERE day_id = %s;", (day_id,))
            if day_fk:
                cur.execute(f"DELETE FROM workout_day_exercises WHERE {day_fk} = %s;", (day_id,))
            cur.execute("DELETE FROM workout_days WHERE id = %s;", (day_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def add_exercise_to_day(day_id: str, exercise_id: int, sets: int, reps: int) -> tuple[str | None, str | None]:
    """INSERT into workout_day_exercises; returns (new_uuid, None) or (None, error_msg)."""
    try:
        conn = get_connection()
        day_fk = _first_existing_column("workout_day_exercises", "day_id", "workout_day_id")
        if day_fk is None:
            return None, "Nenhuma coluna de vínculo de dia foi encontrada em workout_day_exercises."
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO workout_day_exercises ({day_fk}, exercise_id, sets, reps) VALUES (%s, %s, %s, %s) RETURNING id;",
                (day_id, exercise_id, sets, reps),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id), None
    except Exception as e:
        get_connection().rollback()
        return None, str(e)


def update_day_exercise(wde_id: str, sets: int, reps: int) -> tuple[bool, str | None]:
    """UPDATE sets/reps for a prescribed exercise; returns (True, None) or (False, error_msg)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE workout_day_exercises SET sets = %s, reps = %s WHERE id = %s;",
                (sets, reps, wde_id),
            )
        conn.commit()
        return True, None
    except Exception as e:
        get_connection().rollback()
        return False, str(e)


def remove_exercise_from_day(wde_id: str) -> tuple[bool, str | None]:
    """DELETE a prescribed exercise; returns (True, None) or (False, error_msg)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_day_exercises WHERE id = %s;", (wde_id,))
        conn.commit()
        return True, None
    except Exception as e:
        get_connection().rollback()
        return False, str(e)


def get_sheet_days(sheet_id: str) -> list[dict]:
    """Days for a specific workout sheet with exercise count."""
    try:
        sheet_fk = _first_existing_column("workout_days", "sheet_id", "workout_sheet_id")
        day_fk = _first_existing_column("workout_day_exercises", "day_id", "workout_day_id")
        if sheet_fk is None or day_fk is None:
            return []
        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT wd.id, wd.name, COUNT(wde.id) AS exercise_count
                FROM workout_days wd
                LEFT JOIN workout_day_exercises wde ON wde.{day_fk} = wd.id
                WHERE wd.{sheet_fk} = %s
                GROUP BY wd.id, wd.name
                ORDER BY wd.name;
            """, (sheet_id,))
            return [{"id": str(r[0]), "name": r[1], "exercise_count": r[2]} for r in cur.fetchall()]
    except Exception:
        return []


def get_day_exercises_for_builder(day_id: str) -> list[dict]:
    """Prescribed exercises for a day, including wde.id for edit/delete."""
    try:
        day_fk = _first_existing_column("workout_day_exercises", "day_id", "workout_day_id")
        if day_fk is None:
            return []
        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT wde.id, e.id AS exercise_id,
                       COALESCE(e.name_pt, e.name) AS display_name,
                       wde.sets, wde.reps
                FROM workout_day_exercises wde
                JOIN exercises e ON e.id = wde.exercise_id
                WHERE wde.{day_fk} = %s
                ORDER BY wde.id;
            """, (day_id,))
            return [
                {"id": str(r[0]), "exercise_id": r[1], "name": r[2], "sets": r[3], "reps": r[4]}
                for r in cur.fetchall()
            ]
    except Exception:
        return []


# ── Achievements ─────────────────────────────────────────────────────────────

def get_user_achievements(user_id: str) -> dict[str, datetime.datetime]:
    """Returns {slug: unlocked_at} for all achievements the user has earned."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT achievement_slug, unlocked_at
                FROM user_achievements
                WHERE user_id = %s
                ORDER BY unlocked_at DESC;
            """, (user_id,))
            return {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        return {}


def _collect_achievement_stats(user_id: str, cur) -> dict:
    """Collects all stats needed to evaluate achievement conditions."""
    stats: dict = {}

    cur.execute("SELECT COUNT(*) FROM user_pokemon WHERE user_id = %s;", (user_id,))
    stats["pokemon_count"] = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(MAX(streak), 0) FROM user_checkins WHERE user_id = %s;",
        (user_id,),
    )
    stats["checkin_streak_max"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM workout_logs WHERE user_id = %s;", (user_id,))
    stats["workout_count"] = cur.fetchone()[0]

    # PR count — one per exercise per session where a PR was achieved.
    # Derived by counting distinct (workout_log_id, exercise_id) pairs whose
    # best set weight exceeds all prior sessions' best for that exercise.
    cur.execute("""
        WITH ranked AS (
            SELECT el.workout_log_id,
                   el.exercise_id,
                   MAX((s->>'weight')::float) AS session_best,
                   ROW_NUMBER() OVER (
                       PARTITION BY el.exercise_id
                       ORDER BY wl.completed_at
                   ) AS rn
            FROM exercise_logs el
            JOIN workout_logs wl ON wl.id = el.workout_log_id
            JOIN LATERAL jsonb_array_elements(el.sets_data) AS s ON true
            WHERE wl.user_id = %s
              AND (s->>'weight') IS NOT NULL
            GROUP BY el.workout_log_id, el.exercise_id, wl.completed_at
        ),
        with_prev AS (
            SELECT exercise_id,
                   session_best,
                   LAG(session_best) OVER (
                       PARTITION BY exercise_id ORDER BY rn
                   ) AS prev_best
            FROM ranked
        )
        SELECT COUNT(*) FROM with_prev
        WHERE prev_best IS NOT NULL AND session_best > prev_best;
    """, (user_id,))
    stats["pr_count"] = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM user_battles WHERE winner_id = %s;",
        (user_id,),
    )
    stats["battle_wins"] = cur.fetchone()[0]

    cur.execute(
        "SELECT EXISTS(SELECT 1 FROM user_pokemon WHERE user_id = %s AND is_shiny = true);",
        (user_id,),
    )
    stats["has_shiny"] = cur.fetchone()[0]

    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM user_pokemon up
            JOIN pokemon_species ps ON ps.id = up.species_id
            WHERE up.user_id = %s AND ps.id > 10000
        );
    """, (user_id,))
    stats["has_regional"] = cur.fetchone()[0]

    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM user_pokemon up
            JOIN pokemon_evolutions pe ON pe.to_species_id = up.species_id
            WHERE up.user_id = %s
        );
    """, (user_id,))
    stats["has_evolved_pokemon"] = cur.fetchone()[0]

    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM user_pokemon up
            JOIN pokemon_evolutions pe ON pe.to_species_id = up.species_id
            WHERE up.user_id = %s AND pe.trigger_name = 'use-item'
        );
    """, (user_id,))
    stats["has_stone_evolved"] = cur.fetchone()[0]

    # Workout streak (reuse the same logic as get_workout_streak)
    cur.execute("""
        SELECT DISTINCT (completed_at AT TIME ZONE 'America/Sao_Paulo')::date AS d
        FROM workout_logs WHERE user_id = %s ORDER BY d DESC;
    """, (user_id,))
    streak_days = [r[0] for r in cur.fetchall()]
    streak = 0
    check_day = _today_brt()
    for d in streak_days:
        if d == check_day:
            streak += 1
            check_day -= datetime.timedelta(days=1)
        elif d < check_day:
            break
    stats["workout_streak"] = streak

    return stats


_LOOT_VITAMINS = ["hp-up", "protein", "iron", "calcium", "zinc", "carbos"]
_LOOT_STONES   = [
    "fire-stone", "water-stone", "thunder-stone", "leaf-stone", "moon-stone",
    "sun-stone", "shiny-stone", "dusk-stone", "dawn-stone", "ice-stone",
]


def _roll_loot_box(cur, user_id: str) -> dict:
    """Roll loot table and apply coins/items in-transaction.

    XP rewards are NOT applied here — caller must call award_xp after committing.
    Returns a loot info dict: {type, amount?, slug?, name?, label, rarity}
    """
    roll = random.randint(1, 100)

    if roll <= 50:                          # 50% — XP (common)
        amount = random.randint(50, 150)
        return {"type": "xp", "amount": amount, "label": f"+{amount} XP", "rarity": "common"}

    if roll <= 80:                          # 30% — Coins (common)
        amount = random.randint(50, 150)
        cur.execute(
            "UPDATE user_profiles SET coins = coins + %s WHERE id = %s",
            (amount, user_id),
        )
        return {"type": "coins", "amount": amount, "label": f"+{amount} moedas", "rarity": "common"}

    if roll <= 90:                          # 10% — Vitamin (rare)
        slug = random.choice(_LOOT_VITAMINS)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": slug, "name": row[1], "label": f"1x {row[1]}", "rarity": "rare"}

    if roll <= 95:                          # 5% — Nature Mint (rare)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = 'nature-mint'")
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": "nature-mint", "name": row[1], "label": f"1x {row[1]}", "rarity": "rare"}

    if roll <= 99:                          # 4% — Evolution stone (ultra-rare)
        slug = random.choice(_LOOT_STONES)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": slug, "name": row[1], "label": f"1x {row[1]}", "rarity": "ultra_rare"}

    # 1% — XP Share (ultra-rare)
    cur.execute("SELECT id, name FROM shop_items WHERE slug = 'xp-share'")
    row = cur.fetchone()
    if row:
        _add_inventory_item(cur, user_id, row[0])
        return {"type": "item", "slug": "xp-share", "name": row[1], "label": f"1x {row[1]}", "rarity": "ultra_rare"}

    # Fallback — always give coins
    cur.execute("UPDATE user_profiles SET coins = coins + 50 WHERE id = %s", (user_id,))
    return {"type": "coins", "amount": 50, "label": "+50 moedas", "rarity": "common"}


def check_and_award_achievements(user_id: str) -> list[dict]:
    """Check every achievement condition and unlock newly eligible ones.

    Returns list of {slug, loot} for achievements unlocked during this call.
    """
    from utils.achievements import CATALOG
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT achievement_slug FROM user_achievements WHERE user_id = %s;",
                (user_id,),
            )
            already = {r[0] for r in cur.fetchall()}

            stats = _collect_achievement_stats(user_id, cur)

            new_unlocks: list[dict] = []
            for slug, ach in CATALOG.items():
                if slug not in already and ach["check"](stats):
                    cur.execute("""
                        INSERT INTO user_achievements (user_id, achievement_slug)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id, achievement_slug) DO NOTHING
                        RETURNING achievement_slug;
                    """, (user_id, slug))
                    if cur.fetchone():
                        loot = _grant_loot_box(cur, user_id)
                        new_unlocks.append({"slug": slug, "loot": loot})

            if new_unlocks:
                conn.commit()

            return new_unlocks
    except Exception:
        return []


def admin_gift_loot_box(admin_id: str, target_user_id: str, count: int = 1) -> tuple[bool, str, list[dict]]:
    """Gift `count` loot boxes to `target_user_id`.

    Returns (success, message, list_of_granted_loot_box_dicts).
    """
    if count < 1 or count > 10:
        return False, "Quantidade deve estar entre 1 e 10.", []
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM user_profiles WHERE id = %s", (target_user_id,))
            if not cur.fetchone():
                return False, "Usuário não encontrado.", []

            results = [_grant_loot_box(cur, target_user_id, count)]

            conn.commit()

        log_admin_action(
            admin_id, "gift_loot_box",
            target_type="user", target_id=target_user_id,
            details={"count": count, "results": [l["label"] for l in results]},
        )
        labels = ", ".join(l["label"] for l in results)
        return True, f"{count}x loot box(es) enviado(s) para a mochila do usuário: {labels}", results
    except Exception as e:
        return False, f"Erro: {e}", []

def admin_create_exercise(
    name: str,
    name_pt: str,
    target_muscles: list[str],
    body_parts: list[str],
    equipments: list[str],
    gif_url: str | None = None,
) -> tuple[bool, str, int | None]:
    """Insert a new exercise into the catalogue.

    Returns (success, message, new_id).
    """
    if not name.strip():
        return False, "O nome em inglês é obrigatório.", None
    if not name_pt.strip():
        return False, "O nome em português é obrigatório.", None
    if not body_parts:
        return False, "Informe ao menos uma parte do corpo.", None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exercises (name, name_pt, target_muscles, body_parts, equipments, gif_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    name.strip(),
                    name_pt.strip(),
                    target_muscles,
                    body_parts,
                    equipments,
                    gif_url.strip() if gif_url and gif_url.strip() else None,
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        get_exercises.clear()
        get_distinct_body_parts.clear()
        return True, f"Exercício #{new_id} criado com sucesso.", new_id
    except Exception as e:
        return False, f"Erro ao criar exercício: {e}", None


# ── Leaderboard ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_leaderboard_pokemon_count(limit: int = 20) -> list[dict]:
    """Ranks all users by total Pokémon owned (all-time collection size)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT pr.id, pr.username, COUNT(up.id) AS pokemon_count,
                       ps.name AS lead_pokemon, ps.sprite_url AS lead_sprite,
                       up2.level AS lead_level
                FROM user_profiles pr
                JOIN user_pokemon up ON up.user_id = pr.id
                LEFT JOIN user_team ut ON ut.user_id = pr.id AND ut.slot = 1
                LEFT JOIN user_pokemon up2 ON up2.id = ut.user_pokemon_id
                LEFT JOIN pokemon_species ps ON ps.id = up2.species_id
                GROUP BY pr.id, pr.username, ps.name, ps.sprite_url, up2.level
                ORDER BY pokemon_count DESC
                LIMIT %s;
            """, (limit,))
            cols = ["user_id", "username", "value", "lead_pokemon", "lead_sprite", "lead_level"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_leaderboard_checkin_streak(year: int, month: int, limit: int = 20) -> list[dict]:
    """Ranks users by their best check-in streak reached in the given month."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT pr.id, pr.username, MAX(uc.streak) AS value,
                       ps.name AS lead_pokemon, ps.sprite_url AS lead_sprite,
                       up2.level AS lead_level
                FROM user_profiles pr
                JOIN user_checkins uc ON uc.user_id = pr.id
                LEFT JOIN user_team ut ON ut.user_id = pr.id AND ut.slot = 1
                LEFT JOIN user_pokemon up2 ON up2.id = ut.user_pokemon_id
                LEFT JOIN pokemon_species ps ON ps.id = up2.species_id
                WHERE EXTRACT(YEAR  FROM uc.checked_date) = %s
                  AND EXTRACT(MONTH FROM uc.checked_date) = %s
                GROUP BY pr.id, pr.username, ps.name, ps.sprite_url, up2.level
                ORDER BY value DESC
                LIMIT %s;
            """, (year, month, limit))
            cols = ["user_id", "username", "value", "lead_pokemon", "lead_sprite", "lead_level"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_leaderboard_workout_xp(year: int, month: int, limit: int = 20) -> list[dict]:
    """Ranks users by total workout XP earned in the given month."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT pr.id, pr.username, COALESCE(SUM(wl.xp_earned), 0) AS value,
                       ps.name AS lead_pokemon, ps.sprite_url AS lead_sprite,
                       up2.level AS lead_level
                FROM user_profiles pr
                JOIN workout_logs wl ON wl.user_id = pr.id
                LEFT JOIN user_team ut ON ut.user_id = pr.id AND ut.slot = 1
                LEFT JOIN user_pokemon up2 ON up2.id = ut.user_pokemon_id
                LEFT JOIN pokemon_species ps ON ps.id = up2.species_id
                WHERE EXTRACT(YEAR  FROM wl.completed_at AT TIME ZONE 'America/Sao_Paulo') = %s
                  AND EXTRACT(MONTH FROM wl.completed_at AT TIME ZONE 'America/Sao_Paulo') = %s
                GROUP BY pr.id, pr.username, ps.name, ps.sprite_url, up2.level
                ORDER BY value DESC
                LIMIT %s;
            """, (year, month, limit))
            cols = ["user_id", "username", "value", "lead_pokemon", "lead_sprite", "lead_level"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


# ── Admin ──────────────────────────────────────────────────────────────────────

def is_admin(user_id: str) -> bool:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM user_profiles WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])
    except Exception:
        return False


def get_all_users(search: str = "") -> list[dict]:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            pattern = f"%{search}%"
            cur.execute("""
                SELECT up.id, up.username, up.coins, up.is_admin,
                       au.email, au.created_at, au.last_sign_in_at,
                       COUNT(DISTINCT upk.id) AS pokemon_count,
                       COUNT(DISTINCT wl.id)  AS workout_count
                FROM user_profiles up
                JOIN auth.users au ON au.id = up.id
                LEFT JOIN user_pokemon upk ON upk.user_id = up.id
                LEFT JOIN workout_logs wl  ON wl.user_id  = up.id
                WHERE (%s = '' OR up.username ILIKE %s OR au.email ILIKE %s)
                GROUP BY up.id, up.username, up.coins, up.is_admin,
                         au.email, au.created_at, au.last_sign_in_at
                ORDER BY au.created_at DESC;
            """, (search, pattern, pattern))
            cols = ["id", "username", "coins", "is_admin", "email",
                    "created_at", "last_sign_in_at", "pokemon_count", "workout_count"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


def admin_update_user(target_user_id: str, username: str, coins: int) -> tuple[bool, str]:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE user_profiles SET username = %s, coins = %s WHERE id = %s",
                (username, coins, target_user_id),
            )
            conn.commit()
            return True, "Usuário atualizado."
    except Exception as e:
        return False, str(e)


def admin_delete_user(acting_admin_id: str, target_user_id: str) -> tuple[bool, str]:
    if acting_admin_id == target_user_id:
        return False, "Você não pode deletar a si mesmo."
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM user_profiles WHERE id = %s", (target_user_id,))
            conn.commit()
            log_admin_action(acting_admin_id, "delete_user",
                             target_type="user", target_id=target_user_id)
            return True, "Perfil deletado. Conta de auth requer remoção manual no Supabase."
    except Exception as e:
        return False, str(e)


def set_admin_role(acting_admin_id: str, target_user_id: str, grant: bool) -> tuple[bool, str]:
    if acting_admin_id == target_user_id and not grant:
        return False, "Você não pode remover seu próprio acesso de admin."
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE user_profiles SET is_admin = %s WHERE id = %s",
                (grant, target_user_id),
            )
            conn.commit()
            action = "grant_admin" if grant else "revoke_admin"
            log_admin_action(acting_admin_id, action,
                             target_type="user", target_id=target_user_id)
            label = "concedido" if grant else "revogado"
            return True, f"Acesso admin {label}."
    except Exception as e:
        return False, str(e)


def log_admin_action(user_id: str, action: str,
                     target_type: str | None = None,
                     target_id: str | None = None,
                     details: dict | None = None) -> None:
    try:
        import json as _json
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO system_logs (user_id, action, target_type, target_id, details)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, action, target_type, target_id,
                 _json.dumps(details) if details else None),
            )
            conn.commit()
    except Exception:
        pass


def get_system_logs(limit: int = 200, action_filter: str = "",
                    user_filter: str = "") -> list[dict]:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT sl.id, sl.action, sl.target_type, sl.target_id,
                       sl.details, sl.created_at, up.username
                FROM system_logs sl
                LEFT JOIN user_profiles up ON up.id = sl.user_id
                WHERE (%s = '' OR sl.action ILIKE %s)
                  AND (%s = '' OR up.username ILIKE %s)
                ORDER BY sl.created_at DESC
                LIMIT %s;
            """, (action_filter, f"%{action_filter}%",
                  user_filter, f"%{user_filter}%",
                  limit))
            cols = ["id", "action", "target_type", "target_id",
                    "details", "created_at", "username"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


def get_global_stats() -> dict:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT
                  (SELECT COUNT(*) FROM user_profiles)                       AS total_users,
                  (SELECT COUNT(*) FROM user_profiles WHERE is_admin = TRUE) AS total_admins,
                  (SELECT COUNT(*) FROM user_pokemon)                        AS total_pokemon,
                  (SELECT COUNT(*) FROM workout_logs)                        AS total_workouts,
                  (SELECT COUNT(*) FROM user_checkins)                       AS total_checkins,
                  (SELECT COUNT(*) FROM user_battles)                        AS total_battles,
                  (SELECT COALESCE(SUM(coins),0) FROM user_profiles)         AS total_coins,
                  (SELECT COUNT(DISTINCT user_id) FROM workout_logs
                   WHERE completed_at >= NOW() - INTERVAL '7 days')          AS active_7d;
            """)
            row = cur.fetchone()
            keys = ["total_users", "total_admins", "total_pokemon",
                    "total_workouts", "total_checkins", "total_battles",
                    "total_coins", "active_7d"]
            return dict(zip(keys, row)) if row else {}
    except Exception:
        return {}


# ── Missões ────────────────────────────────────────────────────────────────────

def _week_start(d: datetime.date) -> datetime.date:
    """Return the Monday of the week containing date d (BRT)."""
    return d - datetime.timedelta(days=d.weekday())


def _ensure_missions(cur, user_id: str) -> None:
    """Generate daily (3) and weekly (1) missions for the current period if absent."""
    from utils.missions import pick_daily_slugs, pick_weekly_slug, get_mission
    today = _today_brt()
    week_start = _week_start(today)

    # Daily: check how many missions already exist for today
    cur.execute(
        "SELECT mission_slug FROM user_missions WHERE user_id = %s AND mission_type = 'daily' AND period_start = %s;",
        (user_id, today),
    )
    existing_daily = {r[0] for r in cur.fetchall()}
    if len(existing_daily) < 3:
        needed = 3 - len(existing_daily)
        # pick from full pool, avoid duplicates with what's already assigned today
        pool = [m for m in pick_daily_slugs(n=6) if m not in existing_daily]
        for slug in pool[:needed]:
            m = get_mission(slug)
            if not m:
                continue
            cur.execute("""
                INSERT INTO user_missions (user_id, mission_slug, mission_type, period_start, target)
                VALUES (%s, %s, 'daily', %s, %s)
                ON CONFLICT (user_id, mission_slug, period_start) DO NOTHING;
            """, (user_id, slug, today, m["target"]))

    # Weekly: check if one exists for this week
    cur.execute(
        "SELECT mission_slug FROM user_missions WHERE user_id = %s AND mission_type = 'weekly' AND period_start = %s;",
        (user_id, week_start),
    )
    if not cur.fetchone():
        slug = pick_weekly_slug()
        if slug:
            m = get_mission(slug)
            if m:
                cur.execute("""
                    INSERT INTO user_missions (user_id, mission_slug, mission_type, period_start, target)
                    VALUES (%s, %s, 'weekly', %s, %s)
                    ON CONFLICT (user_id, mission_slug, period_start) DO NOTHING;
                """, (user_id, slug, week_start, m["target"]))


def get_user_missions(user_id: str) -> dict:
    """Return {'daily': [...], 'weekly': [...]} for the current period.

    Generates missions for today/this week on first call of each period.
    Each mission dict includes all catalog fields plus db state:
    {slug, label, icon, target, event, reward_type, reward_amount, reward_label,
     id, progress, completed, reward_claimed, period_start}
    """
    from utils.missions import get_mission
    today = _today_brt()
    week_start = _week_start(today)
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            _ensure_missions(cur, user_id)
            conn.commit()

            cur.execute("""
                SELECT id, mission_slug, mission_type, period_start,
                       target, progress, completed, reward_claimed
                FROM user_missions
                WHERE user_id = %s
                  AND ((mission_type = 'daily'  AND period_start = %s)
                    OR (mission_type = 'weekly' AND period_start = %s))
                ORDER BY mission_type, id;
            """, (user_id, today, week_start))
            rows = cur.fetchall()

        result: dict[str, list] = {"daily": [], "weekly": []}
        for mid, slug, mtype, pstart, target, progress, completed, claimed in rows:
            catalog = get_mission(slug) or {}
            result[mtype].append({
                **catalog,
                "id":             mid,
                "slug":           slug,
                "progress":       progress,
                "target":         target,
                "completed":      completed,
                "reward_claimed": claimed,
                "period_start":   pstart,
            })
        return result
    except Exception:
        return {"daily": [], "weekly": []}


def update_mission_progress(user_id: str, event_type: str, data: dict | None = None) -> list[dict]:
    """Increment progress on active missions that match event_type.

    event_type values and expected data keys:
      "workout"       — data: {sets_total: int, max_weight: float, xp_earned: int}
      "battle_win"    — data: {} (just the event)
      "checkin"       — data: {} (just the event)
      "pr"            — data: {count: int} (number of PRs in session)

    Returns list of mission dicts that were newly completed by this call.
    """
    from utils.missions import get_mission
    if data is None:
        data = {}

    today = _today_brt()
    week_start = _week_start(today)

    # Map event_type → {mission_event_key: increment_value}
    # A single workout call can contribute to multiple event keys simultaneously.
    increments: dict[str, int] = {}
    if event_type == "workout":
        increments["workout"] = 1
        sets_total = int(data.get("sets_total", 0))
        if sets_total:
            increments["workout_sets"] = sets_total
        max_weight = float(data.get("max_weight", 0.0))
        if max_weight >= 50.0:
            increments["workout_heavy"] = 1
        xp_earned = int(data.get("xp_earned", 0))
        if xp_earned:
            increments["workout_xp"] = xp_earned
    elif event_type == "battle_win":
        increments["battle_win"] = 1
    elif event_type == "checkin":
        increments["checkin"] = 1
    elif event_type == "pr":
        increments["pr"] = int(data.get("count", 1))
    else:
        return []

    try:
        conn = get_connection()
        newly_completed: list[dict] = []
        with conn.cursor() as cur:
            # Fetch all active uncompleted missions for this period
            cur.execute("""
                SELECT id, mission_slug, mission_type, target, progress
                FROM user_missions
                WHERE user_id = %s
                  AND completed = FALSE
                  AND ((mission_type = 'daily'  AND period_start = %s)
                    OR (mission_type = 'weekly' AND period_start = %s));
            """, (user_id, today, week_start))
            missions = cur.fetchall()

            for mid, slug, mtype, target, current_progress in missions:
                catalog = get_mission(slug)
                if not catalog:
                    continue
                mission_event = catalog.get("event", "")
                delta = increments.get(mission_event, 0)
                if delta <= 0:
                    continue

                new_progress = min(current_progress + delta, target)
                now_complete = new_progress >= target
                cur.execute("""
                    UPDATE user_missions
                    SET progress = %s, completed = %s
                    WHERE id = %s;
                """, (new_progress, now_complete, mid))
                if now_complete:
                    newly_completed.append({**catalog, "id": mid, "mission_type": mtype})

        conn.commit()
        return newly_completed
    except Exception:
        return []


def claim_mission_reward(user_id: str, mission_id: int) -> tuple[bool, str, dict | None]:
    """Claim the reward for a completed mission.

    Returns (success, message, reward_info_dict).
    reward_info_dict keys: type, label, amount (for xp/coins), xp_result (for xp rewards)
    """
    from utils.missions import get_mission
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT mission_slug, completed, reward_claimed
                FROM user_missions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
            """, (mission_id, user_id))
            row = cur.fetchone()
            if not row:
                return False, "Missão não encontrada.", None
            slug, completed, claimed = row
            if not completed:
                return False, "Missão ainda não concluída.", None
            if claimed:
                return False, "Recompensa já coletada.", None

            catalog = get_mission(slug)
            if not catalog:
                return False, "Missão inválida.", None

            reward_type   = catalog["reward_type"]
            reward_amount = catalog["reward_amount"]
            reward_label  = catalog["reward_label"]
            reward_info: dict = {"type": reward_type, "label": reward_label}

            if reward_type == "coins":
                cur.execute(
                    "UPDATE user_profiles SET coins = coins + %s WHERE id = %s;",
                    (reward_amount, user_id),
                )
                reward_info["amount"] = reward_amount

            elif reward_type == "xp":
                # Apply after commit — fetch slot 1 first
                cur.execute(
                    "SELECT user_pokemon_id FROM user_team WHERE user_id = %s AND slot = 1;",
                    (user_id,),
                )
                slot1 = cur.fetchone()
                reward_info["slot1_pokemon_id"] = slot1[0] if slot1 else None
                reward_info["amount"] = reward_amount

            elif reward_type == "stone":
                stone_slug = random.choice(_LOOT_STONES)
                cur.execute("SELECT id FROM shop_items WHERE slug = %s;", (stone_slug,))
                item_row = cur.fetchone()
                if item_row:
                    _add_inventory_item(cur, user_id, item_row[0])
                    reward_info["slug"] = stone_slug
                else:
                    # Fallback: give coins
                    cur.execute(
                        "UPDATE user_profiles SET coins = coins + 10 WHERE id = %s;", (user_id,)
                    )
                    reward_info = {"type": "coins", "label": "+10 moedas", "amount": 10}

            elif reward_type == "vitamin":
                vitamin_slug = random.choice(_LOOT_VITAMINS)
                cur.execute("SELECT id FROM shop_items WHERE slug = %s;", (vitamin_slug,))
                item_row = cur.fetchone()
                if item_row:
                    _add_inventory_item(cur, user_id, item_row[0])
                    reward_info["slug"] = vitamin_slug
                else:
                    cur.execute(
                        "UPDATE user_profiles SET coins = coins + 10 WHERE id = %s;", (user_id,)
                    )
                    reward_info = {"type": "coins", "label": "+10 moedas", "amount": 10}

            elif reward_type == "loot_box":
                loot_box_info = _grant_loot_box(cur, user_id)
                reward_info["granted"] = loot_box_info

            cur.execute(
                "UPDATE user_missions SET reward_claimed = TRUE WHERE id = %s;",
                (mission_id,),
            )
        conn.commit()

        # Apply XP post-commit (avoids nesting connections)
        if reward_type == "xp" and reward_info.get("slot1_pokemon_id"):
            xp_result = award_xp(reward_info["slot1_pokemon_id"], reward_amount, "mission_reward")
            reward_info["xp_result"] = xp_result

        return True, f"Recompensa coletada: {reward_label}!", reward_info
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Erro ao coletar recompensa: {e}", None
