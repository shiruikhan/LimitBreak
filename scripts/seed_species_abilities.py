"""Seed ability_slug for pokemon_species via PokéAPI.

Fetches each species' first non-hidden ability and writes it to pokemon_species.ability_slug.
Only updates rows where ability_slug IS NULL (idempotent).
Skips species that the PokéAPI doesn't recognise (regional forms with id > 10000 use their
base-form slug).

Usage:
    python scripts/seed_species_abilities.py [--dry-run] [--limit N]
"""

import argparse
import os
import sys
import time

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

POKEAPI_BASE = "https://pokeapi.co/api/v2"
REQUEST_DELAY = 0.3  # seconds between API calls to avoid rate limiting


def _db_conn():
    return psycopg2.connect(
        host=os.getenv("host"),
        port=os.getenv("port", 5432),
        dbname=os.getenv("database"),
        user=os.getenv("user"),
        password=os.getenv("password"),
    )


def _fetch_ability_slug(species_id: int) -> str | None:
    """Returns the first non-hidden ability slug for a species, or None on failure."""
    url = f"{POKEAPI_BASE}/pokemon/{species_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        for entry in data.get("abilities", []):
            if not entry.get("is_hidden", True):
                return entry["ability"]["name"]
        # All hidden — take the first one anyway
        abilities = data.get("abilities", [])
        if abilities:
            return abilities[0]["ability"]["name"]
        return None
    except Exception as exc:
        print(f"  [warn] species {species_id}: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Seed ability_slug into pokemon_species")
    parser.add_argument("--dry-run", action="store_true", help="Print updates without writing")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N species (0 = all)")
    args = parser.parse_args()

    conn = _db_conn()
    cur = conn.cursor()

    # Fetch species that still need an ability (normal + regional)
    cur.execute("""
        SELECT id FROM pokemon_species
        WHERE ability_slug IS NULL
        ORDER BY id;
    """)
    rows = [r[0] for r in cur.fetchall()]
    if args.limit:
        rows = rows[: args.limit]

    print(f"Found {len(rows)} species without ability_slug.")
    updated = 0
    skipped = 0

    for sid in rows:
        # Regional forms (id > 10000) — use the base national dex id for the API call
        api_id = sid if sid <= 1025 else sid % 10000
        slug = _fetch_ability_slug(api_id)
        if slug is None:
            print(f"  skip  #{sid:04d}  (no ability found)")
            skipped += 1
        else:
            print(f"  {'(dry) ' if args.dry_run else ''}#{sid:04d}  → {slug}")
            if not args.dry_run:
                cur.execute(
                    "UPDATE pokemon_species SET ability_slug = %s WHERE id = %s;",
                    (slug, sid),
                )
            updated += 1
        time.sleep(REQUEST_DELAY)

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone. Updated: {updated}  Skipped: {skipped}  (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
