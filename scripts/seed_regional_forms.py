"""Populates shop_items (category='regional_form') and pokemon_regional_forms.

Run after migrate_regional_forms.sql has been applied.
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

# Regional forms catalog: (species_id, region, form_slug, display_name)
# Sprites are fetched from PokéAPI at seed time.
REGIONAL_FORMS = [
    # ── Alola ──────────────────────────────────────────────────────────────────
    (26,  "alola", "raichu-alola",    "Raichu de Alola"),
    (27,  "alola", "sandshrew-alola", "Sandshrew de Alola"),
    (28,  "alola", "sandslash-alola", "Sandslash de Alola"),
    (37,  "alola", "vulpix-alola",    "Vulpix de Alola"),
    (38,  "alola", "ninetales-alola", "Ninetales de Alola"),
    (50,  "alola", "diglett-alola",   "Diglett de Alola"),
    (51,  "alola", "dugtrio-alola",   "Dugtrio de Alola"),
    (52,  "alola", "meowth-alola",    "Meowth de Alola"),
    (53,  "alola", "persian-alola",   "Persian de Alola"),
    (74,  "alola", "geodude-alola",   "Geodude de Alola"),
    (75,  "alola", "graveler-alola",  "Graveler de Alola"),
    (76,  "alola", "golem-alola",     "Golem de Alola"),
    (88,  "alola", "grimer-alola",    "Grimer de Alola"),
    (89,  "alola", "muk-alola",       "Muk de Alola"),
    (103, "alola", "exeggutor-alola", "Exeggutor de Alola"),
    (105, "alola", "marowak-alola",   "Marowak de Alola"),
    # ── Galar ──────────────────────────────────────────────────────────────────
    (52,  "galar", "meowth-galar",    "Meowth de Galar"),
    (77,  "galar", "ponyta-galar",    "Ponyta de Galar"),
    (78,  "galar", "rapidash-galar",  "Rapidash de Galar"),
    (79,  "galar", "slowpoke-galar",  "Slowpoke de Galar"),
    (80,  "galar", "slowbro-galar",   "Slowbro de Galar"),
    (83,  "galar", "farfetchd-galar", "Farfetch'd de Galar"),
    (110, "galar", "weezing-galar",   "Weezing de Galar"),
    (122, "galar", "mr-mime-galar",   "Mr. Mime de Galar"),
    (199, "galar", "slowking-galar",  "Slowking de Galar"),
    (222, "galar", "corsola-galar",   "Corsola de Galar"),
    (263, "galar", "zigzagoon-galar", "Zigzagoon de Galar"),
    (264, "galar", "linoone-galar",   "Linoone de Galar"),
    (554, "galar", "darumaka-galar",  "Darumaka de Galar"),
    (562, "galar", "yamask-galar",    "Yamask de Galar"),
    (618, "galar", "stunfisk-galar",  "Stunfisk de Galar"),
    # ── Hisui ──────────────────────────────────────────────────────────────────
    (58,  "hisui", "growlithe-hisui",  "Growlithe de Hisui"),
    (59,  "hisui", "arcanine-hisui",   "Arcanine de Hisui"),
    (100, "hisui", "voltorb-hisui",    "Voltorb de Hisui"),
    (101, "hisui", "electrode-hisui",  "Electrode de Hisui"),
    (157, "hisui", "typhlosion-hisui", "Typhlosion de Hisui"),
    (211, "hisui", "qwilfish-hisui",   "Qwilfish de Hisui"),
    (215, "hisui", "sneasel-hisui",    "Sneasel de Hisui"),
    (570, "hisui", "zorua-hisui",      "Zorua de Hisui"),
    (571, "hisui", "zoroark-hisui",    "Zoroark de Hisui"),
    (628, "hisui", "braviary-hisui",   "Braviary de Hisui"),
    (713, "hisui", "avalugg-hisui",    "Avalugg de Hisui"),
]

REGION_META = {
    "alola": {"icon": "🌴", "price": 500, "label": "Alola"},
    "galar": {"icon": "🌹", "price": 600, "label": "Galar"},
    "hisui": {"icon": "❄️", "price": 700, "label": "Hisui"},
}


def fetch_sprite(session: requests.Session, form_slug: str) -> str | None:
    url = f"https://pokeapi.co/api/v2/pokemon/{form_slug}/"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("sprites", {}).get("front_default")
    except Exception as e:
        print(f"  ⚠️  Sprite fetch failed for {form_slug}: {e}")
        return None


def seed():
    conn = psycopg2.connect(**DB_PARAMS)
    session = requests.Session()
    try:
        cur = conn.cursor()

        inserted_forms = 0
        inserted_items = 0

        for species_id, region, form_slug, display_name in REGIONAL_FORMS:
            meta = REGION_META[region]
            item_slug = f"form-{form_slug}"
            description = f"Altera a aparência do seu {display_name.split(' de ')[0]} para a forma regional de {meta['label']}. Efeito visual — stats inalterados."

            # Fetch sprite from PokéAPI
            print(f"  Fetching {form_slug}...", end=" ")
            sprite_url = fetch_sprite(session, form_slug)
            print("ok" if sprite_url else "no sprite")
            time.sleep(0.3)

            # Upsert shop_item
            cur.execute("""
                INSERT INTO shop_items (slug, name, description, icon, category, price)
                VALUES (%s, %s, %s, %s, 'regional_form', %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    icon        = EXCLUDED.icon,
                    price       = EXCLUDED.price
                RETURNING id;
            """, (item_slug, display_name, description, meta["icon"], meta["price"]))
            shop_item_id = cur.fetchone()[0]
            inserted_items += 1

            # Upsert regional form catalog entry
            cur.execute("""
                INSERT INTO pokemon_regional_forms
                    (shop_item_id, species_id, region, form_slug, sprite_url, name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (form_slug) DO UPDATE SET
                    shop_item_id = EXCLUDED.shop_item_id,
                    sprite_url   = EXCLUDED.sprite_url,
                    name         = EXCLUDED.name;
            """, (shop_item_id, species_id, region, form_slug, sprite_url, display_name))
            inserted_forms += 1

        conn.commit()
        print(f"\n✅ Seeded {inserted_forms} regional forms and {inserted_items} shop items.")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()
        session.close()


if __name__ == "__main__":
    seed()
