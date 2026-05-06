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
    get_workout_sheets,
    get_workout_streak,
    get_xp_share_status,
    is_admin,
)


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


def clear_user_cache() -> None:
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
    get_cached_recent_muscle_balance.clear()
    get_cached_workout_sheets.clear()
    get_cached_user_achievements.clear()
    get_cached_monthly_rest_days.clear()
