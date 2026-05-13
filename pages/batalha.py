import streamlit as st
from utils.app_cache import (
    clear_user_cache,
    get_cached_battle_opponents,
    get_cached_daily_battle_count,
    get_cached_user_profile,
    get_cached_user_team,
)
from utils.db import (
    start_battle, finalize_battle,
    get_image_as_base64, sprite_img_tag, _MAX_BATTLES_PER_DAY, _calc_damage, _best_move, _MAX_TURNS,
    _type_effectiveness, check_and_award_achievements, update_mission_progress,
)
from utils.quest_tracker import render_quest_sidebar

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.battle-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 20px; padding: 20px 24px; margin-bottom: 20px;
    border: 1px solid #e94560;
}
.battle-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #e94560, #ff8099);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.battle-sub    { font-size: 0.85rem; color: #8b949e; margin: 4px 0 0 0; }
.counter-badge {
    display: inline-flex; align-items: center;
    padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 0.78rem;
    letter-spacing: 0.5px; text-transform: uppercase;
}
.counter-ok    { background: rgba(47,158,68,0.15); color: #69db7c; border: 1px solid rgba(47,158,68,0.5); }
.counter-warn  { background: rgba(232,89,12,0.15); color: #ffa94d; border: 1px solid rgba(232,89,12,0.5); }
.counter-full  { background: rgba(233,69,96,0.15); color: #ff8099; border: 1px solid rgba(233,69,96,0.4); }
.fighter-card  {
    background: #161b22; border-radius: 16px; padding: 16px;
    border: 1px solid #30363d; text-align: center;
    transition: all 0.2s ease;
}
.fighter-name  { font-size: 1rem; font-weight: 700; color: #e6edf3; margin: 6px 0 2px 0; }
.fighter-level { font-size: 0.75rem; color: #8b949e; font-family: "JetBrains Mono", monospace; }
.hp-bar-bg     {
    background: #21262d; border-radius: 9999px; height: 8px; margin: 8px 0;
    border: 1px solid #30363d; overflow: hidden;
}
.hp-bar-fill   { height: 8px; border-radius: 9999px; transition: width 0.4s ease; }
.vs-badge      {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    color: #e94560; text-align: center; padding-top: 30px;
}
.turn-log      {
    background: #0d1117; border-radius: 16px; padding: 12px 16px;
    max-height: 200px; overflow-y: auto; margin-top: 12px;
    border: 1px solid #21262d;
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 0.72rem; color: #D4FC6B;
}
.turn-row-ch   { color: #58A6FF; margin: 4px 0; }
.turn-row-op   { color: #e94560; margin: 4px 0; }
.result-win    { background: linear-gradient(135deg,#1a472a,#2d6a3f); border: 1px solid #2f9e44; border-radius: 16px; padding: 24px; text-align: center; }
.result-loss   { background: linear-gradient(135deg,#3b1219,#6b2131); border: 1px solid #e94560; border-radius: 16px; padding: 24px; text-align: center; }
.result-draw   { background: linear-gradient(135deg,#161b22,#1a1f35); border: 1px solid #484f58; border-radius: 16px; padding: 24px; text-align: center; }
.result-title  {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px; margin: 0;
}
.reward-chip   { display: inline-block; margin: 4px; padding: 5px 14px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; }
.move-type-ph  { background: rgba(245,172,120,0.15); color: #F5AC78; border: 1px solid rgba(245,172,120,0.4); }
.move-type-sp  { background: rgba(157,183,245,0.15); color: #9DB7F5; border: 1px solid rgba(157,183,245,0.4); }
.move-type-st  { background: rgba(167,219,141,0.15); color: #A7DB8D; border: 1px solid rgba(167,219,141,0.4); }
</style>
""", unsafe_allow_html=True)

user_id = st.session_state.user_id
profile = get_cached_user_profile(user_id)
coins   = profile["coins"] if profile else 0

# ── Sidebar quest tracker ──────────────────────────────────────────────────────
with st.sidebar:
    render_quest_sidebar(user_id)

# ── Header ─────────────────────────────────────────────────────────────────────
daily_count = get_cached_daily_battle_count(user_id)
remaining   = _MAX_BATTLES_PER_DAY - daily_count

if remaining == 0:
    ctr_cls, ctr_txt = "counter-full", f"0/{_MAX_BATTLES_PER_DAY} batalhas restantes"
elif remaining == 1:
    ctr_cls, ctr_txt = "counter-warn", f"1/{_MAX_BATTLES_PER_DAY} batalha restante"
else:
    ctr_cls, ctr_txt = "counter-ok",   f"{remaining}/{_MAX_BATTLES_PER_DAY} batalhas restantes"

st.markdown(f"""
<div class="battle-header">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <p class="battle-title">🥊 ARENA</p>
      <p class="battle-sub">Slot 1 vs slot 1 · você escolhe os golpes · oponente usa melhor golpe</p>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="counter-badge {ctr_cls}">{ctr_txt}</span>
      <span style="display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,#FFC531,#B38200);border-radius:9999px;padding:6px 14px;font-size:0.85rem;font-weight:800;color:#0d1117;">🪙 {coins:,}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de UI
# ══════════════════════════════════════════════════════════════════════════════

def _hp_color(pct: int) -> str:
    if pct > 50: return "#B8F82F"
    if pct > 20: return "#FFC531"
    return "#e94560"


def _fighter_card(poke: dict, label: str, is_winner: bool):
    pct    = int(poke["hp"] / max(1, poke["max_hp"]) * 100)
    border = "2px solid #FFC531" if is_winner else "1px solid #30363d"
    glow   = "box-shadow:0 0 0 1px #FFC531,0 8px 24px rgba(255,197,49,0.25);" if is_winner else ""
    img_tag = (
        sprite_img_tag(poke["sprite_url"], width=80,
                       extra_style="image-rendering:pixelated;margin:8px 0")
        or "<div style='font-size:3rem;margin:8px 0'>❓</div>"
    )
    col    = _hp_color(pct)
    return f"""
    <div class="fighter-card" style="border:{border};{glow}">
      <div style="font-size:0.62rem;color:#8b949e;text-transform:uppercase;letter-spacing:2px;font-weight:700;">{label}</div>
      {img_tag}
      <p class="fighter-name">{poke['name']}</p>
      <p class="fighter-level">Lv.{poke['level']}</p>
      <div style="display:flex;justify-content:space-between;font-size:0.62rem;margin-top:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">
        <span style="color:#8b949e;">HP</span>
        <span style="color:{col};font-family:'JetBrains Mono',monospace;">{poke['hp']}/{poke['max_hp']}</span>
      </div>
      <div class="hp-bar-bg">
        <div class="hp-bar-fill" style="width:{pct}%;background:{col};"></div>
      </div>
    </div>
    """


def _move_class_badge(dmg_class: str) -> str:
    if dmg_class == "physical": return "move-type-ph", "FÍS"
    if dmg_class == "special":  return "move-type-sp", "ESP"
    return "move-type-st", "STA"


def _effectiveness_label(mult: float) -> str:
    if mult == 0:    return "🚫 Não afeta!"
    if mult >= 4:    return "🔥🔥 É superefeticaz!!"
    if mult >= 2:    return "🔥 É supereficaz!"
    if mult <= 0.25: return "❄️ Não é muito eficaz..."
    if mult <= 0.5:  return "❄️ Não é muito eficaz..."
    return ""


def _resolve_turn(state: dict, ch_move: dict) -> dict:
    """Processa um turno completo: ataque do jogador + resposta do oponente."""
    ch  = state["ch"]
    op  = state["op"]
    state["turn_num"] += 1
    turn = state["turn_num"]

    op_move = _best_move(op["moves"])
    ch_first = ch["stat_speed"] >= op["stat_speed"]

    events = []

    def _attack(attacker, defender, move, is_ch):
        if not move["power"]:
            events.append({"attacker_id": attacker["id"], "is_ch": is_ch,
                           "move_name": move["name"], "move_power": 0, "damage": 0,
                           "critical": False, "effectiveness": 1.0, "stab": False,
                           "label": ""})
            return

        if move["damage_class"] == "physical":
            atk  = attacker["stat_attack"]
            defs = defender["stat_defense"]
        else:
            atk  = attacker["stat_sp_attack"]
            defs = defender["stat_sp_defense"]

        att_types = (attacker.get("type1_id"), attacker.get("type2_id"))
        def_types = (defender.get("type1_id"), defender.get("type2_id"))

        result = _calc_damage(atk, defs, move["power"], attacker["level"],
                              move_type_id=move.get("type_id"),
                              attacker_types=att_types,
                              defender_types=def_types)
        dmg = result["damage"]

        if is_ch:
            op["hp"] = max(0, op["hp"] - dmg)
        else:
            ch["hp"] = max(0, ch["hp"] - dmg)

        label = _effectiveness_label(result["effectiveness"])
        if result["critical"]:
            label = ("⚡ Acerto crítico! " + label).strip()
        if result["stab"]:
            label = (label + " ✨STAB").strip() if label else "✨ STAB"

        events.append({
            "attacker_id": attacker["id"], "is_ch": is_ch,
            "move_name": move["name"], "move_power": move["power"], "damage": dmg,
            "critical": result["critical"], "effectiveness": result["effectiveness"],
            "stab": result["stab"], "label": label,
        })

    first_attacker  = (ch, op, ch_move, True)  if ch_first else (op, ch, op_move, False)
    second_attacker = (op, ch, op_move, False) if ch_first else (ch, op, ch_move, True)

    _attack(*first_attacker)
    if ch["hp"] > 0 and op["hp"] > 0:
        _attack(*second_attacker)

    for ev in events:
        state["turns"].append({
            "turn": turn, "attacker_id": ev["attacker_id"],
            "move_name": ev["move_name"], "move_power": ev["move_power"],
            "damage": ev["damage"], "ch_hp": ch["hp"], "op_hp": op["hp"],
            "label": ev.get("label", ""),
        })

    if ch["hp"] <= 0 or op["hp"] <= 0 or turn >= _MAX_TURNS:
        state["finished"] = True
        if ch["hp"] > op["hp"]:
            state["result"] = "challenger_win"
            state["winner_id"] = state["challenger_id"]
        elif op["hp"] > ch["hp"]:
            state["result"] = "opponent_win"
            state["winner_id"] = state["opponent_id"]
        else:
            state["result"] = "draw"
            state["winner_id"] = None

    return state


# ══════════════════════════════════════════════════════════════════════════════
# Estado da batalha
# ══════════════════════════════════════════════════════════════════════════════

bs = st.session_state.get("battle_state")

# ── Sem batalha ativa → seleção de oponente ────────────────────────────────────
if bs is None:
    if remaining == 0:
        st.warning("Você usou todas as batalhas de hoje. Volte amanhã!")
    else:
        _team = get_cached_user_team(user_id)
        if not any(m["slot"] == 1 for m in _team):
            st.warning("Você precisa ter um Pokémon no slot 1 da equipe para batalhar.")
            st.stop()

        st.subheader("Desafiar oponente")
        opponents = get_cached_battle_opponents(user_id)

        if not opponents:
            st.info("Nenhum outro treinador disponível ainda.")
        else:
            opts = {
                f"{o['username']} — {o['pokemon_name']} Lv.{o['level']}": o["user_id"]
                for o in opponents
            }
            col_sel, col_btn = st.columns([4, 1])
            with col_sel:
                chosen = st.selectbox("Oponente", list(opts.keys()),
                                      label_visibility="collapsed")
            with col_btn:
                if st.button("⚔️ Batalhar", use_container_width=True, type="primary"):
                    result = start_battle(user_id, opts[chosen])
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state.battle_state  = result
                        st.session_state.battle_saved  = False
                        st.rerun()

# ── Batalha em andamento ───────────────────────────────────────────────────────
elif not bs["finished"]:
    ch = bs["ch"]
    op = bs["op"]

    # Cards dos pokémon
    col1, col2, col3 = st.columns([5, 1, 5])
    with col1:
        st.markdown(_fighter_card(ch, "Seu Pokémon", False), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(_fighter_card(op, "Oponente", False), unsafe_allow_html=True)

    st.markdown(f"<p style='text-align:center;color:#8892b0;margin:8px 0;'>Turno {bs['turn_num'] + 1}</p>",
                unsafe_allow_html=True)

    # Seleção de golpe
    st.markdown("**Escolha seu golpe:**")
    move_cols = st.columns(len(ch["moves"]))
    chosen_move = None

    for i, (col, move) in enumerate(zip(move_cols, ch["moves"])):
        with col:
            badge_cls, badge_txt = _move_class_badge(move["damage_class"])
            power_info = f"Poder: {move['power']}" if move["power"] else "—"
            label = f"{move['name']}\n{power_info}"
            if st.button(label, key=f"move_{i}", use_container_width=True):
                chosen_move = move

    if chosen_move:
        st.session_state.battle_state = _resolve_turn(bs, chosen_move)
        st.rerun()

    if st.button("🏳 Render-se"):
        bs["finished"] = True
        bs["result"]   = "opponent_win"
        bs["winner_id"] = bs["opponent_id"]
        st.session_state.battle_state = bs
        st.rerun()

# ── Batalha finalizada → resultado ────────────────────────────────────────────
else:
    ch = bs["ch"]
    op = bs["op"]

    # Salva no banco apenas uma vez
    if not st.session_state.get("battle_saved"):
        saved = finalize_battle(bs)
        clear_user_cache(user_id)
        st.session_state.battle_saved        = True
        st.session_state.battle_result       = saved
        st.session_state.battle_daily_count  = get_cached_daily_battle_count(user_id)
        new_ach = check_and_award_achievements(user_id)
        if new_ach:
            pending = st.session_state.get("new_achievements_pending", [])
            seen = {a["slug"] for a in pending}
            st.session_state.new_achievements_pending = pending + [a for a in new_ach if a["slug"] not in seen]
        if saved and saved.get("winner_id") == user_id:
            _m_done = update_mission_progress(user_id, "battle_win")
            for _md in (_m_done or []):
                st.toast(f"🎯 Missão concluída: {_md.get('icon','')} {_md.get('label','')} — {_md.get('reward_label','')}", icon="✅")

    saved = st.session_state.get("battle_result", {})
    winner_id = bs["winner_id"]

    if bs["result"] == "draw":
        res_cls, res_icon, res_txt = "result-draw", "🤝", "Empate!"
    elif winner_id == user_id:
        res_cls, res_icon, res_txt = "result-win",  "🏆", "Vitória!"
    else:
        res_cls, res_icon, res_txt = "result-loss", "💀", "Derrota!"

    ch_xp = saved.get("ch_xp", 0)
    coins_earned = saved.get("coins_earned", 0) if winner_id == user_id else 0
    lvl_up = saved.get("ch_xp_result", {}).get("levels_gained", 0) if "ch_xp_result" in saved else 0

    rewards_html = f'<span class="reward-chip" style="background:rgba(184,248,47,0.12);color:#B8F82F;border:1px solid rgba(184,248,47,0.4);">+{ch_xp} XP</span>'
    if coins_earned:
        rewards_html += f'<span class="reward-chip" style="background:rgba(255,197,49,0.12);color:#FFC531;border:1px solid rgba(255,197,49,0.4);">+{coins_earned} 🪙</span>'
    if lvl_up:
        rewards_html += f'<span class="reward-chip" style="background:rgba(188,140,255,0.12);color:#BC8CFF;border:1px solid rgba(188,140,255,0.4);">+{lvl_up} nível!</span>'

    st.markdown(f"""
    <div class="{res_cls}" style="margin-bottom:20px;">
      <p class="result-title">{res_icon} {res_txt}</p>
      <p style="color:#8b949e;margin:6px 0;font-size:0.85rem;">{bs['turn_num']} turnos · {ch['name']} vs {op['name']}</p>
      <div style="margin-top:12px;">{rewards_html}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([5, 1, 5])
    with col1:
        st.markdown(_fighter_card(ch, "Seu Pokémon", winner_id == user_id), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(_fighter_card(op, "Oponente", winner_id == bs["opponent_id"]),
                    unsafe_allow_html=True)

    # ── Log de combate ────────────────────────────────────────────────────────
    turns = bs.get("turns", [])
    if turns:
        ch_id = ch["id"]
        rows_html = ""
        for ev in turns:
            is_challenger = ev["attacker_id"] == ch_id
            row_cls  = "turn-row-ch" if is_challenger else "turn-row-op"
            attacker = ch["name"] if is_challenger else op["name"]
            defender = op["name"] if is_challenger else ch["name"]
            def_hp   = ev["op_hp"] if is_challenger else ev["ch_hp"]
            dmg_txt  = f"(-{ev['damage']} HP)" if ev["damage"] else "(sem dano)"
            label    = f" {ev['label']}" if ev.get("label") else ""
            rows_html += (
                f'<p class="{row_cls}">T{ev["turn"]} {attacker} usou '
                f'<strong>{ev["move_name"]}</strong> {dmg_txt} '
                f'→ {defender} HP: {def_hp}{label}</p>'
            )
        st.markdown(
            f'<div class="turn-log">{rows_html}</div>',
            unsafe_allow_html=True,
        )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔄 Nova batalha", use_container_width=True):
            del st.session_state.battle_state
            st.session_state.pop("battle_saved", None)
            st.session_state.pop("battle_result", None)
            st.rerun()
    with btn_col2:
        fresh_count      = st.session_state.get("battle_daily_count", daily_count)
        rematch_disabled = (_MAX_BATTLES_PER_DAY - fresh_count) <= 0
        if st.button(
            f"⚔️ Revanche vs {op['name']}",
            use_container_width=True,
            type="primary",
            disabled=rematch_disabled,
        ):
            opponent_id = bs["opponent_id"]
            del st.session_state.battle_state
            st.session_state.pop("battle_saved", None)
            st.session_state.pop("battle_result", None)
            result = start_battle(user_id, opponent_id)
            if "error" in result:
                st.error(result["error"])
            else:
                st.session_state.battle_state = result
                st.session_state.battle_saved = False
                st.rerun()
