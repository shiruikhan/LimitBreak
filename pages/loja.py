import streamlit as st
from utils.app_cache import (
    clear_inventory_cache,
    clear_profile_cache,
    get_cached_user_inventory,
    get_cached_user_profile,
    get_cached_user_team,
    get_cached_xp_share_status,
)
from utils.db import (
    get_shop_items, buy_item,
)
from utils.bag_ui import ensure_bag_session_state, render_bag_view

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

for key, val in [("shop_using_item", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

ensure_bag_session_state()


def _clear_msg():
    st.session_state.shop_msg = None


# ── Dados ──────────────────────────────────────────────────────────────────────

user_id      = st.session_state.user_id
profile      = get_cached_user_profile(user_id)
coins        = profile["coins"] if profile else 0
items        = get_shop_items()
inventory    = get_cached_user_inventory(user_id)
team         = get_cached_user_team(user_id)
xp_share_st  = get_cached_xp_share_status(user_id)

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
                        clear_profile_cache(user_id)
                        clear_inventory_cache(user_id)
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
    st.caption("Itens com efeitos especiais. XP Share ativa direto; demais itens vão para a Mochila.")

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
                clear_profile_cache(user_id)
                clear_inventory_cache(user_id)
                st.session_state.shop_msg      = msg
                st.session_state.shop_msg_type = "success" if ok else "error"
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB — MOCHILA
# ═══════════════════════════════════════════════════════════════════════════════

with tab_bag:
    render_bag_view(user_id)
