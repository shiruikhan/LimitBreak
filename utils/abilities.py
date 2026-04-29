"""Passive ability registry for Release 3A.

Only the Pokémon in team slot 1 applies an ability, and only during workout events.
Unsupported or null ability slugs are a no-op.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Supported workout abilities (v1 whitelist)
# ---------------------------------------------------------------------------
# Each entry maps ability_slug -> description shown in the UI.
# Effect logic lives in do_exercise_event(); this dict is the source of truth
# for which slugs are recognized and what text to display.

WORKOUT_ABILITIES: dict[str, str] = {
    "blaze":          "+15% XP em treinos de alta intensidade (≥200 XP bruto)",
    "synchronize":    "Aumenta a distribuição do XP Share para os outros membros da equipe",
    "pickup":         "Pequena chance de ganhar um item aleatório após o treino",
    "pressure":       "Aumenta a chance de spawn do tipo mais frequente da sessão",
    "compound-eyes":  "Rerrola uma tentativa de spawn sem sucesso antes de desistir",
}


def get_ability_description(ability_slug: str | None) -> str | None:
    """Returns the display description for a supported ability, or None."""
    if ability_slug is None:
        return None
    return WORKOUT_ABILITIES.get(ability_slug)


def is_supported(ability_slug: str | None) -> bool:
    """True if the slug is in the v1 workout whitelist."""
    return ability_slug in WORKOUT_ABILITIES


# ---------------------------------------------------------------------------
# Effect helpers (stubs — wired up in do_exercise_event() Release 3A)
# ---------------------------------------------------------------------------

def apply_blaze(raw_xp: int) -> int:
    """Returns boosted XP if raw_xp qualifies, else raw_xp unchanged."""
    if raw_xp >= 200:
        return int(raw_xp * 1.15)
    return raw_xp


def apply_synchronize_multiplier() -> float:
    """Returns the XP Share distribution multiplier when synchronize is active."""
    return 0.45  # default share is 30%; synchronize raises it to 45%


def compound_eyes_reroll() -> bool:
    """Returns True to signal a spawn reroll should be attempted."""
    return True
