import os
import base64
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("host"),
        port=os.getenv("port"),
        dbname=os.getenv("database"),
        user=os.getenv("user"),
        password=os.getenv("password"),
    )


@st.cache_data
def get_image_as_base64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


# ── Pokédex queries ────────────────────────────────────────────────────────────

@st.cache_data
def get_all_pokemon() -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("SELECT id, name FROM pokemon_species ORDER BY id;")
        return cur.fetchall()


def get_pokemon_details(pokemon_id: int) -> tuple | None:
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url,
                   t1.name AS type1, t2.name AS type2, p.base_experience
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
                   fc.min_level, fc.trigger_name, fc.item_name
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

            # Add starter to user_pokemon
            cur.execute("""
                INSERT INTO user_pokemon (user_id, species_id, level, xp)
                VALUES (%s, %s, 1, 0)
                RETURNING id;
            """, (user_id, starter_id))
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
                       up.level, up.xp, t1.name AS type1, t2.name AS type2
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
                INSERT INTO user_pokemon (user_id, species_id, level, xp)
                VALUES (%s, %s, 1, 0) RETURNING id;
            """, (user_id, species_id))
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
            cur.execute("SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s;", (user_id, slot_a))
            row_a = cur.fetchone()
            cur.execute("SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s;", (user_id, slot_b))
            row_b = cur.fetchone()

            if not row_a or not row_b:
                return False

            # Swap via temp slot 99
            cur.execute("UPDATE user_team SET slot=99 WHERE user_id=%s AND slot=%s;", (user_id, slot_a))
            cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=%s;", (slot_a, user_id, slot_b))
            cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=99;", (slot_b, user_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
