"""
Faz upload dos sprites de Pokémon para o Supabase Storage e atualiza as URLs no banco.

Estrutura do bucket "pokemon-sprites" (público):
  normal/{id:04d}.png       — sprite regular     (PokéAPI front_default)
  shiny/{id:04d}.png        — sprite shiny        (PokéAPI front_shiny)
  hq/{id:04d}.png           — artwork HQ normal   (PokéAPI official-artwork)
  hq-shiny/{id:04d}.png     — artwork HQ shiny    (PokéAPI official-artwork/shiny)
  normal/{NNNN}-{Reg}.png  — sprite regular regional   (HybridShivam CDN)
  shiny/{NNNN}-{Reg}.png   — sprite shiny regional     (PokéAPI shiny/{pk_id})

Uso:
  python scripts/upload_sprites_to_supabase.py              # tudo
  python scripts/upload_sprites_to_supabase.py --only-normal
  python scripts/upload_sprites_to_supabase.py --only-regional
  python scripts/upload_sprites_to_supabase.py --skip-hq    # sem HQ nem HQ-shiny

Credenciais lidas de .streamlit/secrets.toml:
  [supabase]
  url         = "https://xxxx.supabase.co"
  service_key = "..."   # service_role — necessário apenas para este script

  [database]
  host = "..." | port = "..." | name = "..." | user = "..." | password = "..."

Idempotente: lista os arquivos já existentes no bucket de uma vez (sem HEAD por arquivo)
e só faz upload do que falta. Atualiza o banco apenas quando a URL muda.
"""

import re
import sys
import time
import pathlib
import argparse
import psycopg2
import requests

# ── Leitura de .streamlit/secrets.toml ────────────────────────────────────────

def _load_secrets() -> dict:
    secrets_path = pathlib.Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        print(f"ERRO: {secrets_path} não encontrado.")
        sys.exit(1)
    try:
        import tomllib          # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib   # pip install tomli
        except ImportError:
            print("ERRO: instale 'tomli' (pip install tomli) ou use Python ≥ 3.11")
            sys.exit(1)
    with open(secrets_path, "rb") as f:
        return tomllib.load(f)

_secrets             = _load_secrets()
_db                  = _secrets.get("database", {})
DB_HOST              = _db.get("host")
DB_PORT              = _db.get("port")
DB_NAME              = _db.get("name")
DB_USER              = _db.get("user")
DB_PASS              = _db.get("password")
_sup                 = _secrets.get("supabase", {})
SUPABASE_URL         = _sup.get("url", "")
SUPABASE_SERVICE_KEY = _sup.get("service_key", "")

# ── Constantes ─────────────────────────────────────────────────────────────────

BUCKET             = "pokemon-sprites"
NORMAL_POKEMON     = 1025
DELAY              = 0.05   # 50 ms entre downloads — evita 429
MAX_RETRIES        = 3

# Fontes de sprites
POKEAPI_NORMAL  = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png"
POKEAPI_SHINY   = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{id}.png"
POKEAPI_HQ      = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{id}.png"
POKEAPI_HQ_SHINY = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/{id}.png"
HYBRIDSHIVAM    = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/images"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _db_connect():
    return psycopg2.connect(
        host=DB_HOST, port=int(DB_PORT), dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )


