import streamlit as st

from utils.db import (
    get_battle_history,
    get_battle_opponents,
    get_checkin_streak,
    get_daily_battle_count,
    get_daily_xp_from_exercise,
    get_monthly_checkins,
    get_monthly_rest_days,
    get_recent_muscle_balance,
    get_team_stat_boost_counts,
    get_user_achievements,
    get_user_bench,
    get_user_inventory,
    get_user_missions,
    get_user_pokemon_ids,
    get_user_profile,
    get_user_team,
    get_workout_history,
    get_workout_builder_tree,
    get_workout_sheets,
    get_workout_streak,
    get_xp_share_status,
    is_admin,
)

_BATTLE_HISTORY_LIMITS = (20,)
_WORKOUT_HISTORY_LIMITS = (10, 30)
_RECENT_MUSCLE_BALANCE_WINDOWS = (7,)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_user_profile(user_id: str):
    return get_user_profile(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_user_team(user_id: str):
    return get_user_team(user_id)


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_user_pokemon_ids(user_id: str):
    return get_user_pokemon_ids(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_checkin_streak(user_id: str):
    return get_checkin_streak(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_monthly_checkins(user_id: str, year: int, month: int):
    return get_monthly_checkins(user_id, year, month)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_daily_battle_count(user_id: str):
    return get_daily_battle_count(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_battle_opponents(user_id: str):
    return get_battle_opponents(user_id)


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_battle_history(user_id: str, limit: int = 20):
    return get_battle_history(user_id, limit)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_user_inventory(user_id: str):
    return get_user_inventory(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_xp_share_status(user_id: str):
    return get_xp_share_status(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_user_missions(user_id: str):
    return get_user_missions(user_id)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_is_admin(user_id: str):
    return is_admin(user_id)


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_user_achievements(user_id: str):
    return get_user_achievements(user_id)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_monthly_rest_days(user_id: str, year: int, month: int):
    return get_monthly_rest_days(user_id, year, month)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_user_bench(user_id: str):
    return get_user_bench(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_team_stat_boost_counts(user_id: str):
    return get_team_stat_boost_counts(user_id)


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_workout_streak(user_id: str):
    return get_workout_streak(user_id)


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_daily_xp_from_exercise(user_id: str):
    return get_daily_xp_from_exercise(user_id)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_workout_history(user_id: str, limit: int = 10):
    return get_workout_history(user_id, limit)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_recent_muscle_balance(user_id: str, days: int = 7):
    return get_recent_muscle_balance(user_id, days)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_workout_sheets(user_id: str):
    return get_workout_sheets(user_id)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_workout_builder_tree(user_id: str):
    return get_workout_builder_tree(user_id)


def _clear_cached_call(cached_func, *args) -> None:
    if args:
        cached_func.clear(*args)
        return
    cached_func.clear()


def clear_profile_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_user_profile, user_id)
    _clear_cached_call(get_cached_is_admin, user_id)


def clear_team_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_user_team, user_id)
    _clear_cached_call(get_cached_user_pokemon_ids, user_id)
    _clear_cached_call(get_cached_user_bench, user_id)
    _clear_cached_call(get_cached_team_stat_boost_counts, user_id)


def clear_checkin_cache(user_id: str, year: int | None = None, month: int | None = None) -> None:
    _clear_cached_call(get_cached_checkin_streak, user_id)
    if year is not None and month is not None:
        _clear_cached_call(get_cached_monthly_checkins, user_id, year, month)
        _clear_cached_call(get_cached_monthly_rest_days, user_id, year, month)
    else:
        get_cached_monthly_checkins.clear()
        get_cached_monthly_rest_days.clear()


def clear_battle_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_daily_battle_count, user_id)
    _clear_cached_call(get_cached_battle_opponents, user_id)
    for limit in _BATTLE_HISTORY_LIMITS:
        _clear_cached_call(get_cached_battle_history, user_id, limit)


def clear_inventory_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_user_inventory, user_id)
    _clear_cached_call(get_cached_xp_share_status, user_id)


def clear_missions_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_user_missions, user_id)


def clear_achievements_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_user_achievements, user_id)


def clear_workout_cache(user_id: str) -> None:
    _clear_cached_call(get_cached_workout_streak, user_id)
    _clear_cached_call(get_cached_daily_xp_from_exercise, user_id)
    _clear_cached_call(get_cached_workout_sheets, user_id)
    _clear_cached_call(get_cached_workout_builder_tree, user_id)
    for limit in _WORKOUT_HISTORY_LIMITS:
        _clear_cached_call(get_cached_workout_history, user_id, limit)
    for days in _RECENT_MUSCLE_BALANCE_WINDOWS:
        _clear_cached_call(get_cached_recent_muscle_balance, user_id, days)


def clear_user_cache(
    user_id: str | None = None,
    *,
    year: int | None = None,
    month: int | None = None,
) -> None:
    if user_id is None:
        get_cached_user_profile.clear()
        get_cached_user_team.clear()
        get_cached_user_pokemon_ids.clear()
        get_cached_checkin_streak.clear()
        get_cached_monthly_checkins.clear()
        get_cached_daily_battle_count.clear()
        get_cached_battle_opponents.clear()
        get_cached_battle_history.clear()
        get_cached_user_inventory.clear()
        get_cached_xp_share_status.clear()
        get_cached_user_missions.clear()
        get_cached_is_admin.clear()
        get_cached_user_bench.clear()
        get_cached_team_stat_boost_counts.clear()
        get_cached_workout_streak.clear()
        get_cached_daily_xp_from_exercise.clear()
        get_cached_workout_history.clear()
        get_cached_workout_builder_tree.clear()
        get_cached_recent_muscle_balance.clear()
        get_cached_workout_sheets.clear()
        get_cached_user_achievements.clear()
        get_cached_monthly_rest_days.clear()
        return

    clear_profile_cache(user_id)
    clear_team_cache(user_id)
    clear_checkin_cache(user_id, year=year, month=month)
    clear_battle_cache(user_id)
    clear_inventory_cache(user_id)
    clear_missions_cache(user_id)
    clear_achievements_cache(user_id)
    clear_workout_cache(user_id)
