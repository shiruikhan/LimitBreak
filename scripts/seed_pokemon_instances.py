"""
seed_pokemon_instances.py - Seeds IV, EV, and Nature for user_pokemon rows.

Run with:
    python scripts/seed_pokemon_instances.py

What it does:
    1. Ensures IV / EV / Nature columns exist on user_pokemon.
    2. Seeds only rows that still have missing values.

Ranges used:
    - IV: 0..31 per stat
    - EV: 0..252 per stat, max total 510
    - Nature: one of the 25 standard Pokemon natures

Idempotent:
    Safe to re-run. Existing non-null values are preserved.
"""

import os
import random

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = dict(
    host=os.getenv("host"),
    port=os.getenv("port"),
    dbname=os.getenv("database"),
    user=os.getenv("user"),
    password=os.getenv("password"),
)

STAT_ORDER = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")

NATURES = (
    "Hardy",
    "Lonely",
    "Brave",
    "Adamant",
    "Naughty",
    "Bold",
    "Docile",
    "Relaxed",
    "Impish",
    "Lax",
    "Timid",
    "Hasty",
    "Serious",
    "Jolly",
    "Naive",
    "Modest",
    "Mild",
    "Quiet",
    "Bashful",
    "Rash",
    "Calm",
    "Gentle",
    "Sassy",
    "Careful",
    "Quirky",
)


def ensure_columns(cur) -> None:
    """Add IV / EV / Nature columns when they do not exist yet."""
    cur.execute(
        """
        ALTER TABLE user_pokemon
            ADD COLUMN IF NOT EXISTS iv_hp SMALLINT,
            ADD COLUMN IF NOT EXISTS iv_attack SMALLINT,
            ADD COLUMN IF NOT EXISTS iv_defense SMALLINT,
            ADD COLUMN IF NOT EXISTS iv_sp_attack SMALLINT,
            ADD COLUMN IF NOT EXISTS iv_sp_defense SMALLINT,
            ADD COLUMN IF NOT EXISTS iv_speed SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_hp SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_attack SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_defense SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_sp_attack SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_sp_defense SMALLINT,
            ADD COLUMN IF NOT EXISTS ev_speed SMALLINT,
            ADD COLUMN IF NOT EXISTS nature TEXT;
        """
    )


def random_ivs() -> dict:
    return {f"iv_{stat}": random.randint(0, 31) for stat in STAT_ORDER}


def random_evs() -> dict:
    """Generate legal EVs as multiples of 4 within modern limits."""
    remaining = 510
    evs = {}
    for stat in random.sample(STAT_ORDER, len(STAT_ORDER)):
        max_for_stat = min(252, remaining)
        value = random.randint(0, max_for_stat // 4) * 4
        evs[f"ev_{stat}"] = value
        remaining -= value

    for stat in STAT_ORDER:
        evs.setdefault(f"ev_{stat}", 0)
    return evs


def random_nature() -> str:
    return random.choice(NATURES)


def rows_to_seed(cur) -> list[int]:
    cur.execute(
        """
        SELECT id
        FROM user_pokemon
        WHERE nature IS NULL
           OR iv_hp IS NULL OR iv_attack IS NULL OR iv_defense IS NULL
           OR iv_sp_attack IS NULL OR iv_sp_defense IS NULL OR iv_speed IS NULL
           OR ev_hp IS NULL OR ev_attack IS NULL OR ev_defense IS NULL
           OR ev_sp_attack IS NULL OR ev_sp_defense IS NULL OR ev_speed IS NULL
        ORDER BY id;
        """
    )
    return [row[0] for row in cur.fetchall()]


def seed_row(cur, user_pokemon_id: int) -> None:
    values = {}
    values.update(random_ivs())
    values.update(random_evs())
    values["nature"] = random_nature()
    values["id"] = user_pokemon_id

    cur.execute(
        """
        UPDATE user_pokemon
        SET
            iv_hp         = COALESCE(iv_hp, %(iv_hp)s),
            iv_attack     = COALESCE(iv_attack, %(iv_attack)s),
            iv_defense    = COALESCE(iv_defense, %(iv_defense)s),
            iv_sp_attack  = COALESCE(iv_sp_attack, %(iv_sp_attack)s),
            iv_sp_defense = COALESCE(iv_sp_defense, %(iv_sp_defense)s),
            iv_speed      = COALESCE(iv_speed, %(iv_speed)s),
            ev_hp         = COALESCE(ev_hp, %(ev_hp)s),
            ev_attack     = COALESCE(ev_attack, %(ev_attack)s),
            ev_defense    = COALESCE(ev_defense, %(ev_defense)s),
            ev_sp_attack  = COALESCE(ev_sp_attack, %(ev_sp_attack)s),
            ev_sp_defense = COALESCE(ev_sp_defense, %(ev_sp_defense)s),
            ev_speed      = COALESCE(ev_speed, %(ev_speed)s),
            nature        = COALESCE(nature, %(nature)s)
        WHERE id = %(id)s;
        """,
        values,
    )


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    try:
        ensure_columns(cur)
        conn.commit()

        ids = rows_to_seed(cur)
        total = len(ids)
        print(f"Seeding IV / EV / Nature for {total} Pokemon instances...")

        updated = 0
        for i, user_pokemon_id in enumerate(ids, 1):
            seed_row(cur, user_pokemon_id)
            updated += 1

            if i % 100 == 0 or i == total:
                conn.commit()
                print(f"  [{i}/{total}] committed (last user_pokemon_id={user_pokemon_id})")

        conn.commit()
        print(f"\nDone - {updated}/{total} Pokemon instances seeded.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
