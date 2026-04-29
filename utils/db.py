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

            # Adiciona starter com stats escalados para nível 1
            cur.execute("""
                INSERT INTO user_pokemon (
                    user_id, species_id, level, xp,
                    stat_hp, stat_attack, stat_defense,
                    stat_sp_attack, stat_sp_defense, stat_speed
                )
                SELECT %s, %s, 1, 0,
                    GREATEST(1, 2*base_hp         /100 + 11),
                    GREATEST(1, 2*base_attack      /100 + 5),
                    GREATEST(1, 2*base_defense     /100 + 5),
                    GREATEST(1, 2*base_sp_attack   /100 + 5),
                    GREATEST(1, 2*base_sp_defense  /100 + 5),
                    GREATEST(1, 2*base_speed       /100 + 5)
                FROM pokemon_species WHERE id = %s
                RETURNING id;
            """, (user_id, starter_id, starter_id))
            up_id = cur.fetchone()[0]

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
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ut.slot, up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp, t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       p.base_hp, p.base_attack, p.base_defense,
                       p.base_sp_attack, p.base_sp_defense, p.base_speed
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
            cur.execute("""
                INSERT INTO user_pokemon (
                    user_id, species_id, level, xp,
                    stat_hp, stat_attack, stat_defense,
                    stat_sp_attack, stat_sp_defense, stat_speed
                )
                SELECT %s, %s, 1, 0,
                    GREATEST(1, 2*base_hp         /100 + 11),
                    GREATEST(1, 2*base_attack      /100 + 5),
                    GREATEST(1, 2*base_defense     /100 + 5),
                    GREATEST(1, 2*base_sp_attack   /100 + 5),
                    GREATEST(1, 2*base_sp_defense  /100 + 5),
                    GREATEST(1, 2*base_speed       /100 + 5)
                FROM pokemon_species WHERE id = %s
                RETURNING id;
            """, (user_id, species_id, species_id))
            up_id = cur.fetchone()[0]

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
            cur.execute("""
                SELECT up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp,
                       t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed
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
                    # Pokémon que o usuário ainda não possui
                    cur.execute("""
                        SELECT id FROM pokemon_species
                        WHERE id NOT IN (
                            SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
                        )
                        ORDER BY RANDOM() LIMIT 1;
                    """, (user_id,))
                    spawn_row = cur.fetchone()
                    if spawn_row:
                        spawned_species_id = spawn_row[0]

                        # Captura o Pokémon (nível 5, stats escalados)
                        cur.execute("""
                            INSERT INTO user_pokemon (
                                user_id, species_id, level, xp,
                                stat_hp, stat_attack, stat_defense,
                                stat_sp_attack, stat_sp_defense, stat_speed
                            )
                            SELECT %s, %s, 5, 0,
                                GREATEST(1, 2*base_hp         *5/100 + 5 + 10),
                                GREATEST(1, 2*base_attack     *5/100 + 5),
                                GREATEST(1, 2*base_defense    *5/100 + 5),
                                GREATEST(1, 2*base_sp_attack  *5/100 + 5),
                                GREATEST(1, 2*base_sp_defense *5/100 + 5),
                                GREATEST(1, 2*base_speed      *5/100 + 5)
                            FROM pokemon_species WHERE id = %s
                            RETURNING id;
                        """, (user_id, spawned_species_id, spawned_species_id))
                        up_id = cur.fetchone()[0]

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
                            SELECT p.id, p.name, p.sprite_url,
                                   t1.name AS type1
                            FROM pokemon_species p
                            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                            WHERE p.id = %s;
                        """, (spawned_species_id,))
                        pdata = cur.fetchone()
                        if pdata:
                            result["spawned"] = {
                                "id": pdata[0], "name": pdata[1],
                                "sprite_url": pdata[2], "type1": pdata[3],
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

def _scaled_stat(base: int, level: int, is_hp: bool = False) -> int:
    """Fórmula Pokémon simplificada (sem IVs / EVs / Natureza).

    HP:   floor(2 × base × level / 100) + level + 10
    Demais: floor(2 × base × level / 100) + 5

    Cap: nível máximo 100 (consistente com award_xp).
    """
    level = min(level, 100)
    scaled = int(2 * base * level / 100)
    if is_hp:
        return max(1, scaled + level + 10)
    return max(1, scaled + 5)


def _recalc_stats_for_level(
    cur, user_pokemon_id: int, species_id: int, level: int
) -> None:
    """Recalcula stat_* usando a fórmula Pokémon escalada pelo nível + vitaminas.

    Deve ser chamada após level-ups e evoluções para manter os stats
    individuais em sincronia com o nível atual e a espécie atual.
    """
    cur.execute("""
        SELECT stat, COALESCE(SUM(delta), 0)
        FROM user_pokemon_stat_boosts
        WHERE user_pokemon_id = %s
        GROUP BY stat;
    """, (user_pokemon_id,))
    boosts = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute("""
        SELECT base_hp, base_attack, base_defense,
               base_sp_attack, base_sp_defense, base_speed
        FROM pokemon_species WHERE id = %s;
    """, (species_id,))
    bases = cur.fetchone()
    if not bases:
        return

    stat_cols = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    values = [
        _scaled_stat(bases[i] or 0, level, is_hp=(stat == "hp")) + boosts.get(stat, 0)
        for i, stat in enumerate(stat_cols)
    ]
    set_parts = ", ".join(f"stat_{stat} = %s" for stat in stat_cols)
    cur.execute(
        f"UPDATE user_pokemon SET {set_parts} WHERE id = %s;",
        values + [user_pokemon_id],
    )


def _recalc_stats_on_evolution(
    cur, user_pokemon_id: int, new_species_id: int, level: int
) -> None:
    """Recalcula stat_* após uma evolução usando a nova espécie e o nível atual.

    Delega para _recalc_stats_for_level com a espécie pós-evolução.
    """
    _recalc_stats_for_level(cur, user_pokemon_id, new_species_id, level)


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
                                cur.execute("""
                                    INSERT INTO user_pokemon (
                                        user_id, species_id, level, xp,
                                        stat_hp, stat_attack, stat_defense,
                                        stat_sp_attack, stat_sp_defense, stat_speed
                                    )
                                    SELECT %s, %s, %s, 0,
                                        GREATEST(1, 2*base_hp        *%s/100 + %s + 10),
                                        GREATEST(1, 2*base_attack    *%s/100 + 5),
                                        GREATEST(1, 2*base_defense   *%s/100 + 5),
                                        GREATEST(1, 2*base_sp_attack *%s/100 + 5),
                                        GREATEST(1, 2*base_sp_defense*%s/100 + 5),
                                        GREATEST(1, 2*base_speed     *%s/100 + 5)
                                    FROM pokemon_species WHERE id = %s
                                    RETURNING id;
                                """, (user_id, shed_id, level,
                                      level, level,   # HP: ×level + +level
                                      level,          # attack
                                      level,          # defense
                                      level,          # sp_attack
                                      level,          # sp_defense
                                      level,          # speed
                                      shed_id))
                                shed_up_id = cur.fetchone()[0]
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
                # Nova espécie + novo nível → usa _recalc_stats_on_evolution
                # (que delega para _recalc_stats_for_level com new_species_id)
                _recalc_stats_on_evolution(cur, user_pokemon_id, species_id, level)
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
            _recalc_stats_on_evolution(cur, user_pokemon_id, to_id, poke_level)

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

# body_parts (campo de exercises) → slug de tipo Pokémon para spawn temático
_BODY_PART_TYPE: dict[str, str] = {
    "chest":      "fighting",
    "upper arms": "fighting",
    "lower arms": "normal",
    "back":       "dark",
    "shoulders":  "flying",
    "upper legs": "ground",
    "lower legs": "ground",
    "waist":      "steel",
    "neck":       "rock",
    "cardio":     "water",
}


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
    """XP bruto de uma sessão: sets × reps × 2 + FLOOR(weight_kg / 10) × sets."""
    total = 0
    for ex in exercises:
        for s in ex.get("sets_data", []):
            reps   = int(s.get("reps") or 0)
            weight = float(s.get("weight") or 0)
            total += reps * 2 + int(weight / 10)
    return max(0, total)


def _spawn_typed(cur, user_id: str, type_slug: str | None = None, is_shiny: bool = False):
    """Captura um Pokémon não capturado (tipo opcional) dentro de uma transação aberta.

    Tenta primeiro com filtro de tipo; se não encontrar, usa qualquer espécie.
    Retorna (species_id, {id, name, sprite_url, type1, is_shiny}) ou (None, None).
    """
    def _query_species(with_type: bool):
        if with_type:
            cur.execute("""
                SELECT ps.id
                FROM pokemon_species ps
                JOIN pokemon_types pt1 ON ps.type1_id = pt1.id
                WHERE ps.id NOT IN (
                    SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
                )
                AND (pt1.slug = %s
                     OR EXISTS (
                         SELECT 1 FROM pokemon_types pt2
                         WHERE pt2.id = ps.type2_id AND pt2.slug = %s
                     ))
                ORDER BY RANDOM() LIMIT 1;
            """, (user_id, type_slug, type_slug))
        else:
            cur.execute("""
                SELECT id FROM pokemon_species
                WHERE id NOT IN (
                    SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
                )
                ORDER BY RANDOM() LIMIT 1;
            """, (user_id,))
        return cur.fetchone()

    row = _query_species(with_type=bool(type_slug))
    if not row and type_slug:
        row = _query_species(with_type=False)
    if not row:
        return None, None

    species_id = row[0]
    cur.execute("""
        INSERT INTO user_pokemon (
            user_id, species_id, level, xp, is_shiny,
            stat_hp, stat_attack, stat_defense,
            stat_sp_attack, stat_sp_defense, stat_speed
        )
        SELECT %s, %s, 5, 0, %s,
            GREATEST(1, 2*base_hp         *5/100 + 5 + 10),
            GREATEST(1, 2*base_attack     *5/100 + 5),
            GREATEST(1, 2*base_defense    *5/100 + 5),
            GREATEST(1, 2*base_sp_attack  *5/100 + 5),
            GREATEST(1, 2*base_sp_defense *5/100 + 5),
            GREATEST(1, 2*base_speed      *5/100 + 5)
        FROM pokemon_species WHERE id = %s
        RETURNING id;
    """, (user_id, species_id, is_shiny, species_id))
    up_id = cur.fetchone()[0]

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
        "spawned":      None,
        "xp_result":    None,
        "milestone":    None,
        "milestone_xp": 0,
        "streak":       0,
        "error":        None,
    }

    if not exercises:
        result["error"] = "Nenhum exercício informado."
        return result

    raw_xp = _calc_exercise_xp(exercises)
    if raw_xp <= 0:
        result["error"] = "Nenhuma série registrada."
        return result

    already_today = get_daily_xp_from_exercise(user_id)
    remaining     = max(0, _EXERCISE_XP_DAILY_CAP - already_today)
    xp_to_award   = min(raw_xp, remaining)

    if xp_to_award == 0:
        result["capped"] = True
        result["error"]  = f"Limite diário de {_EXERCISE_XP_DAILY_CAP} XP por exercício já atingido."
        return result
    if xp_to_award < raw_xp:
        result["capped"] = True

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Primeiro treino? (antes do INSERT)
            cur.execute("SELECT COUNT(*) FROM workout_logs WHERE user_id = %s;", (user_id,))
            is_first_workout = cur.fetchone()[0] == 0

            # Busca body_parts dos exercícios para determinar tipo de spawn
            ex_ids = [ex["exercise_id"] for ex in exercises]
            cur.execute(
                "SELECT id, body_parts FROM exercises WHERE id = ANY(%s);",
                (ex_ids,)
            )
            bp_map = {r[0]: (r[1] or []) for r in cur.fetchall()}

            bp_counts: dict[str, int] = {}
            for ex in exercises:
                for bp in bp_map.get(ex["exercise_id"], []):
                    bp_counts[bp] = bp_counts.get(bp, 0) + 1
            dominant_bp = max(bp_counts, key=lambda k: bp_counts[k]) if bp_counts else None
            type_slug   = _BODY_PART_TYPE.get(dominant_bp) if dominant_bp else None

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

            # Spawn temático
            result["spawn_rolled"] = True
            should_spawn = force_spawn or (random.random() < 0.25)
            if should_spawn:
                species_id, spawn_info = _spawn_typed(cur, user_id, type_slug, is_shiny=force_shiny)
                if species_id:
                    result["spawned"] = spawn_info
                    cur.execute(
                        "UPDATE workout_logs SET spawned_species_id = %s WHERE id = %s;",
                        (species_id, wl_id)
                    )

        conn.commit()
        result["xp_earned"] = xp_to_award

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
                result["xp_result"] = award_xp(slot1_id, xp_to_award, "exercise")
        except Exception:
            pass

        # Bônus de primeiro treino (+50 XP fora do cap diário)
        if is_first_workout and slot1_id:
            try:
                bonus_res = award_xp(slot1_id, _FIRST_WORKOUT_BONUS_XP, "first_workout_bonus")
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

        return result

    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result


