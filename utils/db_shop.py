"""utils/db_shop.py — Loja, inventário e itens consumíveis do LimitBreak.

Contém:
  - Catálogo da loja (get_shop_items, get_user_inventory)
  - Compra e uso de itens (buy_item, use_stat_item, use_xp_share_item,
    use_nature_mint, open_loot_box)
  - XP Share (get_xp_share_status, _extend_xp_share)
  - Evolução por pedra (get_stone_targets, evolve_with_stone)
  - Helpers internos de inventário e loot (_add_inventory_item,
    _ensure_loot_box_item, _grant_loot_box, _roll_loot_box)

Depende de db_core e db_user.
Nota: open_loot_box usa import tardio de award_xp (db_progression)
para evitar import circular.
"""

import random
import datetime
import streamlit as st

from utils.db_core import (
    get_connection,
    _today_brt, _BRT,
    _ALL_NATURES,
    _sync_user_pokemon_stats,
    _recalc_stats_on_evolution,
    _LOOT_VITAMINS,
)
from utils.db_user import _VALID_STATS, _MAX_STAT_BOOSTS_PER_STAT


# ── Constantes de loot ─────────────────────────────────────────────────────────

_LOOT_BOX_ITEM = {
    "slug": "loot-box",
    "name": "Loot Box",
    "description": "Abra na Mochila para receber uma recompensa aleatoria.",
    "category": "other",
    "price": 1,
    "icon": "🎁",
}

_LOOT_STONES = [
    "fire-stone", "water-stone", "thunder-stone", "leaf-stone", "moon-stone",
    "sun-stone", "shiny-stone", "dusk-stone", "dawn-stone", "ice-stone",
]


