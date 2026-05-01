"""seed_spawn_tiers.py
Refina is_spawnable e rarity_tier em pokemon_species usando PokéAPI.

Execução (idempotente):
    python scripts/seed_spawn_tiers.py

Regras:
  - is_legendary = TRUE  → is_spawnable = FALSE
  - is_mythical  = TRUE  → is_spawnable = FALSE
  - Formas regionais (id > 10000) herdam is_spawnable da espécie base.
  - rarity_tier por base_experience (fallback se PokéAPI não retornar):
      common   = base_experience < 100
      uncommon = 100–179
      rare     = 180–299 (e ≥ 300 mas is_spawnable=FALSE)
"""

import os
import sys
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://pokeapi.co/api/v2/pokemon-species"

def _db_conn():
    try:
        import streamlit as st
        db = st.secrets["database"]
        return psycopg2.connect(
            host=db["host"], port=int(db["port"]),
            dbname=db["name"], user=db["user"], password=db["password"],
        )
    except Exception:
        return psycopg2.connect(
            host=os.getenv("host"), port=os.getenv("port"),
            dbname=os.getenv("database"), user=os.getenv("user"),
            password=os.getenv("password"),
        )


def _tier_from_base_exp(base_exp):
    if base_exp is None or base_exp < 100:
        return "common"
    if base_exp < 180:
        return "uncommon"
    return "rare"


def main():
    conn = _db_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, base_experience FROM pokemon_species WHERE id <= 1025 ORDER BY id;")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Processando {total} espécies normais...")

    for i, (species_id, base_exp) in enumerate(rows, 1):
        url = f"{BASE_URL}/{species_id}/"
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 404:
                    print(f"  [{i}/{total}] #{species_id}: não encontrado na PokéAPI, pulando.")
                    break
                resp.raise_for_status()
                data = resp.json()
                is_legendary = data.get("is_legendary", False)
                is_mythical  = data.get("is_mythical", False)
                spawnable    = not (is_legendary or is_mythical)
                tier         = _tier_from_base_exp(base_exp)

                cur.execute(
                    "UPDATE pokemon_species SET is_spawnable = %s, rarity_tier = %s WHERE id = %s;",
                    (spawnable, tier, species_id),
                )
                flag = ""
                if is_legendary: flag = " [LENDÁRIO]"
                if is_mythical:  flag = " [MÍTICO]"
                print(f"  [{i}/{total}] #{species_id}: {tier}, spawnable={spawnable}{flag}")
                break
            except requests.RequestException as e:
                if attempt < 2:
                    print(f"  [{i}/{total}] #{species_id}: erro ({e}), tentando novamente...")
                    time.sleep(2)
                else:
                    print(f"  [{i}/{total}] #{species_id}: falhou após 3 tentativas, usando fallback.")
                    tier = _tier_from_base_exp(base_exp)
                    cur.execute(
                        "UPDATE pokemon_species SET rarity_tier = %s WHERE id = %s;",
                        (tier, species_id),
                    )

        if i % 50 == 0:
            conn.commit()
            print(f"  → Commit parcial ({i}/{total})")
        time.sleep(0.3)

    # Formas regionais (id > 10000): herdam is_spawnable da espécie base
    # e ficam como 'uncommon' por padrão (são formas alternativas, menos comuns)
    print("\nAtualizando formas regionais (id > 10000)...")
    cur.execute("""
        UPDATE pokemon_species
        SET rarity_tier = 'uncommon',
            is_spawnable = TRUE
        WHERE id > 10000;
    """)
    print(f"  {cur.rowcount} formas regionais atualizadas.")

    conn.commit()
    cur.close()
    conn.close()
    print("\nConcluído.")


if __name__ == "__main__":
    main()
