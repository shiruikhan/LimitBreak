import os
import streamlit as st
from utils.db import (
    get_user_team, get_user_profile, swap_team_slots,
    remove_from_team, get_image_as_base64,
    get_available_moves, get_active_moves, equip_move, unequip_move,
)
from utils.type_colors import get_type_color

BASE_DIR   = os.getcwd()
XP_PER_LV  = 100   # XP needed = level * XP_PER_LV

# ── Helpers ────────────────────────────────────────────────────────────────────

def _thumb(pokemon_id: int) -> str | None:
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
                        f"{str(pokemon_id).zfill(4)}.png")
    return get_image_as_base64(path)

def _dmg_icon(damage_class: str | None) -> str:
    if not damage_class:
        return ""
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others",
                        "damage-category-icons", "1x", f"{damage_class.capitalize()}.png")
    b64 = get_image_as_base64(path)
    return f"<img src='data:image/png;base64,{b64}' width='18' style='vertical-align:middle'>" if b64 else ""

def _type_icon(type_name: str | None) -> str:
    if not type_name:
        return ""
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others",
                        "type-icons", "png", f"{type_name.lower()}.png")
    b64 = get_image_as_base64(path)
    return f"<img src='data:image/png;base64,{b64}' width='16' style='vertical-align:middle'>" if b64 else ""