def _download(url: str) -> bytes | None:
    """Baixa bytes de uma URL com retry. Retorna None em caso de 404 ou falha."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            time.sleep(1 + attempt)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                print(f"    ✗ download falhou ({url}): {exc}")
            time.sleep(1 + attempt)
    return None


def _auth_headers(content_type: str = "image/png") -> dict:
    return {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  content_type,
    }


def _object_url(path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"


def _public_url(path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"


def _list_folder(prefix: str) -> set[str]:
    """
    Lista todos os arquivos de uma pasta no bucket.
    Retorna um set de nomes de arquivo (sem o prefixo da pasta).
    Faz paginação automática (Supabase limita 1000 por chamada).
    """
    names: set[str] = set()
    offset = 0
    limit  = 1000
    while True:
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
            json={"prefix": prefix, "limit": limit, "offset": offset,
                  "sortBy": {"column": "name", "order": "asc"}},
            headers=_auth_headers("application/json"),
            timeout=20,
        )
        if r.status_code != 200:
            print(f"  AVISO: não conseguiu listar '{prefix}': {r.status_code} {r.text[:80]}")
            break
        batch = r.json()
        if not batch:
            break
        names.update(obj["name"] for obj in batch)
        if len(batch) < limit:
            break
        offset += limit
    return names


def _upload(path: str, data: bytes) -> bool:
    """PUT com upsert. Retorna True se bem-sucedido."""
    r = requests.put(
        _object_url(path),
        data=data,
        headers={**_auth_headers(), "x-upsert": "true"},
        timeout=30,
    )
    if r.status_code in (200, 201):
        return True
    print(f"    ✗ upload falhou [{r.status_code}] {path}: {r.text[:120]}")
    return False


def _ensure_bucket():
    r = requests.get(
        f"{SUPABASE_URL}/storage/v1/bucket/{BUCKET}",
        headers=_auth_headers(),
        timeout=10,
    )
    if r.status_code == 200:
        print(f"Bucket '{BUCKET}' OK.")
        return
    r = requests.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        json={"id": BUCKET, "name": BUCKET, "public": True},
        headers=_auth_headers("application/json"),
        timeout=10,
    )
    if r.status_code in (200, 201):
        print(f"Bucket '{BUCKET}' criado.")
    else:
        print(f"ERRO ao criar bucket: {r.status_code} {r.text}")
        sys.exit(1)


# ── Upload de espécies normais (id 1–1025) ─────────────────────────────────────

def _upload_normal_species(include_hq: bool):
    print(f"\n=== Espécies normais (1–{NORMAL_POKEMON}) ===")

    # Lista arquivos existentes de uma vez — evita 4×1025 HEAD requests
    print("  Listando arquivos já existentes no bucket...")
    existing_normal   = _list_folder("normal/")
    existing_shiny    = _list_folder("shiny/")
    existing_hq       = _list_folder("hq/")        if include_hq else set()
    existing_hq_shiny = _list_folder("hq-shiny/")  if include_hq else set()
    print(f"  Existentes: {len(existing_normal)} normal | {len(existing_shiny)} shiny"
          + (f" | {len(existing_hq)} hq | {len(existing_hq_shiny)} hq-shiny" if include_hq else ""))

    conn = _db_connect()
    cur  = conn.cursor()

    updates_sprite = []   # (nova_url, pk_id)
    updates_shiny  = []

    stats = {"normal": [0, 0, 0], "shiny": [0, 0, 0],
             "hq": [0, 0, 0],     "hq_shiny": [0, 0, 0]}  # [uploaded, skipped, missing]

    for pk_id in range(1, NORMAL_POKEMON + 1):
        padded    = str(pk_id).zfill(4)
        filename  = f"{padded}.png"
        n_path    = f"normal/{filename}"
        s_path    = f"shiny/{filename}"
        hq_path   = f"hq/{filename}"
        hqs_path  = f"hq-shiny/{filename}"

        progress = f"[{pk_id:4d}/{NORMAL_POKEMON}]"

        # ── normal ─────────────────────────────────────────────────────────────
        if filename not in existing_normal:
            data = _download(POKEAPI_NORMAL.format(id=pk_id))
            time.sleep(DELAY)
            if data and _upload(n_path, data):
                print(f"  {progress} #{padded} normal ✓")
                stats["normal"][0] += 1
            else:
                print(f"  {progress} #{padded} normal — não encontrado")
                stats["normal"][2] += 1
        else:
            stats["normal"][1] += 1

        updates_sprite.append((_public_url(n_path), pk_id))

        # ── shiny ──────────────────────────────────────────────────────────────
        if filename not in existing_shiny:
            data = _download(POKEAPI_SHINY.format(id=pk_id))
            time.sleep(DELAY)
            if data and _upload(s_path, data):
                print(f"  {progress} #{padded} shiny ✓")
                stats["shiny"][0] += 1
            else:
                print(f"  {progress} #{padded} shiny — não encontrado")
                stats["shiny"][2] += 1
        else:
            stats["shiny"][1] += 1

        updates_shiny.append((_public_url(s_path), pk_id))

        if not include_hq:
            continue

        # ── HQ normal ──────────────────────────────────────────────────────────
        if filename not in existing_hq:
            data = _download(POKEAPI_HQ.format(id=pk_id))
            time.sleep(DELAY)
            if data and _upload(hq_path, data):
                print(f"  {progress} #{padded} HQ ✓")
                stats["hq"][0] += 1
            else:
                print(f"  {progress} #{padded} HQ — não encontrado")
                stats["hq"][2] += 1
        else:
            stats["hq"][1] += 1

        # ── HQ shiny ───────────────────────────────────────────────────────────
        if filename not in existing_hq_shiny:
            data = _download(POKEAPI_HQ_SHINY.format(id=pk_id))
            time.sleep(DELAY)
            if data and _upload(hqs_path, data):
                print(f"  {progress} #{padded} HQ-shiny ✓")
                stats["hq_shiny"][0] += 1
            else:
                # Muitos Pokémon não têm artwork shiny — é esperado
                stats["hq_shiny"][2] += 1
        else:
            stats["hq_shiny"][1] += 1

    # ── Atualiza banco em lote ──────────────────────────────────────────────────
    print("\n  Atualizando sprite_url...")
    cur.executemany(
        """UPDATE pokemon_species SET sprite_url = %s
           WHERE id = %s AND sprite_url IS DISTINCT FROM %s""",
        [(url, pk_id, url) for url, pk_id in updates_sprite],
    )
    print("  Atualizando sprite_shiny_url...")
    cur.executemany(
        """UPDATE pokemon_species SET sprite_shiny_url = %s
           WHERE id = %s AND sprite_shiny_url IS DISTINCT FROM %s""",
        [(url, pk_id, url) for url, pk_id in updates_shiny],
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"\n  Resultado normal:   {stats['normal'][0]} enviados | {stats['normal'][1]} já existiam | {stats['normal'][2]} não encontrados")
    print(f"  Resultado shiny:    {stats['shiny'][0]} enviados | {stats['shiny'][1]} já existiam | {stats['shiny'][2]} não encontrados")
    if include_hq:
        print(f"  Resultado HQ:       {stats['hq'][0]} enviados | {stats['hq'][1]} já existiam | {stats['hq'][2]} não encontrados")
        print(f"  Resultado HQ-shiny: {stats['hq_shiny'][0]} enviados | {stats['hq_shiny'][1]} já existiam | {stats['hq_shiny'][2]} não encontrados")


# ── Upload de formas regionais (id > 10000) ────────────────────────────────────

def _upload_regional_species():
    print("\n=== Formas regionais (id > 10000) ===")

    conn = _db_connect()
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, sprite_url, sprite_shiny_url FROM pokemon_species WHERE id > 10000 ORDER BY id"
    )
    regionals = cur.fetchall()
    print(f"  {len(regionals)} formas regionais encontradas")

    # Lista existentes de uma vez
    existing_normal = _list_folder("normal/")
    existing_shiny  = _list_folder("shiny/")
    print(f"  Existentes: {len(existing_normal)} normal | {len(existing_shiny)} shiny")

    updates_sprite = []
    updates_shiny  = []
    stats = {"normal": [0, 0, 0], "shiny": [0, 0, 0]}

    for pk_id, current_sprite, current_shiny in regionals:
        if not current_sprite:
            print(f"  #{pk_id} sem sprite_url, pulando")
            continue

        # Extrai "0026-Alola.png" da URL atual ou monta a partir do ID do banco
        m = re.search(r'(\d{4}-\w+\.png)$', current_sprite)
        if not m:
            print(f"  #{pk_id} — filename não reconhecido: {current_sprite}")
            continue

        filename  = m.group(1)
        n_path    = f"normal/{filename}"
        s_path    = f"shiny/{filename}"
        prefix    = f"  #{pk_id} ({filename})"

        # ── normal ─────────────────────────────────────────────────────────────
        uploaded_normal = False
        if filename not in existing_normal:
            # Tenta URL atual (HybridShivam ou outra), depois fallback direto
            src = current_sprite if current_sprite.startswith("http") else f"{HYBRIDSHIVAM}/{filename}"
            data = _download(src)
            time.sleep(DELAY)
            if not data and src != f"{HYBRIDSHIVAM}/{filename}":
                data = _download(f"{HYBRIDSHIVAM}/{filename}")
                time.sleep(DELAY)
            if data and _upload(n_path, data):
                print(f"{prefix} normal ✓")
                stats["normal"][0] += 1
                uploaded_normal = True
            else:
                print(f"{prefix} normal — não encontrado")
                stats["normal"][2] += 1
        else:
            stats["normal"][1] += 1
            uploaded_normal = True

        if uploaded_normal:
            updates_sprite.append((_public_url(n_path), pk_id))

        # ── shiny ──────────────────────────────────────────────────────────────
        # PokéAPI mantém sprites shiny para formas regionais pelo ID numérico (>10000)
        uploaded_shiny = False
        if filename not in existing_shiny:
            # Fonte primária: PokéAPI pelo ID numérico (já está em sprite_shiny_url atual)
            shiny_src = (current_shiny
                         if (current_shiny and current_shiny.startswith("http")
                             and "supabase" not in current_shiny)
                         else POKEAPI_SHINY.format(id=pk_id))
            data = _download(shiny_src)
            time.sleep(DELAY)
            if not data:
                # Fallback: PokéAPI direto pelo ID
                data = _download(POKEAPI_SHINY.format(id=pk_id))
                time.sleep(DELAY)
            if data and _upload(s_path, data):
                print(f"{prefix} shiny ✓")
                stats["shiny"][0] += 1
                uploaded_shiny = True
            else:
                print(f"{prefix} shiny — não encontrado")
                stats["shiny"][2] += 1
        else:
            stats["shiny"][1] += 1
            uploaded_shiny = True

        if uploaded_shiny:
            updates_shiny.append((_public_url(s_path), pk_id))

    # ── Atualiza banco ──────────────────────────────────────────────────────────
    if updates_sprite:
        print("\n  Atualizando sprite_url das formas regionais...")
        cur.executemany(
            """UPDATE pokemon_species SET sprite_url = %s
               WHERE id = %s AND sprite_url IS DISTINCT FROM %s""",
            [(url, pk_id, url) for url, pk_id in updates_sprite],
        )
    if updates_shiny:
        print("  Atualizando sprite_shiny_url das formas regionais...")
        cur.executemany(
            """UPDATE pokemon_species SET sprite_shiny_url = %s
               WHERE id = %s AND sprite_shiny_url IS DISTINCT FROM %s""",
            [(url, pk_id, url) for url, pk_id in updates_shiny],
        )
    conn.commit()
    cur.close()
    conn.close()

    print(f"\n  Resultado normal: {stats['normal'][0]} enviados | {stats['normal'][1]} já existiam | {stats['normal'][2]} não encontrados")
    print(f"  Resultado shiny:  {stats['shiny'][0]} enviados | {stats['shiny'][1]} já existiam | {stats['shiny'][2]} não encontrados")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload de sprites Pokémon para Supabase Storage")
    parser.add_argument("--only-normal",   action="store_true", help="Processa apenas espécies normais (1–1025)")
    parser.add_argument("--only-regional", action="store_true", help="Processa apenas formas regionais (id > 10000)")
    parser.add_argument("--skip-hq",       action="store_true", help="Pula o upload de HQ e HQ-shiny")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERRO: Adicione [supabase] url e service_key em .streamlit/secrets.toml")
        sys.exit(1)
    if not DB_HOST:
        print("ERRO: Credenciais do banco ausentes em .streamlit/secrets.toml [database]")
        sys.exit(1)

    print(f"Projeto Supabase : {SUPABASE_URL}")
    print(f"Bucket           : {BUCKET}")

    _ensure_bucket()

    if not args.only_regional:
        _upload_normal_species(include_hq=not args.skip_hq)

    if not args.only_normal:
        _upload_regional_species()

    print("\n✅ Concluído!")


if __name__ == "__main__":
    main()
