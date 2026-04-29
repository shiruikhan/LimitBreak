"""Retroactively distribute loot box rewards for all existing achievements.

Run once after deploying the loot box system:
    python scripts/retroactive_loot.py

Safe to inspect with --dry-run first:
    python scripts/retroactive_loot.py --dry-run
"""

import os
import random
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

# ── Loot table (mirrors _roll_loot_box in utils/db.py) ───────────────────────

VITAMINS = ["hp-up", "protein", "iron", "calcium", "zinc", "carbos"]
STONES   = [
    "fire-stone", "water-stone", "thunder-stone", "leaf-stone", "moon-stone",
    "sun-stone", "shiny-stone", "dusk-stone", "dawn-stone", "ice-stone",
]


def roll_loot() -> dict:
    """Return a loot descriptor without touching the DB."""
    r = random.randint(1, 100)
    if r <= 50:
        return {"type": "xp",    "amount": random.randint(50, 150), "rarity": "common"}
    if r <= 80:
        return {"type": "coins", "amount": random.randint(50, 150), "rarity": "common"}
    if r <= 95:
        return {"type": "item",  "slug": random.choice(VITAMINS),   "rarity": "rare"}
    if r <= 99:
        return {"type": "item",  "slug": random.choice(STONES),     "rarity": "ultra_rare"}
    return     {"type": "item",  "slug": "xp-share",                 "rarity": "ultra_rare"}


def apply_loot(cur, user_id: str, loot: dict) -> str:
    """Apply loot to the DB. Returns a human-readable description."""
    t = loot["type"]

    if t == "coins":
        cur.execute(
            "UPDATE user_profiles SET coins = coins + %s WHERE id = %s",
            (loot["amount"], user_id),
        )
        return f"+{loot['amount']} moedas"

    if t == "xp":
        # Grant XP directly to slot-1 pokemon (simple UPDATE; no level-up processing
        # to keep this script simple and avoid triggering evolution side-effects).
        cur.execute("""
            SELECT up.id, up.xp, up.level
            FROM user_team ut
            JOIN user_pokemon up ON up.id = ut.user_pokemon_id
            WHERE ut.user_id = %s AND ut.slot = 1
        """, (user_id,))
        row = cur.fetchone()
        if row:
            pokemon_id, current_xp, level = row
            cur.execute(
                "UPDATE user_pokemon SET xp = xp + %s WHERE id = %s",
                (loot["amount"], pokemon_id),
            )
            return f"+{loot['amount']} XP (pokemon #{pokemon_id})"
        return f"+{loot['amount']} XP (sem slot 1)"

    if t == "item":
        slug = loot["slug"]
        cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (slug,))
        item_row = cur.fetchone()
        if item_row:
            item_id, item_name = item_row
            cur.execute("""
                INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (%s, %s, 1)
                ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = user_inventory.quantity + 1
            """, (user_id, item_id))
            return f"1x {item_name}"
        return f"item '{slug}' não encontrado no catálogo"

    return "sem recompensa"


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

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Distribuindo loot para {len(rows)} conquistas...\n")

    stats: dict[str, list[str]] = defaultdict(list)  # username → [descriptions]
    totals = {"xp": 0, "coins": 0, "items": 0}

    for user_id, slug, username in rows:
        loot = roll_loot()

        if DRY_RUN:
            desc = f"[simulado] {loot}"
        else:
            desc = apply_loot(cur, user_id, loot)

        # tally
        if loot["type"] == "xp":    totals["xp"]    += loot.get("amount", 0)
        if loot["type"] == "coins": totals["coins"]  += loot.get("amount", 0)
        if loot["type"] == "item":  totals["items"]  += 1

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
    print(f"  XP distribuído:     {totals['xp']}")
    print(f"  Moedas distribuídas:{totals['coins']}")
    print(f"  Itens concedidos:   {totals['items']}")
    print(f"  Total de conquistas:{len(rows)}")
    if DRY_RUN:
        print("\n⚠️  Modo DRY RUN — nenhuma alteração foi salva.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
