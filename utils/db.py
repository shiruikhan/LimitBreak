# ── db.py — Facade de re-exportação ──────────────────────────────────────────
# Este arquivo não contém lógica própria. Importa e re-exporta todos os
# símbolos públicos e internos dos sub-módulos temáticos para manter
# compatibilidade total com `from utils.db import ...` em todo o projeto.
#
# Sub-módulos:
#   db_core        → conexão, helpers BRT, fórmulas de stat, sprites
#   db_catalog     → Pokédex somente-leitura (espécies, moves, evoluções)
#   db_user        → perfil, equipe, banco, moves equipados, stat boosts
#   db_shop        → loja, inventário, loot box, XP Share, pedras, mint
#   db_combat      → batalhas PvP (type chart, dano, turnos, histórico)
#   db_workout     → exercícios, treino, ovos, analytics, rotinas
#   db_progression → XP, check-in, conquistas, missões, rival, desafio
#   db_admin       → admin CRUD, leaderboard, logs de sistema

# ── db_core: conexão, helpers BRT, fórmulas de stat, sprites ─────────────────
from utils.db_core import (  # noqa: F401, F403
    _BRT, _today_brt, _brt_day_bounds, _brt_date_range_bounds,
    _brt_month_bounds, _to_brt_date,
    _unique_workout_days_brt, _compute_streak_from_days,
    _db_params, _new_conn, get_connection,
    _workout_days_sheet_fk, _workout_day_exercises_day_fk,
    _STAT_ORDER, _NEUTRAL_NATURES, _NATURE_EFFECTS, _STAT_LABELS, _ALL_NATURES,
    _pokemon_stat_value, _build_pokemon_stats, _get_species_bases,
    _random_ivs, _random_evs, _random_nature,
    _nature_payload, _nature_modifiers, _nature_select_sql,
    _load_pokemon_genetics, _stored_user_pokemon_stats, _flat_stat_boosts,
    _expected_user_pokemon_stats, _sync_user_pokemon_stats,
    _audit_and_sync_user_team_stats, _insert_user_pokemon,
    _GITHUB_ASSETS_CDN, _asset_fallback_url,
    get_image_as_base64, sprite_img_tag, hq_sprite_url,
    _LOOT_VITAMINS,
    _recalc_stats_for_level, _recalc_stats_on_evolution, _bump_happiness,
)

# ── db_catalog: Pokédex somente-leitura ───────────────────────────────────────
from utils.db_catalog import (  # noqa: F401
    get_all_pokemon, get_all_pokemon_with_types,
    get_pokemon_details, get_pokemon_moves,
    get_full_evolution_chain,
)

# ── db_shop: loja, inventário, loot box, XP Share, pedras, mint ───────────────
from utils.db_shop import (  # noqa: F401
    _LOOT_BOX_ITEM, _LOOT_STONES,
    get_shop_items, get_user_inventory,
    _add_inventory_item, _ensure_loot_box_item, _grant_loot_box, _roll_loot_box,
    get_xp_share_status, _extend_xp_share,
    buy_item, use_stat_item, use_xp_share_item, use_nature_mint, open_loot_box,
    get_stone_targets, evolve_with_stone,
)

# ── db_user: perfil, equipe, banco, moves, stat boosts ───────────────────────
from utils.db_user import (  # noqa: F401
    _VALID_STATS, _MAX_STAT_BOOSTS_PER_STAT,
    get_user_profile, create_user_profile,
    get_user_team, get_user_bench,
    add_to_team, set_team_slot, remove_from_team, swap_team_slots,
    get_user_pokemon_ids, capture_pokemon,
    get_available_moves, get_active_moves, equip_move, unequip_move,
    apply_stat_boost, get_stat_boosts, get_stat_boost_summary,
    get_team_stat_boost_counts,
)

# ── db_combat: batalhas PvP ───────────────────────────────────────────────────
from utils.db_combat import (  # noqa: F401
    _MAX_BATTLES_PER_DAY, _MAX_TURNS, _BYPASS_LEVEL,
    _WIN_COINS, _WIN_XP, _LOSS_XP,
    _TYPE_CHART, _CRIT_CHANCE, _CRIT_MULT,
    _pokemon_max_hp, _type_effectiveness, _calc_damage, _best_move,
    get_battle_opponents, get_daily_battle_count,
    start_battle, finalize_battle,
    get_battle_history, get_battle_detail,
)

# ── db_workout: exercícios, treino, ovos, analytics, rotinas ──────────────────
from utils.db_workout import (  # noqa: F401
    _EXERCISE_XP_DAILY_CAP, _FIRST_WORKOUT_BONUS_XP,
    _EXERCISE_REP_XP_DIVISOR, _EXERCISE_WEIGHT_XP_DIVISOR,
    _MAX_DAILY_SPAWNS, _EXERCISE_SPAWN_CHANCE,
    _EXERCISE_DISTANCE_XP_PER_100M, _EXERCISE_TIME_XP_PER_30S,
    _PR_XP_BONUS, _PR_MAX_PER_SESSION,
    _EGG_MILESTONES, _EGG_WORKOUTS_TO_HATCH,
    _SPAWN_TIER_WEIGHTS, _CHALLENGE_TYPES, _CHALLENGE_REWARD_SLUG,
    _BODY_PART_TYPES,
    _ranked_spawn_types, _calc_exercise_xp, _shiny_roll,
    _pick_spawn_species, _spawn_multi_typed, _spawn_typed,
    _get_exercise_bests, _detect_prs,
    _get_slot1_ability,
    _ensure_weekly_challenge, _update_weekly_challenge,
    _pick_egg_species, _grant_eggs_if_milestone, _advance_and_hatch_eggs,
    get_user_eggs,
    get_muscle_groups, get_exercises, get_distinct_body_parts,
    get_workout_days, get_day_exercises,
    get_daily_xp_from_exercise, get_workout_streak, get_workout_history,
    get_last_exercise_values,
    do_exercise_event,
    get_workout_sheets, get_workout_builder_tree,
    create_workout_sheet, update_workout_sheet, delete_workout_sheet,
    create_workout_day, delete_workout_day,
    add_exercise_to_day, update_day_exercise, remove_exercise_from_day,
    get_sheet_days, get_day_exercises_for_builder,
    get_volume_history, get_exercise_bests_all,
    get_muscle_distribution, get_recent_muscle_balance,
)

# ── db_progression: XP, check-in, conquistas, missões, rival, desafio ─────────
from utils.db_progression import (  # noqa: F401
    get_monthly_checkins, get_checkin_streak, do_checkin,
    register_rest, get_monthly_rest_days,
    _distribute_xp_share, award_xp, apply_evolution_choice,
    get_user_achievements, _collect_achievement_stats, check_and_award_achievements,
    _week_start, get_current_mission_periods,
    _ensure_missions, ensure_current_user_missions,
    get_user_missions, update_mission_progress, claim_mission_reward,
    _monday_of, assign_weekly_rival, get_rival_status,
    _CHALLENGE_GOAL_LABELS, get_current_challenge, claim_weekly_challenge_reward,
)

# ── db_admin: admin CRUD, leaderboard, logs de sistema ───────────────────────
from utils.db_admin import (  # noqa: F401
    admin_gift_loot_box, admin_gift_xp_bag, admin_create_exercise,
    get_leaderboard_pokemon_count, get_leaderboard_checkin_streak,
    get_leaderboard_workout_xp,
    is_admin, get_all_users,
    admin_update_user, admin_delete_user, set_admin_role,
    log_admin_action, get_system_logs, get_global_stats,
)
