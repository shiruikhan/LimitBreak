"""db_workout.py — Exercise catalogue, workout logging, spawn logic, PR detection,
egg system, weekly challenge helpers, workout builder CRUD, and training analytics.

All external callers should import from utils.db (the facade), not directly from
this module, so that re-export aliases remain stable.

Circular-dependency note:
    do_exercise_event() calls award_xp() from db_progression.  To break the
    import cycle, award_xp is imported lazily *inside* the function body.
"""
from __future__ import annotations

import datetime
import json
import random

import streamlit as st

from utils.logger import logger
from utils.db_core import (
    get_connection,
    _today_brt,
    _brt_day_bounds,
    _brt_date_range_bounds,
    _to_brt_date,
    _unique_workout_days_brt,
    _compute_streak_from_days,
    _insert_user_pokemon,
    _bump_happiness,
    _LOOT_VITAMINS,
    _workout_days_sheet_fk,
    _workout_day_exercises_day_fk,
)
from utils.db_shop import _add_inventory_item
from utils.abilities import apply_blaze as _apply_blaze

# ── Constants ──────────────────────────────────────────────────────────────────

_EXERCISE_XP_DAILY_CAP        = 300
_WEEKEND_XP_MULTIPLIER        = 2      # dobro de XP e cap nas sex/sab/dom
_FIRST_WORKOUT_BONUS_XP       = 50
_EXERCISE_REP_XP_DIVISOR      = 2
_EXERCISE_WEIGHT_XP_DIVISOR   = 20
_MAX_DAILY_SPAWNS              = 1
_EXERCISE_SPAWN_CHANCE         = 0.25
_EXERCISE_DISTANCE_XP_PER_100M = 100   # 1 XP per 100 m (5 km run = 50 XP)
_EXERCISE_TIME_XP_PER_30S      = 30    # 1 XP per 30 s  (10 min = 20 XP)

_PR_XP_BONUS        = 50   # XP awarded per personal record
_PR_MAX_PER_SESSION = 3    # cap on how many PR bonuses can fire in one session

# Egg system
_EGG_MILESTONES: dict[int, str]       = {25: "uncommon", 50: "rare", 100: "rare"}
_EGG_WORKOUTS_TO_HATCH: dict[str, int] = {"common": 5, "uncommon": 8, "rare": 12}

# Weighted spawn tiers — legendary/mythical excluded via is_spawnable=FALSE in DB.
_SPAWN_TIER_WEIGHTS: dict[str, int] = {
    "common":   60,
    "uncommon": 30,
    "rare":      9,
}

# Weekly challenge
_CHALLENGE_TYPES       = ["total_xp", "total_workouts", "total_sets"]
_CHALLENGE_REWARD_SLUG = "egg"  # special slug — granted via user_eggs, not shop_items

# body_parts (campo de exercises) → slugs de tipo Pokémon para spawn temático.
_BODY_PART_TYPES: dict[str, list[str]] = {
    "Peitoral":             ["fighting", "normal"],
    "Braços":               ["fighting", "poison"],
    "Bíceps":               ["fighting", "poison"],
    "Tríceps":              ["fighting", "poison"],
    "Antebraços":           ["normal",   "fighting"],
    "Costas":               ["dark",     "flying"],
    "Costas Superiores":    ["dark",     "flying"],
    "Latíssimo":            ["dark",     "flying"],
    "Coluna":               ["rock",     "ground"],
    "Ombros":               ["flying",   "psychic"],
    "Deltoides":            ["flying",   "psychic"],
    "Elevador da Escápula": ["flying",   "steel"],
    "Trapézio":             ["rock",     "normal"],
    "Coxas":                ["ground",   "fighting"],
    "Pernas":               ["ground",   "rock"],
    "Cintura":              ["steel",    "rock"],
    "Pescoço":              ["rock",     "normal"],
    "Cardio":               ["water",    "electric"],
}

# ── Internal helpers ───────────────────────────────────────────────────────────

def is_weekend_bonus() -> bool:
    """Retorna True se hoje (BRT) é sexta (5), sábado (6) ou domingo (7).

    Nesses dias o XP de treino é multiplicado por _WEEKEND_XP_MULTIPLIER
    e o cap diário também dobra (300 → 600).
    """
    return _today_brt().isoweekday() in (5, 6, 7)


def _ranked_spawn_types(exercises: list[dict], bp_map: dict[int, list[str]]) -> list[str]:
    """Returns type slugs ordered by frequency across the session's body parts."""
    type_counts: dict[str, int] = {}
    for ex in exercises:
        for bp in bp_map.get(ex["exercise_id"], []):
            for t in _BODY_PART_TYPES.get(bp, []):
                type_counts[t] = type_counts.get(t, 0) + 1
    return sorted(type_counts, key=lambda t: type_counts[t], reverse=True)


def _calc_exercise_xp(exercises: list[dict]) -> int:
    """Raw XP for a session broken down by metric_type.

    - weight:   CEIL(reps / 2) + FLOOR(weight_kg / 20) per set
    - distance: FLOOR(distance_m / 100) per entry  →  1 XP / 100 m
    - time:     FLOOR(duration_s / 30) per entry   →  1 XP / 30 s
    """
    total = 0
    for ex in exercises:
        for s in ex.get("sets_data", []):
            if "reps" in s:
                reps      = int(s.get("reps") or 0)
                weight    = float(s.get("weight") or 0)
                rep_xp    = (reps + (_EXERCISE_REP_XP_DIVISOR - 1)) // _EXERCISE_REP_XP_DIVISOR
                weight_xp = int(weight / _EXERCISE_WEIGHT_XP_DIVISOR)
                total    += rep_xp + weight_xp
            elif "distance_m" in s:
                total += int(float(s.get("distance_m") or 0) / _EXERCISE_DISTANCE_XP_PER_100M)
            elif "duration_s" in s:
                total += int(int(s.get("duration_s") or 0) / _EXERCISE_TIME_XP_PER_30S)
    return max(0, total)


