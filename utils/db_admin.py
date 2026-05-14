"""
db_admin.py — Painel administrativo: leaderboard, funções de admin, logs e gifts.

Dependências:
    db_core       → get_connection, _brt_month_bounds
    db_shop       → _grant_loot_box
    db_workout    → get_exercises.clear(), get_distinct_body_parts.clear()
    db_progression → (lazy) award_xp  (admin_gift_xp_bag)
"""
from __future__ import annotations

import json as _json

import streamlit as st

from utils.logger import logger
from utils.db_core import get_connection, _brt_month_bounds
from utils.db_shop import _grant_loot_box


# ── Admin gifts ────────────────────────────────────────────────────────────────

def admin_gift_loot_box(
    admin_id: str, target_user_id: str, count: int = 1
) -> tuple[bool, str, list[dict]]:
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


def admin_gift_xp_bag(
    admin_id: str, target_user_id: str, xp_amount: int = 1000
) -> tuple[bool, str, list[dict]]:
    """Concede XP diretamente a todos os Pokémon da equipe ativa de um usuário.

    XP Share é ignorado: cada membro recebe xp_amount individualmente.
    Retorna (success, message, list[{name, old_level, new_level, xp_given, evolutions}]).
    """
    # Lazy import to avoid db_admin → db_progression cycle at module level
    from utils.db_progression import award_xp  # noqa: PLC0415

    if xp_amount < 1 or xp_amount > 10_000:
        return False, "Quantidade de XP deve estar entre 1 e 10.000.", []
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM user_profiles WHERE id = %s", (target_user_id,))
            if not cur.fetchone():
                return False, "Usuário não encontrado.", []

            cur.execute("""
                SELECT ut.slot, up.id, p.name
                FROM user_team ut
                JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                JOIN pokemon_species p ON up.species_id = p.id
                WHERE ut.user_id = %s
                ORDER BY ut.slot;
            """, (target_user_id,))
            team = cur.fetchall()

        if not team:
            return False, "O usuário não possui Pokémon na equipe ativa.", []

        results = []
        for slot, up_id, poke_name in team:
            xp_result = award_xp(up_id, xp_amount, "xp_bag", _distributing=True)
            results.append({
                "slot": slot,
                "name": poke_name,
                "xp_given": xp_amount,
                "old_level": xp_result.get("old_level", 0),
                "new_level": xp_result.get("new_level", 0),
                "levels_gained": xp_result.get("levels_gained", 0),
                "evolutions": xp_result.get("evolutions", []),
                "error": xp_result.get("error"),
            })

        log_admin_action(
            admin_id, "gift_xp_bag",
            target_type="user", target_id=target_user_id,
            details={"xp_amount": xp_amount, "pokemon_count": len(team)},
        )
        return True, f"Bolsa de XP concedida: {xp_amount} XP para {len(team)} Pokémon da equipe.", results
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
    # Lazy imports to access cache-clear functions from db_workout
    from utils.db_workout import get_exercises, get_distinct_body_parts  # noqa: PLC0415

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
        start_ts, end_ts = _brt_month_bounds(year, month)
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
                WHERE wl.completed_at >= %s
                  AND wl.completed_at < %s
                GROUP BY pr.id, pr.username, ps.name, ps.sprite_url, up2.level
                ORDER BY value DESC
                LIMIT %s;
            """, (start_ts, end_ts, limit))
            cols = ["user_id", "username", "value", "lead_pokemon", "lead_sprite", "lead_level"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


# ── Admin CRUD ────────────────────────────────────────────────────────────────

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


def log_admin_action(
    user_id: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    try:
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


def get_system_logs(
    limit: int = 200, action_filter: str = "", user_filter: str = ""
) -> list[dict]:
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
