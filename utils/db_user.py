"""utils/db_user.py — Operações de usuário, equipe e stats do LimitBreak.

Contém:
  - Perfil de usuário (get_user_profile, create_user_profile)
  - Equipe ativa e banco (get_user_team, get_user_bench, add_to_team,
    set_team_slot, remove_from_team, swap_team_slots)
  - Captura e IDs de Pokémon (capture_pokemon, get_user_pokemon_ids)
  - Movimentos equipados (get_available_moves, get_active_moves,
    equip_move, unequip_move)
  - Stat boosts de vitaminas (apply_stat_boost, get_stat_boosts,
    get_stat_boost_summary, get_team_stat_boost_counts)

Depende apenas de db_core.
"""

import streamlit as st
from utils.db_core import (
    get_connection,
    _insert_user_pokemon,
    _nature_select_sql,
    _nature_payload,
)

# ── Constantes de stat boost ───────────────────────────────────────────────────

# Stats válidos — usados como whitelist antes de interpolar no nome da coluna
_VALID_STATS = frozenset({"hp", "attack", "defense", "sp_attack", "sp_defense", "speed"})
_MAX_STAT_BOOSTS_PER_STAT = 5  # vitaminas por stat por Pokémon


# ── Perfil ─────────────────────────────────────────────────────────────────────

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


# ── Equipe ─────────────────────────────────────────────────────────────────────

def get_user_team(user_id: str) -> list[dict]:
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            nature_select = _nature_select_sql()
            cur.execute(f"""
                SELECT ut.slot, up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp, t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       p.base_hp, p.base_attack, p.base_defense,
                       p.base_sp_attack, p.base_sp_defense, p.base_speed,
                       {nature_select},
                       p.ability_slug,
                       up.is_shiny, p.sprite_shiny_url,
                       up.happiness
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
                    "happiness": r[25] if len(r) > 25 else 70,
                }
                for r in rows
            ]
    except Exception:
        return []


def get_user_bench(user_id: str) -> list[dict]:
    """Retorna todos os user_pokemon do usuário que NÃO estão na equipe ativa."""
    try:
        with get_connection().cursor() as cur:
            nature_select = _nature_select_sql()
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
                ORDER BY up.level DESC, up.id DESC
                LIMIT 200;
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


# ── Captura ────────────────────────────────────────────────────────────────────

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


# ── Movimentos ─────────────────────────────────────────────────────────────────

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


# ── Stat boosts (vitaminas) ────────────────────────────────────────────────────

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
            cur.execute("""
                SELECT COUNT(*) FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s AND stat = %s AND delta > 0;
            """, (user_pokemon_id, stat))
            if cur.fetchone()[0] >= _MAX_STAT_BOOSTS_PER_STAT:
                return False

            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, delta, source_item))

            # stat é validado pela whitelist acima — seguro interpolar
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
    """Retorna o total acumulado de boosts por stat para um Pokémon."""
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
