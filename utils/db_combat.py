"""utils/db_combat.py — Batalhas PvP do LimitBreak.

Contém:
  - Constantes e helpers de batalha (_TYPE_CHART, _calc_damage,
    _type_effectiveness, _pokemon_max_hp, _best_move)
  - Operações de batalha (get_battle_opponents, get_daily_battle_count,
    start_battle, finalize_battle, get_battle_history, get_battle_detail)

Depende de db_core e db_user.
finalize_battle usa import tardio de award_xp (db_progression) para
evitar import circular.
"""

import random

from utils.db_core import (
    get_connection,
    _today_brt, _brt_day_bounds,
    _audit_and_sync_user_team_stats,
)
from utils.logger import logger

# ── Constantes ─────────────────────────────────────────────────────────────────

_MAX_BATTLES_PER_DAY = 3
_MAX_TURNS = 50

# Nível em que evoluções com triggers não-padrão são disparadas automaticamente.
_BYPASS_LEVEL = 36
_WIN_COINS = 1
_WIN_XP    = 30
_LOSS_XP   = 10

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


# ── Helpers de batalha ─────────────────────────────────────────────────────────

def _pokemon_max_hp(stat_hp: int, level: int) -> int:
    return max(1, stat_hp)


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
    """Fórmula oficial Pokémon com STAB, efetividade, crítico e roll aleatório."""
    if not power:
        return {"damage": 0, "critical": False, "effectiveness": 1.0, "stab": False}

    stab         = move_type_id in attacker_types if move_type_id else False
    effectiveness = _type_effectiveness(move_type_id, defender_types)
    critical      = random.random() < _CRIT_CHANCE

    base  = ((2 * level / 5 + 2) * power * (atk_stat / max(1, def_stat))) / 50 + 2
    dmg   = base
    dmg  *= 1.5 if stab else 1.0
    dmg  *= effectiveness
    dmg  *= _CRIT_MULT if critical else 1.0
    dmg  *= random.uniform(0.85, 1.0)

    return {
        "damage":        max(1, int(dmg)) if effectiveness > 0 else 0,
        "critical":      critical,
        "effectiveness": effectiveness,
        "stab":          stab,
    }


def _best_move(moves: list) -> dict:
    """Seleciona o move de maior power; fallback para Investida."""
    _tackle = {"name": "Investida", "power": 40, "damage_class": "physical", "id": None, "type_id": 1}
    if not moves:
        return _tackle
    pool = [m for m in moves if m["damage_class"] in ("physical", "special") and m["power"]]
    return max(pool, key=lambda m: m["power"]) if pool else _tackle


# ── Operações públicas ─────────────────────────────────────────────────────────

def get_battle_opponents(user_id: str) -> list:
    """Retorna outros usuários que têm Pokémon no slot 1, com dados do Pokémon."""
    with get_connection().cursor() as cur:
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
    return [
        {"username": r[0], "user_id": str(r[1]), "level": r[2],
         "pokemon_name": r[3], "sprite_url": r[4]}
        for r in rows
    ]


def get_daily_battle_count(user_id: str) -> int:
    """Quantidade de batalhas iniciadas hoje (como desafiante)."""
    start_ts, end_ts = _brt_day_bounds(_today_brt())
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM user_battles
            WHERE challenger_id = %s
              AND battled_at >= %s AND battled_at < %s;
        """, (user_id, start_ts, end_ts))
        return cur.fetchone()[0]


def start_battle(challenger_id: str, opponent_id: str) -> dict:
    """Inicia batalha: verifica limite diário, carrega pokémon e moves.

    Retorna estado inicial para manter em session_state.
    Não persiste nada no banco — apenas finalize_battle() persiste.
    """
    if get_daily_battle_count(challenger_id) >= _MAX_BATTLES_PER_DAY:
        return {"error": f"Limite de {_MAX_BATTLES_PER_DAY} batalhas por dia atingido."}

    conn = get_connection()
    with conn.cursor() as cur:
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

        _tackle = {"name": "Investida", "power": 40, "damage_class": "physical", "id": None, "type_id": 1}
        ch_moves = _load_moves(ch["id"]) or [_tackle]
        op_moves = _load_moves(op["id"]) or [_tackle]
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
            "turns": [], "turn_num": 0,
            "finished": False, "result": None, "winner_id": None,
        }


def finalize_battle(state: dict) -> dict:
    """Persiste batalha concluída no banco e concede XP/moedas."""
    challenger_id = state["challenger_id"]
    opponent_id   = state["opponent_id"]
    ch = state["ch"]
    op = state["op"]
    result    = state["result"]
    winner_id = state["winner_id"]
    turns     = state["turns"]

    ch_xp = _WIN_XP if result == "challenger_win" else _LOSS_XP
    op_xp = _WIN_XP if result == "opponent_win"   else _LOSS_XP
    coins = _WIN_COINS if winner_id else 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
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
        logger.exception(
            "finalize_battle falhou | challenger={} opponent={} result={}",
            challenger_id, opponent_id, result,
        )
        conn.rollback()
        return {"error": str(e)}

    # Import tardio para evitar import circular com db_progression
    from utils.db_progression import award_xp  # noqa: PLC0415
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
    with get_connection().cursor() as cur:
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
    cols = ["id", "result", "winner_id",
            "challenger_id", "challenger_name",
            "opponent_id", "opponent_name",
            "ch_pokemon", "op_pokemon",
            "ch_xp", "op_xp", "coins", "turn_count", "battled_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_battle_detail(battle_id: int) -> list:
    """Retorna todos os turnos de uma batalha."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT turn_number, attacker_pokemon_id, move_name, move_power,
                   damage, challenger_hp_remaining, opponent_hp_remaining
            FROM user_battle_turns
            WHERE battle_id = %s
            ORDER BY turn_number, id;
        """, (battle_id,))
        rows = cur.fetchall()
    cols = ["turn", "attacker_id", "move_name", "move_power", "damage", "ch_hp", "op_hp"]
    return [dict(zip(cols, r)) for r in rows]
