import os
import streamlit as st

from utils.db import get_user_eggs, sprite_img_tag

BASE_DIR = os.getcwd()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Faça login para ver seus ovos.")
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #0d1117; color: #e6edf3; }

.eggs-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px; text-transform: uppercase;
}
.eggs-sub { color: #8b949e; font-size: 0.85rem; margin-bottom: 20px; }

.egg-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 18px 14px;
    text-align: center;
    transition: border-color 0.2s, transform 0.15s;
}
.egg-card:hover { border-color: #484f58; transform: translateY(-2px); }
.egg-card.rarity-uncommon { border-color: rgba(59,130,246,0.5); }
.egg-card.rarity-rare     { border-color: rgba(168,85,247,0.6); }

.egg-emoji { font-size: 2.6rem; line-height: 1; }

.egg-rarity {
    font-size: 0.6rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; margin: 8px 0 4px;
}
.egg-rarity.common   { color: #8b949e; }
.egg-rarity.uncommon { color: #58a6ff; }
.egg-rarity.rare     { color: #d2a8ff; }

.egg-progress-bg {
    background: #21262d; border-radius: 9999px; height: 8px;
    margin: 8px 0 4px; overflow: hidden; border: 1px solid #30363d;
}
.egg-progress-fill { height: 100%; border-radius: 9999px; }
.egg-progress-fill.common   { background: #4b5563; }
.egg-progress-fill.uncommon { background: #3b82f6; }
.egg-progress-fill.rare     { background: linear-gradient(90deg, #8b5cf6, #d946ef); }

.egg-count {
    font-size: 0.68rem; color: #8b949e; margin-bottom: 4px;
    font-family: "JetBrains Mono", monospace;
}
.egg-count span { color: #e6edf3; font-weight: 700; }

.egg-date {
    font-size: 0.6rem; color: #484f58; margin-top: 4px;
    font-family: "JetBrains Mono", monospace;
}

.egg-almost {
    font-size: 0.62rem; font-weight: 700; color: #B8F82F;
    margin-top: 6px; letter-spacing: 0.5px;
}

.egg-species {
    font-size: 0.72rem; font-weight: 700; color: #e6edf3; margin-top: 6px;
}
.egg-species-hint { color: #8b949e; font-size: 0.62rem; font-style: italic; }

.eggs-empty {
    text-align: center; padding: 48px 24px; color: #8b949e;
}
.eggs-empty-icon { font-size: 3.5rem; margin-bottom: 12px; }
.eggs-empty-title { font-size: 1rem; font-weight: 700; color: #e6edf3; margin-bottom: 8px; }
.eggs-empty-body  { font-size: 0.85rem; line-height: 1.6; max-width: 380px; margin: 0 auto; }

.eggs-tip {
    background: rgba(184,248,47,0.06); border: 1px solid rgba(184,248,47,0.18);
    border-radius: 12px; padding: 12px 16px; margin-bottom: 20px;
    font-size: 0.8rem; color: #8b949e; line-height: 1.5;
}
.eggs-tip strong { color: #B8F82F; }
</style>
""", unsafe_allow_html=True)

# ── Dados ──────────────────────────────────────────────────────────────────────
eggs = get_user_eggs(user_id)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("<div class='eggs-title'>OVOS EM INCUBAÇÃO</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='eggs-sub'>"
    f"{'Nenhum ovo pendente.' if not eggs else f'{len(eggs)} ovo(s) aguardando chocagem.'}"
    f"</div>",
    unsafe_allow_html=True,
)

# ── Dica ───────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='eggs-tip'>"
    "🥚 Ovos avançam a cada <strong>sessão de treino registrada</strong>. "
    "Ovos comuns chocam em <strong>5 treinos</strong>, incomuns em <strong>8</strong> e raros em <strong>12</strong>. "
    "A espécie só é revelada quando o ovo chocar."
    "</div>",
    unsafe_allow_html=True,
)

# ── Estado vazio ───────────────────────────────────────────────────────────────
if not eggs:
    st.markdown(
        "<div class='eggs-empty'>"
        "<div class='eggs-empty-icon'>🥚</div>"
        "<div class='eggs-empty-title'>Nenhum ovo em incubação</div>"
        "<div class='eggs-empty-body'>"
        "Você ganha ovos ao completar marcos de treino: "
        "<strong>25</strong>, <strong>50</strong> e <strong>100</strong> sessões registradas. "
        "Continue treinando para conquistar os próximos!"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("🏋️ Ir para Treino", use_container_width=False):
        st.switch_page("pages/treino.py")
    st.stop()

# ── Grade de ovos ──────────────────────────────────────────────────────────────
_rarity_emoji  = {"common": "⚪", "uncommon": "🔵", "rare": "🟣"}
_rarity_labels = {"common": "Comum", "uncommon": "Incomum", "rare": "Raro"}

COLS_PER_ROW = 4
rows = [eggs[i : i + COLS_PER_ROW] for i in range(0, len(eggs), COLS_PER_ROW)]

for row in rows:
    cols = st.columns(COLS_PER_ROW)
    for col, egg in zip(cols, row):
        with col:
            rar   = egg["rarity"]
            done  = egg["workouts_done"]
            total = egg["workouts_to_hatch"]
            pct   = min(done / total, 1.0) if total else 1.0
            emoji = _rarity_emoji.get(rar, "⚪")
            label = _rarity_labels.get(rar, rar.capitalize())
            remaining = total - done
            is_almost = remaining <= 2 and remaining > 0
            is_ready  = done >= total

            received_str = ""
            if egg.get("received_at"):
                try:
                    received_str = egg["received_at"].strftime("%d/%m/%Y")
                except Exception:
                    received_str = str(egg["received_at"])[:10]

            almost_html = ""
            if is_ready:
                almost_html = "<div class='egg-almost'>🔥 Pronto para chocar!</div>"
            elif is_almost:
                almost_html = f"<div class='egg-almost'>⚡ Falta {remaining} treino(s)!</div>"

            st.markdown(
                f"<div class='egg-card rarity-{rar}'>"
                f"<div class='egg-emoji'>🥚</div>"
                f"<div class='egg-rarity {rar}'>{emoji} {label}</div>"
                f"<div class='egg-progress-bg'>"
                f"<div class='egg-progress-fill {rar}' style='width:{pct*100:.0f}%'></div>"
                f"</div>"
                f"<div class='egg-count'><span>{done}</span>/{total} treinos</div>"
                f"{almost_html}"
                f"<div class='egg-date'>Recebido {received_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Spoiler toggle: mostra espécie apenas quando o usuário pede
            species_name = egg.get("species_name")
            if species_name:
                show_key = f"egg_spoiler_{egg['id']}"
                if st.checkbox("Revelar espécie", key=show_key):
                    sprite_url = egg.get("sprite_url", "")
                    img_html = sprite_img_tag(
                        sprite_url, width=56,
                        extra_style="image-rendering:pixelated;display:block;margin:4px auto",
                    )
                    st.markdown(
                        f"{img_html}"
                        f"<div class='egg-species'>{species_name}</div>",
                        unsafe_allow_html=True,
                    )

# ── Rodapé com atalhos ─────────────────────────────────────────────────────────
st.write("")
col_a, col_b = st.columns(2)
with col_a:
    if st.button("🏋️ Registrar Treino", use_container_width=True):
        st.switch_page("pages/treino.py")
with col_b:
    if st.button("⚔️ Ver Equipe", use_container_width=True):
        st.switch_page("pages/equipe.py")