# ── Catálogo da loja ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_shop_items() -> list[dict]:
    """Retorna o catálogo completo da loja — cacheado globalmente."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT id, slug, name, description, category,
                   price, effect_stat, effect_value, icon
            FROM shop_items
            ORDER BY category, price;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "slug": r[1], "name": r[2], "description": r[3],
                "category": r[4], "price": r[5], "effect_stat": r[6],
                "effect_value": r[7], "icon": r[8],
            }
            for r in rows
        ]


def get_user_inventory(user_id: str) -> dict[int, int]:
    """Retorna {item_id: quantity} para os itens que o usuário possui (quantity > 0)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT item_id, quantity FROM user_inventory
                WHERE user_id = %s AND quantity > 0;
            """, (user_id,))
            return {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        return {}


# ── Helpers internos de inventário e loot ─────────────────────────────────────

def _add_inventory_item(cur, user_id: str, item_id: int, quantity: int = 1) -> None:
    """Adiciona quantidade ao inventario do usuario dentro da transacao atual."""
    cur.execute("""
        INSERT INTO user_inventory (user_id, item_id, quantity)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, item_id)
        DO UPDATE SET quantity = user_inventory.quantity + EXCLUDED.quantity;
    """, (user_id, item_id, quantity))


def _ensure_loot_box_item(cur) -> tuple[int, str]:
    """Garante que a Loot Box exista em shop_items e retorna (id, name)."""
    cur.execute("SELECT id, name FROM shop_items WHERE slug = %s;", (_LOOT_BOX_ITEM["slug"],))
    row = cur.fetchone()
    if row:
        return row[0], row[1]

    cur.execute("""
        INSERT INTO shop_items (slug, name, description, category, price, effect_stat, effect_value, icon)
        VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s)
        RETURNING id, name;
    """, (
        _LOOT_BOX_ITEM["slug"],
        _LOOT_BOX_ITEM["name"],
        _LOOT_BOX_ITEM["description"],
        _LOOT_BOX_ITEM["category"],
        _LOOT_BOX_ITEM["price"],
        _LOOT_BOX_ITEM["icon"],
    ))
    get_shop_items.clear()
    row = cur.fetchone()
    return row[0], row[1]


def _grant_loot_box(cur, user_id: str, count: int = 1) -> dict:
    """Entrega loot boxes ao inventario do usuario dentro da transacao atual."""
    item_id, item_name = _ensure_loot_box_item(cur)
    _add_inventory_item(cur, user_id, item_id, count)
    label = f"{count}x {item_name}" if count != 1 else f"1x {item_name}"
    return {
        "type": "loot_box",
        "slug": _LOOT_BOX_ITEM["slug"],
        "name": item_name,
        "label": label,
        "rarity": "common",
        "count": count,
    }


def _roll_loot_box(cur, user_id: str) -> dict:
    """Roll loot table and apply coins/items in-transaction.

    XP rewards are NOT applied here — caller must call award_xp after committing.
    Returns a loot info dict: {type, amount?, slug?, name?, label, rarity}
    """
    roll = random.randint(1, 100)

    if roll <= 50:                          # 50% — XP (common)
        amount = random.randint(50, 150)
        return {"type": "xp", "amount": amount, "label": f"+{amount} XP", "rarity": "common"}

    if roll <= 80:                          # 30% — Coins (common)
        amount = random.randint(50, 150)
        cur.execute(
            "UPDATE user_profiles SET coins = coins + %s WHERE id = %s",
            (amount, user_id),
        )
        return {"type": "coins", "amount": amount, "label": f"+{amount} moedas", "rarity": "common"}

    if roll <= 90:                          # 10% — Vitamin (rare)
        slug = random.choice(_LOOT_VITAMINS)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": slug, "name": row[1], "label": f"1x {row[1]}", "rarity": "rare"}

    if roll <= 95:                          # 5% — Nature Mint (rare)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = 'nature-mint'")
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": "nature-mint", "name": row[1], "label": f"1x {row[1]}", "rarity": "rare"}

    if roll <= 99:                          # 4% — Evolution stone (ultra-rare)
        slug = random.choice(_LOOT_STONES)
        cur.execute("SELECT id, name FROM shop_items WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            _add_inventory_item(cur, user_id, row[0])
            return {"type": "item", "slug": slug, "name": row[1], "label": f"1x {row[1]}", "rarity": "ultra_rare"}

    # 1% — XP Share (ultra-rare)
    cur.execute("SELECT id, name FROM shop_items WHERE slug = 'xp-share'")
    row = cur.fetchone()
    if row:
        _add_inventory_item(cur, user_id, row[0])
        return {"type": "item", "slug": "xp-share", "name": row[1], "label": f"1x {row[1]}", "rarity": "ultra_rare"}

    # Fallback — always give coins
    cur.execute("UPDATE user_profiles SET coins = coins + 50 WHERE id = %s", (user_id,))
    return {"type": "coins", "amount": 50, "label": "+50 moedas", "rarity": "common"}


# ── XP Share ───────────────────────────────────────────────────────────────────

def get_xp_share_status(user_id: str) -> dict:
    """Retorna o status do XP Share do usuário.

    Returns:
        {"active": bool, "expires_at": datetime | None, "days_left": int}
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                "SELECT xp_share_expires_at FROM user_profiles WHERE id = %s;",
                (user_id,)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return {"active": False, "expires_at": None, "days_left": 0}
            expires_at = row[0]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
            now    = datetime.datetime.now(tz=_BRT)
            active = expires_at > now
            days_left = max(0, (expires_at.date() - _today_brt()).days) if active else 0
            return {"active": active, "expires_at": expires_at, "days_left": days_left}
    except Exception:
        return {"active": False, "expires_at": None, "days_left": 0}


def _extend_xp_share(cur, user_id: str) -> None:
    """Estende (ou inicia) o XP Share em +15 dias dentro de uma transação aberta."""
    cur.execute("""
        UPDATE user_profiles
        SET xp_share_expires_at =
            GREATEST(COALESCE(xp_share_expires_at, NOW()), NOW())
            + INTERVAL '15 days'
        WHERE id = %s;
    """, (user_id,))


# ── Compra e uso de itens ──────────────────────────────────────────────────────

