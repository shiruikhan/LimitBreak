"""
audit_team_stats.py - Audits active team stats and syncs stale rows.

Run with:
    python scripts/audit_team_stats.py
    python scripts/audit_team_stats.py --dry-run
    python scripts/audit_team_stats.py --user-id <uuid>

What it does:
    1. Scans user_team entries.
    2. Recomputes expected stat_* from the current species base stats,
       level, IVs, EVs, nature, and permanent flat boosts.
    3. Updates any mismatched user_pokemon rows unless --dry-run is used.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.db import (  # noqa: E402
    _STAT_ORDER,
    _db_params,
    _expected_user_pokemon_stats,
    _stored_user_pokemon_stats,
    _sync_user_pokemon_stats,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit and sync active team stats using canonical species formulas."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report mismatches without updating user_pokemon.",
    )
    parser.add_argument(
        "--user-id",
        help="Limit the audit to a single user's active team.",
    )
    return parser.parse_args()


def team_rows(cur, user_id: str | None) -> list[tuple]:
    where_sql = "WHERE ut.user_id = %s" if user_id else ""
    params = (user_id,) if user_id else ()
    cur.execute(
        f"""
        SELECT ut.user_id, ut.slot, up.id, ps.name, up.level
        FROM user_team ut
        JOIN user_pokemon up ON up.id = ut.user_pokemon_id
        JOIN pokemon_species ps ON ps.id = up.species_id
        {where_sql}
        ORDER BY ut.user_id, ut.slot, up.id;
        """,
        params,
    )
    return cur.fetchall()


def format_stats(values: list[int] | None) -> str:
    if not values:
        return "unavailable"
    return ", ".join(
        f"{stat}={value}" for stat, value in zip(_STAT_ORDER, values)
    )


def main() -> int:
    args = parse_args()
    conn = psycopg2.connect(**_db_params())
    updated = 0
    mismatches = 0

    try:
        with conn.cursor() as cur:
            rows = team_rows(cur, args.user_id)
            print(f"Scanning {len(rows)} active team entries...")

            for team_user_id, slot, user_pokemon_id, species_name, level in rows:
                stored = _stored_user_pokemon_stats(cur, user_pokemon_id)
                expected = _expected_user_pokemon_stats(cur, user_pokemon_id)
                if stored == expected or expected is None:
                    continue

                mismatches += 1
                print(
                    f"[MISMATCH] user={team_user_id} slot={slot} "
                    f"user_pokemon_id={user_pokemon_id} species={species_name} level={level}"
                )
                print(f"  stored:   {format_stats(stored)}")
                print(f"  expected: {format_stats(expected)}")

                if not args.dry_run and _sync_user_pokemon_stats(cur, user_pokemon_id):
                    updated += 1

            if args.dry_run:
                conn.rollback()
                print("\nDry run complete.")
            else:
                conn.commit()
                print("\nSync complete.")

        print(f"Mismatches found: {mismatches}")
        print(f"Rows updated: {updated}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"Audit failed: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