# ── Workout Builder — write helpers ──────────────────────────────────────────

def get_workout_sheets(user_id: str) -> list[dict]:
    """Sheets owned by the user with day count."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ws.id, ws.name, COUNT(wd.id) AS day_count
                FROM workout_sheets ws
                LEFT JOIN workout_days wd ON wd.workout_sheet_id = ws.id
                WHERE ws.user_id = %s
                GROUP BY ws.id, ws.name
                ORDER BY ws.name;
            """, (user_id,))
            rows = cur.fetchall()
        return [{"id": str(r[0]), "name": r[1], "day_count": r[2]} for r in rows]
    except Exception:
        return []


def create_workout_sheet(user_id: str, name: str) -> str | None:
    """INSERT into workout_sheets; returns new UUID or None on error."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workout_sheets (user_id, name) VALUES (%s, %s) RETURNING id;",
                (user_id, name.strip()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id)
    except Exception:
        get_connection().rollback()
        return None


def delete_workout_sheet(sheet_id: str) -> bool:
    """DELETE a sheet (cascades to workout_days and workout_day_exercises)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_sheets WHERE id = %s;", (sheet_id,))
        conn.commit()
        return True
    except Exception:
        get_connection().rollback()
        return False


def create_workout_day(sheet_id: str, name: str) -> str | None:
    """INSERT into workout_days; returns new UUID or None on error."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workout_days (workout_sheet_id, name) VALUES (%s, %s) RETURNING id;",
                (sheet_id, name.strip()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id)
    except Exception:
        get_connection().rollback()
        return None


def delete_workout_day(day_id: str) -> bool:
    """DELETE a day (cascades to workout_day_exercises)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_days WHERE id = %s;", (day_id,))
        conn.commit()
        return True
    except Exception:
        get_connection().rollback()
        return False


