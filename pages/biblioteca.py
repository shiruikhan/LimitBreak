import streamlit as st
from utils.db import get_exercises, get_muscle_groups, get_distinct_body_parts
from utils.type_colors import get_type_color

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

# ── body_part → tipo Pokémon ──────────────────────────────────────────────────
_BODY_PART_TYPE: dict[str, str] = {
    "chest":      "fighting",
    "upper arms": "fighting",
    "lower arms": "normal",
    "back":       "dark",
    "shoulders":  "flying",
    "upper legs": "ground",
    "lower legs": "ground",
    "waist":      "steel",
    "neck":       "rock",
    "cardio":     "water",
    "Cardio":     "water",
}

_TYPE_PT: dict[str, str] = {
    "fighting": "Lutador",
    "normal":   "Normal",
    "dark":     "Sombrio",
    "flying":   "Voador",
    "ground":   "Terra",
    "steel":    "Aço",
    "rock":     "Pedra",
    "water":    "Água",
}

_BODY_PART_PT: dict[str, str] = {
    "chest":      "Peito",
    "upper arms": "Braços superiores",
    "lower arms": "Antebraços",
    "back":       "Costas",
    "shoulders":  "Ombros",
    "upper legs": "Coxas",
    "lower legs": "Pernas inferiores",
    "waist":      "Abdômen",
    "neck":       "Pescoço",
    "cardio":     "Cardio",
    "Cardio":     "Cardio",
}


def _dominant_type(body_parts: list[str] | None) -> str | None:
    if not body_parts:
        return None
    for bp in body_parts:
        if bp in _BODY_PART_TYPE:
            return _BODY_PART_TYPE[bp]
    return None


st.title("Biblioteca 📚")
st.caption("Catálogo de exercícios — clique em um card para ver detalhes.")

# ── filtros ───────────────────────────────────────────────────────────────────
col_search, col_bp, col_eq = st.columns([2, 2, 2])
with col_search:
    search = st.text_input("🔍 Buscar", placeholder="nome do exercício…", label_visibility="collapsed")
with col_bp:
    all_body_parts = get_distinct_body_parts()
    sel_bp = st.multiselect(
        "Parte do corpo",
        options=all_body_parts,
        format_func=lambda x: _BODY_PART_PT.get(x, x),
        placeholder="Parte do corpo…",
        label_visibility="collapsed",
    )
with col_eq:
    all_exercises = get_exercises()
    all_equip: list[str] = sorted({eq for ex in all_exercises for eq in (ex["equipments"] or [])})
    sel_eq = st.multiselect(
        "Equipamento",
        options=all_equip,
        placeholder="Equipamento…",
        label_visibility="collapsed",
    )

# ── filtrar lista ─────────────────────────────────────────────────────────────
exercises = all_exercises
if search:
    q = search.lower()
    exercises = [e for e in exercises if q in (e["name_pt"] or "").lower() or q in e["name"].lower()]
if sel_bp:
    exercises = [e for e in exercises if any(bp in (e["body_parts"] or []) for bp in sel_bp)]
if sel_eq:
    exercises = [e for e in exercises if any(eq in (e["equipments"] or []) for eq in sel_eq)]

st.markdown(f"**{len(exercises)}** exercícios encontrados")
st.divider()

# ── grade 4 colunas ───────────────────────────────────────────────────────────
COLS = 4
cols = st.columns(COLS)

for idx, ex in enumerate(exercises):
    col = cols[idx % COLS]
    with col:
        dom_type = _dominant_type(ex["body_parts"])
        tc = get_type_color(dom_type)
        bg = tc["bg"]
        text = tc["text"]
        type_label = _TYPE_PT.get(dom_type or "", dom_type or "?") if dom_type else "?"

        body_tags = " ".join(
            f'<span style="background:#eee;border-radius:4px;padding:1px 5px;font-size:10px;color:#555">'
            f'{_BODY_PART_PT.get(bp, bp)}</span>'
            for bp in (ex["body_parts"] or [])[:2]
        )

        with st.expander(ex["name_pt"] or ex["name"], expanded=False):
            # GIF
            if ex["gif_url"]:
                st.image(ex["gif_url"], use_container_width=True)

            # metric type badge + pokémon type badge + body part tags
            _mt      = ex.get("metric_type", "weight")
            _mt_data = {
                "weight":   ("🏋️", "Carga",     "#30363d", "#c9d1d9"),
                "distance": ("📏", "Distância",  "#0d4a8a", "#79c0ff"),
                "time":     ("⏱️", "Tempo",      "#2d4a1e", "#56d364"),
            }.get(_mt, ("🏋️", "Carga", "#30363d", "#c9d1d9"))
            _mt_icon, _mt_lbl, _mt_bg, _mt_text = _mt_data
            metric_badge = (
                f'<span style="background:{_mt_bg};color:{_mt_text};border-radius:6px;'
                f'padding:2px 8px;font-size:11px;font-weight:600;margin-right:4px">'
                f'{_mt_icon} {_mt_lbl}</span>'
            )
            st.markdown(
                f'{metric_badge}'
                f'<span style="background:{bg};color:{text};border-radius:6px;'
                f'padding:2px 8px;font-size:12px;font-weight:600">⚡ {type_label}</span> '
                f'{body_tags}',
                unsafe_allow_html=True,
            )

            st.write("")

            # target muscles
            muscles = ex["target_muscles"] or []
            if muscles:
                st.markdown("**Músculos alvo:**")
                st.write(", ".join(muscles))

            # equipment
            equips = ex["equipments"] or []
            if equips:
                st.markdown("**Equipamentos:**")
                st.write(", ".join(equips))

            # type affinity explanation
            if dom_type:
                first_bp = next((bp for bp in (ex["body_parts"] or []) if bp in _BODY_PART_TYPE), None)
                bp_pt = _BODY_PART_PT.get(first_bp or "", first_bp or "")
                st.info(
                    f"Exercícios de **{bp_pt}** invocam Pokémon do tipo **{type_label}**.",
                    icon="🎮",
                )