def _shiny_roll(streak: int) -> bool:
    """Returns True with increasing probability based on streak."""
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


def _pick_spawn_species(
    cur,
    user_id: str,
    type_slug: str | None = None,
) -> int | None:
    """Picks a spawnable species_id using weighted tier sampling.

    Tries typed filter first (if type_slug given), falls back to any type.
    Returns species_id or None if pool exhausted.
    """
    tiers   = list(_SPAWN_TIER_WEIGHTS.keys())
    weights = [_SPAWN_TIER_WEIGHTS[t] for t in tiers]

    tier_order: list[str] = random.choices(tiers, weights=weights, k=len(tiers))
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
    """Tries candidate_types in order, falls back to untyped.

    Returns (species_id, info_dict) or (None, None).
    """
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
            (user_id, free, up_id),
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
    """Captures an uncaught Pokémon (optional type filter) within an open transaction.

    Returns (species_id, {id, name, sprite_url, type1, is_shiny}) or (None, None).
    """
    species_id = _pick_spawn_species(cur, user_id, type_slug)
    if species_id is None:
        return None, None

    up_id = _insert_user_pokemon(cur, user_id, species_id, level=5, xp=0, is_shiny=is_shiny)
    if up_id is None:
        raise ValueError("Espécie sorteada não encontrada para calcular stats.")

    cur.execute("SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;", (user_id,))
    used = {r[0] for r in cur.fetchall()}
    free = next((s for s in range(1, 7) if s not in used), None)
    if free:
        cur.execute(
            "INSERT INTO user_team (user_id, slot, user_pokemon_id) VALUES (%s, %s, %s);",
            (user_id, free, up_id),
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


def _get_exercise_bests(cur, user_id: str, exercise_ids: list[int]) -> dict[int, tuple[float, int]]:
    """Returns {exercise_id: (best_weight, best_reps_at_best_weight)} from historical logs."""
    if not exercise_ids:
        return {}
    cur.execute("""
        SELECT el.exercise_id,
               MAX((s->>'weight')::float)  AS best_weight,
               MAX((s->>'reps')::int)      AS best_reps
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
            (int(s.get("reps") or 0) for s in sets_data
             if float(s.get("weight") or 0) == cur_best_w),
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


# ── Egg system ─────────────────────────────────────────────────────────────────

def get_user_eggs(user_id: str) -> list[dict]:
    """Returns all pending (unhatched) eggs for a user, oldest first."""
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
    """Grants one egg if workout_count is exactly a milestone.

    Returns list of granted egg dicts (empty if no milestone hit).
    """
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
                (user_id, free, up_id),
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


# ── Slot-1 ability ─────────────────────────────────────────────────────────────

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


# ── Weekly challenge helpers (private) ────────────────────────────────────────

def _ensure_weekly_challenge(cur) -> int | None:
    """Returns challenge id for this week, creating it if absent. Returns None on error."""
    from utils.db_core import _brt_date_range_bounds as _drb  # already in scope but explicit for clarity
    today = _today_brt()
    this_monday = today - datetime.timedelta(days=today.weekday())
    cur.execute("SELECT id FROM weekly_challenges WHERE week_start = %s;", (this_monday,))
    row = cur.fetchone()
    if row:
        return row[0]

    last_monday = this_monday - datetime.timedelta(weeks=1)
    last_sunday = this_monday - datetime.timedelta(days=1)
    last_week_start_ts, last_week_end_ts = _brt_date_range_bounds(last_monday, last_sunday)

    cur.execute("""
        SELECT COUNT(DISTINCT user_id) FROM workout_logs
        WHERE completed_at >= NOW() - INTERVAL '28 days';
    """)
    active_users = max(int(cur.fetchone()[0] or 0), 1)

    goal_type = random.choice(_CHALLENGE_TYPES)

    if goal_type == "total_xp":
        cur.execute("""
            SELECT COALESCE(SUM(xp_earned), 0) FROM workout_logs
            WHERE completed_at >= %s AND completed_at < %s;
        """, (last_week_start_ts, last_week_end_ts))
        last_week_val = int(cur.fetchone()[0] or 0)
        goal_value = last_week_val if last_week_val > 0 else active_users * 200

    elif goal_type == "total_workouts":
        cur.execute("""
            SELECT COUNT(*) FROM workout_logs
            WHERE completed_at >= %s AND completed_at < %s;
        """, (last_week_start_ts, last_week_end_ts))
        last_week_val = int(cur.fetchone()[0] or 0)
        goal_value = last_week_val if last_week_val > 0 else max(active_users * 3, 5)

    else:  # total_sets
        cur.execute("""
            SELECT COALESCE(SUM(jsonb_array_length(sets_data)), 0) FROM exercise_logs el
            JOIN workout_logs wl ON wl.id = el.workout_log_id
            WHERE wl.completed_at >= %s AND wl.completed_at < %s;
        """, (last_week_start_ts, last_week_end_ts))
        last_week_val = int(cur.fetchone()[0] or 0)
        goal_value = last_week_val if last_week_val > 0 else active_users * 30

    cur.execute("""
        INSERT INTO weekly_challenges
            (week_start, goal_type, goal_value, reward_item_slug, reward_quantity)
        VALUES (%s, %s, %s, %s, 1)
        ON CONFLICT (week_start) DO NOTHING
        RETURNING id;
    """, (this_monday, goal_type, goal_value, _CHALLENGE_REWARD_SLUG))
    new_row = cur.fetchone()
    if new_row:
        return new_row[0]
    cur.execute("SELECT id FROM weekly_challenges WHERE week_start = %s;", (this_monday,))
    fetched = cur.fetchone()
    return fetched[0] if fetched else None


def _update_weekly_challenge(cur, user_id: str, xp_earned: int, sets_total: int) -> None:
    """Increments community challenge progress and upserts participant. Fire-and-forget."""
    challenge_id = _ensure_weekly_challenge(cur)
    if challenge_id is None:
        return

    cur.execute(
        "SELECT goal_type, goal_value, current_value, completed FROM weekly_challenges WHERE id = %s;",
        (challenge_id,),
    )
    ch = cur.fetchone()
    if not ch:
        return
    goal_type, goal_value, current_value, completed = ch

    if goal_type == "total_xp":
        delta = xp_earned
    elif goal_type == "total_workouts":
        delta = 1
    else:
        delta = sets_total

    if delta <= 0:
        return

    cur.execute("""
        UPDATE weekly_challenges
        SET current_value = current_value + %s,
            completed = (current_value + %s >= goal_value)
        WHERE id = %s;
    """, (delta, delta, challenge_id))

    cur.execute("""
        INSERT INTO weekly_challenge_participants (challenge_id, user_id, contributed)
        VALUES (%s, %s, %s)
        ON CONFLICT (challenge_id, user_id)
        DO UPDATE SET contributed = weekly_challenge_participants.contributed + %s;
    """, (challenge_id, user_id, delta, delta))


# ── Exercise catalogue (read-only) ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_muscle_groups() -> list[dict]:
    """Muscle groups with anatomical image."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("SELECT id, name, image_url FROM muscle_groups ORDER BY name;")
            return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in cur.fetchall()]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_exercises(body_part: str | None = None) -> list[dict]:
    """Exercise catalogue, optionally filtered by body_part."""
    try:
        with get_connection().cursor() as cur:
            if body_part:
                cur.execute("""
                    SELECT id, name, name_pt, target_muscles, body_parts, equipments, gif_url,
                           COALESCE(metric_type, 'weight') AS metric_type
                    FROM exercises
                    WHERE %s = ANY(body_parts)
                    ORDER BY COALESCE(name_pt, name);
                """, (body_part,))
            else:
                cur.execute("""
                    SELECT id, name, name_pt, target_muscles, body_parts, equipments, gif_url,
                           COALESCE(metric_type, 'weight') AS metric_type
                    FROM exercises
                    ORDER BY COALESCE(name_pt, name);
                """)
            return [
                {
                    "id": r[0], "name": r[1], "name_pt": r[2],
                    "target_muscles": r[3], "body_parts": r[4],
                    "equipments": r[5], "gif_url": r[6],
                    "metric_type": r[7],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_distinct_body_parts() -> list[str]:
    """Distinct body_parts present in the exercise catalogue."""
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


# ── Workout log read helpers ────────────────────────────────────────────────────

def get_workout_days(user_id: str) -> list[dict]:
    """Active plan days for the user with exercise counts."""
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
    """Prescribed exercises for a workout day."""
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
    """XP earned from exercise today (used to check the daily cap)."""
    start_ts, end_ts = _brt_day_bounds(_today_brt())
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(xp_earned), 0)
                FROM workout_logs
                WHERE user_id = %s
                  AND completed_at >= %s
                  AND completed_at < %s;
            """, (user_id, start_ts, end_ts))
            return cur.fetchone()[0]
    except Exception:
        return 0


def get_workout_streak(user_id: str) -> int:
    """Consecutive days with at least one registered workout."""
    try:
        with get_connection().cursor() as cur:
            return _compute_streak_from_days(_unique_workout_days_brt(cur, user_id))
    except Exception:
        return 0


def get_workout_history(user_id: str, limit: int = 10) -> list[dict]:
    """Last workout sessions with exercise count and XP earned."""
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


def get_last_exercise_values(user_id: str, exercise_ids: list[int]) -> dict[int, dict]:
    """Most-recent logged values per exercise for Import Default pre-fill.

    Returns {exercise_id: {reps, weight, distance_km, duration_min}}.
    Fields irrelevant to the exercise's metric_type are None.
    """
    if not exercise_ids:
        return {}
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (el.exercise_id)
                    el.exercise_id,
                    (el.sets_data->0->>'reps')::int         AS last_reps,
                    (el.sets_data->0->>'weight')::float     AS last_weight,
                    (el.sets_data->0->>'distance_m')::float AS last_distance_m,
                    (el.sets_data->0->>'duration_s')::int   AS last_duration_s
                FROM exercise_logs el
                JOIN workout_logs wl ON wl.id = el.workout_log_id
                WHERE wl.user_id = %s
                  AND el.exercise_id = ANY(%s)
                ORDER BY el.exercise_id, wl.completed_at DESC;
            """, (user_id, exercise_ids))
            result: dict[int, dict] = {}
            for eid, last_reps, last_weight, last_dist_m, last_dur_s in cur.fetchall():
                result[eid] = {
                    "reps":         int(last_reps)               if last_reps   is not None else None,
                    "weight":       float(last_weight)           if last_weight is not None else None,
                    "distance_km":  round(last_dist_m / 1000, 2) if last_dist_m is not None else None,
                    "duration_min": round(last_dur_s  / 60,   1) if last_dur_s  is not None else None,
                }
            return result
    except Exception:
        return {}


# ── Main workout event ─────────────────────────────────────────────────────────

def do_exercise_event(
    user_id: str,
    exercises: list[dict],
    day_id: str | None = None,
) -> dict:
    """Registers a workout session and awards XP to the slot-1 Pokémon.

    Args:
        user_id:   UUID do usuário.
        exercises: [{"exercise_id": int,
                     "sets_data":   [{"reps": int, "weight": float}],
                     "notes":       str | None}]
        day_id:    UUID do workout_day prescrito (None = free workout).

    Returns:
        {xp_earned, capped, spawn_rolled, spawned, xp_result, milestone,
         milestone_xp, streak, prs, eggs_granted, eggs_hatched,
         ability_effects, error}

    Transaction structure:
        1. Main tx — workout_log + exercise_logs + spawn + eggs
           + weekly_challenge + happiness + pickup (all atomic).
           Secondary effects use SAVEPOINTs to avoid aborting the main tx.
        2. Post-commit — award_xp() calls (slot 1, PR bonus, first-workout
           bonus, synchronize).  Each opens its own transaction; errors are
           logged but do NOT revert the already-saved workout.
    """
    # Lazy import to break circular dependency with db_progression
    from utils.db_progression import award_xp  # noqa: PLC0415

    result = {
        "xp_earned":      0,
        "capped":         False,
        "spawn_rolled":   False,
        "spawned":        [],
        "spawn_context":  None,
        "xp_result":      None,
        "milestone":      None,
        "milestone_xp":   0,
        "streak":         0,
        "prs":            [],
        "eggs_granted":   [],
        "eggs_hatched":   [],
        "ability_effects": None,
        "weekend_bonus":  False,
        "error":          None,
    }

    if not exercises:
        result["error"] = "Nenhum exercício informado."
        return result

    slot1_ability = _get_slot1_ability(user_id)
    _abilfx: dict = {}

    raw_xp = _calc_exercise_xp(exercises)
    if slot1_ability == "blaze" and raw_xp >= 200:
        boosted = _apply_blaze(raw_xp)
        _abilfx["blaze_xp_before"] = raw_xp
        _abilfx["blaze_xp_after"]  = boosted
        raw_xp = boosted

    if raw_xp <= 0:
        result["error"] = "Nenhuma série registrada."
        return result

    # ── Bônus de fim de semana (sex/sab/dom): XP e cap em dobro ─────────────
    _weekend = is_weekend_bonus()
    if _weekend:
        raw_xp *= _WEEKEND_XP_MULTIPLIER
    effective_cap = _EXERCISE_XP_DAILY_CAP * (_WEEKEND_XP_MULTIPLIER if _weekend else 1)
    result["weekend_bonus"] = _weekend

    already_today = get_daily_xp_from_exercise(user_id)
    remaining     = max(0, effective_cap - already_today)
    xp_to_award   = min(raw_xp, remaining)

    if xp_to_award < raw_xp:
        result["capped"] = True

    _sets_total = sum(len(ex.get("sets_data", [])) for ex in exercises)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # ── Pre-insert reads ──────────────────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM workout_logs WHERE user_id = %s;", (user_id,))
            _pre_insert_count = cur.fetchone()[0]
            is_first_workout  = _pre_insert_count == 0

            ex_ids = [ex["exercise_id"] for ex in exercises]
            cur.execute(
                "SELECT id, body_parts, COALESCE(name_pt, name) FROM exercises WHERE id = ANY(%s);",
                (ex_ids,),
            )
            ex_rows     = cur.fetchall()
            bp_map      = {r[0]: (r[1] or []) for r in ex_rows}
            ex_name_map = {r[0]: r[2] for r in ex_rows}

            candidate_types = _ranked_spawn_types(exercises, bp_map)
            if slot1_ability == "pressure" and candidate_types:
                candidate_types = [candidate_types[0]]
                _abilfx["pressure_type"] = candidate_types[0]

            historical_bests = _get_exercise_bests(cur, user_id, ex_ids)

            # ── Insert session and exercise logs ──────────────────────────────
            cur.execute("""
                INSERT INTO workout_logs (user_id, day_id, xp_earned)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (user_id, day_id, xp_to_award))
            wl_id = cur.fetchone()[0]

            for ex in exercises:
                cur.execute("""
                    INSERT INTO exercise_logs (workout_log_id, exercise_id, sets_data, notes)
                    VALUES (%s, %s, %s::jsonb, %s);
                """, (wl_id, ex["exercise_id"],
                      json.dumps(ex.get("sets_data", [])),
                      ex.get("notes")))

            # ── Streak and milestone ──────────────────────────────────────────
            new_streak      = _compute_streak_from_days(_unique_workout_days_brt(cur, user_id))
            result["streak"] = new_streak

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

            # ── Spawn with daily budget ───────────────────────────────────────
            cur.execute("""
                SELECT COUNT(*) FROM workout_logs
                WHERE user_id = %s
                  AND completed_at >= %s
                  AND completed_at < %s
                  AND id != %s
                  AND spawned_species_id IS NOT NULL;
            """, (user_id, *_brt_day_bounds(_today_brt()), wl_id))
            prior_spawns   = int(cur.fetchone()[0])
            spawn_budget   = max(0, _MAX_DAILY_SPAWNS - prior_spawns)
            session_spawns = 0

            if force_spawn and spawn_budget > 0:
                cur.execute("SAVEPOINT sp_spawn_milestone")
                try:
                    roll_shiny  = force_shiny or _shiny_roll(new_streak)
                    species_id, spawn_info = _spawn_multi_typed(
                        cur, user_id, candidate_types, is_shiny=roll_shiny
                    )
                    if species_id:
                        result["spawn_rolled"] = True
                        result["spawned"].append(spawn_info)
                        session_spawns += 1
                        cur.execute(
                            "UPDATE workout_logs SET spawned_species_id = %s WHERE id = %s;",
                            (species_id, wl_id),
                        )
                    cur.execute("RELEASE SAVEPOINT sp_spawn_milestone")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_spawn_milestone")
                    logger.warning("do_exercise_event: milestone spawn falhou | user_id={}", user_id)

            if session_spawns < spawn_budget and random.random() < _EXERCISE_SPAWN_CHANCE:
                session_types = candidate_types
                if slot1_ability == "pressure" and session_types:
                    session_types = [session_types[0]]
                cur.execute("SAVEPOINT sp_spawn_session")
                try:
                    roll_shiny  = _shiny_roll(new_streak)
                    species_id, spawn_info = _spawn_multi_typed(
                        cur, user_id, session_types, is_shiny=roll_shiny
                    )
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
                                (species_id, wl_id),
                            )
                    cur.execute("RELEASE SAVEPOINT sp_spawn_session")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_spawn_session")
                    logger.warning("do_exercise_event: session spawn falhou | user_id={}", user_id)

            # ── Eggs ──────────────────────────────────────────────────────────
            _post_workout_count = _pre_insert_count + 1
            cur.execute("SAVEPOINT sp_eggs")
            try:
                result["eggs_granted"] = _grant_eggs_if_milestone(cur, user_id, _post_workout_count)
                result["eggs_hatched"] = _advance_and_hatch_eggs(cur, user_id)
                cur.execute("RELEASE SAVEPOINT sp_eggs")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_eggs")
                result["eggs_granted"] = []
                result["eggs_hatched"] = []
                logger.warning("do_exercise_event: egg system falhou | user_id={}", user_id)

            # ── Community challenge ───────────────────────────────────────────
            cur.execute("SAVEPOINT sp_weekly_challenge")
            try:
                _update_weekly_challenge(cur, user_id, xp_to_award, _sets_total)
                cur.execute("RELEASE SAVEPOINT sp_weekly_challenge")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_weekly_challenge")
                logger.warning("do_exercise_event: weekly challenge falhou | user_id={}", user_id)

            # ── Happiness: inactivity penalty + workout bonus ─────────────────
            cur.execute("SAVEPOINT sp_happiness")
            try:
                cur.execute("""
                    SELECT completed_at FROM workout_logs
                    WHERE user_id = %s
                    ORDER BY completed_at DESC
                    LIMIT 1 OFFSET 1;
                """, (user_id,))
                _prev = cur.fetchone()
                if _prev:
                    _prev_day = _to_brt_date(_prev[0])
                    _days_gap = (_today_brt() - _prev_day).days if _prev_day else 0
                    if _days_gap > 7:
                        cur.execute("""
                            SELECT up.id FROM user_team ut
                            JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                            WHERE ut.user_id = %s;
                        """, (user_id,))
                        for (_tid,) in cur.fetchall():
                            _bump_happiness(cur, _tid, -5)
                cur.execute("""
                    SELECT ut.user_pokemon_id FROM user_team ut
                    WHERE ut.user_id = %s AND ut.slot = 1;
                """, (user_id,))
                _s1 = cur.fetchone()
                if _s1:
                    _bump_happiness(cur, _s1[0], 1)
                cur.execute("RELEASE SAVEPOINT sp_happiness")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_happiness")
                logger.warning("do_exercise_event: happiness update falhou | user_id={}", user_id)

            # ── Pickup ability ────────────────────────────────────────────────
            if slot1_ability == "pickup" and random.random() < 0.10:
                cur.execute("SAVEPOINT sp_pickup")
                try:
                    pickup_slug = random.choice(_LOOT_VITAMINS)
                    cur.execute("SELECT id FROM shop_items WHERE slug = %s;", (pickup_slug,))
                    _row = cur.fetchone()
                    if _row:
                        _add_inventory_item(cur, user_id, _row[0])
                    _abilfx["pickup_item"] = pickup_slug
                    cur.execute("RELEASE SAVEPOINT sp_pickup")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_pickup")
                    logger.warning("do_exercise_event: pickup ability falhou | user_id={}", user_id)

        conn.commit()
        result["xp_earned"] = xp_to_award

        # ── Post-commit: award_xp has its own transaction ─────────────────────
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
            logger.warning("do_exercise_event: award_xp slot1 falhou | user_id={}", user_id)

        # Synchronize: +15% bonus XP for XP Share recipients
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
                            logger.warning(
                                "do_exercise_event: synchronize bonus falhou | pokemon_id={}",
                                entry.get("user_pokemon_id"),
                            )
                    _abilfx["synchronize_bonus_xp"] = sync_bonus

        # PRs: XP bonus outside daily cap (max _PR_MAX_PER_SESSION)
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
                logger.warning("do_exercise_event: pr bonus xp falhou | user_id={}", user_id)

        # First workout bonus (+50 XP outside daily cap)
        if is_first_workout and slot1_id:
            try:
                bonus_res = award_xp(slot1_id, _FIRST_WORKOUT_BONUS_XP,
                                     "first_workout_bonus", _distributing=True)
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
                logger.warning("do_exercise_event: first_workout bonus xp falhou | user_id={}", user_id)

        if _abilfx and slot1_ability:
            result["ability_effects"] = {"slug": slot1_ability, **_abilfx}

        return result

    except Exception as e:
        logger.exception("do_exercise_event falhou | user_id={}", user_id)
        conn.rollback()
        result["error"] = str(e)
        return result


# ── Workout builder CRUD ───────────────────────────────────────────────────────

def get_workout_sheets(user_id: str) -> list[dict]:
    """Sheets owned by the user with day count."""
    try:
        day_sheet_fk = _workout_days_sheet_fk()
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


def get_workout_builder_tree(user_id: str) -> list[dict]:
    """Returns the full workout builder tree in one read pass.

    Structure:
      [{id, name, day_count, days: [{id, name, exercise_count,
        exercises: [{id, exercise_id, name, sets, reps, metric_type}]}]}]
    """
    try:
        day_sheet_fk = _workout_days_sheet_fk()
        day_fk       = _workout_day_exercises_day_fk()

        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT
                    ws.id, ws.name,
                    wd.id, wd.name,
                    wde.id,
                    e.id AS exercise_id,
                    COALESCE(e.name_pt, e.name) AS display_name,
                    wde.sets, wde.reps,
                    COALESCE(e.metric_type, 'weight') AS metric_type
                FROM workout_sheets ws
                LEFT JOIN workout_days wd ON wd.{day_sheet_fk} = ws.id
                LEFT JOIN workout_day_exercises wde ON wde.{day_fk} = wd.id
                LEFT JOIN exercises e ON e.id = wde.exercise_id
                WHERE ws.user_id = %s
                ORDER BY ws.name, wd.name, wd.id, wde.id;
            """, (user_id,))
            rows = cur.fetchall()

        sheets: list[dict]      = []
        sheet_map: dict[str, dict] = {}
        day_map: dict[str, dict]   = {}

        for row in rows:
            (sheet_id, sheet_name,
             day_id, day_name,
             wde_id, exercise_id, display_name,
             sets, reps, metric_type) = row

            sheet_key = str(sheet_id)
            sheet = sheet_map.get(sheet_key)
            if sheet is None:
                sheet = {"id": sheet_key, "name": sheet_name, "day_count": 0, "days": []}
                sheet_map[sheet_key] = sheet
                sheets.append(sheet)

            if day_id is None:
                continue

            day_key = str(day_id)
            day = day_map.get(day_key)
            if day is None:
                day = {"id": day_key, "name": day_name, "exercise_count": 0, "exercises": []}
                day_map[day_key] = day
                sheet["days"].append(day)
                sheet["day_count"] += 1

            if wde_id is None:
                continue

            day["exercises"].append({
                "id": str(wde_id),
                "exercise_id": exercise_id,
                "name": display_name,
                "sets": sets,
                "reps": reps,
                "metric_type": metric_type,
            })
            day["exercise_count"] += 1

        return sheets
    except Exception:
        return []


def create_workout_sheet(
    user_id: str,
    name: str,
    created_by: str | None = None,
) -> tuple[str | None, str | None]:
    """INSERT into workout_sheets; returns (new_uuid, None) or (None, error_msg)."""
    try:
        conn     = get_connection()
        actor_id = created_by or user_id
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO workout_sheets (user_id, created_by, name)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (user_id, actor_id, name.strip()))
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
            cur.execute("""
                UPDATE workout_sheets
                SET name = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s;
            """, (name.strip(), sheet_id, user_id))
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
        conn      = get_connection()
        sheet_fk  = _workout_days_sheet_fk()
        day_fk    = _workout_day_exercises_day_fk()
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE workout_logs SET day_id = NULL
                WHERE day_id IN (
                    SELECT id FROM workout_days WHERE {sheet_fk} = %s
                );
            """, (sheet_id,))
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
    conn = get_connection()
    try:
        sheet_fk = _workout_days_sheet_fk()
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO workout_days ({sheet_fk}, name) VALUES (%s, %s) RETURNING id;",
                (sheet_id, name.strip()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id), None
    except Exception as e:
        conn.rollback()
        return None, str(e)


def delete_workout_day(day_id: str) -> tuple[bool, str | None]:
    """DELETE a day with all its exercises."""
    try:
        conn   = get_connection()
        day_fk = _workout_day_exercises_day_fk()
        with conn.cursor() as cur:
            cur.execute("UPDATE workout_logs SET day_id = NULL WHERE day_id = %s;", (day_id,))
            cur.execute(f"DELETE FROM workout_day_exercises WHERE {day_fk} = %s;", (day_id,))
            cur.execute("DELETE FROM workout_days WHERE id = %s;", (day_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def add_exercise_to_day(
    day_id: str, exercise_id: int, sets: int, reps: int
) -> tuple[str | None, str | None]:
    """INSERT into workout_day_exercises; returns (new_uuid, None) or (None, error_msg)."""
    conn = get_connection()
    try:
        day_fk = _workout_day_exercises_day_fk()
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO workout_day_exercises ({day_fk}, exercise_id, sets, reps)"
                " VALUES (%s, %s, %s, %s) RETURNING id;",
                (day_id, exercise_id, sets, reps),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id), None
    except Exception as e:
        conn.rollback()
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
        sheet_fk = _workout_days_sheet_fk()
        day_fk   = _workout_day_exercises_day_fk()
        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT wd.id, wd.name, COUNT(wde.id) AS exercise_count
                FROM workout_days wd
                LEFT JOIN workout_day_exercises wde ON wde.{day_fk} = wd.id
                WHERE wd.{sheet_fk} = %s
                GROUP BY wd.id, wd.name
                ORDER BY wd.name;
            """, (sheet_id,))
            return [
                {"id": str(r[0]), "name": r[1], "exercise_count": r[2]}
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def get_day_exercises_for_builder(day_id: str) -> list[dict]:
    """Prescribed exercises for a day, including wde.id for edit/delete."""
    try:
        day_fk = _workout_day_exercises_day_fk()
        with get_connection().cursor() as cur:
            cur.execute(f"""
                SELECT wde.id, e.id AS exercise_id,
                       COALESCE(e.name_pt, e.name) AS display_name,
                       wde.sets, wde.reps,
                       COALESCE(e.metric_type, 'weight') AS metric_type
                FROM workout_day_exercises wde
                JOIN exercises e ON e.id = wde.exercise_id
                WHERE wde.{day_fk} = %s
                ORDER BY wde.id;
            """, (day_id,))
            return [
                {
                    "id": str(r[0]), "exercise_id": r[1], "name": r[2],
                    "sets": r[3], "reps": r[4], "metric_type": r[5],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


# ── Training analytics ─────────────────────────────────────────────────────────

def get_volume_history(user_id: str, exercise_id: int, days: int = 90) -> list[dict]:
    """Daily volume for one exercise, adapting to its metric_type.

    - weight:   volume = Σ(weight × reps), max_val = best kg,   unit = 'kg'
    - distance: volume = Σ(distance_m / 1000), max_val = km,    unit = 'km'
    - time:     volume = Σ(duration_s / 60),    max_val = min,   unit = 'min'

    Returns list of {date, volume, max_val, total_sets, metric_type, unit}.
    """
    try:
        end_date   = _today_brt()
        days       = max(int(days or 90), 1)
        start_date = end_date - datetime.timedelta(days=days - 1)
        start_ts, end_ts = _brt_date_range_bounds(start_date, end_date)
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(e.metric_type, 'weight') AS metric_type,
                    (wl.completed_at + INTERVAL '-3 hours')::date AS d,
                    CASE COALESCE(e.metric_type, 'weight')
                        WHEN 'weight'   THEN ROUND(SUM((s->>'weight')::float * (s->>'reps')::int)::numeric, 1)
                        WHEN 'distance' THEN ROUND(SUM((s->>'distance_m')::float / 1000)::numeric, 2)
                        WHEN 'time'     THEN ROUND(SUM((s->>'duration_s')::int / 60.0)::numeric, 1)
                    END AS volume,
                    CASE COALESCE(e.metric_type, 'weight')
                        WHEN 'weight'   THEN MAX((s->>'weight')::float)
                        WHEN 'distance' THEN MAX((s->>'distance_m')::float / 1000)
                        WHEN 'time'     THEN MAX((s->>'duration_s')::int / 60.0)
                    END AS max_val,
                    COUNT(*) AS total_sets
                FROM exercise_logs el
                JOIN workout_logs wl ON wl.id = el.workout_log_id
                JOIN exercises e ON e.id = el.exercise_id
                JOIN LATERAL jsonb_array_elements(el.sets_data) AS s ON true
                WHERE wl.user_id = %s
                  AND el.exercise_id = %s
                  AND wl.completed_at >= %s
                  AND wl.completed_at < %s
                  AND (
                      (COALESCE(e.metric_type, 'weight') = 'weight'   AND (s->>'weight')::float > 0)
                   OR (COALESCE(e.metric_type, 'weight') = 'distance' AND (s->>'distance_m') IS NOT NULL)
                   OR (COALESCE(e.metric_type, 'weight') = 'time'     AND (s->>'duration_s')  IS NOT NULL)
                  )
                GROUP BY COALESCE(e.metric_type, 'weight'), d
                ORDER BY d;
            """, (user_id, exercise_id, start_ts, end_ts))
            _unit_map = {"weight": "kg", "distance": "km", "time": "min"}
            rows = []
            for metric_type, d, volume, max_val, total_sets in cur.fetchall():
                rows.append({
                    "date":        d,
                    "volume":      float(volume or 0),
                    "max_val":     float(max_val or 0),
                    "total_sets":  int(total_sets),
                    "metric_type": metric_type,
                    "unit":        _unit_map.get(metric_type, ""),
                })
            return rows
    except Exception:
        return []


def get_exercise_bests_all(user_id: str) -> list[dict]:
    """Best metric for every exercise the user has logged, per metric_type.

    Returns list of {exercise_id, name, metric_type, unit, best_primary, best_secondary}.
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT
                    e.id,
                    COALESCE(e.name_pt, e.name) AS name,
                    COALESCE(e.metric_type, 'weight') AS metric_type,
                    CASE COALESCE(e.metric_type, 'weight')
                        WHEN 'weight'   THEN MAX((s->>'weight')::float)
                        WHEN 'distance' THEN MAX((s->>'distance_m')::float / 1000)
                        WHEN 'time'     THEN MAX((s->>'duration_s')::int / 60.0)
                    END AS best_primary,
                    CASE COALESCE(e.metric_type, 'weight')
                        WHEN 'weight' THEN MAX((s->>'reps')::int)::float
                        ELSE NULL
                    END AS best_secondary
                FROM exercise_logs el
                JOIN workout_logs wl ON wl.id = el.workout_log_id
                JOIN exercises e ON e.id = el.exercise_id
                JOIN LATERAL jsonb_array_elements(el.sets_data) AS s ON true
                WHERE wl.user_id = %s
                  AND (
                      (COALESCE(e.metric_type, 'weight') = 'weight'   AND (s->>'weight')::float > 0)
                   OR (COALESCE(e.metric_type, 'weight') = 'distance' AND (s->>'distance_m') IS NOT NULL)
                   OR (COALESCE(e.metric_type, 'weight') = 'time'     AND (s->>'duration_s')  IS NOT NULL)
                  )
                GROUP BY e.id, e.name, e.name_pt, COALESCE(e.metric_type, 'weight')
                ORDER BY name;
            """, (user_id,))
            _unit_map = {"weight": "kg", "distance": "km", "time": "min"}
            rows = []
            for eid, name, metric_type, best_primary, best_secondary in cur.fetchall():
                rows.append({
                    "exercise_id":    eid,
                    "name":           name,
                    "metric_type":    metric_type,
                    "unit":           _unit_map.get(metric_type, ""),
                    "best_primary":   float(best_primary)   if best_primary   is not None else None,
                    "best_secondary": int(best_secondary)   if best_secondary is not None else None,
                })
            return rows
    except Exception:
        return []


def get_muscle_distribution(user_id: str) -> dict:
    """Body-part set counts for the current week and previous week.

    Returns:
    {
        "this_week":  {body_part: total_sets, ...},
        "last_week":  {body_part: total_sets, ...},
        "this_label": "DD/MM – DD/MM",
        "last_label": "DD/MM – DD/MM",
    }
    """
    today    = _today_brt()
    this_mon = today - datetime.timedelta(days=today.weekday())
    last_mon = this_mon - datetime.timedelta(days=7)
    last_sun = this_mon - datetime.timedelta(days=1)

    def _query(start, end):
        try:
            start_ts, end_ts = _brt_date_range_bounds(start, end)
            with get_connection().cursor() as cur:
                cur.execute("""
                    SELECT unnest(e.body_parts) AS bp,
                           SUM(jsonb_array_length(el.sets_data)) AS total_sets
                    FROM exercise_logs el
                    JOIN workout_logs wl ON wl.id = el.workout_log_id
                    JOIN exercises e ON e.id = el.exercise_id
                    WHERE wl.user_id = %s
                      AND wl.completed_at >= %s
                      AND wl.completed_at < %s
                    GROUP BY bp
                    ORDER BY total_sets DESC;
                """, (user_id, start_ts, end_ts))
                return {r[0]: int(r[1]) for r in cur.fetchall()}
        except Exception:
            return {}

    fmt = lambda d: d.strftime("%d/%m")
    return {
        "this_week":  _query(this_mon, today),
        "last_week":  _query(last_mon, last_sun),
        "this_label": f"{fmt(this_mon)} – {fmt(today)}",
        "last_label": f"{fmt(last_mon)} – {fmt(last_sun)}",
    }


def get_recent_muscle_balance(user_id: str, days: int = 7) -> dict:
    """Recent body-part summary with cold groups highlighted.

    Returns:
    {
        "days": 7,
        "start_date": date,
        "end_date": date,
        "entries": [{"body_part", "sets", "workouts", "status"}, ...],
        "cold_parts": [...],
        "trained_parts": int,
        "total_parts": int,
    }
    Status values: "hot" (≥12 sets), "warm" (>0), "cold" (0 sets).
    """
    end_date   = _today_brt()
    days       = max(int(days or 7), 1)
    start_date = end_date - datetime.timedelta(days=days - 1)

    try:
        start_ts, end_ts = _brt_date_range_bounds(start_date, end_date)
        with get_connection().cursor() as cur:
            cur.execute("""
                WITH all_parts AS (
                    SELECT DISTINCT unnest(body_parts) AS body_part
                    FROM exercises
                ),
                recent_parts AS (
                    SELECT
                        unnest(e.body_parts) AS body_part,
                        SUM(jsonb_array_length(el.sets_data)) AS total_sets,
                        COUNT(DISTINCT wl.id) AS workout_count
                    FROM exercise_logs el
                    JOIN workout_logs wl ON wl.id = el.workout_log_id
                    JOIN exercises e ON e.id = el.exercise_id
                    WHERE wl.user_id = %s
                      AND wl.completed_at >= %s
                      AND wl.completed_at < %s
                    GROUP BY 1
                )
                SELECT
                    ap.body_part,
                    COALESCE(rp.total_sets, 0)    AS total_sets,
                    COALESCE(rp.workout_count, 0) AS workout_count
                FROM all_parts ap
                LEFT JOIN recent_parts rp ON rp.body_part = ap.body_part
                ORDER BY COALESCE(rp.total_sets, 0) DESC, ap.body_part;
            """, (user_id, start_ts, end_ts))
            rows = cur.fetchall()
    except Exception:
        return {
            "days": days, "start_date": start_date, "end_date": end_date,
            "entries": [], "cold_parts": [], "trained_parts": 0, "total_parts": 0,
        }

    entries = []
    for body_part, total_sets, workout_count in rows:
        sets     = int(total_sets or 0)
        workouts = int(workout_count or 0)
        status   = "cold" if sets == 0 else ("hot" if sets >= 12 else "warm")
        entries.append({"body_part": body_part, "sets": sets,
                        "workouts": workouts, "status": status})

    cold_parts    = [e["body_part"] for e in entries if e["status"] == "cold"]
    trained_parts = sum(1 for e in entries if e["sets"] > 0)
    return {
        "days": days, "start_date": start_date, "end_date": end_date,
        "entries": entries, "cold_parts": cold_parts,
        "trained_parts": trained_parts, "total_parts": len(entries),
    }
