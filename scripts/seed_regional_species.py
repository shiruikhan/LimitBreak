"""Seeds regional form Pokémon as full species entries.

For each regional variant, this script:
  1. Fetches data from PokéAPI (/pokemon/{form_slug}/)
  2. Upserts into pokemon_species (types, base stats, sprites)
  3. Upserts level-up moves into pokemon_moves + pokemon_species_moves
  4. Inserts a pokemon_evolutions entry with trigger='use-item' and
     item_name matching the shop item slug ('form-{form_slug}')

Run AFTER migrate_regional_forms.sql and seed_regional_forms.py.
Idempotent — safe to re-run.
"""

import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = dict(
    host=os.getenv("host"), port=os.getenv("port"),
    dbname=os.getenv("database"), user=os.getenv("user"), password=os.getenv("password"),
)

# (base_species_id, region, form_slug)
REGIONAL_FORMS = [
    (26,  "alola", "raichu-alola"),
    (27,  "alola", "sandshrew-alola"),
    (28,  "alola", "sandslash-alola"),
    (37,  "alola", "vulpix-alola"),
    (38,  "alola", "ninetales-alola"),
    (50,  "alola", "diglett-alola"),
    (51,  "alola", "dugtrio-alola"),
    (52,  "alola", "meowth-alola"),
    (53,  "alola", "persian-alola"),
    (74,  "alola", "geodude-alola"),
    (75,  "alola", "graveler-alola"),
    (76,  "alola", "golem-alola"),
    (88,  "alola", "grimer-alola"),
    (89,  "alola", "muk-alola"),
    (103, "alola", "exeggutor-alola"),
    (105, "alola", "marowak-alola"),
    (52,  "galar", "meowth-galar"),
    (77,  "galar", "ponyta-galar"),
    (78,  "galar", "rapidash-galar"),
    (79,  "galar", "slowpoke-galar"),
    (80,  "galar", "slowbro-galar"),
    (83,  "galar", "farfetchd-galar"),
    (110, "galar", "weezing-galar"),
    (122, "galar", "mr-mime-galar"),
    (199, "galar", "slowking-galar"),
    (222, "galar", "corsola-galar"),
    (263, "galar", "zigzagoon-galar"),
    (264, "galar", "linoone-galar"),
    (554, "galar", "darumaka-galar"),
    (562, "galar", "yamask-galar"),
    (618, "galar", "stunfisk-galar"),
    (58,  "hisui", "growlithe-hisui"),
    (59,  "hisui", "arcanine-hisui"),
    (100, "hisui", "voltorb-hisui"),
    (101, "hisui", "electrode-hisui"),
    (157, "hisui", "typhlosion-hisui"),
    (211, "hisui", "qwilfish-hisui"),
    (215, "hisui", "sneasel-hisui"),
    (570, "hisui", "zorua-hisui"),
    (571, "hisui", "zoroark-hisui"),
    (628, "hisui", "braviary-hisui"),
    (713, "hisui", "avalugg-hisui"),
]

STAT_MAP = {
    "hp":              "base_hp",
    "attack":          "base_attack",
    "defense":         "base_defense",
    "special-attack":  "base_sp_attack",
    "special-defense": "base_sp_defense",
    "speed":           "base_speed",
}


def extract_id(url: str) -> int | None:
    if not url:
        return None
    return int(url.rstrip("/").split("/")[-1])


