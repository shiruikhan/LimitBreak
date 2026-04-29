"""
seed_pokemon_instances.py - Seeds IV, EV, Nature, and backfills effective stats.

Run with:
    python scripts/seed_pokemon_instances.py

What it does:
    1. Ensures IV / EV / Nature columns exist on user_pokemon.
    2. Seeds only rows that still have missing values.
    3. Recalculates stored stat_* for every user_pokemon row using:
       - species base stats
       - level
       - IVs / EVs
       - Nature (+10% / -10% on non-HP stats)
       - permanent flat boosts from user_pokemon_stat_boosts

Ranges used:
    - IV: 0..31 per stat
    - EV: 0..252 per stat, max total 510
    - Nature: one of the 25 standard Pokemon natures

Idempotent:
    Safe to re-run. Existing non-null genetic values are preserved and
    effective stats are refreshed.
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
NATURE_EFFECTS = {
    "lonely": ("attack", "defense"),
    "brave": ("attack", "speed"),
    "adamant": ("attack", "sp_attack"),
    "naughty": ("attack", "sp_defense"),
    "bold": ("defense", "attack"),
    "relaxed": ("defense", "speed"),
    "impish": ("defense", "sp_attack"),
    "lax": ("defense", "sp_defense"),
    "timid": ("speed", "attack"),
    "hasty": ("speed", "defense"),
    "jolly": ("speed", "sp_attack"),
    "naive": ("speed", "sp_defense"),
    "modest": ("sp_attack", "attack"),
    "mild": ("sp_attack", "defense"),
    "quiet": ("sp_attack", "speed"),
    "rash": ("sp_attack", "sp_defense"),
    "calm": ("sp_defense", "attack"),
    "gentle": ("sp_defense", "defense"),
    "sassy": ("sp_defense", "speed"),
    "careful": ("sp_defense", "sp_attack"),
}

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


def nature_modifiers(nature_name: str | None) -> dict[str, float]:
    modifiers = {stat: 1.0 for stat in STAT_ORDER}
    slug = str(nature_name or "").strip().lower()
    boosted_nerfed = NATURE_EFFECTS.get(slug)
    if not boosted_nerfed:
        return modifiers

    boosted, nerfed = boosted_nerfed
    modifiers[boosted] = 1.1
    modifiers[nerfed] = 0.9
    return modifiers


def pokemon_stat_value(
    base: int,
    level: int,
    *,
    iv: int = 0,
    ev: int = 0,
    nature: float = 1.0,
    is_hp: bool = False,
) -> int:
    level = max(1, min(level or 1, 100))
    base = max(0, base or 0)
    iv = max(0, iv or 0)
    ev = max(0, ev or 0)
    scaled = ((2 * base + iv + (ev // 4)) * level) // 100
    if is_hp:
        return max(1, scaled + level + 10)
    return max(1, int((scaled + 5) * nature))


def build_pokemon_stats(
    bases: tuple[int, ...],
    level: int,
    *,
    ivs: dict[str, int],
    evs: dict[str, int],
    nature_name: str | None,
    flat_boosts: dict[str, int],
) -> list[int]:
    nature_mods = nature_modifiers(nature_name)
    values = []
    for i, stat in enumerate(STAT_ORDER):
        values.append(
            pokemon_stat_value(
                bases[i],
                level,
                iv=ivs.get(stat, 0),
                ev=evs.get(stat, 0),
                nature=nature_mods.get(stat, 1.0),
                is_hp=(stat == "hp"),
            ) + flat_boosts.get(stat, 0)
        )
    return values


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


def all_row_ids(cur) -> list[int]:
    cur.execute("SELECT id FROM user_pokemon ORDER BY id;")
    return [row[0] for row in cur.fetchall()]


def has_stat_boosts_table(cur) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'user_pokemon_stat_boosts'
              AND table_schema = ANY(current_schemas(false))
        );
        """
    )
    return bool(cur.fetchone()[0])


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


def get_row_payload(cur, user_pokemon_id: int) -> tuple | None:
    cur.execute(
        """
        SELECT
            up.level,
            COALESCE(up.iv_hp, 0), COALESCE(up.iv_attack, 0), COALESCE(up.iv_defense, 0),
            COALESCE(up.iv_sp_attack, 0), COALESCE(up.iv_sp_defense, 0), COALESCE(up.iv_speed, 0),
            COALESCE(up.ev_hp, 0), COALESCE(up.ev_attack, 0), COALESCE(up.ev_defense, 0),
            COALESCE(up.ev_sp_attack, 0), COALESCE(up.ev_sp_defense, 0), COALESCE(up.ev_speed, 0),
            up.nature,
            ps.base_hp, ps.base_attack, ps.base_defense,
            ps.base_sp_attack, ps.base_sp_defense, ps.base_speed
        FROM user_pokemon up
        JOIN pokemon_species ps ON ps.id = up.species_id
        WHERE up.id = %s;
        """,
        (user_pokemon_id,),
    )
    return cur.fetchone()


def get_flat_boosts(cur, user_pokemon_id: int, boosts_enabled: bool) -> dict[str, int]:
    boosts = {stat: 0 for stat in STAT_ORDER}
    if not boosts_enabled:
        return boosts

    cur.execute(
        """
        SELECT stat, COALESCE(SUM(delta), 0)
        FROM user_pokemon_stat_boosts
        WHERE user_pokemon_id = %s
        GROUP BY stat;
        """,
        (user_pokemon_id,),
    )
    for stat, total in cur.fetchall():
        boosts[stat] = total
    return boosts


def recalc_row(cur, user_pokemon_id: int, boosts_enabled: bool) -> None:
    row = get_row_payload(cur, user_pokemon_id)
    if not row:
        return

    level = row[0]
    ivs = {stat: row[i + 1] for i, stat in enumerate(STAT_ORDER)}
    evs = {stat: row[i + 7] for i, stat in enumerate(STAT_ORDER)}
    nature = row[13]
    bases = tuple(row[14:20])
    boosts = get_flat_boosts(cur, user_pokemon_id, boosts_enabled)
    stats = build_pokemon_stats(
        bases,
        level,
        ivs=ivs,
        evs=evs,
        nature_name=nature,
        flat_boosts=boosts,
    )

    cur.execute(
        """
        UPDATE user_pokemon
        SET stat_hp = %s,
            stat_attack = %s,
            stat_defense = %s,
            stat_sp_attack = %s,
            stat_sp_defense = %s,
            stat_speed = %s
        WHERE id = %s;
        """,
        (*stats, user_pokemon_id),
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

        boosts_enabled = has_stat_boosts_table(cur)
        all_ids = all_row_ids(cur)
        total_recalc = len(all_ids)
        print(f"Backfilling effective stats for {total_recalc} Pokemon instances...")

        recalculated = 0
        for i, user_pokemon_id in enumerate(all_ids, 1):
            recalc_row(cur, user_pokemon_id, boosts_enabled)
            recalculated += 1

            if i % 100 == 0 or i == total_recalc:
                conn.commit()
                print(f"  [{i}/{total_recalc}] stats refreshed (last user_pokemon_id={user_pokemon_id})")

        conn.commit()
        print(f"\nDone - {recalculated}/{total_recalc} Pokemon instances refreshed.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
