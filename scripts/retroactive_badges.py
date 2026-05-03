"""Distribute gym badge achievements retroactively to all existing users.

Checks every user's current stats against the 8 Kanto gym badge conditions
and awards any badges they've already earned but haven't received yet.
Grants 1 Loot Box per new badge as the standard achievement reward.

Usage:
    python scripts/retroactive_badges.py            # apply changes
    python scripts/retroactive_badges.py --dry-run  # preview only
"""

import datetime
import os
import sys

import psycopg2
from dotenv import load_dotenv  # noqa: F401

load_dotenv()


def _load_db_params() -> dict:
    """Load DB credentials: secrets.toml → .env fallback."""
    secrets_path = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "secrets.toml")
    secrets_path = os.path.normpath(secrets_path)

    if os.path.isfile(secrets_path):
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                tomllib = None  # type: ignore[assignment]

        if tomllib is not None:
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            db = data.get("database", {})
            if db.get("host"):
                return {
                    "host":     db["host"],
                    "port":     int(db.get("port", 6543)),
                    "dbname":   db.get("name") or db.get("database", "postgres"),
                    "user":     db["user"],
                    "password": db["password"],
                    "sslmode":  "require",
                }

    # Fallback: .env
    return {
        "host":     os.getenv("host"),
        "port":     int(os.getenv("port", 6543)),
        "dbname":   os.getenv("database", "postgres"),
        "user":     os.getenv("user"),
        "password": os.getenv("password"),
        "sslmode":  "require",
    }


DB_PARAMS = _load_db_params()

DRY_RUN = "--dry-run" in sys.argv

# ── Gym badge definitions (mirrors utils/achievements.py) ─────────────────────

GYM_BADGE_SLUGS = [
    "badge_pedra",
    "badge_cascata",
    "badge_trovao",
    "badge_arco_iris",
    "badge_alma",
    "badge_pantano",
    "badge_vulcao",
    "badge_terra",
]

GYM_BADGE_META = {
    "badge_pedra":     {"name": "Insígnia Pedra",     "check": lambda s: s["workout_count"] >= 10},
    "badge_cascata":   {"name": "Insígnia Cascata",   "check": lambda s: s["checkin_streak_max"] >= 7},
    "badge_trovao":    {"name": "Insígnia Trovão",    "check": lambda s: s["battle_wins"] >= 5},
    "badge_arco_iris": {"name": "Insígnia Arco-íris", "check": lambda s: s["pokemon_count"] >= 25},
    "badge_alma":      {"name": "Insígnia Alma",      "check": lambda s: s["workout_streak"] >= 30},
    "badge_pantano":   {"name": "Insígnia Pântano",   "check": lambda s: s["pr_count"] >= 10},
    "badge_vulcao":    {"name": "Insígnia Vulcão",    "check": lambda s: s["evolved_count"] >= 10},
    "badge_terra":     {"name": "Insígnia Terra",     "check": lambda s: s["workout_count"] >= 100},
}


def _today_brt() -> datetime.date:
    return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()