def _xp_progress(level: int, xp: int) -> float:
    needed = level * XP_PER_LV
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
.page-sub { color: #8b949e; font-size: 0.85rem; margin-bottom: 20px; }

/* Team card */
.team-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 16px;
    padding: 16px 12px; transition: all 0.2s ease; min-height: 200px;
}
.team-card.main-slot {
    border-color: #78C850;
    box-shadow: 0 0 0 1px #78C850, 0 8px 24px rgba(120,200,80,0.15);
}
.team-card.selected-slot {
    border-color: #58a6ff;
    box-shadow: 0 0 0 1px #58a6ff, 0 8px 24px rgba(88,166,255,0.15);
}
.team-card.empty-slot {
    border: 2px dashed #21262d; background: #0d1117;
    display: flex; align-items: center; justify-content: center;
}
.slot-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #8b949e; margin-bottom: 8px; }
.main-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; color: #78C850; text-transform: uppercase; }
.sel-label  { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; color: #58a6ff; text-transform: uppercase; }
.poke-card-name { font-size: 0.88rem; font-weight: 700; color: #e6edf3; margin: 4px 0 2px; text-align: center; }
.type-sm {
    display: inline-block; padding: 2px 7px; border-radius: 10px;
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase; margin-right: 3px;
}
.xp-track { background: #21262d; border-radius: 4px; height: 5px; margin-top: 8px; overflow: hidden; }
.xp-fill  { height: 100%; border-radius: 4px; background: linear-gradient(90deg,#4E8234,#78C850); }
.xp-label { font-size: 0.62rem; color: #8b949e; margin-top: 2px; }
.coins-badge {
    display: inline-flex; align-items: center; gap: 6px; background: #21262d;
    border-radius: 20px; padding: 6px 14px; font-weight: 700; font-size: 0.82rem; border: 1px solid #30363d;
}

/* Move panel */
.move-panel {
    background: #0d1117; border: 1px solid #21262d; border-radius: 16px;
    padding: 20px 24px; margin-top: 16px;
}
.move-panel-title {
    font-size: 1rem; font-weight: 800; letter-spacing: 1px; color: #e6edf3; margin-bottom: 16px;
}
.section-lbl {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e; margin-bottom: 10px;
}

/* Active move slot */
.move-slot {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 10px 14px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 10px;
}
.move-slot.empty-move {
    border: 1px dashed #30363d; background: #0d1117;
    justify-content: center; color: #8b949e; font-size: 0.8rem;
}
.move-slot-num {
    font-size: 0.65rem; font-weight: 700; color: #8b949e;
    min-width: 18px; text-align: center;
}
.move-slot-name { flex: 1; font-weight: 600; font-size: 0.88rem; color: #e6edf3; }
.move-stat { font-size: 0.68rem; color: #8b949e; text-align: center; min-width: 30px; }
.move-stat span { display: block; font-size: 0.58rem; text-transform: uppercase; }

/* Available move row */
.avail-move {
    display: flex; align-items: center; gap: 8px;
    background: #161b22; border-radius: 8px; padding: 7px 12px; margin-bottom: 6px;
    border-left: 3px solid #30363d;
}
.avail-move-lv   { font-size: 0.65rem; font-weight: 700; color: #8b949e; min-width: 32px; }
.avail-move-name { flex: 1; font-weight: 600; font-size: 0.85rem; color: #e6edf3; }
.avail-scroll { max-height: 380px; overflow-y: auto; padding-right: 4px; }
.avail-scroll::-webkit-scrollbar { width: 4px; }
.avail-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }

/* Replace mode highlight */
.replace-mode { border-color: #f8d030 !important; background: #1a1700 !important; }

.stButton > button { border-radius: 6px !important; }
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

# ── Session state defaults ─────────────────────────────────────────────────────
for k, v in [("sel_team_slot", None), ("replacing_move_id", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Data ───────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.error("Sessão expirada. Faça login novamente.")
    st.stop()

profile     = get_user_profile(user_id)
team        = get_user_team(user_id)
team_by_slot = {m["slot"]: m for m in team}

# ── Header ─────────────────────────────────────────────────────────────────────
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
        f"<span class='coins-badge'>🪙 {coins:,} moedas</span></div>",
        unsafe_allow_html=True,
    )

# ── 6 Team slots ───────────────────────────────────────────────────────────────
slot_cols = st.columns(3)
for slot in range(1, 7):
    col    = slot_cols[(slot - 1) % 3]
    member = team_by_slot.get(slot)
    is_sel = st.session_state.sel_team_slot == slot

    with col:
        if member:
            is_main = slot == 1
            if is_sel:
                card_cls = "team-card selected-slot"
                lbl_html = "<div class='sel-label'>▶ Selecionado</div>"
            elif is_main:
                card_cls = "team-card main-slot"
                lbl_html = "<div class='main-label'>★ Principal</div>"
            else:
                card_cls = "team-card"
                lbl_html = f"<div class='slot-label'>Slot {slot}</div>"

            b64     = _thumb(member["species_id"])
            img_tag = (f"<img src='data:image/png;base64,{b64}' width='72' style='display:block;margin:0 auto'>"
                       if b64 else "<div style='text-align:center;font-size:2.5rem'>❓</div>")

            c1 = get_type_color(member["type1"])
            c2 = get_type_color(member["type2"])
            t1 = (f"<span class='type-sm' style='background:{c1['bg']};color:{c1['text']}'>"
                  f"{member['type1'].upper()}</span>") if member["type1"] else ""
            t2 = (f"<span class='type-sm' style='background:{c2['bg']};color:{c2['text']}'>"
                  f"{member['type2'].upper()}</span>") if member["type2"] else ""

            prog     = _xp_progress(member["level"], member["xp"])
            needed   = member["level"] * XP_PER_LV

            st.markdown(
                f"<div class='{card_cls}'>{lbl_html}{img_tag}"
                f"<div class='poke-card-name'>#{member['species_id']} {member['name'].upper()}</div>"
                f"<div style='text-align:center'>{t1}{t2}</div>"
                f"<div style='text-align:center;font-size:0.78rem;color:#8b949e;margin-top:4px'>Lv. {member['level']}</div>"
                f"<div class='xp-track'><div class='xp-fill' style='width:{prog*100:.0f}%'></div></div>"
                f"<div class='xp-label'>{member['xp']} / {needed} XP</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            b1, b2, b3 = st.columns(3)
            with b1:
                label = "✕ Fechar" if is_sel else "⚔ Golpes"
                if st.button(label, key=f"sel_{slot}", use_container_width=True):
                    st.session_state.sel_team_slot   = None if is_sel else slot
                    st.session_state.replacing_move_id = None
                    st.rerun()
            with b2:
                if slot > 1:
                    if st.button("↑ Main", key=f"promote_{slot}", use_container_width=True):
                        swap_team_slots(user_id, 1, slot)
                        if st.session_state.sel_team_slot == slot:
                            st.session_state.sel_team_slot = 1
                        st.rerun()
            with b3:
                if st.button("🗑", key=f"remove_{slot}", use_container_width=True):
                    remove_from_team(user_id, slot)
                    if st.session_state.sel_team_slot == slot:
                        st.session_state.sel_team_slot = None
                    st.rerun()
        else:
            st.markdown(
                f"<div class='team-card empty-slot'>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:2rem;opacity:.2'>+</div>"
                f"<div style='color:#8b949e;font-size:0.72rem;margin-top:4px'>Slot {slot} vazio</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

# ── Move management panel ──────────────────────────────────────────────────────
sel_slot = st.session_state.sel_team_slot
if sel_slot and sel_slot in team_by_slot:
    member        = team_by_slot[sel_slot]
    up_id         = member["user_pokemon_id"]
    species_id    = member["species_id"]
    level         = member["level"]
    active_moves  = get_active_moves(up_id)
    avail_moves   = get_available_moves(species_id, level)
    active_by_slot = {m["slot"]: m for m in active_moves}
    active_ids     = {m["id"] for m in active_moves}
    replacing_id   = st.session_state.replacing_move_id  # move_id waiting to be slotted

    st.markdown(
        f"<div class='move-panel'>"
        f"<div class='move-panel-title'>⚔ GOLPES — {member['name'].upper()} Lv.{level}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1.6])

    # ── LEFT: active move slots ────────────────────────────────────────────────
    with left:
        st.markdown("<div class='section-lbl'>Golpes Ativos (máx. 4)</div>", unsafe_allow_html=True)

        if replacing_id:
            repl_name = next((m["name"] for m in avail_moves if m["id"] == replacing_id), "?")
            st.warning(f"Escolha o slot para **{repl_name}** ou clique em Cancelar.")
            if st.button("✕ Cancelar substituição", key="cancel_repl"):
                st.session_state.replacing_move_id = None
                st.rerun()

        for s in range(1, 5):
            mv = active_by_slot.get(s)
            is_replace_target = bool(replacing_id)

            if mv:
                tc        = get_type_color(mv["type_name"])
                type_ic   = _type_icon(mv["type_name"])
                dmg_ic    = _dmg_icon(mv["damage_class"])
                pow_str   = str(mv["power"]) if mv["power"] else "—"
                acc_str   = f"{mv['accuracy']}%" if mv["accuracy"] else "—"
                slot_cls  = "move-slot replace-mode" if is_replace_target else "move-slot"

                st.markdown(
                    f"<div class='{slot_cls}' style='border-left:3px solid {tc['bg']}'>"
                    f"<span class='move-slot-num'>{s}</span>"
                    f"<span class='move-slot-name'>{mv['name']}</span>"
                    f"{type_ic}"
                    f"<span class='move-stat'>{pow_str}<span>Pow</span></span>"
                    f"<span class='move-stat'>{acc_str}<span>Acc</span></span>"
                    f"{dmg_ic}</div>",
                    unsafe_allow_html=True,
                )
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if is_replace_target:
                        if st.button(f"↩ Slot {s}", key=f"repl_{up_id}_{s}", use_container_width=True):
                            equip_move(up_id, s, replacing_id)
                            st.session_state.replacing_move_id = None
                            st.rerun()
                with btn_c2:
                    if st.button(f"✕", key=f"unequip_{up_id}_{s}", use_container_width=True):
                        unequip_move(up_id, s)
                        st.rerun()
            else:
                slot_cls = "move-slot empty-move replace-mode" if is_replace_target else "move-slot empty-move"
                st.markdown(
                    f"<div class='{slot_cls}'>"
                    f"<span style='font-size:0.7rem;color:#8b949e'>Slot {s} — vazio</span></div>",
                    unsafe_allow_html=True,
                )
                if is_replace_target:
                    if st.button(f"+ Colocar no Slot {s}", key=f"fill_{up_id}_{s}", use_container_width=True):
                        equip_move(up_id, s, replacing_id)
                        st.session_state.replacing_move_id = None
                        st.rerun()

    # ── RIGHT: available moves ─────────────────────────────────────────────────
    with right:
        st.markdown(
            f"<div class='section-lbl'>Golpes Disponíveis — Lv ≤ {level} "
            f"({len(avail_moves)} golpes)</div>",
            unsafe_allow_html=True,
        )

        if not avail_moves:
            st.markdown("<span style='color:#8b949e;font-size:0.85rem'>Nenhum golpe disponível neste nível.</span>",
                        unsafe_allow_html=True)
        else:
            html = "<div class='avail-scroll'>"
            for mv in avail_moves:
                tc       = get_type_color(mv["type_name"])
                type_ic  = _type_icon(mv["type_name"])
                dmg_ic   = _dmg_icon(mv["damage_class"])
                pow_str  = str(mv["power"]) if mv["power"] else "—"
                acc_str  = f"{mv['accuracy']}%" if mv["accuracy"] else "—"
                is_active = mv["id"] in active_ids
                opacity  = "opacity:0.4;" if is_active else ""
                html += (
                    f"<div class='avail-move' style='border-left-color:{tc['bg']};{opacity}'>"
                    f"<span class='avail-move-lv'>Lv.{mv['level_learned_at']}</span>"
                    f"<span class='avail-move-name'>{mv['name']}</span>"
                    f"{type_ic}"
                    f"<span class='move-stat'>{pow_str}<span>Pow</span></span>"
                    f"<span class='move-stat'>{acc_str}<span>Acc</span></span>"
                    f"{dmg_ic}</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

            # Equip buttons rendered below the HTML block (Streamlit constraint)
            st.markdown("<div class='section-lbl' style='margin-top:12px'>Equipar golpe:</div>",
                        unsafe_allow_html=True)
            for mv in avail_moves:
                is_active = mv["id"] in active_ids
                col_name, col_btn = st.columns([3, 1])
                with col_name:
                    tc = get_type_color(mv["type_name"])
                    st.markdown(
                        f"<span style='font-size:0.82rem;color:{'#8b949e' if is_active else '#e6edf3'}'>"
                        f"Lv.{mv['level_learned_at']} {mv['name']}</span>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if is_active:
                        st.markdown("<small style='color:#8b949e'>✓ Ativo</small>", unsafe_allow_html=True)
                    else:
                        free_slot = next((s for s in range(1, 5) if s not in active_by_slot), None)
                        if free_slot:
                            if st.button("+ Equipar", key=f"eq_{up_id}_{mv['id']}", use_container_width=True):
                                equip_move(up_id, free_slot, mv["id"])
                                st.rerun()
                        else:
                            if st.button("↩ Trocar", key=f"repl_init_{up_id}_{mv['id']}", use_container_width=True):
                                st.session_state.replacing_move_id = mv["id"]
                                st.rerun()

elif not team:
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#8b949e'>"
        "<div style='font-size:3rem'>🎮</div>"
        "<div style='font-size:1.1rem;margin-top:12px'>Equipe vazia</div>"
        "<div style='font-size:0.85rem;margin-top:6px'>Sua equipe é formada durante o cadastro e ao capturar Pokémon na Pokédex.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
