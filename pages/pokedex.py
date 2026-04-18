import os
import streamlit as st
from utils.db import (
    get_all_pokemon, get_pokemon_details, get_pokemon_moves,
    get_full_evolution_chain, get_image_as_base64,
)
from utils.type_colors import get_type_color, TYPE_COLORS

BASE_DIR = os.getcwd()
TOTAL_POKEMON = 1025
_GITHUB_ASSETS_CDN = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_asset(local_path: str) -> str:
    """Retorna o caminho local se existir, senão URL do GitHub CDN."""
    if os.path.isfile(local_path):
        return local_path
    norm = local_path.replace("\\", "/")
    if "assets/" in norm:
        rel = norm.split("assets/", 1)[1]
        return f"{_GITHUB_ASSETS_CDN}/assets/{rel}"
    return local_path  # melhor esforço

def _hq_path(sprite_url: str) -> str:
    """Caminho/URL para a imagem HQ (official artwork)."""
    local = os.path.join(BASE_DIR, sprite_url.replace("/images/", "/imagesHQ/").lstrip("/\\"))
    return _resolve_asset(local)

def _thumb_path(pokemon_id: int) -> str:
    """Caminho/URL para o thumbnail de um Pokémon."""
    local = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
                         f"{str(pokemon_id).zfill(4)}.png")
    return _resolve_asset(local)

def _type_icon_path(type_name: str) -> str:
    return os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others", "type-icons", "png", f"{type_name.lower()}.png")

def _dmg_icon_path(damage_class: str) -> str:
    return os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others", "damage-category-icons", "1x", f"{damage_class.capitalize()}.png")

def _img_tag(b64: str | None, width: int = 20) -> str:
    if not b64:
        return ""
    return f"<img src='data:image/png;base64,{b64}' width='{width}' style='vertical-align:middle'>"


# ── CSS ────────────────────────────────────────────────────────────────────────

def _inject_global_css():
    st.markdown("""
<style>
/* App background */
.stApp { background: #0d1117; color: #e6edf3; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #161b22 !important; border-color: #30363d !important;
}

/* Section labels */
.section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e; margin-bottom: 10px;
}

/* Type badge */
.type-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; margin-right: 6px;
}

/* Move card */
.move-card {
    display: flex; align-items: center; gap: 10px;
    background: #161b22; border-radius: 10px;
    padding: 8px 14px; margin-bottom: 8px;
    border-left: 4px solid #30363d;
    transition: all 0.18s ease;
}
.move-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.move-lv {
    font-size: 0.7rem; font-weight: 700; color: #8b949e;
    min-width: 36px; text-align: right;
}
.move-name { flex: 1; font-weight: 600; font-size: 0.92rem; color: #e6edf3; }
.move-stat { font-size: 0.72rem; color: #8b949e; text-align: center; min-width: 32px; }
.move-stat span { display: block; font-size: 0.62rem; text-transform: uppercase; }

/* Moves scroll container */
.moves-wrap {
    max-height: 480px; overflow-y: auto; padding-right: 4px;
}
.moves-wrap::-webkit-scrollbar { width: 4px; }
.moves-wrap::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }

/* Pokemon header card */
.poke-header {
    border-radius: 20px; padding: 28px 32px 20px;
    margin-bottom: 20px; position: relative; overflow: hidden;
}
.poke-header::before {
    content: ""; position: absolute;
    width: 280px; height: 280px; border-radius: 50%;
    background: rgba(255,255,255,0.06);
    right: -60px; top: -80px;
}
.poke-header::after {
    content: ""; position: absolute;
    width: 160px; height: 160px; border-radius: 50%;
    background: rgba(255,255,255,0.04);
    right: 80px; top: 60px;
}
.poke-number { font-size: 0.85rem; font-weight: 700; letter-spacing: 2px; opacity: 0.6; }
.poke-name {
    font-size: 2.8rem; font-weight: 900; letter-spacing: 1px;
    line-height: 1; margin: 4px 0 12px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.poke-xp { font-size: 0.78rem; opacity: 0.7; margin-top: 8px; }

/* Evolution chain */
.evo-container {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 16px; padding: 24px 20px; margin-top: 16px;
}
.evo-node {
    text-align: center; padding: 12px 8px;
    border-radius: 12px; transition: all 0.2s ease;
}
.evo-node.active {
    background: rgba(120,200,80,0.12);
    box-shadow: 0 0 0 2px #78C850;
}
.evo-name {
    font-size: 0.78rem; font-weight: 700; margin-top: 6px;
    letter-spacing: 0.5px;
}
.evo-arrow {
    text-align: center; color: #8b949e; font-size: 1.4rem;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 2px;
}
.evo-cond { font-size: 0.68rem; color: #8b949e; white-space: nowrap; }

/* Info rows */
.info-row {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
}
.info-row:last-child { border-bottom: none; }
.info-key { font-size: 0.72rem; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: #8b949e; min-width: 70px; }

</style>
""", unsafe_allow_html=True)