def seed():
    conn = psycopg2.connect(**DB_PARAMS)
    session = requests.Session()
    cur = conn.cursor()

    ok = 0
    failed = []

    for base_id, region, form_slug in REGIONAL_FORMS:
        print(f"  [{region}] {form_slug}...", end=" ", flush=True)
        try:
            resp = session.get(f"https://pokeapi.co/api/v2/pokemon/{form_slug}/", timeout=15)
            resp.raise_for_status()
            d = resp.json()
            time.sleep(0.35)
        except Exception as e:
            print(f"FETCH ERROR: {e}")
            failed.append(form_slug)
            continue

        form_id   = d["id"]
        name      = form_slug.replace("-", " ").title()
        slug      = d["name"]
        base_exp  = d.get("base_experience") or 0
        sprite    = (d.get("sprites") or {}).get("front_default") or ""
        shiny     = (d.get("sprites") or {}).get("front_shiny")   or ""

        types     = d.get("types", [])
        type1_id  = extract_id(types[0]["type"]["url"]) if len(types) > 0 else None
        type2_id  = extract_id(types[1]["type"]["url"]) if len(types) > 1 else None

        stats = {s["stat"]["name"]: s["base_stat"] for s in d.get("stats", [])}

        # ── Upsert species ──────────────────────────────────────────────────────
        cur.execute("""
            INSERT INTO pokemon_species
                (id, name, slug, type1_id, type2_id, base_experience,
                 sprite_url, sprite_shiny_url,
                 base_hp, base_attack, base_defense,
                 base_sp_attack, base_sp_defense, base_speed)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
                name             = EXCLUDED.name,
                type1_id         = EXCLUDED.type1_id,
                type2_id         = EXCLUDED.type2_id,
                base_experience  = EXCLUDED.base_experience,
                sprite_url       = EXCLUDED.sprite_url,
                sprite_shiny_url = EXCLUDED.sprite_shiny_url,
                base_hp          = EXCLUDED.base_hp,
                base_attack      = EXCLUDED.base_attack,
                base_defense     = EXCLUDED.base_defense,
                base_sp_attack   = EXCLUDED.base_sp_attack,
                base_sp_defense  = EXCLUDED.base_sp_defense,
                base_speed       = EXCLUDED.base_speed;
        """, (
            form_id, name, slug, type1_id, type2_id, base_exp, sprite, shiny,
            stats.get("hp", 0), stats.get("attack", 0), stats.get("defense", 0),
            stats.get("special-attack", 0), stats.get("special-defense", 0),
            stats.get("speed", 0),
        ))

        # ── Upsert level-up moves ───────────────────────────────────────────────
        for move_entry in d.get("moves", []):
            move_id = extract_id(move_entry["move"]["url"])
            if not move_id or move_id > 10000:
                continue
            level_up = [
                vd for vd in move_entry.get("version_group_details", [])
                if vd["move_learn_method"]["name"] == "level-up"
            ]
            if not level_up:
                continue
            # Take the entry with the highest level (latest version group)
            best = max(level_up, key=lambda x: x["level_learned_at"])
            level_at = best["level_learned_at"]

            # Upsert move record (species_id-based moves may already exist)
            move_slug = move_entry["move"]["name"]
            move_name = move_slug.replace("-", " ").title()
            cur.execute("""
                INSERT INTO pokemon_moves (id, name, slug)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (move_id, move_name, move_slug))

            cur.execute("""
                INSERT INTO pokemon_species_moves
                    (species_id, move_id, learn_method, level_learned_at)
                VALUES (%s, %s, 'level-up', %s)
                ON CONFLICT DO NOTHING;
            """, (form_id, move_id, level_at))

        # ── Upsert evolution entry ──────────────────────────────────────────────
        # id formula consistent with seed_evolutions.py: (from * 1000) + to
        evo_id    = base_id * 1000 + form_id
        item_name = f"form-{form_slug}"   # matches shop_items.slug from seed_regional_forms.py
        cur.execute("""
            INSERT INTO pokemon_evolutions
                (id, from_species_id, to_species_id, min_level, trigger_name, item_name)
            VALUES (%s, %s, %s, NULL, 'use-item', %s)
            ON CONFLICT (id) DO UPDATE SET
                trigger_name = EXCLUDED.trigger_name,
                item_name    = EXCLUDED.item_name;
        """, (evo_id, base_id, form_id, item_name))

        # ── Update pokemon_regional_forms sprite_url with the definitive one ────
        cur.execute("""
            UPDATE pokemon_regional_forms
            SET sprite_url = %s
            WHERE form_slug = %s;
        """, (sprite, form_slug))

        print("✅")
        ok += 1

    conn.commit()
    print(f"\n✅ {ok} regional species seeded.")
    if failed:
        print(f"⚠️  Failed: {', '.join(failed)}")

    cur.close()
    conn.close()
    session.close()


if __name__ == "__main__":
    seed()
