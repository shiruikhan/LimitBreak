import streamlit as st

from utils.app_cache import (
    get_cached_shop_items,
    clear_inventory_cache,
    clear_profile_cache,
    clear_team_cache,
    clear_user_cache,
    get_cached_user_inventory,
    get_cached_user_profile,
    get_cached_user_team,
)
from utils.db import (
    evolve_with_stone,
    get_stone_targets,
    open_loot_box,
    hq_sprite_url,
    sprite_img_tag,
    use_nature_mint,
    use_stat_item,
    use_xp_share_item,
)

_ALL_NATURES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)

def ensure_bag_session_state() -> None:
    for key, val in [("shop_msg", None), ("shop_msg_type", "success")]:
        if key not in st.session_state:
            st.session_state[key] = val


def render_bag_styles() -> None:
    st.markdown(
        """
<style>
.bag-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #B8F82F, #7AB21A);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.bag-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px; }
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
.bag-shortcut-note {
    background: rgba(184,248,47,0.08);
    border: 1px solid rgba(184,248,47,0.28);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 14px;
    color: #c9d1d9;
    font-size: 0.82rem;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_bag_header(*, show_shop_button: bool) -> None:
    user_id = st.session_state.get("user_id")
    profile = get_cached_user_profile(user_id) if user_id else None
    coins = profile["coins"] if profile else 0

    col_title, col_actions = st.columns([3, 1])
    with col_title:
        st.markdown("<p class='bag-title'>MOCHILA</p>", unsafe_allow_html=True)
        st.markdown("<p class='bag-sub'>USE SEUS ITENS SEM PASSAR PELA LOJA</p>", unsafe_allow_html=True)
    with col_actions:
        st.markdown(
            f"<div style='text-align:right;margin-top:8px'>"
            f"<div class='coins-badge'>🪙 {coins:,}</div></div>",
            unsafe_allow_html=True,
        )

    if show_shop_button:
        left, right = st.columns([1.4, 4])
        with left:
            if st.button("🛒 Ir para Loja", use_container_width=True):
                st.switch_page("pages/loja.py")
        with right:
            st.markdown(
                "<div class='bag-shortcut-note'>"
                "Atalho direto para gerenciar sua mochila e abrir itens recebidos."
                "</div>",
                unsafe_allow_html=True,
            )
        st.markdown("---")


def render_bag_view(user_id: str) -> None:
    ensure_bag_session_state()

    inventory = get_cached_user_inventory(user_id)
    items = get_cached_shop_items()
    team = get_cached_user_team(user_id)

    if st.session_state.shop_msg:
        if st.session_state.shop_msg_type == "success":
            st.success(st.session_state.shop_msg)
        else:
            st.error(st.session_state.shop_msg)
        st.session_state.shop_msg = None

    if not inventory:
        st.info("Sua mochila está vazia. Compre itens na Loja!")
        return

    item_map = {i["id"]: i for i in items}

    inv_stat = [
        (iid, qty) for iid, qty in inventory.items()
        if item_map.get(iid, {}).get("category") == "stat_boost"
    ]
    inv_nature_mint = [
        (iid, qty) for iid, qty in inventory.items()
        if item_map.get(iid, {}).get("category") == "nature_mint"
        or item_map.get(iid, {}).get("slug") == "nature-mint"
    ]
    inv_stones = [
        (iid, qty) for iid, qty in inventory.items()
        if item_map.get(iid, {}).get("category") == "stone"
    ]
    inv_loot_boxes = [
        (iid, qty) for iid, qty in inventory.items()
        if item_map.get(iid, {}).get("slug") == "loot-box"
        or item_map.get(iid, {}).get("category") == "loot_box"
    ]
    inv_others = [
        (iid, qty) for iid, qty in inventory.items()
        if item_map.get(iid, {}).get("category") == "other"
        and item_map.get(iid, {}).get("slug") not in ("loot-box", "nature-mint")
    ]

    if inv_stat:
        st.markdown("<div class='section-title'>💊 Vitaminas</div>", unsafe_allow_html=True)

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
            target_label = "—"
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
                    clear_inventory_cache(user_id)
                    clear_team_cache(user_id)
                    st.session_state.shop_msg = msg
                    st.session_state.shop_msg_type = "success" if ok else "error"
                    st.rerun()

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

            available_natures = [n for n in _ALL_NATURES if n.lower() != (current_nature or "").lower()]

            _NATURE_EFFECTS_UI = {
                "Lonely": ("+ATK", "-DEF"), "Brave": ("+ATK", "-SPD"),
                "Adamant": ("+ATK", "-SpA"), "Naughty": ("+ATK", "-SpD"),
                "Bold": ("+DEF", "-ATK"), "Relaxed": ("+DEF", "-SPD"),
                "Impish": ("+DEF", "-SpA"), "Lax": ("+DEF", "-SpD"),
                "Timid": ("+SPD", "-ATK"), "Hasty": ("+SPD", "-DEF"),
                "Jolly": ("+SPD", "-SpA"), "Naive": ("+SPD", "-SpD"),
                "Modest": ("+SpA", "-ATK"), "Mild": ("+SpA", "-DEF"),
                "Quiet": ("+SpA", "-SPD"), "Rash": ("+SpA", "-SpD"),
                "Calm": ("+SpD", "-ATK"), "Gentle": ("+SpD", "-DEF"),
                "Sassy": ("+SpD", "-SPD"), "Careful": ("+SpD", "-SpA"),
            }

            def _nature_preview(name: str) -> str:
                effects = _NATURE_EFFECTS_UI.get(name)
                if not effects:
                    return "Neutro"
                return f"{effects[0]} / {effects[1]}"

            col_cur, col_arrow, col_new = st.columns([2, 1, 2])
            with col_cur:
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid #30363d;border-radius:10px;"
                    f"padding:10px;text-align:center'>"
                    f"<div style='font-size:.65rem;color:#8b949e;text-transform:uppercase;"
                    f"letter-spacing:1px;margin-bottom:4px'>Natureza atual</div>"
                    f"<div style='font-weight:700;color:#e6edf3'>{current_nature}</div>"
                    f"<div style='font-size:.72rem;color:#8b949e;margin-top:2px'>{_nature_preview(current_nature)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_arrow:
                st.markdown(
                    "<div style='text-align:center;padding-top:22px;font-size:1.4rem;color:#7038F8'>→</div>",
                    unsafe_allow_html=True,
                )
            with col_new:
                new_nature = st.selectbox(
                    "Nova natureza",
                    available_natures,
                    key="bag_mint_new_nature",
                    label_visibility="collapsed",
                )
                st.markdown(
                    f"<div style='text-align:center;font-size:.72rem;color:#A27DFA;margin-top:2px'>"
                    f"{_nature_preview(new_nature)}</div>",
                    unsafe_allow_html=True,
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
                        f"✨ Usar em {mint_target['name']} → {new_nature}",
                        key=f"use_mint_{iid}",
                        use_container_width=True,
                        type="primary",
                    ):
                        ok, msg = use_nature_mint(user_id, iid, mint_target_id, new_nature)
                        clear_inventory_cache(user_id)
                        clear_team_cache(user_id)
                        st.session_state.shop_msg = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        st.rerun()

    if inv_stones:
        st.markdown("<div class='section-title'>🪨 Pedras de Evolução</div>", unsafe_allow_html=True)

        for iid, qty in inv_stones:
            item = item_map[iid]
            stone_slug = item["slug"]
            targets = get_stone_targets(user_id, stone_slug)

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

                    sprite_html = ""
                    if chosen["sprite_url"]:
                        sprite_html = (
                            sprite_img_tag(
                                hq_sprite_url(chosen["sprite_url"]),
                                width=80,
                                extra_style="image-rendering:pixelated",
                            )
                            or sprite_img_tag(
                                chosen["sprite_url"],
                                width=80,
                                extra_style="image-rendering:pixelated",
                            )
                        )

                    col_img, col_info = st.columns([1, 3])
                    with col_img:
                        if sprite_html:
                            st.markdown(sprite_html, unsafe_allow_html=True)
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
                        clear_inventory_cache(user_id)
                        clear_team_cache(user_id)
                        st.session_state.shop_msg = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        if ok and evo_data:
                            st.session_state.team_evo_notice = evo_data
                        st.rerun()

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
                    clear_user_cache(user_id)
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
                        clear_inventory_cache(user_id)
                        clear_profile_cache(user_id)
                        st.session_state.shop_msg = msg
                        st.session_state.shop_msg_type = "success" if ok else "error"
                        st.rerun()
                elif item["slug"] == "streak-shield":
                    st.button(
                        "🛡️ Auto",
                        key=f"use_other_{iid}",
                        disabled=True,
                        use_container_width=True,
                        help="Consumido automaticamente no check-in quando você perde um dia.",
                    )
                else:
                    st.markdown(
                        "<div style='display:block;text-align:center;margin-top:4px;color:#6e7681'>Em breve</div>",
                        unsafe_allow_html=True,
                    )