def _inject_header_css(c1: dict, c2: dict):
    """Injects a dynamic gradient for the Pokémon header card based on types."""
    g = f"linear-gradient(135deg, {c1['dark']} 0%, {c1['bg']} 45%, {c2['bg']} 100%)"
    st.markdown(f"<style>.poke-header {{ background: {g}; color: {c1['text']}; }}</style>",
                unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _render_sidebar(pokemon_dict: dict) -> int:
    with st.sidebar:
        # User info + logout
        user_id = st.session_state.get("user_id")
        email = st.session_state.get("user", {})
        if hasattr(email, "email"):
            st.markdown(f"<small style='color:#8b949e'>👤 {email.email}</small>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<div class='section-label'>Pokédex Nacional</div>", unsafe_allow_html=True)

        selected = st.selectbox(
            "Buscar Pokémon",
            options=list(pokemon_dict.keys()),
            label_visibility="collapsed",
        )

        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            for k in ["user", "user_id", "access_token", "refresh_token", "needs_starter"]:
                st.session_state[k] = None
            st.rerun()

    return pokemon_dict[selected]


# ── Type badge HTML ────────────────────────────────────────────────────────────

def _type_badge(type_name: str, size: str = "md") -> str:
    c = get_type_color(type_name)
    icon_b64 = get_image_as_base64(_type_icon_path(type_name))
    icon = _img_tag(icon_b64, 14) if icon_b64 else ""
    pad = "5px 14px" if size == "md" else "3px 10px"
    fs = "0.78rem" if size == "md" else "0.7rem"
    return (
        f"<span class='type-badge' style='background:{c['bg']};color:{c['text']};padding:{pad};font-size:{fs}'>"
        f"{icon} {type_name.upper()}</span>"
    )


# ── Main render ────────────────────────────────────────────────────────────────

def _render_pokedex(pid: int):
    details = get_pokemon_details(pid)
    if not details:
        st.error("Pokémon não encontrado.")
        return

    pk_id, name, sprite_url, sprite_shiny_url, type1, type2, base_xp = details
    moves = get_pokemon_moves(pid)
    evolutions = get_full_evolution_chain(pid)

    c1 = get_type_color(type1)
    c2 = get_type_color(type2 or type1)
    _inject_header_css(c1, c2)

    # ── HEADER CARD ──────────────────────────────────────────────────────────
    st.markdown("<div class='poke-header'>", unsafe_allow_html=True)

    col_info, col_img, col_moves = st.columns([1.2, 1.4, 1.6])

    # Left: Info
    with col_info:
        st.markdown(
            f"<div class='poke-number'>#{str(pk_id).zfill(3)} / {TOTAL_POKEMON}</div>"
            f"<div class='poke-name'>{name.upper()}</div>",
            unsafe_allow_html=True,
        )

        badges = _type_badge(type1) if type1 else ""
        badges += _type_badge(type2) if type2 else ""
        st.markdown(badges, unsafe_allow_html=True)

        st.write("")
        st.markdown(
            f"<div class='info-row'>"
            f"<span class='info-key'>XP Base</span>"
            f"<span style='font-weight:600'>{base_xp or '—'}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Center: Image
    with col_img:
        if sprite_url:
            hq = _hq_path(sprite_url)
            try:
                st.image(hq, width=280)
            except Exception:
                local_sp = os.path.join(BASE_DIR, sprite_url.lstrip("/\\"))
                st.image(_resolve_asset(local_sp), width=280)

    # Right: Moves
    with col_moves:
        st.markdown("<div class='section-label'>Movepool (Level Up)</div>", unsafe_allow_html=True)
        if moves:
            html = "<div class='moves-wrap'>"
            for m_name, m_lv, m_class, m_type, m_pow, m_acc in moves:
                tc = get_type_color(m_type)
                border_color = tc["bg"]

                type_b64 = get_image_as_base64(_type_icon_path(m_type)) if m_type else None
                dmg_b64 = get_image_as_base64(_dmg_icon_path(m_class)) if m_class else None

                type_icon = _img_tag(type_b64, 16)
                dmg_icon = _img_tag(dmg_b64, 18)

                pow_str = str(m_pow) if m_pow else "—"
                acc_str = f"{m_acc}%" if m_acc else "—"

                html += (
                    f"<div class='move-card' style='border-left-color:{border_color}'>"
                    f"<span class='move-lv'>Lv.{m_lv}</span>"
                    f"<span class='move-name'>{m_name}</span>"
                    f"{type_icon}"
                    f"<span class='move-stat'>{pow_str}<span>Power</span></span>"
                    f"<span class='move-stat'>{acc_str}<span>Acc</span></span>"
                    f"{dmg_icon}"
                    f"</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#8b949e'>Nenhum golpe mapeado.</span>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # close .poke-header

    # ── EVOLUTION CHAIN ───────────────────────────────────────────────────────
    if evolutions:
        st.markdown("<div class='section-label' style='margin-top:24px'>Linha Evolutiva</div>",
                    unsafe_allow_html=True)
        st.markdown("<div class='evo-container'>", unsafe_allow_html=True)

        # Build stage tree
        nodes = {e[0]: e[1] for e in evolutions}
        nodes.update({e[2]: e[3] for e in evolutions})
        to_ids = {e[2] for e in evolutions}
        root_id = next((i for i in nodes if i not in to_ids), list(nodes.keys())[0])

        stages = [[root_id]]
        current = [root_id]
        while True:
            nxt = []
            for n in current:
                for e in evolutions:
                    if e[0] == n and e[2] not in nxt:
                        nxt.append(e[2])
            if not nxt:
                break
            stages.append(nxt)
            current = nxt

        # Column ratios: [img, arrow, img, arrow, img ...]
        ratios = []
        for i in range(len(stages)):
            ratios.append(max(len(stages[i]), 1) * 1.2)
            if i < len(stages) - 1:
                ratios.append(0.6)

        evo_cols = st.columns(ratios)

        for i, stage in enumerate(stages):
            with evo_cols[i * 2]:
                for p_id in stage:
                    b64 = get_image_as_base64(_thumb_path(p_id))
                    img = _img_tag(b64, 80) if b64 else "❓"
                    active_cls = "active" if p_id == pid else ""
                    p_name = nodes[p_id].upper()
                    color = "#78C850" if p_id == pid else "#8b949e"
                    st.markdown(
                        f"<div class='evo-node {active_cls}'>"
                        f"{img}"
                        f"<div class='evo-name' style='color:{color}'>#{p_id} {p_name}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            if i < len(stages) - 1:
                with evo_cols[i * 2 + 1]:
                    child_id = stages[i + 1][0]
                    edge = next(
                        (e for e in evolutions if e[0] == stage[0] and e[2] == child_id), None
                    )
                    if edge:
                        cond = f"Lv. {edge[4]}+" if edge[4] else (edge[6] or edge[5] or "?")
                    else:
                        cond = "?"
                    st.markdown(
                        f"<div class='evo-arrow'>"
                        f"<span class='evo-cond'>{cond}</span>"
                        f"<span>→</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)  # close .evo-container
    else:
        st.markdown(
            "<div style='text-align:center;color:#8b949e;padding:20px;background:#161b22;"
            "border-radius:12px;margin-top:16px'>Este Pokémon não evolui.</div>",
            unsafe_allow_html=True,
        )


# ── Entry point ────────────────────────────────────────────────────────────────

_inject_global_css()

pokemon_list = get_all_pokemon()
pokemon_dict = {f"#{str(p[0]).zfill(3)} {p[1]}": p[0] for p in pokemon_list}

selected_id = _render_sidebar(pokemon_dict)
_render_pokedex(selected_id)
