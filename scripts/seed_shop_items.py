"""
seed_shop_items.py — Atualiza shop_items com dados oficiais da PokéAPI.

Busca nome localizado (pt-BR com fallback para en) e descrição de efeito
para cada item do catálogo da loja. Preços, ícones e efeitos de stat são
mantidos conforme configurados no banco (não sobrescritos).

Executar após criar as tabelas e fazer o seed inicial:
    python scripts/seed_shop_items.py

Idempotente: usa UPDATE, pode ser reexecutado a qualquer momento.
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

API_BASE = "https://pokeapi.co/api/v2/item"
DELAY    = 0.3   # segundos entre requisições

# Mapeamento slug do banco → slug da PokéAPI
# (alguns nomes diferem ligeiramente)
SLUG_MAP = {
    "fire-stone":    "fire-stone",
    "water-stone":   "water-stone",
    "thunder-stone": "thunder-stone",
    "leaf-stone":    "leaf-stone",
    "moon-stone":    "moon-stone",
    "sun-stone":     "sun-stone",
    "shiny-stone":   "shiny-stone",
    "dusk-stone":    "dusk-stone",
    "dawn-stone":    "dawn-stone",
    "ice-stone":     "ice-stone",
    "hp-up":         "hp-up",
    "protein":       "protein",
    "iron":          "iron",
    "calcium":       "calcium",
    "zinc":          "zinc",
    "carbos":        "carbos",
    "xp-share":      "exp-share",   # PokéAPI usa "exp-share"
}

# Ícones mantidos localmente (PokéAPI não tem emoji)
ICONS = {
    "fire-stone":    "🔥",
    "water-stone":   "💧",
    "thunder-stone": "⚡",
    "leaf-stone":    "🌿",
    "moon-stone":    "🌙",
    "sun-stone":     "☀️",
    "shiny-stone":   "✨",
    "dusk-stone":    "🌑",
    "dawn-stone":    "🌅",
    "ice-stone":     "🧊",
    "hp-up":         "❤️",
    "protein":       "💪",
    "iron":          "🛡️",
    "calcium":       "💙",
    "zinc":          "🧿",
    "carbos":        "💨",
    "xp-share":      "📡",
}


def _pick_text(entries: list[dict], key: str, lang_priority: list[str]) -> str | None:
    """Retorna o primeiro texto encontrado na ordem de prioridade de idiomas."""
    by_lang = {e["language"]["name"]: e[key] for e in entries if key in e}
    for lang in lang_priority:
        if lang in by_lang:
            return by_lang[lang].replace("\n", " ").replace("\f", " ").strip()
    return None


def fetch_item(api_slug: str) -> dict | None:
    """Retorna {name, description} ou None em caso de erro."""
    url = f"{API_BASE}/{api_slug}/"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            print(f"  [404] {api_slug} não encontrado na PokéAPI")
            return None
        r.raise_for_status()
        data = r.json()

        # Nome localizado (pt-BR > en)
        name = _pick_text(data.get("names", []), "name", ["pt-BR", "en"])
        if not name:
            # fallback: formata o slug
            name = api_slug.replace("-", " ").title()

        # Descrição de efeito curto (flavor text pt-BR > en, ou effect entry en)
        desc = _pick_text(data.get("flavor_text_entries", []), "text", ["pt-BR", "en"])
        if not desc:
            effects = data.get("effect_entries", [])
            for e in effects:
                if e.get("language", {}).get("name") == "en":
                    desc = e.get("short_effect") or e.get("effect", "")
                    desc = desc.replace("\n", " ").replace("\f", " ").strip()
                    break
        if not desc:
            desc = "Item especial."

        return {"name": name, "description": desc}

    except Exception as ex:
        print(f"  [ERRO] {api_slug}: {ex}")
        return None


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur  = conn.cursor()

    cur.execute("SELECT slug FROM shop_items ORDER BY id;")
    db_slugs = [r[0] for r in cur.fetchall()]

    print(f"Atualizando {len(db_slugs)} itens da loja via PokéAPI...\n")

    updated = 0
    for db_slug in db_slugs:
        api_slug = SLUG_MAP.get(db_slug, db_slug)
        data     = fetch_item(api_slug)

        if not data:
            print(f"  [{db_slug}] — sem dados, mantendo atual")
            time.sleep(DELAY)
            continue

        cur.execute("""
            UPDATE shop_items
            SET name = %s, description = %s
            WHERE slug = %s;
        """, (data["name"], data["description"], db_slug))

        print(f"  [OK] {db_slug} -> \"{data['name']}\"")
        updated += 1
        time.sleep(DELAY)

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nConcluído — {updated}/{len(db_slugs)} itens atualizados.")


if __name__ == "__main__":
    main()
