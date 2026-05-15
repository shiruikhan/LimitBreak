"""
db_progression.py — Progressão do usuário: check-in, XP, conquistas,
missões, rival semanal e desafio comunitário.

Dependências:
    db_core      → conexão, helpers BRT, stats helpers, _bump_happiness, _insert_user_pokemon
    db_combat    → _BYPASS_LEVEL
    db_shop      → get_xp_share_status, _extend_xp_share, _add_inventory_item,
                   _grant_loot_box, _LOOT_STONES
    db_workout   → (lazy) _pick_spawn_species, _shiny_roll, _pick_egg_species,
                   _EGG_WORKOUTS_TO_HATCH, _ensure_weekly_challenge

Ciclos resolvidos com lazy import dentro das funções:
    do_checkin          → db_workout._pick_spawn_species, _shiny_roll
    get_current_challenge / claim_weekly_challenge_reward → db_workout._pick_egg_species,
        _EGG_WORKOUTS_TO_HATCH, _ensure_weekly_challenge
"""
from __future__ import annotations

import datetime
import calendar as cal_module
import random

import psycopg2
import streamlit as st

from utils.logger import logger
from utils.db_core import (
    get_connection,
    _today_brt,
    _brt_day_bounds,
    _brt_date_range_bounds,
    _unique_workout_days_brt,
    _compute_streak_from_days,
    _insert_user_pokemon,
    _bump_happiness,
    _LOOT_VITAMINS,
    _recalc_stats_on_evolution,
    _recalc_stats_for_level,
)
from utils.db_combat import _BYPASS_LEVEL
from utils.db_shop import (
    get_xp_share_status,
    _extend_xp_share,
    _add_inventory_item,
    _grant_loot_box,
    _LOOT_STONES,
)


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
            "spawn_rolled":  bool,
            "spawned": {id, name, sprite_url, type1} | None,
        }
    """
    # Lazy imports to break db_workout ↔ db_progression cycle
    from utils.db_workout import _pick_spawn_species, _shiny_roll  # noqa: PLC0415

    conn    = get_connection()
    today   = _today_brt()
    result  = {
        "success": False, "already_done": False,
        "streak": 0, "coins_earned": 0,
        "bonus_xp_share": False, "spawn_rolled": False, "spawned": None,
        "shield_used": False, "bonus_shield": False,
    }

    try:
        with conn.cursor() as cur:

            # ── Streak ────────────────────────────────────────────────────────
            cur.execute("""
                SELECT checked_date, streak FROM user_checkins
                WHERE user_id = %s ORDER BY checked_date DESC LIMIT 1;
            """, (user_id,))
            last = cur.fetchone()
            if last:
                gap = (today - last[0]).days
                if gap == 1:
                    streak = last[1] + 1
                elif gap == 2:
                    # One missed day — check for streak-shield in inventory
                    cur.execute("""
                        SELECT ui.item_id, ui.quantity FROM user_inventory ui
                        JOIN shop_items si ON si.id = ui.item_id
                        WHERE ui.user_id = %s AND si.slug = 'streak-shield' AND ui.quantity > 0;
                    """, (user_id,))
                    shield_row = cur.fetchone()
                    if shield_row:
                        shield_item_id, shield_qty = shield_row
                        streak = last[1] + 1
                        if shield_qty > 1:
                            cur.execute(
                                "UPDATE user_inventory SET quantity = quantity - 1"
                                " WHERE user_id = %s AND item_id = %s;",
                                (user_id, shield_item_id),
                            )
                        else:
                            cur.execute(
                                "DELETE FROM user_inventory WHERE user_id = %s AND item_id = %s;",
                                (user_id, shield_item_id),
                            )
                        result["shield_used"] = True
                    else:
                        streak = 1
                else:
                    streak = 1
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

            # ── Streak Shield: concessão nos dias 7 e 21 ──────────────────────
            if today.day in (7, 21):
                cur.execute("SELECT id FROM shop_items WHERE slug = 'streak-shield';")
                _sr = cur.fetchone()
                if _sr:
                    cur.execute("""
                        INSERT INTO user_inventory (user_id, item_id, quantity)
                        VALUES (%s, %s, 1)
                        ON CONFLICT (user_id, item_id)
                        DO UPDATE SET quantity = user_inventory.quantity + 1;
                    """, (user_id, _sr[0]))
                    result["bonus_shield"] = True

            # ── Spawn em múltiplo de 3 (garantido — 100%) ────────────────────
            spawned_species_id = None
            if streak % 3 == 0:
                result["spawn_rolled"] = True
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
        xp_result = None
        slot1_id_checkin = None
        try:
            with get_connection().cursor() as cur2:
                cur2.execute("""
                    SELECT up.id FROM user_team ut
                    JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                    WHERE ut.user_id = %s AND ut.slot = 1;
                """, (user_id,))
                main_row = cur2.fetchone()
            if main_row:
                slot1_id_checkin = main_row[0]
                xp_result = award_xp(slot1_id_checkin, 10, "check-in")
        except Exception:
            pass  # XP é bônus — falha silenciosa para não cancelar o check-in
        result["xp_result"] = xp_result

        # +1 happiness no slot 1 pelo check-in
        try:
            if slot1_id_checkin:
                _hconn = get_connection()
                with _hconn.cursor() as _hc:
                    _bump_happiness(_hc, slot1_id_checkin, 1)
                _hconn.commit()
        except Exception:
            pass

        return result

    except Exception as e:
        logger.exception("do_checkin falhou | user_id={}", user_id)
        conn.rollback()
        result["error"] = str(e)
        return result


# ── Descanso e Felicidade ──────────────────────────────────────────────────────

def register_rest(user_id: str) -> dict:
    """Registra um dia de descanso para o usuário.

    Não quebra o streak de check-in. Concede +5 happiness ao Pokémon do slot 1.

    Returns:
        {"success": bool, "already_done": bool, "happiness_gained": int, "error": str | None}
    """
    result = {"success": False, "already_done": False, "happiness_gained": 0, "error": None}
    conn  = get_connection()
    today = _today_brt()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO user_rest_days (user_id, rest_date) VALUES (%s, %s);
                """, (user_id, today))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                result["already_done"] = True
                return result

            cur.execute("""
                SELECT up.id FROM user_team ut
                JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                WHERE ut.user_id = %s AND ut.slot = 1;
            """, (user_id,))
            row = cur.fetchone()
            if row:
                _bump_happiness(cur, row[0], 5)

        conn.commit()
        result["success"] = True
        result["happiness_gained"] = 5
        return result
    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result


