import streamlit as st
from utils.db import (
    get_battle_opponents, get_daily_battle_count, simulate_battle,
    get_battle_history, get_battle_detail, get_user_profile,
    get_image_as_base64, _MAX_BATTLES_PER_DAY,
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.battle-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
    border: 1px solid #e94560;
}
.battle-title { font-size: 28px; font-weight: 800; color: #e94560; margin: 0; }
.battle-subtitle { font-size: 14px; color: #8892b0; margin: 4px 0 0 0; }
.counter-badge {
    display: inline-block; padding: 6px 16px;
    border-radius: 20px; font-weight: 700; font-size: 15px;
}
.counter-ok   { background: #1a472a; color: #69db7c; border: 1px solid #2f9e44; }
.counter-warn { background: #5c2d0a; color: #ffa94d; border: 1px solid #e8590c; }
.counter-full { background: #3b1219; color: #ff6b6b; border: 1px solid #c92a2a; }
.fighter-card {
    background: #161b27; border-radius: 10px; padding: 14px;
    border: 2px solid #2d3748; text-align: center;
}
.fighter-name { font-size: 16px; font-weight: 700; color: #e2e8f0; margin: 6px 0 2px 0; }
.fighter-level { font-size: 12px; color: #8892b0; }
.hp-bar-bg {
    background: #2d3748; border-radius: 4px; height: 8px; margin: 8px 0;
}
.hp-bar-fill {
    height: 8px; border-radius: 4px;
    transition: width 0.3s;
}
.vs-badge {
    font-size: 32px; font-weight: 900; color: #e94560;
    text-align: center; padding-top: 30px;
}
.result-win {
    background: linear-gradient(135deg, #1a472a, #2d6a3f);
    border: 2px solid #2f9e44; border-radius: 12px; padding: 20px; text-align: center;
}
.result-loss {
    background: linear-gradient(135deg, #3b1219, #6b2131);
    border: 2px solid #c92a2a; border-radius: 12px; padding: 20px; text-align: center;
}
.result-draw {
    background: linear-gradient(135deg, #1a1f35, #2a3050);
    border: 2px solid #4a5568; border-radius: 12px; padding: 20px; text-align: center;
}
.result-title { font-size: 26px; font-weight: 900; margin: 0; }
.result-sub { font-size: 14px; color: #a0aec0; margin: 6px 0 0 0; }
.reward-chip {
    display: inline-block; margin: 4px;
    padding: 4px 12px; border-radius: 14px; font-size: 13px; font-weight: 600;
}
.turn-row {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 10px; border-radius: 6px; margin-bottom: 4px;
    font-size: 13px;
}
.turn-ch { background: #1a2a4a; border-left: 3px solid #4299e1; }
.turn-op { background: #2a1a1a; border-left: 3px solid #e94560; }
.history-card {
    background: #161b27; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px;
    border: 1px solid #2d3748;
}
.history-win  { border-left: 4px solid #2f9e44; }
.history-loss { border-left: 4px solid #c92a2a; }
.history-draw { border-left: 4px solid #4a5568; }
</style>
""", unsafe_allow_html=True)

user_id  = st.session_state.user_id
profile  = get_user_profile(user_id)
coins    = profile["coins"] if profile else 0

# ── Header ─────────────────────────────────────────────────────────────────────
daily_count = get_daily_battle_count(user_id)
remaining   = _MAX_BATTLES_PER_DAY - daily_count

if remaining == 0:
    counter_cls = "counter-full"
    counter_txt = f"0/{_MAX_BATTLES_PER_DAY} batalhas restantes"
elif remaining == 1:
    counter_cls = "counter-warn"
    counter_txt = f"1/{_MAX_BATTLES_PER_DAY} batalha restante"
else:
    counter_cls = "counter-ok"
    counter_txt = f"{remaining}/{_MAX_BATTLES_PER_DAY} batalhas restantes"

st.markdown(f"""
<div class="battle-header">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
      <p class="battle-title">⚔️ Arena de Batalhas</p>
      <p class="battle-subtitle">Batalhas offline · slot 1 vs slot 1 · sem dano permanente</p>
    </div>
    <div>
      <span class="counter-badge {counter_cls}">{counter_txt}</span>
      <span style="margin-left:12px;color:#ffd700;font-weight:700;">🪙 {coins}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Iniciar batalha ────────────────────────────────────────────────────────────
st.subheader("Desafiar oponente")

opponents = get_battle_opponents(user_id)

if not opponents:
    st.info("Nenhum outro treinador disponível ainda. Convide amigos!")
else:
    options = {
        f"{o['username']} — {o['pokemon_name']} Lv.{o['level']}": o["user_id"]
        for o in opponents
    }
    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        chosen_label = st.selectbox(
            "Oponente", list(options.keys()), disabled=(remaining == 0),
            label_visibility="collapsed",
        )
    with col_btn:
        fight_btn = st.button(
            "⚔️ Batalhar", disabled=(remaining == 0),
            use_container_width=True, type="primary",
        )

    if remaining == 0:
        st.warning("Você usou todas as batalhas de hoje. Volte amanhã!")

    if fight_btn:
        opponent_id = options[chosen_label]
        with st.spinner("Simulando batalha..."):
            result = simulate_battle(user_id, opponent_id)
        st.session_state.battle_result = result
        st.rerun()

# ── Resultado da última batalha ────────────────────────────────────────────────
if "battle_result" in st.session_state:
    res = st.session_state.battle_result

    if "error" in res:
        st.error(res["error"])
    else:
        ch    = res["challenger"]
        op    = res["opponent"]
        is_ch = (user_id == res["challenger_id"]) if "challenger_id" in res else True
        my    = ch if is_ch else op
        their = op if is_ch else ch

        # Cabeçalho do resultado
        if res["result"] == "draw":
            result_cls, result_icon, result_txt = "result-draw", "🤝", "Empate!"
        elif (res["result"] == "challenger_win") == is_ch:
            result_cls, result_icon, result_txt = "result-win",  "🏆", "Vitória!"
        else:
            result_cls, result_icon, result_txt = "result-loss", "💀", "Derrota!"

        xp_earned    = my.get("xp_earned", 0)
        coins_earned = res["coins_earned"] if res["winner_id"] == user_id else 0

        rewards_html = f'<span class="reward-chip" style="background:#1a3a1a;color:#69db7c;">+{xp_earned} XP</span>'
        if coins_earned:
            rewards_html += f'<span class="reward-chip" style="background:#3a2f00;color:#ffd700;">+{coins_earned} 🪙</span>'

        lvl_up = my.get("xp_result", {}).get("levels_gained", 0)
        if lvl_up:
            rewards_html += f'<span class="reward-chip" style="background:#2a1a4a;color:#b39ddb;">+{lvl_up} nível!</span>'

        st.markdown(f"""
        <div class="{result_cls}" style="margin-bottom:20px;">
          <p class="result-title">{result_icon} {result_txt}</p>
          <p class="result-sub">{res["turn_count"]} turnos · {ch["name"]} vs {op["name"]}</p>
          <div style="margin-top:10px;">{rewards_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Cards dos lutadores
        def _fighter_card(poke, label, is_winner):
            pct    = int(poke["final_hp"] / max(1, poke["max_hp"]) * 100)
            hp_col = "#2f9e44" if pct > 50 else "#e8590c" if pct > 20 else "#c92a2a"
            border = "2px solid #ffd700" if is_winner else "2px solid #2d3748"
            img    = get_image_as_base64(poke["sprite_url"])
            img_tag = f'<img src="data:image/png;base64,{img}" width="72">' if img else "🔴"
            return f"""
            <div class="fighter-card" style="border:{border};">
              <div style="font-size:11px;color:#8892b0;text-transform:uppercase;letter-spacing:1px;">{label}</div>
              {img_tag}
              <p class="fighter-name">{poke["name"]}</p>
              <p class="fighter-level">Lv.{poke["level"]}</p>
              <div class="hp-bar-bg">
                <div class="hp-bar-fill" style="width:{pct}%;background:{hp_col};"></div>
              </div>
              <div style="font-size:11px;color:#8892b0;">{poke["final_hp"]}/{poke["max_hp"]} HP</div>
            </div>
            """

        ch_win = res["result"] == "challenger_win"
        c1, c2, c3 = st.columns([5, 1, 5])
        with c1:
            st.markdown(_fighter_card(ch, "Desafiante", ch_win), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
        with c3:
            st.markdown(_fighter_card(op, "Oponente", not ch_win and res["result"] != "draw"),
                        unsafe_allow_html=True)

        # Log de turnos
        with st.expander(f"📜 Log da batalha ({res['turn_count']} turnos)"):
            for t in res["turns"]:
                is_ch_turn = t["attacker_id"] == ch["id"]
                attacker   = ch["name"] if is_ch_turn else op["name"]
                css_cls    = "turn-ch" if is_ch_turn else "turn-op"
                st.markdown(f"""
                <div class="turn-row {css_cls}">
                  <span style="color:#8892b0;min-width:24px;">T{t["turn"]}</span>
                  <span style="font-weight:700;">{attacker}</span>
                  <span>usou <strong>{t["move_name"]}</strong></span>
                  <span style="color:#fc8181;">-{t["damage"]} HP</span>
                  <span style="color:#8892b0;margin-left:auto;">
                    🔵 {t["ch_hp"]} | 🔴 {t["op_hp"]}
                  </span>
                </div>
                """, unsafe_allow_html=True)

        if st.button("🗑 Fechar resultado"):
            del st.session_state.battle_result
            st.rerun()

    st.divider()

# ── Histórico ──────────────────────────────────────────────────────────────────
st.subheader("Histórico de batalhas")

history = get_battle_history(user_id)

if not history:
    st.info("Nenhuma batalha ainda. Desafie um oponente!")
else:
    for b in history:
        is_ch     = str(b["challenger_id"]) == user_id
        my_name   = b["challenger_name"]   if is_ch else b["opponent_name"]
        their_name = b["opponent_name"]    if is_ch else b["challenger_name"]
        my_poke   = b["ch_pokemon"]        if is_ch else b["op_pokemon"]
        their_poke = b["op_pokemon"]       if is_ch else b["ch_pokemon"]
        my_xp     = b["ch_xp"]            if is_ch else b["op_xp"]

        if b["winner_id"] is None:
            outcome, css_cls, icon = "Empate", "history-draw", "🤝"
        elif str(b["winner_id"]) == user_id:
            outcome, css_cls, icon = "Vitória", "history-win", "🏆"
        else:
            outcome, css_cls, icon = "Derrota", "history-loss", "💀"

        coins_info = f" · +{b['coins']} 🪙" if str(b["winner_id"]) == user_id else ""
        date_str   = b["battled_at"].strftime("%d/%m %H:%M") if b["battled_at"] else ""

        with st.expander(f"{icon} {outcome} vs {their_name} · {my_poke} vs {their_poke} · {date_str}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Seu Pokémon:** {my_poke}")
                st.markdown(f"**Oponente:** {their_name} ({their_poke})")
            with col2:
                st.markdown(f"**Turnos:** {b['turn_count']}")
                st.markdown(f"**XP ganho:** +{my_xp}{coins_info}")

            turns = get_battle_detail(b["id"])
            if turns:
                st.markdown("---")
                for t in turns:
                    is_ch_turn = True  # sem info de qual pokemon é o challenger aqui, ok
                    st.markdown(
                        f"T{t['turn']} · **{t['move_name']}** · -{t['damage']} HP "
                        f"· 🔵{t['ch_hp']} 🔴{t['op_hp']}",
                        help=f"Power: {t['move_power']}"
                    )
