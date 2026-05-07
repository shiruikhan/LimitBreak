import os
import re
import streamlit as st
from utils.app_cache import get_cached_user_pokemon_ids
from utils.db import get_all_pokemon_with_types, sprite_img_tag
from utils.type_colors import TYPE_COLORS, get_type_color

BASE_DIR = os.getcwd()

# ── Constantes ─────────────────────────────────────────────────────────────────

ALL_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
]

GENERATIONS = {
    "Gen 1 (1–151)":   (1,   151),
    "Gen 2 (152–251)": (152, 251),
    "Gen 3 (252–386)": (252, 386),
    "Gen 4 (387–493)": (387, 493),
    "Gen 5 (494–649)": (494, 649),
    "Gen 6 (650–721)": (650, 721),
    "Gen 7 (722–809)": (722, 809),
    "Gen 8 (810–905)": (810, 905),
    "Gen 9 (906–1025)":(906, 1025),
}

# ── CSS ─────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.pdex-header {
    display: flex; align-items: center; gap: 16px; margin-bottom: 4px;
}
.pdex-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.pdex-subtitle { color: #8b949e; font-size: 0.85rem; margin: 0; }

.progress-wrap {
    background: #161b22; border: 1px solid #30363d; border-radius: 16px;
    padding: 16px 20px; margin-bottom: 20px;
}
.progress-row {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 8px;
}
.progress-count { font-size: 2rem; font-weight: 800; color: #B8F82F; }
.progress-total { color: #8b949e; font-size: 0.9rem; }
.progress-pct   { color: #e6edf3; font-size: 1rem; font-weight: 600; }
.progress-bar-bg {
    background: #0d1117; border-radius: 8px; height: 10px; overflow: hidden;
}
.progress-bar-fill {
    height: 100%; border-radius: 8px;
    background: linear-gradient(90deg, #7AB21A, #B8F82F);
    transition: width 0.4s ease;
}

/* Grade de cards */
.pdex-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
    gap: 8px;
    margin-top: 8px;
}
.pdex-card {
    background: #161b22;
    border-radius: 10px;
    padding: 8px 4px 6px;
    text-align: center;
    border: 2px solid #21262d;
    transition: transform 0.15s ease, border-color 0.15s ease;
    position: relative;
    cursor: default;
}
.pdex-card:hover { transform: translateY(-3px); }
.pdex-card.captured { border-color: transparent; }
.pdex-card.captured:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.4); }

.pdex-num {
    font-size: 0.6rem; color: #484f58; font-weight: 600;
    letter-spacing: 0.5px; margin-bottom: 2px;
}
.pdex-img-wrap {
    width: 56px; height: 56px; margin: 0 auto 4px;
    display: flex; align-items: center; justify-content: center;
}
.pdex-img-wrap img { width: 56px; height: 56px; image-rendering: pixelated; }

/* Silhueta para não capturados */
.pdex-silhouette {
    width: 56px; height: 56px; margin: 0 auto 4px;
    background: #21262d; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; color: #30363d;
}
.pdex-name {
    font-size: 0.62rem; color: #e6edf3; font-weight: 500;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    padding: 0 2px;
}
.pdex-name.unknown { color: #30363d; }

.type-pip {
    display: inline-block; border-radius: 9999px;
    font-size: 0.5rem; font-weight: 700; letter-spacing: 0.5px;
    padding: 2px 6px; margin: 2px 1px 0; text-transform: uppercase;
}

/* Contadores de geração */
.gen-row {
    display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
}
.gen-chip {
    background: #161b22; border: 1px solid #30363d; border-radius: 9999px;
    padding: 3px 12px; font-size: 0.7rem; color: #8b949e;
}
.gen-chip span { color: #B8F82F; font-weight: 700; font-family: "JetBrains Mono", monospace; }

.filter-label {
    font-size: 0.75rem; color: #8b949e; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
}

.region-badge {
    display: inline-block; border-radius: 9999px;
    font-size: 0.48rem; font-weight: 700; letter-spacing: 0.5px;
    padding: 1px 5px; margin-top: 2px; text-transform: uppercase;
    background: #30363d; color: #c9d1d9;
}
</style>
""", unsafe_allow_html=True)

# ── Dados ────────────────────────────────────────────────────────────────────────

with st.spinner("Carregando Pokédex..."):
    all_pokemon  = get_all_pokemon_with_types()
    captured_ids = get_cached_user_pokemon_ids(st.session_state.user_id)
total = len(all_pokemon)

# ── single-pass: contadores globais e por geração ──────────────────────────
_gen_totals: dict[str, int] = {}
_gen_captured: dict[str, int] = {}
captured_n = 0
reg_total = 0
reg_captured = 0
for _p in all_pokemon:
    _pid = _p["id"]
    _cap = _pid in captured_ids
    if _cap:
        captured_n += 1
    if _pid > 10000:
        reg_total += 1
        if _cap:
            reg_captured += 1
    else:
        for _lbl, (_lo, _hi) in GENERATIONS.items():
            if _lo <= _pid <= _hi:
                _gen_totals[_lbl] = _gen_totals.get(_lbl, 0) + 1
                if _cap:
                    _gen_captured[_lbl] = _gen_captured.get(_lbl, 0) + 1
                break
pct = (captured_n / total * 100) if total else 0

# ── Header ───────────────────────────────────────────────────────────────────────

st.markdown("""
<div class='pdex-header'>
  <div>
    <p class='pdex-title'>MINHA POKÉDEX</p>
    <p class='pdex-subtitle'>REGISTRO PESSOAL DE CAPTURAS</p>
  </div>
</div>
""", unsafe_allow_html=True)

# Barra de progresso geral
bar_w = f"{pct:.1f}%"
st.markdown(f"""
<div class='progress-wrap'>
  <div class='progress-row'>
    <div>
      <span class='progress-count'>{captured_n}</span>
      <span class='progress-total'> / {total} capturados</span>
    </div>
    <span class='progress-pct'>{pct:.1f}%</span>
  </div>
  <div class='progress-bar-bg'>
    <div class='progress-bar-fill' style='width:{bar_w}'></div>
  </div>
</div>
""", unsafe_allow_html=True)

# Chips por geração
gen_chips_html = "<div class='gen-row'>"
for label in GENERATIONS:
    g_tot = _gen_totals.get(label, 0)
    g_cap = _gen_captured.get(label, 0)
    short = label.split(" ")[0] + " " + label.split(" ")[1]
    gen_chips_html += (
        f"<div class='gen-chip'>{short} "
        f"<span>{g_cap}/{g_tot}</span></div>"
    )
gen_chips_html += (
    f"<div class='gen-chip'>Regionais "
    f"<span>{reg_captured}/{reg_total}</span></div>"
)
gen_chips_html += "</div>"
st.markdown(gen_chips_html, unsafe_allow_html=True)

# ── Helpers de renderização ──────────────────────────────────────────────────────

_REGION_COLORS = {
    "Alola":  ("#FF9B00", "#000"),
    "Galar":  ("#9B59B6", "#fff"),
    "Hisui":  ("#2E86AB", "#fff"),
}

def _region_from_sprite(pokemon_id: int, sprite_url: str | None) -> str:
    if pokemon_id <= 10000 or not sprite_url:
        return ""
    m = re.search(r'/(\d{4})-(Alola|Galar|Hisui)\.png', sprite_url)
    return m.group(2) if m else ""


def _num_str(pokemon_id: int, sprite_url: str | None) -> str:
    if pokemon_id <= 10000:
        return f"#{str(pokemon_id).zfill(4)}"
    m = re.search(r'/(\d{4})-\w+\.png', sprite_url or "")
    return f"#{m.group(1)}" if m else f"#{pokemon_id}"


def _thumb_src(pokemon_id: int, sprite_url: str | None = None) -> str | None:
    if sprite_url and sprite_url.startswith("http"):
        return sprite_url
    path = os.path.join(
        BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
        f"{str(pokemon_id).zfill(4)}.png",
    )
    return path


def _type_pip(type_name: str | None, type_slug: str | None) -> str:
    if not type_name or not type_slug:
        return ""
    c  = get_type_color(type_slug)
    bg = c["bg"]
    fg = c["text"]
    return (
        f"<span class='type-pip' style='background:{bg};color:{fg}'>"
        f"{type_name}</span>"
    )


# ── Filtros + Grade (fragment: só esta seção reroda ao mudar filtros) ────────────

@st.fragment
def _render_filters_and_grid(all_pkm: list, cap_ids: set) -> None:
    col_search, col_type, col_status = st.columns([2, 2, 1])

    with col_search:
        st.markdown("<div class='filter-label'>Buscar</div>", unsafe_allow_html=True)
        search = st.text_input(
            "Buscar", label_visibility="collapsed",
            placeholder="Nome ou número...", key="pdex_search"
        )

    with col_type:
        st.markdown("<div class='filter-label'>Tipo</div>", unsafe_allow_html=True)
        type_filter = st.multiselect(
            "Tipo", ALL_TYPES, label_visibility="collapsed",
            placeholder="Todos os tipos", key="pdex_types"
        )

    with col_status:
        st.markdown("<div class='filter-label'>Status</div>", unsafe_allow_html=True)
        status = st.radio(
            "Status", ["Todos", "✅ Capturados", "❌ Não capturados"],
            label_visibility="collapsed", key="pdex_status"
        )

    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)

    # ── Single-pass filter ────────────────────────────────────────────────────
    q          = search.strip().lower()
    type_slugs = {t.lower() for t in type_filter} if type_filter else None
    cap_only   = status == "✅ Capturados"
    notcap_only = status == "❌ Não capturados"

    filtered = [
        p for p in all_pkm
        if (not q or q in p["name"].lower() or q == str(p["id"]))
        and (not type_slugs or (p["type1_slug"] or "") in type_slugs or (p["type2_slug"] or "") in type_slugs)
        and (not cap_only or p["id"] in cap_ids)
        and (not notcap_only or p["id"] not in cap_ids)
    ]

    result_count = len(filtered)
    st.markdown(
        f"<div style='color:#8b949e;font-size:0.8rem;margin-bottom:8px'>"
        f"{result_count} Pokémon encontrado{'s' if result_count != 1 else ''}</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("Nenhum Pokémon corresponde aos filtros selecionados.")
        return

    cards_html = "<div class='pdex-grid'>"

    for p in filtered:
        pid         = p["id"]
        sprite_url  = p.get("sprite_url")
        is_captured = pid in cap_ids
        pnum_str    = _num_str(pid, sprite_url)
        t1_pip      = _type_pip(p["type1"], p["type1_slug"])
        t2_pip      = _type_pip(p["type2"], p["type2_slug"])
        region      = _region_from_sprite(pid, sprite_url)

        if is_captured:
            thumb = _thumb_src(pid, sprite_url)
            pname = p["name"]
            img_tag = sprite_img_tag(thumb, width=56) if thumb else ""
            if img_tag:
                img_html = f"<div class='pdex-img-wrap'>{img_tag}</div>"
            else:
                img_html = "<div class='pdex-img-wrap' style='font-size:1.8rem'>❓</div>"

            region_html = ""
            if region:
                rbg, rfg = _REGION_COLORS.get(region, ("#30363d", "#c9d1d9"))
                region_html = (
                    f"<div><span class='region-badge' "
                    f"style='background:{rbg};color:{rfg}'>{region}</span></div>"
                )

            c      = get_type_color(p["type1_slug"])
            border = c["bg"]
            card   = (
                f"<div class='pdex-card captured' "
                f"style='border-color:{border};background:linear-gradient("
                f"180deg,{border}22 0%,#161b22 40%)'>"
                f"<div class='pdex-num'>{pnum_str}</div>"
                f"{img_html}"
                f"<div class='pdex-name'>{pname}</div>"
                f"<div>{t1_pip}{t2_pip}</div>"
                f"{region_html}"
                f"</div>"
            )
        else:
            card = (
                f"<div class='pdex-card'>"
                f"<div class='pdex-num'>{pnum_str}</div>"
                f"<div class='pdex-silhouette'>?</div>"
                f"<div class='pdex-name unknown'>???</div>"
                f"<div style='height:14px'></div>"
                f"</div>"
            )

        cards_html += card

    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)


_render_filters_and_grid(all_pokemon, captured_ids)