def buy_item(user_id: str, item_id: int) -> tuple[bool, str]:
    """Compra um item: debita moedas e adiciona ao inventário.

    XP Share não vai ao inventário — ativa/estende o efeito diretamente.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, price, slug FROM shop_items WHERE id = %s;", (item_id,))
            row = cur.fetchone()
            if not row:
                return False, "Item não encontrado."
            item_name, price, slug = row
            if slug == _LOOT_BOX_ITEM["slug"]:
                return False, "Este item não pode ser comprado na loja."

            cur.execute(
                "SELECT coins FROM user_profiles WHERE id = %s FOR UPDATE;",
                (user_id,)
            )
            profile = cur.fetchone()
            if not profile:
                return False, "Perfil não encontrado."
            if profile[0] < price:
                return False, f"Moedas insuficientes. Você tem {profile[0]} 🪙, precisa de {price} 🪙."

            cur.execute(
                "UPDATE user_profiles SET coins = coins - %s WHERE id = %s;",
                (price, user_id)
            )

            if slug == "xp-share":
                _extend_xp_share(cur, user_id)
                conn.commit()
                return True, f"📡 **{item_name}** ativado! +15 dias adicionados ao efeito."

            cur.execute("""
                INSERT INTO user_inventory (user_id, item_id, quantity)
                VALUES (%s, %s, 1)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = user_inventory.quantity + 1;
            """, (user_id, item_id))

        conn.commit()
        return True, f"**{item_name}** comprado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao comprar: {e}"


def use_stat_item(user_id: str, item_id: int, user_pokemon_id: int) -> tuple[bool, str]:
    """Usa uma vitamina de stat em um Pokémon da equipe do usuário."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, category, effect_stat, effect_value
                FROM shop_items WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            iname, category, stat, value = item
            if category != "stat_boost" or not stat or not value:
                return False, "Este item não pode ser usado diretamente."
            if stat not in _VALID_STATS:
                return False, "Stat inválido."

            cur.execute(
                "SELECT id FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            if not cur.fetchone():
                return False, "Pokémon não encontrado na sua coleção."

            cur.execute("""
                SELECT COUNT(*) FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s AND stat = %s AND delta > 0;
            """, (user_pokemon_id, stat))
            if cur.fetchone()[0] >= _MAX_STAT_BOOSTS_PER_STAT:
                stat_label = {
                    "hp": "HP", "attack": "Ataque", "defense": "Defesa",
                    "sp_attack": "Atq. Especial", "sp_defense": "Def. Especial",
                    "speed": "Velocidade",
                }.get(stat, stat)
                return False, f"Este Pokémon já atingiu o limite de {_MAX_STAT_BOOSTS_PER_STAT} vitaminas de {stat_label}."

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, value, iname))

            # stat validado pela whitelist acima — seguro interpolar
            cur.execute(f"""
                UPDATE user_pokemon
                SET stat_{stat} = COALESCE(stat_{stat}, 0) + %s
                WHERE id = %s;
            """, (value, user_pokemon_id))

        conn.commit()
        stat_label = {
            "hp": "HP", "attack": "Ataque", "defense": "Defesa",
            "sp_attack": "Atq. Especial", "sp_defense": "Def. Especial", "speed": "Velocidade",
        }.get(stat, stat)
        return True, f"+{value} {stat_label} aplicado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao usar item: {e}"


