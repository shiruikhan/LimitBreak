import os
import streamlit as st
from utils.db import get_all_pokemon_with_types, get_user_pokemon_ids, get_image_as_base64
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
    font-size: 2rem; font-weight: 900; letter-spacing: 3px;
    background: linear-gradient(90deg, #78C850, #A7DB8D);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.pdex-subtitle { color: #8b949e; font-size: 0.85rem; margin: 0; }

.progress-wrap {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 20px;
}
.progress-row {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 8px;
}
.progress-count { font-size: 2rem; font-weight: 800; color: #78C850; }
.progress-total { color: #8b949e; font-size: 0.9rem; }
.progress-pct   { color: #e6edf3; font-size: 1rem; font-weight: 600; }
.progress-bar-bg {
    background: #0d1117; border-radius: 8px; height: 10px; overflow: hidden;
}
.progress-bar-fill {
    height: 100%; border-radius: 8px;
    background: linear-gradient(90deg, #4E8234, #78C850);
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
    display: inline-block; border-radius: 4px;
    font-size: 0.5rem; font-weight: 700; letter-spacing: 0.5px;
    padding: 1px 5px; margin: 2px 1px 0; text-transform: uppercase;
}

/* Contadores de geração */
.gen-row {
    display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
}
.gen-chip {
    background: #161b22; border: 1px solid #30363d; border-radius: 20px;
    padding: 3px 10px; font-size: 0.72rem; color: #8b949e;
}
.gen-chip span { color: #78C850; font-weight: 700; }

.filter-label {
    font-size: 0.75rem; color: #8b949e; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Dados ────────────────────────────────────────────────────────────────────────

all_pokemon  = get_all_pokemon_with_types()
captured_ids = get_user_pokemon_ids(st.session_state.user_id)
total        = len(all_pokemon)
captured_n   = sum(1 for p in all_pokemon if p["id"] in captured_ids)
pct          = (captured_n / total * 100) if total else 0

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
for label, (lo, hi) in GENERATIONS.items():
    gen_total    = sum(1 for p in all_pokemon if lo <= p["id"] <= hi)
    gen_captured = sum(1 for p in all_pokemon if lo <= p["id"] <= hi and p["id"] in captured_ids)
    short = label.split(" ")[0] + " " + label.split(" ")[1]
    gen_chips_html += (
        f"<div class='gen-chip'>{short} "
        f"<span>{gen_captured}/{gen_total}</span></div>"
    )
gen_chips_html += "</div>"
st.markdown(gen_chips_html, unsafe_allow_html=True)

# ── Filtros ───────────────────────────────────────────────────────────────────────

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

# ── Filtragem ─────────────────────────────────────────────────────────────────────

filtered = all_pokemon

if search.strip():
    q = search.strip().lower()
    filtered = [
        p for p in filtered
        if q in p["name"].lower() or q == str(p["id"])
    ]

if type_filter:
    slugs = {t.lower() for t in type_filter}
    filtered = [
        p for p in filtered
        if (p["type1_slug"] or "") in slugs or (p["type2_slug"] or "") in slugs
    ]

if status == "✅ Capturados":
    filtered = [p for p in filtered if p["id"] in captured_ids]
elif status == "❌ Não capturados":
    filtered = [p for p in filtered if p["id"] not in captured_ids]

# ── Grade ──────────────────────────────────────────────────────────────────────────

def _thumb_b64(pokemon_id: int) -> str | None:
    path = os.path.join(
        BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
        f"{str(pokemon_id).zfill(4)}.png",
    )
    return get_image_as_base64(path)


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


result_count = len(filtered)
st.markdown(
    f"<div style='color:#8b949e;font-size:0.8rem;margin-bottom:8px'>"
    f"{result_count} Pokémon encontrado{'s' if result_count != 1 else ''}</div>",
    unsafe_allow_html=True,
)

if not filtered:
    st.info("Nenhum Pokémon corresponde aos filtros selecionados.")
else:
    cards_html = "<div class='pdex-grid'>"

    for p in filtered:
        pid        = p["id"]
        is_captured = pid in captured_ids
        num_str    = f"#{str(pid).zfill(4)}"
        t1_pip     = _type_pip(p["type1"], p["type1_slug"])
        t2_pip     = _type_pip(p["type2"], p["type2_slug"])

        if is_captured:
            b64      = _thumb_b64(pid)
            pname    = p["name"]
            if b64:
                img_html = (
                    f"<div class='pdex-img-wrap'>"
                    f"<img src='data:image/png;base64,{b64}' alt='{pname}'>"
                    f"</div>"
                )
            else:
                img_html = "<div class='pdex-img-wrap' style='font-size:1.8rem'>❓</div>"

            # Borda colorida pelo tipo primário
            c      = get_type_color(p["type1_slug"])
            border = c["bg"]
            card   = (
                f"<div class='pdex-card captured' "
                f"style='border-color:{border};background:linear-gradient("
                f"180deg,{border}22 0%,#161b22 40%)'>"
                f"<div class='pdex-num'>{num_str}</div>"
                f"{img_html}"
                f"<div class='pdex-name'>{pname}</div>"
                f"<div>{t1_pip}{t2_pip}</div>"
                f"</div>"
            )
        else:
            card = (
                f"<div class='pdex-card'>"
                f"<div class='pdex-num'>{num_str}</div>"
                f"<div class='pdex-silhouette'>?</div>"
                f"<div class='pdex-name unknown'>???</div>"
                f"<div style='height:14px'></div>"
                f"</div>"
            )

        cards_html += card

    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