def add_exercise_to_day(day_id: str, exercise_id: int, sets: int, reps: int) -> str | None:
    """INSERT into workout_day_exercises; returns new UUID or None on error."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workout_day_exercises (workout_day_id, exercise_id, sets, reps) VALUES (%s, %s, %s, %s) RETURNING id;",
                (day_id, exercise_id, sets, reps),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id)
    except Exception:
        get_connection().rollback()
        return None


def update_day_exercise(wde_id: str, sets: int, reps: int) -> bool:
    """UPDATE sets/reps for a prescribed exercise."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE workout_day_exercises SET sets = %s, reps = %s WHERE id = %s;",
                (sets, reps, wde_id),
            )
        conn.commit()
        return True
    except Exception:
        get_connection().rollback()
        return False


def remove_exercise_from_day(wde_id: str) -> bool:
    """DELETE a prescribed exercise from a day."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_day_exercises WHERE id = %s;", (wde_id,))
        conn.commit()
        return True
    except Exception:
        get_connection().rollback()
        return False


def get_sheet_days(sheet_id: str) -> list[dict]:
    """Days for a specific workout sheet with exercise count."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT wd.id, wd.name, COUNT(wde.id) AS exercise_count
                FROM workout_days wd
                LEFT JOIN workout_day_exercises wde ON wde.workout_day_id = wd.id
                WHERE wd.workout_sheet_id = %s
                GROUP BY wd.id, wd.name
                ORDER BY wd.name;
            """, (sheet_id,))
            return [{"id": str(r[0]), "name": r[1], "exercise_count": r[2]} for r in cur.fetchall()]
    except Exception:
        return []


def get_day_exercises_for_builder(day_id: str) -> list[dict]:
    """Prescribed exercises for a day, including wde.id for edit/delete."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT wde.id, e.id AS exercise_id,
                       COALESCE(e.name_pt, e.name) AS display_name,
                       wde.sets, wde.reps
                FROM workout_day_exercises wde
                JOIN exercises e ON e.id = wde.exercise_id
                WHERE wde.workout_day_id = %s
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