def use_xp_share_item(user_id: str, item_id: int) -> tuple[bool, str]:
    """Ativa um XP Share que esteja guardado no inventario do usuario."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, slug, category
                FROM shop_items WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            item_name, slug, category = item
            if slug != "xp-share" or category != "other":
                return False, "Este item não pode ser ativado aqui."

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))
            _extend_xp_share(cur, user_id)

        conn.commit()
        return True, f"📡 **{item_name}** ativado! +15 dias adicionados ao efeito."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao ativar item: {e}"


def use_nature_mint(user_id: str, item_id: int, user_pokemon_id: int, new_nature: str) -> tuple[bool, str]:
    """Troca a natureza de um Pokémon. Consome 1 Nature Mint do inventário."""
    if new_nature not in _ALL_NATURES:
        return False, "Natureza inválida."
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, category, slug FROM shop_items WHERE id = %s;", (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            iname, category, slug = item
            if category != "nature_mint" and slug != "nature-mint":
                return False, "Este item não pode ser usado aqui."

            cur.execute(
                "SELECT nature FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return False, "Pokémon não encontrado na sua coleção."
            current_nature = (row[0] or "").capitalize()
            if current_nature == new_nature:
                return False, f"Este Pokémon já tem a natureza {new_nature}."

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))
            cur.execute(
                "UPDATE user_pokemon SET nature = %s WHERE id = %s;",
                (new_nature, user_pokemon_id),
            )
            _sync_user_pokemon_stats(cur, user_pokemon_id)

        conn.commit()
        return True, f"Natureza alterada para **{new_nature}** com sucesso! 🌿"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao usar Nature Mint: {e}"


def open_loot_box(user_id: str, item_id: int) -> tuple[bool, str, dict | None]:
    """Consome 1 Loot Box do inventario e aplica o premio sorteado."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name FROM shop_items
                WHERE id = %s AND slug = %s;
            """, (item_id, _LOOT_BOX_ITEM["slug"]))
            item = cur.fetchone()
            if not item:
                return False, "Loot Box não encontrada.", None

            _, item_name = item
            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui nenhuma Loot Box.", None

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

            loot = _roll_loot_box(cur, user_id)

        conn.commit()

        if loot["type"] == "xp":
            try:
                # Import tardio para evitar import circular com db_progression
                from utils.db_progression import award_xp  # noqa: PLC0415
                with get_connection().cursor() as cur2:
                    cur2.execute(
                        "SELECT user_pokemon_id FROM user_team WHERE user_id = %s AND slot = 1",
                        (user_id,),
                    )
                    slot1 = cur2.fetchone()
                if slot1:
                    xp_result = award_xp(slot1[0], loot["amount"], "loot_box_open")
                    loot["xp_result"] = xp_result
                    if xp_result.get("error"):
                        return False, f"Loot Box aberta, mas houve erro ao aplicar o XP: {xp_result['error']}", loot
                else:
                    loot["xp_result"] = {"error": "Sem Pokémon no slot 1 para receber o XP."}
                    return False, "Loot Box aberta, mas você não tem Pokémon no slot 1 para receber o XP.", loot
            except Exception as e:
                loot["xp_result"] = {"error": str(e)}
                return False, f"Loot Box aberta, mas houve erro ao aplicar o XP: {e}", loot

        return True, f"🎁 **{item_name}** aberta com sucesso! Recompensa: {loot['label']}", loot
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao abrir Loot Box: {e}", None


# ── Evolução por pedra ─────────────────────────────────────────────────────────

def get_stone_targets(user_id: str, stone_slug: str) -> list[dict]:
    """Retorna os Pokémon do usuário que podem evoluir com a pedra especificada."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT up.id, up.species_id, p1.name AS from_name,
                       e.to_species_id, p2.name AS to_name, p2.sprite_url,
                       up.level,
                       EXISTS(
                           SELECT 1 FROM user_team ut
                           WHERE ut.user_pokemon_id = up.id
                       ) AS in_team
                FROM user_pokemon up
                JOIN pokemon_species p1 ON up.species_id = p1.id
                JOIN pokemon_evolutions e
                     ON e.from_species_id = up.species_id
                    AND e.trigger_name    = 'use-item'
                    AND e.item_name       = %s
                JOIN pokemon_species p2 ON e.to_species_id = p2.id
                WHERE up.user_id = %s
                ORDER BY in_team DESC, up.id;
            """, (stone_slug, user_id))
            return [
                {
                    "user_pokemon_id": r[0],
                    "species_id":      r[1],
                    "from_name":       r[2],
                    "to_species_id":   r[3],
                    "to_name":         r[4],
                    "sprite_url":      r[5],
                    "level":           r[6],
                    "in_team":         r[7],
                }
                for r in cur.fetchall()
            ]
    except Exception:
        return []


def evolve_with_stone(user_id: str, item_id: int, user_pokemon_id: int) -> tuple[bool, str, dict]:
    """Evolui um Pokémon usando uma pedra do inventário do usuário."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, name FROM shop_items WHERE id = %s AND category = 'stone';",
                (item_id,)
            )
            item_row = cur.fetchone()
            if not item_row:
                return False, "Item não encontrado ou não é uma pedra de evolução.", {}
            stone_slug, stone_name = item_row

            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, f"Você não possui {stone_name}.", {}

            cur.execute(
                "SELECT species_id, level FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            poke_row = cur.fetchone()
            if not poke_row:
                return False, "Pokémon não encontrado na sua coleção.", {}
            current_species, _ = poke_row

            cur.execute("""
                SELECT e.to_species_id, p1.name, p2.name, p2.sprite_url
                FROM pokemon_evolutions e
                JOIN pokemon_species p1 ON e.from_species_id = p1.id
                JOIN pokemon_species p2 ON e.to_species_id   = p2.id
                WHERE e.from_species_id = %s
                  AND e.trigger_name    = 'use-item'
                  AND e.item_name       = %s
                LIMIT 1;
            """, (current_species, stone_slug))
            evo_row = cur.fetchone()
            if not evo_row:
                return False, "Este Pokémon não evolui com essa pedra.", {}

            to_id, from_name, to_name, to_sprite = evo_row

            cur.execute(
                "UPDATE user_pokemon SET species_id = %s WHERE id = %s;",
                (to_id, user_pokemon_id)
            )
            _recalc_stats_on_evolution(cur, user_pokemon_id)

            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

        conn.commit()
        return True, f"{from_name} evoluiu para {to_name}!", {
            "from_name":  from_name,
            "to_name":    to_name,
            "to_id":      to_id,
            "sprite_url": to_sprite,
        }
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao evoluir: {e}", {}
