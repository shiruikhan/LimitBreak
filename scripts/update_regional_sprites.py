"""Update sprite_url for regional form Pokémon from PokeAPI CDN to HybridShivam assets.

For each regional form (pokemon_species.id > 10000), constructs the HybridShivam CDN URL
using the pattern:
  https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/images/{NNNN}-{Region}.png

Verifies each URL via HEAD request before updating. Falls back to keeping the existing
PokeAPI URL for any form whose HybridShivam file doesn't exist.

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

CDN_BASE = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/images"

# (base_dex_id, region, form_slug) — must match pokemon_species.slug in DB
REGIONAL_FORMS = [
    # Alola
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
    # Galar
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
    # Hisui
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


def hybrid_url(base_id: int, region: str) -> str:
    return f"{CDN_BASE}/{base_id:04d}-{region.capitalize()}.png"


def url_exists(session: requests.Session, url: str) -> bool:
    try:
        r = session.head(url, timeout=10, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def run():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    session = requests.Session()

    # Build slug → DB id map
    cur.execute("SELECT id, slug FROM pokemon_species WHERE id > 10000;")
    slug_to_id = {row[1]: row[0] for row in cur.fetchall()}

    updated = []
    missing = []

    for base_id, region, form_slug in REGIONAL_FORMS:
        db_id = slug_to_id.get(form_slug)
        if db_id is None:
            print(f"  SKIP  {form_slug} — not found in pokemon_species")
            continue

        url = hybrid_url(base_id, region)
        print(f"  checking {url} ...", end="  ", flush=True)

        if url_exists(session, url):
            cur.execute(
                "UPDATE pokemon_species SET sprite_url = %s WHERE id = %s;",
                (url, db_id),
            )
            print("✅ updated")
            updated.append(form_slug)
        else:
            print("❌ not found — keeping PokeAPI URL")
            missing.append((form_slug, url))

        time.sleep(0.1)

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone. {len(updated)} updated, {len(missing)} kept PokeAPI fallback.")
    if missing:
        print("\nForms without HybridShivam sprite:")
        for slug, url in missing:
            print(f"  {slug}  →  {url}")


if __name__ == "__main__":
    run()
