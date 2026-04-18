"""
seed_stats.py — Populates base_hp/attack/defense/sp_attack/sp_defense/speed
on pokemon_species by fetching from PokéAPI.

Run after seed_pokedex.py:
    python scripts/seed_stats.py

Idempotent: uses ON CONFLICT DO UPDATE, safe to re-run.
Only processes species with id <= 1025 (national dex).
"""

import os
import time
import requests
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

STAT_SLUGS = {
    "hp":              "base_hp",
    "attack":          "base_attack",
    "defense":         "base_defense",
    "special-attack":  "base_sp_attack",
    "special-defense": "base_sp_defense",
    "speed":           "base_speed",
}

API_BASE = "https://pokeapi.co/api/v2/pokemon"
DELAY    = 0.3   # seconds between requests — be polite to PokéAPI


def fetch_stats(pokemon_id: int) -> dict | None:
    """Returns {base_hp, base_attack, ...} or None on error."""
    url = f"{API_BASE}/{pokemon_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        result = {}
        for stat in data["stats"]:
            slug = stat["stat"]["name"]
            col  = STAT_SLUGS.get(slug)
            if col:
                result[col] = stat["base_stat"]
        return result if len(result) == 6 else None
    except Exception as e:
        print(f"  [ERROR] id={pokemon_id}: {e}")
        return None


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur  = conn.cursor()

    # Fetch all species IDs that still have NULL base stats
    cur.execute("""
        SELECT id FROM pokemon_species
        WHERE base_hp IS NULL AND id <= 1025
        ORDER BY id;
    """)
    ids = [row[0] for row in cur.fetchall()]
    total = len(ids)
    print(f"Seeding stats for {total} Pokémon...")

    updated = 0
    for i, pid in enumerate(ids, 1):
        stats = fetch_stats(pid)
        if not stats:
            print(f"  [{i}/{total}] #{pid} — skipped (no data)")
            continue

        cur.execute("""
            UPDATE pokemon_species SET
                base_hp          = %(base_hp)s,
                base_attack      = %(base_attack)s,
                base_defense     = %(base_defense)s,
                base_sp_attack   = %(base_sp_attack)s,
                base_sp_defense  = %(base_sp_defense)s,
                base_speed       = %(base_speed)s
            WHERE id = %(id)s;
        """, {**stats, "id": pid})

        updated += 1
        if i % 50 == 0 or i == total:
            conn.commit()
            print(f"  [{i}/{total}] committed (last: #{pid})")

        time.sleep(DELAY)

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone — {updated}/{total} Pokémon updated.")


if __name__ == "__main__":
    main()
