import os
import streamlit as st
from utils.db import (
    get_user_team, get_user_profile, swap_team_slots,
    remove_from_team, get_image_as_base64,
)
from utils.type_colors import get_type_color

BASE_DIR = os.getcwd()
XP_PER_LEVEL = 100  # XP necessário por nível (level * XP_PER_LEVEL para o próximo nível)


def _thumb(pokemon_id: int) -> str | None:
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "thumbnails", f"{str(pokemon_id).zfill(4)}.png")
    return get_image_as_base64(path)


def _xp_progress(level: int, xp: int) -> float:
    """Returns 0.0–1.0 progress toward next level."""
    needed = level * XP_PER_LEVEL
    return min(xp / needed, 1.0) if needed else 1.0


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #0d1117; color: #e6edf3; }
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

.page-title {
    font-size: 2rem; font-weight: 900; letter-spacing: 2px;
    background: linear-gradient(90deg, #78C850, #A7DB8D);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.page-sub { color: #8b949e; font-size: 0.85rem; margin-bottom: 28px; }

/* Team card */
.team-card {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 16px; padding: 20px 16px;
    position: relative; transition: all 0.2s ease;
    min-height: 220px;
}
.team-card.main-slot {
    border-color: #78C850;
    box-shadow: 0 0 0 1px #78C850, 0 8px 24px rgba(120,200,80,0.15);
}
.team-card.empty-slot {
    border: 2px dashed #21262d; background: #0d1117;
    display: flex; align-items: center; justify-content: center;
}
.slot-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e; margin-bottom: 10px;
}
.main-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    color: #78C850; text-transform: uppercase;
}
.poke-card-name {
    font-size: 0.95rem; font-weight: 700; color: #e6edf3;
    margin: 6px 0 2px;
}
.poke-card-level { font-size: 0.8rem; color: #8b949e; }

/* Type badge small */
.type-sm {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.5px;
    text-transform: uppercase; margin-right: 3px;
}

/* XP bar */
.xp-track {
    background: #21262d; border-radius: 4px; height: 6px;
    margin-top: 10px; overflow: hidden;
}
.xp-fill {
    height: 100%; border-radius: 4px;
    background: linear-gradient(90deg, #4E8234, #78C850);
    transition: width 0.4s ease;
}
.xp-label { font-size: 0.65rem; color: #8b949e; margin-top: 3px; }

/* Coins badge */
.coins-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #21262d; border-radius: 20px;
    padding: 6px 16px; font-weight: 700; font-size: 0.85rem;
    border: 1px solid #30363d;
}

/* Swap/remove buttons */
.stButton > button {
    font-size: 0.75rem !important; padding: 4px 10px !important;
    border-radius: 6px !important;
}
.action-row { display: flex; gap: 6px; margin-top: 10px; }

/* Empty slot icon */
.empty-icon { font-size: 2.5rem; opacity: 0.2; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    email = st.session_state.get("user")
    if hasattr(email, "email"):
        st.markdown(f"<small style='color:#8b949e'>👤 {email.email}</small>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("Sair", use_container_width=True):
        for k in ["user", "user_id", "access_token", "refresh_token", "needs_starter"]:
            st.session_state[k] = None
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")

if not user_id:
    st.error("Sessão expirada. Faça login novamente.")
    st.stop()

profile = get_user_profile(user_id)
team = get_user_team(user_id)
team_by_slot = {m["slot"]: m for m in team}

# Header
col_title, col_coins = st.columns([3, 1])
with col_title:
    st.markdown("<div class='page-title'>MINHA EQUIPE</div>", unsafe_allow_html=True)
    trainer = profile["username"] if profile else "Treinador"
    st.markdown(f"<div class='page-sub'>Treinador {trainer} · {len(team)}/6 Pokémon</div>",
                unsafe_allow_html=True)
with col_coins:
    coins = profile["coins"] if profile else 0
    st.markdown(
        f"<div style='text-align:right;margin-top:8px'>"
        f"<span class='coins-badge'>🪙 {coins:,} moedas</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── 6 team slots ──────────────────────────────────────────────────────────────
slot_cols = st.columns(3)
for slot in range(1, 7):
    col = slot_cols[(slot - 1) % 3]
    member = team_by_slot.get(slot)

    with col:
        is_main = slot == 1
        card_cls = "team-card main-slot" if is_main else "team-card"

        if member:
            b64 = _thumb(member["species_id"])
            img_tag = (
                f"<img src='data:image/png;base64,{b64}' width='80' style='display:block;margin:0 auto'>"
                if b64 else "<div style='text-align:center;font-size:3rem'>❓</div>"
            )

            c1 = get_type_color(member["type1"])
            c2 = get_type_color(member["type2"])
            t1_html = (
                f"<span class='type-sm' style='background:{c1['bg']};color:{c1['text']}'>"
                f"{member['type1'].upper()}</span>"
            ) if member["type1"] else ""
            t2_html = (
                f"<span class='type-sm' style='background:{c2['bg']};color:{c2['text']}'>"
                f"{member['type2'].upper()}</span>"
            ) if member["type2"] else ""

            prog = _xp_progress(member["level"], member["xp"])
            needed_xp = member["level"] * XP_PER_LEVEL

            main_tag = "<div class='main-label'>★ Principal</div>" if is_main else f"<div class='slot-label'>Slot {slot}</div>"

            st.markdown(
                f"<div class='{card_cls}'>"
                f"{main_tag}"
                f"{img_tag}"
                f"<div class='poke-card-name' style='text-align:center'>#{member['species_id']} {member['name'].upper()}</div>"
                f"<div style='text-align:center'>{t1_html}{t2_html}</div>"
                f"<div class='poke-card-level' style='text-align:center;margin-top:4px'>Lv. {member['level']}</div>"
                f"<div class='xp-track'><div class='xp-fill' style='width:{prog*100:.0f}%'></div></div>"
                f"<div class='xp-label'>{member['xp']} / {needed_xp} XP</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Action buttons
            btn_cols = st.columns([1, 1])
            with btn_cols[0]:
                if slot > 1:
                    if st.button("↑ Principal", key=f"promote_{slot}", use_container_width=True):
                        if swap_team_slots(user_id, 1, slot):
                            st.success("Pokémon definido como principal!")
                            st.rerun()
                        else:
                            st.error("Erro ao trocar.")
                else:
                    st.markdown("<small style='color:#78C850'>★ Principal</small>", unsafe_allow_html=True)

            with btn_cols[1]:
                if st.button("Remover", key=f"remove_{slot}", use_container_width=True):
                    if remove_from_team(user_id, slot):
                        st.rerun()
                    else:
                        st.error("Erro ao remover.")

        else:
            st.markdown(
                f"<div class='team-card empty-slot'>"
                f"<div style='text-align:center'>"
                f"<div class='empty-icon'>+</div>"
                f"<div style='color:#8b949e;font-size:0.75rem;margin-top:4px'>Slot {slot} vazio</div>"
                f"<div style='color:#8b949e;font-size:0.68rem'>Capture Pokémon na Pokédex</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

st.markdown("---")

# ── Tip ───────────────────────────────────────────────────────────────────────
if len(team) < 6:
    remaining = 6 - len(team)
    st.info(
        f"Você tem **{remaining} slot(s)** disponíveis na equipe. "
        f"Vá para a **Pokédex** e capture novos Pokémon para completar seu time!"
    )

if not team:
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#8b949e'>"
        "<div style='font-size:3rem'>🎮</div>"
        "<div style='font-size:1.1rem;margin-top:12px'>Equipe vazia</div>"
        "<div style='font-size:0.85rem;margin-top:6px'>Sua equipe é formada durante o cadastro e ao capturar Pokémon na Pokédex.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