def check_and_award_achievements(user_id: str) -> list[str]:
    """Check every achievement condition and unlock newly eligible ones.

    Returns slugs of achievements unlocked during this call (empty if none new).
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

            new_unlocks: list[str] = []
            for slug, ach in CATALOG.items():
                if slug not in already and ach["check"](stats):
                    cur.execute("""
                        INSERT INTO user_achievements (user_id, achievement_slug)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id, achievement_slug) DO NOTHING
                        RETURNING achievement_slug;
                    """, (user_id, slug))
                    if cur.fetchone():
                        new_unlocks.append(slug)

            if new_unlocks:
                conn.commit()
            return new_unlocks
    except Exception:
        return []


# ── Leaderboard ───────────────────────────────────────────────────────────────

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
                WHERE EXTRACT(YEAR  FROM wl.logged_at AT TIME ZONE 'America/Sao_Paulo') = %s
                  AND EXTRACT(MONTH FROM wl.logged_at AT TIME ZONE 'America/Sao_Paulo') = %s
                GROUP BY pr.id, pr.username, ps.name, ps.sprite_url, up2.level
                ORDER BY value DESC
                LIMIT %s;
            """, (year, month, limit))
            cols = ["user_id", "username", "value", "lead_pokemon", "lead_sprite", "lead_level"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
