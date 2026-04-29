import os
import streamlit as st
from utils.db import (
    get_shop_items, get_user_inventory, get_user_profile,
    get_user_team, buy_item, use_stat_item,
    get_stone_targets, evolve_with_stone, get_image_as_base64,
    get_xp_share_status, open_loot_box, use_xp_share_item,
    use_nature_mint,
)

_ALL_NATURES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)

BASE_DIR = os.getcwd()

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.shop-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #FFDD7A, #FFC531);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.shop-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px; }

.coins-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, #FFC531, #B38200);
    border-radius: 9999px; padding: 6px 16px;
    font-size: 0.95rem; font-weight: 800; color: #0d1117;
}

.section-title {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e;
    border-bottom: 1px solid #21262d; padding-bottom: 6px; margin: 20px 0 12px;
}

/* Cards de item */
.item-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 16px 14px 12px;
    text-align: center; height: 100%;
    display: flex; flex-direction: column; gap: 6px;
    transition: border-color 0.2s ease;
}
.item-icon  { font-size: 2.2rem; line-height: 1; }
.item-name  { font-weight: 700; color: #e6edf3; font-size: 0.88rem; }
.item-desc  { color: #8b949e; font-size: 0.72rem; line-height: 1.4; flex: 1; }
.item-price {
    font-weight: 800; color: #FFC531; font-size: 0.9rem;
    margin-top: 4px; font-family: "JetBrains Mono", monospace;
}
.item-price.cant-afford { color: #484f58; }

/* Badge "em breve" */
.soon-badge {
    display: inline-block; background: #1f2937; border: 1px solid #374151;
    border-radius: 6px; padding: 3px 10px;
    font-size: 0.68rem; color: #6e7681; font-weight: 600;
    letter-spacing: 0.5px;
}

/* Cards do inventário */
.inv-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 16px;
    padding: 14px; display: flex; align-items: center; gap: 10px;
    transition: border-color 0.2s ease;
}
.inv-card:hover { border-color: #484f58; }
.inv-icon  { font-size: 1.8rem; flex-shrink: 0; }
.inv-info  { flex: 1; min-width: 0; }
.inv-name  { font-weight: 700; color: #e6edf3; font-size: 0.85rem; }
.inv-qty   { color: #8b949e; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# ── Estado de sessão ───────────────────────────────────────────────────────────

for key, val in [("shop_using_item", None), ("shop_msg", None), ("shop_msg_type", "success")]:
    if key not in st.session_state:
        st.session_state[key] = val


def _clear_msg():
    st.session_state.shop_msg = None


# ── Dados ──────────────────────────────────────────────────────────────────────

user_id      = st.session_state.user_id
profile      = get_user_profile(user_id)
coins        = profile["coins"] if profile else 0
items        = get_shop_items()
inventory    = get_user_inventory(user_id)
team         = get_user_team(user_id)
xp_share_st  = get_xp_share_status(user_id)

# Catálogo por categoria
stones        = [i for i in items if i["category"] == "stone"]
stat_boosts   = [i for i in items if i["category"] == "stat_boost"]
nature_mints  = [i for i in items if i["category"] == "nature_mint"]
others        = [i for i in items if i["category"] == "other" and i["slug"] != "loot-box"]

# ── Header ─────────────────────────────────────────────────────────────────────

col_title, col_coins = st.columns([3, 1])
with col_title:
    st.markdown("<p class='shop-title'>LOJA</p>", unsafe_allow_html=True)
    st.markdown("<p class='shop-sub'>GASTE SUAS MOEDAS COM SABEDORIA</p>", unsafe_allow_html=True)
with col_coins:
    st.markdown(
        f"<div style='text-align:right;margin-top:8px'>"
        f"<div class='coins-badge'>🪙 {coins:,}</div></div>",
        unsafe_allow_html=True,
    )

# Mensagem de feedback
if st.session_state.shop_msg:
    if st.session_state.shop_msg_type == "success":
        st.success(st.session_state.shop_msg)
    else:
        st.error(st.session_state.shop_msg)
    st.session_state.shop_msg = None

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_shop, tab_bag = st.tabs(["🛒  Loja", "🎒  Mochila"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB — LOJA
# ═══════════════════════════════════════════════════════════════════════════════

with tab_shop:

    def _item_grid(item_list: list[dict], cols: int = 4):
        """Renderiza uma grade de cards de itens com botão de compra."""
        rows = [item_list[i:i+cols] for i in range(0, len(item_list), cols)]
        for row in rows:
            grid_cols = st.columns(cols)
            for col, item in zip(grid_cols, row):
                with col:
                    can_buy   = coins >= item["price"]
                    price_cls = "" if can_buy else "cant-afford"
                    qty_owned = inventory.get(item["id"], 0)
                    owned_txt = f" · você tem {qty_owned}" if qty_owned > 0 else ""

                    st.markdown(
                        f"<div class='item-card'>"
                        f"<div class='item-icon'>{item['icon']}</div>"
                        f"<div class='item-name'>{item['name']}</div>"
                        f"<div class='item-desc'>{item['description']}</div>"
                        f"<div class='item-price {price_cls}'>🪙 {item['price']:,}{owned_txt}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    if st.button(
                        "Comprar" if can_buy else "💸 Sem moedas",
                        key=f"buy_{item['id']}",
                        disabled=not can_buy,
                        use_container_width=True,
                    ):
                        ok, msg = buy_item(user_id, item["id"])
                        st.session_state.shop_msg      = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        st.rerun()

    # ── Pedras de Evolução ─────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>🪨 Pedras de Evolução</div>", unsafe_allow_html=True)
    st.caption("Compre e use na aba Mochila para evoluir Pokémon compatíveis da sua coleção.")
    _item_grid(stones, cols=5)

    # ── Vitaminas ──────────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>💊 Vitaminas — Melhoria Permanente de Stats</div>", unsafe_allow_html=True)
    st.caption("Aumentam permanentemente o stat do Pokémon escolhido. Use na aba Mochila.")
    _item_grid(stat_boosts, cols=6)

    # ── Nature Mint ────────────────────────────────────────────────────────────
    if nature_mints:
        st.markdown("<div class='section-title'>🌿 Nature Mint — Troca de Natureza</div>", unsafe_allow_html=True)
        st.caption("Troca permanentemente a natureza de um Pokémon. Use na aba Mochila.")
        _item_grid(nature_mints, cols=4)

    # ── Outros ────────────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>📦 Outros</div>", unsafe_allow_html=True)
    st.caption("Efeitos ativados automaticamente na compra — não vão para a mochila.")

    cols_other = st.columns(4)
    for idx, item in enumerate(others):
        is_xp_share = item["slug"] == "xp-share"
        can_buy     = coins >= item["price"]
        price_cls   = "" if can_buy else "cant-afford"

        with cols_other[idx % 4]:
            if is_xp_share and xp_share_st["active"]:
                days = xp_share_st["days_left"]
                status_html = (
                    f"<div style='font-size:0.7rem;color:#58A6FF;margin-top:4px'>"
                    f"📡 Ativo · {days} dia{'s' if days != 1 else ''} restante{'s' if days != 1 else ''}</div>"
                )
            else:
                status_html = ""

            st.markdown(
                f"<div class='item-card'>"
                f"<div class='item-icon'>{item['icon']}</div>"
                f"<div class='item-name'>{item['name']}</div>"
                f"<div class='item-desc'>{item['description']}</div>"
                f"<div class='item-price {price_cls}'>🪙 {item['price']:,}</div>"
                f"{status_html}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.write("")
            btn_label = (
                ("✚ +15 dias" if xp_share_st["active"] else "▶ Ativar")
                if is_xp_share
                else ("Comprar" if can_buy else "💸 Sem moedas")
            )
            if st.button(
                btn_label,
                key=f"buy_{item['id']}",
                disabled=not can_buy,
                use_container_width=True,
            ):
                ok, msg = buy_item(user_id, item["id"])
                st.session_state.shop_msg      = msg
                st.session_state.shop_msg_type = "success" if ok else "error"
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB — MOCHILA
# ═══════════════════════════════════════════════════════════════════════════════

with tab_bag:

    if not inventory:
        st.info("Sua mochila está vazia. Compre itens na aba Loja!")
    else:
        # Mapa item_id → detalhes
        item_map = {i["id"]: i for i in items}

        # Separa por categoria para exibição organizada
        inv_stat        = [(iid, qty) for iid, qty in inventory.items()
                           if item_map.get(iid, {}).get("category") == "stat_boost"]
        inv_nature_mint = [(iid, qty) for iid, qty in inventory.items()
                           if item_map.get(iid, {}).get("category") == "nature_mint"]
        inv_stones      = [(iid, qty) for iid, qty in inventory.items()
                           if item_map.get(iid, {}).get("category") == "stone"]
        inv_loot_boxes = [(iid, qty) for iid, qty in inventory.items()
                          if item_map.get(iid, {}).get("slug") == "loot-box"
                          or item_map.get(iid, {}).get("category") == "loot_box"]
        inv_others = [(iid, qty) for iid, qty in inventory.items()
                      if item_map.get(iid, {}).get("category") == "other"
                      and item_map.get(iid, {}).get("slug") != "loot-box"]

        # ── Vitaminas (usáveis) ────────────────────────────────────────────────
        if inv_stat:
            st.markdown("<div class='section-title'>💊 Vitaminas</div>", unsafe_allow_html=True)

            # Seletor de Pokémon alvo (compartilhado para todas as vitaminas)
            if team:
                team_options = {
                    f"{p['name']} (Nv. {p['level']}) — Slot {p['slot']}": p["user_pokemon_id"]
                    for p in team
                }
                target_label = st.selectbox(
                    "Aplicar em qual Pokémon da equipe?",
                    options=list(team_options.keys()),
                    key="bag_target_pokemon",
                )
                target_id = team_options[target_label]
            else:
                st.warning("Você não tem Pokémon na equipe para usar vitaminas.")
                target_id = None

            st.write("")
            cols = st.columns(3)
            for idx, (iid, qty) in enumerate(inv_stat):
                item = item_map[iid]
                with cols[idx % 3]:
                    st.markdown(
                        f"<div class='inv-card'>"
                        f"<div class='inv-icon'>{item['icon']}</div>"
                        f"<div class='inv-info'>"
                        f"<div class='inv-name'>{item['name']}</div>"
                        f"<div class='inv-qty'>Quantidade: {qty}</div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    if st.button(
                        f"Usar em {target_label.split(' —')[0] if team else '—'}",
                        key=f"use_{iid}",
                        disabled=not team or not target_id,
                        use_container_width=True,
                    ):
                        ok, msg = use_stat_item(user_id, iid, target_id)
                        st.session_state.shop_msg      = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        st.rerun()

        # ── Nature Mint ───────────────────────────────────────────────────────
        if inv_nature_mint:
            st.markdown("<div class='section-title'>🌿 Nature Mint</div>", unsafe_allow_html=True)

            if not team:
                st.warning("Você não tem Pokémon na equipe para usar Nature Mint.")
            else:
                mint_team_options = {
                    f"{p['name']} (Nv. {p['level']}) — Slot {p['slot']}": p
                    for p in team
                }
                mint_target_label = st.selectbox(
                    "Aplicar em qual Pokémon da equipe?",
                    options=list(mint_team_options.keys()),
                    key="bag_mint_target_pokemon",
                )
                mint_target = mint_team_options[mint_target_label]
                mint_target_id = mint_target["user_pokemon_id"]
                current_nature = mint_target.get("nature_name") or "Desconhecida"

                st.caption(f"Natureza atual: **{current_nature}**")

                available_natures = [n for n in _ALL_NATURES if n != current_nature]
                new_nature = st.selectbox(
                    "Nova natureza:",
                    options=available_natures,
                    key="bag_mint_new_nature",
                )

                st.write("")
                cols_mint = st.columns(min(len(inv_nature_mint), 4))
                for idx, (iid, qty) in enumerate(inv_nature_mint):
                    item = item_map[iid]
                    with cols_mint[idx % 4]:
                        st.markdown(
                            f"<div class='inv-card'>"
                            f"<div class='inv-icon'>{item['icon']}</div>"
                            f"<div class='inv-info'>"
                            f"<div class='inv-name'>{item['name']}</div>"
                            f"<div class='inv-qty'>Quantidade: {qty}</div>"
                            f"</div></div>",
                            unsafe_allow_html=True,
                        )
                        st.write("")
                        if st.button(
                            f"Usar em {mint_target['name']}",
                            key=f"use_mint_{iid}",
                            use_container_width=True,
                        ):
                            ok, msg = use_nature_mint(user_id, iid, mint_target_id, new_nature)
                            st.session_state.shop_msg      = msg
                            st.session_state.shop_msg_type = "success" if ok else "error"
                            st.rerun()

        # ── Pedras de Evolução ─────────────────────────────────────────────────
        if inv_stones:
            st.markdown("<div class='section-title'>🪨 Pedras de Evolução</div>", unsafe_allow_html=True)

            for iid, qty in inv_stones:
                item       = item_map[iid]
                stone_slug = item["slug"]
                targets    = get_stone_targets(user_id, stone_slug)

                with st.expander(f"{item['icon']} {item['name']}  ·  Qtd: {qty}", expanded=bool(targets)):
                    if not targets:
                        st.info("Nenhum dos seus Pokémon evolui com esta pedra.", icon="ℹ️")
                    else:
                        options = {
                            f"{t['from_name']} → {t['to_name']} (Lv.{t['level']}"
                            f"{' · equipe' if t['in_team'] else ''})": t
                            for t in targets
                        }
                        chosen_label = st.selectbox(
                            "Pokémon para evoluir:",
                            list(options.keys()),
                            key=f"stone_target_{iid}",
                        )
                        chosen = options[chosen_label]

                        # Preview da evolução
                        b64 = None
                        if chosen["sprite_url"]:
                            sp = os.path.join(BASE_DIR, chosen["sprite_url"].lstrip("/\\"))
                            hq = sp.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")
                            b64 = get_image_as_base64(hq) or get_image_as_base64(sp)

                        col_img, col_info = st.columns([1, 3])
                        with col_img:
                            if b64:
                                st.markdown(
                                    f"<img src='data:image/png;base64,{b64}' "
                                    f"style='width:80px;image-rendering:pixelated'>",
                                    unsafe_allow_html=True,
                                )
                        with col_info:
                            st.markdown(
                                f"<div style='font-size:.85rem;color:#8b949e;margin-top:8px'>"
                                f"<b style='color:#e6edf3'>{chosen['from_name']}</b> "
                                f"<span style='color:#7038F8'>→</span> "
                                f"<b style='color:#A27DFA'>{chosen['to_name']}</b>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        if st.button(
                            f"✨ Usar {item['name']} em {chosen['from_name']}",
                            key=f"use_stone_{iid}_{chosen['user_pokemon_id']}",
                            type="primary",
                        ):
                            ok, msg, evo_data = evolve_with_stone(user_id, iid, chosen["user_pokemon_id"])
                            st.session_state.shop_msg      = msg
                            st.session_state.shop_msg_type = "success" if ok else "error"
                            if ok and evo_data:
                                st.session_state.team_evo_notice = evo_data
                            st.rerun()

        # ── Loot Boxes ────────────────────────────────────────────────────────
        if inv_loot_boxes:
            st.markdown("<div class='section-title'>🎁 Loot Boxes</div>", unsafe_allow_html=True)
            cols_loot = st.columns(4)
            for idx, (iid, qty) in enumerate(inv_loot_boxes):
                item = item_map[iid]
                with cols_loot[idx % 4]:
                    st.markdown(
                        f"<div class='inv-card' style='flex-direction:column;text-align:center'>"
                        f"<div class='inv-icon'>{item['icon']}</div>"
                        f"<div class='inv-name'>{item['name']}</div>"
                        f"<div class='inv-qty'>Qtd: {qty}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    if st.button(
                        "Abrir",
                        key=f"open_loot_box_{iid}",
                        type="primary",
                        use_container_width=True,
                    ):
                        ok, msg, loot = open_loot_box(user_id, iid)
                        xp_res = (loot or {}).get("xp_result", {})
                        evolutions = xp_res.get("evolutions", [])
                        if evolutions:
                            evo = next((e for e in evolutions if not e.get("shed")), evolutions[0])
                            st.session_state.team_evo_notice = {
                                "from_name": evo["from_name"],
                                "to_name": evo["to_name"],
                                "sprite_url": evo.get("sprite_url", ""),
                            }
                        xp_shared = xp_res.get("xp_share_distributed", [])
                        if xp_shared:
                            st.session_state.xp_share_log = xp_shared
                        st.session_state.shop_msg = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        st.rerun()

        # ── Outros ────────────────────────────────────────────────────────────
        if inv_others:
            st.markdown("<div class='section-title'>📦 Outros</div>", unsafe_allow_html=True)
            cols_inv_oth = st.columns(4)
            for idx, (iid, qty) in enumerate(inv_others):
                item = item_map[iid]
                with cols_inv_oth[idx % 4]:
                    st.markdown(
                        f"<div class='inv-card' style='flex-direction:column;text-align:center'>"
                        f"<div class='inv-icon'>{item['icon']}</div>"
                        f"<div class='inv-name'>{item['name']}</div>"
                        f"<div class='inv-qty'>Qtd: {qty}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    if item["slug"] == "xp-share":
                        if st.button(
                            "Ativar",
                            key=f"use_other_{iid}",
                            use_container_width=True,
                        ):
                            ok, msg = use_xp_share_item(user_id, iid)
                            st.session_state.shop_msg = msg
                            st.session_state.shop_msg_type = "success" if ok else "error"
                            st.rerun()
                    else:
                        st.markdown("<div class='soon-badge' style='display:block;text-align:center;margin-top:4px'>Em breve</div>", unsafe_allow_html=True)
