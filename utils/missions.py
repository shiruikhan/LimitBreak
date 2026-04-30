"""Mission catalog for the daily/weekly mission system (Priority B).

Each mission has a slug, display metadata, a target count, an event key
(used by update_mission_progress to match incoming events), and a reward
spec.  The pool lists are the source of truth; db.py selects from them
at period start and never hard-codes slugs.
"""

from __future__ import annotations
import random

# ---------------------------------------------------------------------------
# Daily pool — 3 drawn at random each day
# ---------------------------------------------------------------------------

DAILY_POOL: list[dict] = [
    {
        "slug": "register_workout",
        "label": "Registre um treino",
        "icon": "🏋️",
        "target": 1,
        "event": "workout",
        "reward_type": "xp",
        "reward_amount": 15,
        "reward_label": "+15 XP",
    },
    {
        "slug": "win_battle",
        "label": "Vença uma batalha PvP",
        "icon": "⚔️",
        "target": 1,
        "event": "battle_win",
        "reward_type": "coins",
        "reward_amount": 20,
        "reward_label": "+20 moedas",
    },
    {
        "slug": "daily_checkin",
        "label": "Faça seu check-in diário",
        "icon": "📅",
        "target": 1,
        "event": "checkin",
        "reward_type": "coins",
        "reward_amount": 10,
        "reward_label": "+10 moedas",
    },
    {
        "slug": "log_5_sets",
        "label": "Complete 5 séries em um treino",
        "icon": "💪",
        "target": 5,
        "event": "workout_sets",
        "reward_type": "xp",
        "reward_amount": 15,
        "reward_label": "+15 XP",
    },
    {
        "slug": "beat_pr",
        "label": "Supere um recorde pessoal",
        "icon": "🏅",
        "target": 1,
        "event": "pr",
        "reward_type": "xp",
        "reward_amount": 25,
        "reward_label": "+25 XP",
    },
    {
        "slug": "log_heavy_set",
        "label": "Registre um exercício com 50 kg ou mais",
        "icon": "🏆",
        "target": 1,
        "event": "workout_heavy",
        "reward_type": "coins",
        "reward_amount": 10,
        "reward_label": "+10 moedas",
    },
]

# ---------------------------------------------------------------------------
# Weekly pool — 1 drawn at random each Monday
# ---------------------------------------------------------------------------

WEEKLY_POOL: list[dict] = [
    {
        "slug": "weekly_checkin_5",
        "label": "Faça check-in 5 dias esta semana",
        "icon": "🗓️",
        "target": 5,
        "event": "checkin",
        "reward_type": "stone",
        "reward_amount": 1,
        "reward_label": "1× Pedra de evolução aleatória",
    },
    {
        "slug": "weekly_workout_3",
        "label": "Registre 3 treinos esta semana",
        "icon": "🔄",
        "target": 3,
        "event": "workout",
        "reward_type": "coins",
        "reward_amount": 50,
        "reward_label": "+50 moedas",
    },
    {
        "slug": "weekly_wins_3",
        "label": "Vença 3 batalhas esta semana",
        "icon": "🥊",
        "target": 3,
        "event": "battle_win",
        "reward_type": "vitamin",
        "reward_amount": 1,
        "reward_label": "1× Vitamina aleatória",
    },
    {
        "slug": "weekly_xp_200",
        "label": "Acumule 200 XP de treino esta semana",
        "icon": "⚡",
        "target": 200,
        "event": "workout_xp",
        "reward_type": "loot_box",
        "reward_amount": 1,
        "reward_label": "1× Loot Box",
    },
]

# ---------------------------------------------------------------------------
# Internal catalog — quick lookup by slug
# ---------------------------------------------------------------------------

_CATALOG: dict[str, dict] = {m["slug"]: m for m in DAILY_POOL + WEEKLY_POOL}


def get_mission(slug: str) -> dict | None:
    """Returns the catalog entry for a slug, or None if unknown."""
    return _CATALOG.get(slug)


def pick_daily_slugs(n: int = 3) -> list[str]:
    """Draw n distinct slugs from DAILY_POOL at random."""
    pool = [m["slug"] for m in DAILY_POOL]
    return random.sample(pool, min(n, len(pool)))


def pick_weekly_slug() -> str | None:
    """Draw one slug from WEEKLY_POOL at random."""
    return random.choice([m["slug"] for m in WEEKLY_POOL]) if WEEKLY_POOL else None
