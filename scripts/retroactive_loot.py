"""Retroactively grant Loot Box inventory items for all existing achievements.

Run once after deploying the loot box system:
    python scripts/retroactive_loot.py

Safe to inspect with --dry-run first:
    python scripts/retroactive_loot.py --dry-run
"""

import os
import sys
from collections import defaultdict

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "host":     os.getenv("host"),
    "port":     os.getenv("port"),
    "dbname":   os.getenv("database"),
    "user":     os.getenv("user"),
    "password": os.getenv("password"),
}

DRY_RUN = "--dry-run" in sys.argv

LOOT_BOX_ITEM = {
    "slug": "loot-box",
    "name": "Loot Box",
    "description": "Abra na Mochila para receber uma recompensa aleatoria.",
    "category": "other",
    "price": 1,
    "icon": "🎁",
}


def ensure_loot_box_item(cur) -> tuple[int, str]:
    """Garantia idempotente do item Loot Box no catálogo."""
    cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (LOOT_BOX_ITEM["slug"],))
    row = cur.fetchone()
    if row:
        return row[0], row[1]

    cur.execute("""
        INSERT INTO shop_items (slug, name, description, category, price, effect_stat, effect_value, icon)
        VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s)
        RETURNING id, name;
    """, (
        LOOT_BOX_ITEM["slug"],
        LOOT_BOX_ITEM["name"],
        LOOT_BOX_ITEM["description"],
        LOOT_BOX_ITEM["category"],
        LOOT_BOX_ITEM["price"],
        LOOT_BOX_ITEM["icon"],
    ))
    row = cur.fetchone()
    return row[0], row[1]


def grant_loot_box(cur, user_id: str) -> str:
    """Add one Loot Box to the user's inventory."""
    item_id, item_name = ensure_loot_box_item(cur)
    cur.execute("""
        INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (%s, %s, 1)
        ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = user_inventory.quantity + 1
    """, (user_id, item_id))
    return f"1x {item_name}"


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur  = conn.cursor()

    cur.execute("""
        SELECT ua.user_id, ua.achievement_slug, up.username
        FROM user_achievements ua
        JOIN user_profiles up ON up.id = ua.user_id
        ORDER BY ua.user_id, ua.unlocked_at
    """)
    rows = cur.fetchall()

    if not rows:
        print("Nenhuma conquista encontrada.")
        conn.close()
        return

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Concedendo Loot Boxes para {len(rows)} conquistas...\n")

    stats: dict[str, list[str]] = defaultdict(list)  # username → [descriptions]
    totals = {"loot_boxes": 0}

    for user_id, slug, username in rows:
        if DRY_RUN:
            desc = "[simulado] 1x Loot Box"
        else:
            desc = grant_loot_box(cur, user_id)

        totals["loot_boxes"] += 1

        stats[username].append(f"  [{slug}] → {desc}")

    if not DRY_RUN:
        conn.commit()
        print("Commit realizado.\n")

    # ── Report ──────────────────────────────────────────────────────────────────
    for username, lines in sorted(stats.items()):
        print(f"👤 {username} ({len(lines)} conquistas)")
        for line in lines:
            print(line)
        print()

    print("── Totais ──────────────────────────────────────────")
    print(f"  Loot Boxes concedidas: {totals['loot_boxes']}")
    print(f"  Total de conquistas:{len(rows)}")
    if DRY_RUN:
        print("\n⚠️  Modo DRY RUN — nenhuma alteração foi salva.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
