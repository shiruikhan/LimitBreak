import streamlit as st
from utils.db import (
    get_battle_opponents, get_daily_battle_count, start_battle, finalize_battle,
    get_battle_history, get_battle_detail, get_user_profile,
    get_image_as_base64, _MAX_BATTLES_PER_DAY, _calc_damage, _best_move, _MAX_TURNS,
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.battle-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
    border: 1px solid #e94560;
}
.battle-title  { font-size: 28px; font-weight: 800; color: #e94560; margin: 0; }
.battle-sub    { font-size: 14px; color: #8892b0; margin: 4px 0 0 0; }
.counter-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 15px; }
.counter-ok    { background: #1a472a; color: #69db7c; border: 1px solid #2f9e44; }
.counter-warn  { background: #5c2d0a; color: #ffa94d; border: 1px solid #e8590c; }
.counter-full  { background: #3b1219; color: #ff6b6b; border: 1px solid #c92a2a; }
.fighter-card  {
    background: #161b27; border-radius: 10px; padding: 14px;
    border: 2px solid #2d3748; text-align: center;
}
.fighter-name  { font-size: 16px; font-weight: 700; color: #e2e8f0; margin: 6px 0 2px 0; }
.fighter-level { font-size: 12px; color: #8892b0; }
.hp-bar-bg     { background: #2d3748; border-radius: 4px; height: 10px; margin: 8px 0; }
.hp-bar-fill   { height: 10px; border-radius: 4px; }
.vs-badge      { font-size: 32px; font-weight: 900; color: #e94560; text-align: center; padding-top: 30px; }
.turn-log      {
    background: #0d1117; border-radius: 8px; padding: 10px 14px;
    max-height: 200px; overflow-y: auto; margin-top: 12px;
    border: 1px solid #2d3748; font-size: 13px;
}
.turn-row-ch   { color: #63b3ed; margin: 3px 0; }
.turn-row-op   { color: #fc8181; margin: 3px 0; }
.result-win    { background: linear-gradient(135deg,#1a472a,#2d6a3f); border: 2px solid #2f9e44; border-radius: 12px; padding: 20px; text-align: center; }
.result-loss   { background: linear-gradient(135deg,#3b1219,#6b2131); border: 2px solid #c92a2a; border-radius: 12px; padding: 20px; text-align: center; }
.result-draw   { background: linear-gradient(135deg,#1a1f35,#2a3050); border: 2px solid #4a5568; border-radius: 12px; padding: 20px; text-align: center; }
.result-title  { font-size: 26px; font-weight: 900; margin: 0; }
.reward-chip   { display: inline-block; margin: 4px; padding: 4px 12px; border-radius: 14px; font-size: 13px; font-weight: 600; }
.move-type-ph  { background: #3a2000; color: #ffa94d; border: 1px solid #e8590c; }
.move-type-sp  { background: #1a1a4a; color: #74c0fc; border: 1px solid #339af0; }
.move-type-st  { background: #1a2a1a; color: #69db7c; border: 1px solid #2f9e44; }
.history-card  { background: #161b27; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; border: 1px solid #2d3748; }
.history-win   { border-left: 4px solid #2f9e44; }
.history-loss  { border-left: 4px solid #c92a2a; }
.history-draw  { border-left: 4px solid #4a5568; }
</style>
""", unsafe_allow_html=True)

user_id = st.session_state.user_id
profile = get_user_profile(user_id)
coins   = profile["coins"] if profile else 0

# ── Header ─────────────────────────────────────────────────────────────────────
daily_count = get_daily_battle_count(user_id)
remaining   = _MAX_BATTLES_PER_DAY - daily_count

if remaining == 0:
    ctr_cls, ctr_txt = "counter-full", f"0/{_MAX_BATTLES_PER_DAY} batalhas restantes"
elif remaining == 1:
    ctr_cls, ctr_txt = "counter-warn", f"1/{_MAX_BATTLES_PER_DAY} batalha restante"
else:
    ctr_cls, ctr_txt = "counter-ok",   f"{remaining}/{_MAX_BATTLES_PER_DAY} batalhas restantes"

st.markdown(f"""
<div class="battle-header">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
      <p class="battle-title">⚔️ Arena de Batalhas</p>
      <p class="battle-sub">Slot 1 vs slot 1 · você escolhe os golpes · oponente usa melhor golpe</p>
    </div>
    <div>
      <span class="counter-badge {ctr_cls}">{ctr_txt}</span>
      <span style="margin-left:12px;color:#ffd700;font-weight:700;">🪙 {coins}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de UI
# ══════════════════════════════════════════════════════════════════════════════

def _hp_color(pct: int) -> str:
    if pct > 50: return "#2f9e44"
    if pct > 20: return "#e8590c"
    return "#c92a2a"


def _fighter_card(poke: dict, label: str, is_winner: bool):
    pct    = int(poke["hp"] / max(1, poke["max_hp"]) * 100)
    border = "2px solid #ffd700" if is_winner else "2px solid #2d3748"
    img    = get_image_as_base64(poke["sprite_url"])
    img_tag = f'<img src="data:image/png;base64,{img}" width="80">' if img else "🔴"
    col    = _hp_color(pct)
    return f"""
    <div class="fighter-card" style="border:{border};">
      <div style="font-size:11px;color:#8892b0;text-transform:uppercase;letter-spacing:1px;">{label}</div>
      {img_tag}
      <p class="fighter-name">{poke['name']}</p>
      <p class="fighter-level">Lv.{poke['level']}</p>
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-top:6px;">
        <span style="color:#8892b0;">HP</span>
        <span style="color:{col};font-weight:700;">{poke['hp']}/{poke['max_hp']}</span>
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


def _resolve_turn(state: dict, ch_move: dict) -> dict:
    """Processa um turno completo: ataque do jogador + resposta do oponente."""
    ch  = state["ch"]
    op  = state["op"]
    state["turn_num"] += 1
    turn = state["turn_num"]

    op_move = _best_move(op["moves"])

    # Ordem de ataque por speed
    ch_first = ch["stat_speed"] >= op["stat_speed"]

    events = []

    def _attack(attacker, defender, move, is_ch):
        if not move["power"]:
            events.append({"attacker_id": attacker["id"], "is_ch": is_ch,
                           "move_name": move["name"], "move_power": 0, "damage": 0})
            return

        if move["damage_class"] == "physical":
            atk  = attacker["stat_attack"]
            defs = defender["stat_defense"]
        else:
            atk  = attacker["stat_sp_attack"]
            defs = defender["stat_sp_defense"]

        dmg = _calc_damage(atk, defs, move["power"], attacker["level"])

        if is_ch:
            op["hp"] = max(0, op["hp"] - dmg)
        else:
            ch["hp"] = max(0, ch["hp"] - dmg)

        events.append({
            "attacker_id": attacker["id"], "is_ch": is_ch,
            "move_name": move["name"], "move_power": move["power"], "damage": dmg,
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
        })

    # Verifica fim de batalha
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
        st.subheader("Desafiar oponente")
        opponents = get_battle_opponents(user_id)

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

    # Log de turnos
    if bs["turns"]:
        log_html = ""
        for t in reversed(bs["turns"][-10:]):
            is_ch = t["attacker_id"] == ch["id"]
            attacker = ch["name"] if is_ch else op["name"]
            css = "turn-row-ch" if is_ch else "turn-row-op"
            dmg_txt = f" → <strong>-{t['damage']} HP</strong>" if t["damage"] else ""
            log_html += f'<div class="{css}">T{t["turn"]} {attacker} usou <strong>{t["move_name"]}</strong>{dmg_txt} · 🔵{t["ch_hp"]} 🔴{t["op_hp"]}</div>'
        st.markdown(f'<div class="turn-log">{log_html}</div>', unsafe_allow_html=True)

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
        st.session_state.battle_saved  = True
        st.session_state.battle_result = saved

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

    rewards_html = f'<span class="reward-chip" style="background:#1a3a1a;color:#69db7c;">+{ch_xp} XP</span>'
    if coins_earned:
        rewards_html += f'<span class="reward-chip" style="background:#3a2f00;color:#ffd700;">+{coins_earned} 🪙</span>'
    if lvl_up:
        rewards_html += f'<span class="reward-chip" style="background:#2a1a4a;color:#b39ddb;">+{lvl_up} nível!</span>'

    st.markdown(f"""
    <div class="{res_cls}" style="margin-bottom:20px;">
      <p class="result-title">{res_icon} {res_txt}</p>
      <p style="color:#a0aec0;margin:6px 0;">{bs['turn_num']} turnos · {ch['name']} vs {op['name']}</p>
      <div style="margin-top:10px;">{rewards_html}</div>
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

    with st.expander(f"📜 Log completo ({len(bs['turns'])} ações)"):
        for t in bs["turns"]:
            is_ch = t["attacker_id"] == ch["id"]
            attacker = ch["name"] if is_ch else op["name"]
            css = "turn-row-ch" if is_ch else "turn-row-op"
            dmg_txt = f" → **-{t['damage']} HP**" if t["damage"] else ""
            st.markdown(
                f"<div class='{css}'>T{t['turn']} **{attacker}** usou **{t['move_name']}**{dmg_txt} · 🔵{t['ch_hp']} 🔴{t['op_hp']}</div>",
                unsafe_allow_html=True,
            )

    if st.button("🔄 Nova batalha"):
        del st.session_state.battle_state
        st.session_state.pop("battle_saved", None)
        st.session_state.pop("battle_result", None)
        st.rerun()

    st.divider()

# ── Histórico ──────────────────────────────────────────────────────────────────
st.subheader("Histórico de batalhas")
history = get_battle_history(user_id)

if not history:
    st.info("Nenhuma batalha ainda.")
else:
    for b in history:
        is_ch      = str(b["challenger_id"]) == user_id
        their_name = b["opponent_name"]   if is_ch else b["challenger_name"]
        their_poke = b["op_pokemon"]      if is_ch else b["ch_pokemon"]
        my_poke    = b["ch_pokemon"]      if is_ch else b["op_pokemon"]
        my_xp      = b["ch_xp"]          if is_ch else b["op_xp"]

        if b["winner_id"] is None:
            outcome, css, icon = "Empate",  "history-draw", "🤝"
        elif str(b["winner_id"]) == user_id:
            outcome, css, icon = "Vitória", "history-win",  "🏆"
        else:
            outcome, css, icon = "Derrota", "history-loss", "💀"

        coins_info = f" · +{b['coins']} 🪙" if str(b.get("winner_id", "")) == user_id else ""
        date_str   = b["battled_at"].strftime("%d/%m %H:%M") if b["battled_at"] else ""

        with st.expander(f"{icon} {outcome} vs {their_name} ({my_poke} vs {their_poke}) · {date_str}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Oponente:** {their_name} ({their_poke})")
            with c2:
                st.markdown(f"**Turnos:** {b['turn_count']} · **XP:** +{my_xp}{coins_info}")
            for t in get_battle_detail(b["id"]):
                st.markdown(
                    f"T{t['turn']} · **{t['move_name']}** · -{t['damage']} HP · 🔵{t['ch_hp']} 🔴{t['op_hp']}"
                )