def _collect_stats(cur, user_id: str) -> dict:
    """Collect all stats needed for gym badge conditions."""
    stats: dict = {}

    cur.execute("SELECT COUNT(*) FROM user_pokemon WHERE user_id = %s;", (user_id,))
    stats["pokemon_count"] = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(MAX(streak), 0) FROM user_checkins WHERE user_id = %s;",
        (user_id,),
    )
    stats["checkin_streak_max"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM workout_logs WHERE user_id = %s;", (user_id,))
    stats["workout_count"] = cur.fetchone()[0]

    cur.execute("""
        WITH ranked AS (
            SELECT el.workout_log_id,
                   el.exercise_id,
                   MAX((s->>'weight')::float) AS session_best,
                   ROW_NUMBER() OVER (
                       PARTITION BY el.exercise_id
                       ORDER BY wl.completed_at
                   ) AS rn
            FROM exercise_logs el
            JOIN workout_logs wl ON wl.id = el.workout_log_id
            JOIN LATERAL jsonb_array_elements(el.sets_data) AS s ON true
            WHERE wl.user_id = %s
              AND (s->>'weight') IS NOT NULL
            GROUP BY el.workout_log_id, el.exercise_id, wl.completed_at
        ),
        with_prev AS (
            SELECT exercise_id,
                   session_best,
                   LAG(session_best) OVER (
                       PARTITION BY exercise_id ORDER BY rn
                   ) AS prev_best
            FROM ranked
        )
        SELECT COUNT(*) FROM with_prev
        WHERE prev_best IS NOT NULL AND session_best > prev_best;
    """, (user_id,))
    stats["pr_count"] = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM user_battles WHERE winner_id = %s;",
        (user_id,),
    )
    stats["battle_wins"] = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(DISTINCT up.id)
        FROM user_pokemon up
        JOIN pokemon_evolutions pe ON pe.to_species_id = up.species_id
        WHERE up.user_id = %s;
    """, (user_id,))
    stats["evolved_count"] = cur.fetchone()[0]

    # Workout streak
    cur.execute("""
        SELECT DISTINCT (completed_at AT TIME ZONE 'America/Sao_Paulo')::date AS d
        FROM workout_logs WHERE user_id = %s ORDER BY d DESC;
    """, (user_id,))
    streak_days = [r[0] for r in cur.fetchall()]
    streak = 0
    check_day = _today_brt()
    for d in streak_days:
        if d == check_day:
            streak += 1
            check_day -= datetime.timedelta(days=1)
        elif d < check_day:
            break
    stats["workout_streak"] = streak

    return stats


def _ensure_loot_box_item(cur) -> int:
    cur.execute("SELECT id FROM shop_items WHERE slug = 'loot-box';")
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("""
        INSERT INTO shop_items (slug, name, description, category, price, icon)
        VALUES ('loot-box', 'Loot Box', 'Abra na Mochila para receber uma recompensa aleatoria.',
                'other', 1, '🎁')
        RETURNING id;
    """)
    return cur.fetchone()[0]


def _grant_loot_box(cur, user_id: str, loot_box_id: int) -> None:
    cur.execute("""
        INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (%s, %s, 1)
        ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = user_inventory.quantity + 1;
    """, (user_id, loot_box_id))


def _award_badge(cur, user_id: str, slug: str) -> None:
    cur.execute("""
        INSERT INTO user_achievements (user_id, achievement_slug)
        VALUES (%s, %s)
        ON CONFLICT (user_id, achievement_slug) DO NOTHING;
    """, (user_id, slug))


def main():
    print(f"Conectando: {DB_PARAMS['user']}@{DB_PARAMS['host']}:{DB_PARAMS['port']}")
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    cur.execute("SELECT id, username FROM user_profiles ORDER BY username;")
    users = cur.fetchall()

    if not users:
        print("Nenhum usuário encontrado.")
        conn.close()
        return

    loot_box_id = _ensure_loot_box_item(cur)

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Verificando {len(users)} usuário(s)...\n")

    total_badges = 0
    total_loot_boxes = 0

    for user_id, username in users:
        # Load already-earned badges (including non-gym ones)
        cur.execute(
            "SELECT achievement_slug FROM user_achievements WHERE user_id = %s;",
            (user_id,),
        )
        already = {r[0] for r in cur.fetchall()}

        # Check which gym badges are new for this user
        pending = [s for s in GYM_BADGE_SLUGS if s not in already]
        if not pending:
            print(f"  {username}: todas as insígnias já atribuídas — pulando")
            continue

        stats = _collect_stats(cur, user_id)

        earned = []
        for slug in pending:
            meta = GYM_BADGE_META[slug]
            if meta["check"](stats):
                earned.append(slug)

        if not earned:
            print(f"  {username}: nenhuma insígnia nova qualificada")
            continue

        print(f"  {username}:")
        for slug in earned:
            name = GYM_BADGE_META[slug]["name"]
            print(f"    + {name} [{slug}]")
            if not DRY_RUN:
                _award_badge(cur, user_id, slug)
                _grant_loot_box(cur, user_id, loot_box_id)

        total_badges += len(earned)
        total_loot_boxes += len(earned)

    if not DRY_RUN:
        conn.commit()
        print("\nCommit realizado.")

    print(f"\n── Totais {'(simulado) ' if DRY_RUN else ''}──────────────────────────────────────────")
    print(f"  Insígnias concedidas:  {total_badges}")
    print(f"  Loot Boxes concedidas: {total_loot_boxes}")
    if DRY_RUN:
        print("\n⚠️  Modo DRY RUN — nenhuma alteração foi salva.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