def get_monthly_rest_days(user_id: str, year: int, month: int) -> set:
    """Retorna conjunto de números de dias com descanso registrado no mês."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT EXTRACT(DAY FROM rest_date)::int
                FROM user_rest_days
                WHERE user_id = %s
                  AND EXTRACT(YEAR  FROM rest_date) = %s
                  AND EXTRACT(MONTH FROM rest_date) = %s;
            """, (user_id, year, month))
            return {r[0] for r in cur.fetchall()}
    except Exception:
        return set()


# ── XP Share ──────────────────────────────────────────────────────────────────

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
                SELECT level, xp, species_id, user_id, happiness
                FROM user_pokemon WHERE id = %s FOR UPDATE;
            """, (user_pokemon_id,))
            row = cur.fetchone()
            if not row:
                result["error"] = "Pokémon não encontrado."
                return result

            level, xp, species_id, user_id, happiness = row
            happiness = happiness or 70
            result["old_level"] = level

            # Happiness XP modifier: ≥180 → +5%, <50 → −5%
            if happiness >= 180:
                amount = max(1, int(amount * 1.05))
            elif happiness < 50:
                amount = max(1, int(amount * 0.95))

            xp += amount

            # ── Loop de level-up ──────────────────────────────────────────────
            happiness_delta = 0
            while xp >= level * 100 and level < 100:
                xp    -= level * 100
                level += 1
                result["levels_gained"] += 1
                happiness_delta += 2  # +2 happiness per level-up

                if len(result["evolutions"]) < 3:
                    cur.execute("""
                        SELECT e.to_species_id, p2.name, p2.sprite_url,
                               p1.name AS from_name, p1.sprite_url AS from_sprite
                        FROM pokemon_evolutions e
                        JOIN pokemon_species p2 ON e.to_species_id = p2.id
                        JOIN pokemon_species p1 ON e.from_species_id = p1.id
                        WHERE e.from_species_id = %s
                          AND (
                              (e.trigger_name = 'level-up' AND e.min_level <= %s
                               AND (e.min_happiness IS NULL OR %s >= e.min_happiness))
                              OR (e.trigger_name NOT IN ('level-up', 'use-item', 'shed')
                                  AND e.min_happiness IS NULL AND %s >= %s)
                          )
                        ORDER BY e.min_level DESC NULLS LAST
                        LIMIT 1;
                    """, (species_id, level, happiness + happiness_delta, level, _BYPASS_LEVEL))
                    evo = cur.fetchone()
                    if evo:
                        to_id, to_name, to_sprite, from_name, from_sprite = evo
                        result["evolutions"].append({
                            "from_name":       from_name,
                            "from_sprite_url": from_sprite or "",
                            "to_name":         to_name,
                            "to_id":           to_id,
                            "sprite_url":      to_sprite,
                        })

                        # Shed mechanic
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

                        species_id = to_id

            # Ao atingir o cap: congela XP em 0
            if level >= 100:
                level = 100
                xp = 0

            cur.execute("""
                UPDATE user_pokemon
                SET level = %s, xp = %s, species_id = %s,
                    happiness = LEAST(255, GREATEST(0, happiness + %s))
                WHERE id = %s;
            """, (level, xp, species_id, happiness_delta, user_pokemon_id))

            if result["evolutions"]:
                _recalc_stats_on_evolution(cur, user_pokemon_id)
            elif result["levels_gained"] > 0:
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
        logger.exception("award_xp falhou | user_pokemon_id={} source={}", user_pokemon_id, source)
        conn.rollback()
        result["error"] = str(e)
        return result


# ── Achievements ──────────────────────────────────────────────────────────────

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
    """Collects all stats needed to evaluate achievement conditions.

    Executes a single SQL query with parallel CTEs instead of 9 round-trips,
    then computes workout_streak in Python (requires row-by-row gap analysis).
    """
    cur.execute("""
        WITH
        pokemon_stats AS (
            SELECT
                COUNT(*)                                                 AS pokemon_count,
                COALESCE(BOOL_OR(up.is_shiny), false)                   AS has_shiny,
                COALESCE(BOOL_OR(ps.id > 10000), false)                 AS has_regional
            FROM user_pokemon up
            JOIN pokemon_species ps ON ps.id = up.species_id
            WHERE up.user_id = %s
        ),
        checkin_stats AS (
            SELECT COALESCE(MAX(streak), 0) AS checkin_streak_max
            FROM user_checkins
            WHERE user_id = %s
        ),
        workout_stats AS (
            SELECT COUNT(*) AS workout_count
            FROM workout_logs
            WHERE user_id = %s
        ),
        battle_stats AS (
            SELECT COUNT(*) AS battle_wins
            FROM user_battles
            WHERE winner_id = %s
        ),
        evolution_stats AS (
            SELECT
                COUNT(DISTINCT up.id) > 0                                           AS has_evolved_pokemon,
                COUNT(DISTINCT CASE WHEN pe.trigger_name = 'use-item' THEN up.id END) > 0 AS has_stone_evolved,
                COUNT(DISTINCT up.id)                                               AS evolved_count
            FROM user_pokemon up
            JOIN pokemon_evolutions pe ON pe.to_species_id = up.species_id
            WHERE up.user_id = %s
        ),
        pr_ranked AS (
            SELECT
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
        pr_stats AS (
            SELECT COUNT(*) AS pr_count
            FROM (
                SELECT session_best,
                       LAG(session_best) OVER (PARTITION BY exercise_id ORDER BY rn) AS prev_best
                FROM pr_ranked
            ) t
            WHERE prev_best IS NOT NULL AND session_best > prev_best
        )
        SELECT
            ps.pokemon_count,
            ps.has_shiny,
            ps.has_regional,
            cs.checkin_streak_max,
            ws.workout_count,
            bs.battle_wins,
            es.has_evolved_pokemon,
            es.has_stone_evolved,
            es.evolved_count,
            prs.pr_count
        FROM pokemon_stats   ps
        CROSS JOIN checkin_stats   cs
        CROSS JOIN workout_stats   ws
        CROSS JOIN battle_stats    bs
        CROSS JOIN evolution_stats es
        CROSS JOIN pr_stats        prs;
    """, (user_id,) * 6)

    row = cur.fetchone()
    stats: dict = {
        "pokemon_count":      row[0],
        "has_shiny":          row[1],
        "has_regional":       row[2],
        "checkin_streak_max": row[3],
        "workout_count":      row[4],
        "battle_wins":        row[5],
        "has_evolved_pokemon": row[6],
        "has_stone_evolved":  row[7],
        "evolved_count":      row[8],
        "pr_count":           row[9],
    }

    stats["workout_streak"] = _compute_streak_from_days(_unique_workout_days_brt(cur, user_id))

    return stats


def check_and_award_achievements(user_id: str) -> list[dict]:
    """Check every achievement condition and unlock newly eligible ones.

    Returns list of {slug, loot} for achievements unlocked during this call.
    """
    from utils.achievements import CATALOG  # noqa: PLC0415
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


# ── Missões ────────────────────────────────────────────────────────────────────

def _week_start(d: datetime.date) -> datetime.date:
    """Return the Monday of the week containing date d (BRT)."""
    return d - datetime.timedelta(days=d.weekday())


def get_current_mission_periods() -> tuple[datetime.date, datetime.date]:
    """Return current BRT daily and weekly mission period keys."""
    today = _today_brt()
    return today, _week_start(today)


def _ensure_missions(cur, user_id: str) -> None:
    """Generate daily (3) and weekly (1) missions for the current period if absent."""
    from utils.missions import pick_daily_slugs, pick_weekly_slug, get_mission  # noqa: PLC0415
    today, week_start = get_current_mission_periods()

    cur.execute(
        "SELECT mission_slug FROM user_missions WHERE user_id = %s AND mission_type = 'daily' AND period_start = %s;",
        (user_id, today),
    )
    existing_daily = {r[0] for r in cur.fetchall()}
    if len(existing_daily) < 3:
        needed = 3 - len(existing_daily)
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


def ensure_current_user_missions(user_id: str) -> None:
    """Ensure mission rows exist for the current daily and weekly periods."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            _ensure_missions(cur, user_id)
        conn.commit()
    except Exception:
        return


def get_user_missions(user_id: str) -> dict:
    """Return {'daily': [...], 'weekly': [...]} for the current period."""
    from utils.missions import get_mission  # noqa: PLC0415
    today, week_start = get_current_mission_periods()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
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

    Returns list of mission dicts that were newly completed by this call.
    """
    from utils.missions import get_mission  # noqa: PLC0415
    if data is None:
        data = {}

    today = _today_brt()
    week_start = _week_start(today)

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
    """
    from utils.missions import get_mission  # noqa: PLC0415
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

        # Apply XP post-commit
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


# ── Rival Semanal ──────────────────────────────────────────────────────────────

def _monday_of(d: datetime.date) -> datetime.date:
    """Returns the Monday of the ISO week that contains `d`."""
    return d - datetime.timedelta(days=d.weekday())


def assign_weekly_rival(user_id: str) -> dict:
    """Assigns a weekly rival for the current week (idempotent if already assigned).

    On re-assignment (Monday), checks if the user beat last week's rival and
    awards +10 coins if so.

    Returns:
        {rival_id, rival_username, rival_xp, my_xp, won_last_week, bonus_coins}
        or {} on error / no other users.
    """
    today = _today_brt()
    this_monday = _monday_of(today)
    last_monday = this_monday - datetime.timedelta(weeks=1)
    last_sunday = this_monday - datetime.timedelta(days=1)
    this_week_start_ts, _ = _brt_day_bounds(this_monday)
    last_week_start_ts, last_week_end_ts = _brt_date_range_bounds(last_monday, last_sunday)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT weekly_rival_id, rival_assigned_week FROM user_profiles WHERE id = %s;",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            current_rival_id, assigned_week = row

            won_last_week = False
            bonus_coins = 0

            needs_assign = (assigned_week is None or assigned_week < this_monday)

            if needs_assign and current_rival_id and assigned_week:
                cur.execute("""
                    SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                    WHERE user_id = %s
                      AND completed_at >= %s
                      AND completed_at < %s;
                """, (user_id, last_week_start_ts, last_week_end_ts))
                my_last_xp = cur.fetchone()[0] or 0

                cur.execute("""
                    SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                    WHERE user_id = %s
                      AND completed_at >= %s
                      AND completed_at < %s;
                """, (current_rival_id, last_week_start_ts, last_week_end_ts))
                rival_last_xp = cur.fetchone()[0] or 0

                if my_last_xp > rival_last_xp:
                    won_last_week = True
                    bonus_coins = 10
                    cur.execute(
                        "UPDATE user_profiles SET coins = coins + 10 WHERE id = %s;",
                        (user_id,),
                    )

            if needs_assign:
                cur.execute("""
                    SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                    WHERE user_id = %s AND completed_at >= %s;
                """, (user_id, this_week_start_ts))
                my_xp = cur.fetchone()[0] or 0

                cur.execute("""
                    SELECT up.id, COALESCE(SUM(wl.xp_earned), 0) AS week_xp
                    FROM user_profiles up
                    LEFT JOIN workout_logs wl ON wl.user_id = up.id
                      AND wl.completed_at >= %s
                    WHERE up.id != %s
                    GROUP BY up.id
                    ORDER BY ABS(COALESCE(SUM(wl.xp_earned), 0) - %s)
                    LIMIT 1;
                """, (this_week_start_ts, user_id, my_xp))
                rival_row = cur.fetchone()
                if not rival_row:
                    conn.commit()
                    return {"won_last_week": won_last_week, "bonus_coins": bonus_coins}

                new_rival_id = rival_row[0]
                cur.execute(
                    "UPDATE user_profiles SET weekly_rival_id = %s, rival_assigned_week = %s WHERE id = %s;",
                    (new_rival_id, this_monday, user_id),
                )
                conn.commit()
                current_rival_id = new_rival_id
            else:
                conn.commit()

            if not current_rival_id:
                return {"won_last_week": won_last_week, "bonus_coins": bonus_coins}

            cur.execute(
                "SELECT username FROM user_profiles WHERE id = %s;",
                (current_rival_id,),
            )
            rival_name_row = cur.fetchone()
            rival_username = rival_name_row[0] if rival_name_row else "???"

            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                WHERE user_id = %s AND completed_at >= %s;
            """, (user_id, this_week_start_ts))
            my_xp = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                WHERE user_id = %s AND completed_at >= %s;
            """, (current_rival_id, this_week_start_ts))
            rival_xp = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT ps.sprite_url FROM user_team ut
                JOIN user_pokemon up ON up.id = ut.user_pokemon_id
                JOIN pokemon_species ps ON ps.id = up.species_id
                WHERE ut.user_id = %s AND ut.slot = 1;
            """, (current_rival_id,))
            sprite_row = cur.fetchone()
            rival_sprite = sprite_row[0] if sprite_row else None

            return {
                "rival_id": str(current_rival_id),
                "rival_username": rival_username,
                "rival_xp": int(rival_xp),
                "my_xp": int(my_xp),
                "rival_sprite": rival_sprite,
                "won_last_week": won_last_week,
                "bonus_coins": bonus_coins,
            }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}


def get_rival_status(user_id: str) -> dict:
    """Lightweight read of current week rival XP comparison (no writes).

    Returns {rival_username, rival_xp, my_xp, diff, rival_sprite} or {}.
    """
    today = _today_brt()
    this_monday = _monday_of(today)
    this_week_start_ts, _ = _brt_day_bounds(this_monday)
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                "SELECT weekly_rival_id FROM user_profiles WHERE id = %s;",
                (user_id,),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return {}
            rival_id = row[0]

            cur.execute(
                "SELECT username FROM user_profiles WHERE id = %s;",
                (rival_id,),
            )
            rival_name_row = cur.fetchone()
            if not rival_name_row:
                return {}
            rival_username = rival_name_row[0]

            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                WHERE user_id = %s AND completed_at >= %s;
            """, (user_id, this_week_start_ts))
            my_xp = int(cur.fetchone()[0] or 0)

            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
                WHERE user_id = %s AND completed_at >= %s;
            """, (rival_id, this_week_start_ts))
            rival_xp = int(cur.fetchone()[0] or 0)

            cur.execute("""
                SELECT ps.sprite_url FROM user_team ut
                JOIN user_pokemon up ON up.id = ut.user_pokemon_id
                JOIN pokemon_species ps ON ps.id = up.species_id
                WHERE ut.user_id = %s AND ut.slot = 1;
            """, (rival_id,))
            sprite_row = cur.fetchone()
            rival_sprite = sprite_row[0] if sprite_row else None

            return {
                "rival_username": rival_username,
                "rival_xp": rival_xp,
                "my_xp": my_xp,
                "diff": my_xp - rival_xp,
                "rival_sprite": rival_sprite,
            }
    except Exception:
        return {}


# ── Desafio Comunitário Semanal ───────────────────────────────────────────────

_CHALLENGE_GOAL_LABELS = {
    "total_xp":       "a comunidade acumular {goal} XP",
    "total_workouts": "a comunidade completar {goal} sessões de treino",
    "total_sets":     "a comunidade completar {goal} séries no total",
}


def get_current_challenge(user_id: str) -> dict | None:
    """Returns state of this week's community challenge for a specific user.

    Returns:
        {challenge_id, description, goal_value, current_value, completed,
         user_contributed, reward_claimed, reward_item_slug, reward_quantity}
        or None if no challenge exists yet.
    """
    # Lazy import to break db_workout ↔ db_progression cycle
    from utils.db_workout import _ensure_weekly_challenge  # noqa: PLC0415

    today = _today_brt()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            challenge_id = _ensure_weekly_challenge(cur)
            conn.commit()
            if challenge_id is None:
                return None

            cur.execute("""
                SELECT goal_type, goal_value, current_value, completed,
                       reward_item_slug, reward_quantity
                FROM weekly_challenges WHERE id = %s;
            """, (challenge_id,))
            ch = cur.fetchone()
            if not ch:
                return None
            goal_type, goal_value, current_value, completed, reward_slug, reward_qty = ch

            cur.execute("""
                SELECT contributed, reward_claimed FROM weekly_challenge_participants
                WHERE challenge_id = %s AND user_id = %s;
            """, (challenge_id, user_id))
            part = cur.fetchone()
            user_contributed = part[0] if part else 0
            reward_claimed   = part[1] if part else False

            label_tmpl = _CHALLENGE_GOAL_LABELS.get(goal_type, "completar o desafio semanal")
            description = label_tmpl.format(goal=f"{goal_value:,}")

            return {
                "challenge_id":    challenge_id,
                "description":     description,
                "goal_type":       goal_type,
                "goal_value":      goal_value,
                "current_value":   current_value,
                "completed":       completed,
                "user_contributed": user_contributed,
                "reward_claimed":  reward_claimed,
                "reward_item_slug": reward_slug,
                "reward_quantity": reward_qty,
            }
    except Exception:
        return None


def claim_weekly_challenge_reward(user_id: str) -> tuple[bool, str, dict]:
    """Claims the community challenge reward for this week.

    Returns (success, message, reward_dict).
    """
    # Lazy imports to break db_workout ↔ db_progression cycle
    from utils.db_workout import _pick_egg_species, _EGG_WORKOUTS_TO_HATCH  # noqa: PLC0415

    today = _today_brt()
    this_monday = today - datetime.timedelta(days=today.weekday())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, completed, reward_item_slug, reward_quantity
                FROM weekly_challenges WHERE week_start = %s;
            """, (this_monday,))
            ch = cur.fetchone()
            if not ch:
                return False, "Nenhum desafio ativo esta semana.", {}
            challenge_id, completed, reward_slug, reward_qty = ch

            if not completed:
                return False, "O desafio ainda não foi concluído pela comunidade.", {}

            cur.execute("""
                SELECT contributed, reward_claimed FROM weekly_challenge_participants
                WHERE challenge_id = %s AND user_id = %s;
            """, (challenge_id, user_id))
            part = cur.fetchone()
            if not part or part[0] <= 0:
                return False, "Você não contribuiu para este desafio.", {}
            if part[1]:
                return False, "Recompensa já coletada.", {}

            if reward_slug == "egg":
                granted_eggs = []
                for _ in range(reward_qty):
                    rarity = "uncommon"
                    species_id = _pick_egg_species(cur, user_id, rarity)
                    if species_id is None:
                        species_id = _pick_egg_species(cur, user_id, "common")
                        rarity = "common"
                    if species_id is not None:
                        workouts_to_hatch = _EGG_WORKOUTS_TO_HATCH[rarity]
                        cur.execute("""
                            INSERT INTO user_eggs (user_id, species_id, rarity, workouts_to_hatch)
                            VALUES (%s, %s, %s, %s);
                        """, (user_id, species_id, rarity, workouts_to_hatch))
                        granted_eggs.append({"rarity": rarity, "workouts_to_hatch": workouts_to_hatch})
                reward_display = "1× Ovo de Pokémon 🥚"
            else:
                cur.execute("SELECT id, name FROM shop_items WHERE slug = %s;", (reward_slug,))
                item_row = cur.fetchone()
                if not item_row:
                    return False, "Item de recompensa não encontrado.", {}
                item_id, item_name = item_row
                for _ in range(reward_qty):
                    _add_inventory_item(cur, user_id, item_id)
                granted_eggs = []
                reward_display = f"{reward_qty}× {item_name}"

            cur.execute("""
                UPDATE weekly_challenge_participants
                SET reward_claimed = TRUE
                WHERE challenge_id = %s AND user_id = %s;
            """, (challenge_id, user_id))

        conn.commit()
        return True, f"🥚 Recompensa coletada: {reward_display}!", {
            "item_slug": reward_slug,
            "item_name": reward_display,
            "quantity":  reward_qty,
            "eggs":      granted_eggs,
        }
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao coletar recompensa: {e}", {}
