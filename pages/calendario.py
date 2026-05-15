import calendar
import datetime
import os
import streamlit as st
from utils.app_cache import (
    clear_checkin_cache,
    clear_team_cache,
    clear_user_cache,
    get_cached_checkin_streak,
    get_cached_monthly_checkins,
    get_cached_monthly_rest_days,
    get_cached_user_profile,
)
from utils.db import (
    do_checkin, register_rest,
    sprite_img_tag, hq_sprite_url,
    _today_brt, check_and_award_achievements, update_mission_progress,
)
from utils.type_colors import get_type_color
from utils.quest_tracker import render_quest_sidebar

BASE_DIR = os.getcwd()

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

MONTH_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
WEEKDAYS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.cal-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.cal-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px; letter-spacing: 2px; text-transform: uppercase; }

/* Stat cards */
.stat-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 16px;
    padding: 16px 20px; flex: 1; min-width: 120px; text-align: center;
}
.stat-val  { font-family: "Bebas Neue", sans-serif; font-size: 2rem; font-weight: 400; color: #B8F82F; letter-spacing: 2px; }
.stat-lbl  { font-size: 0.65rem; color: #8b949e; text-transform: uppercase;
             letter-spacing: 2px; margin-top: 4px; font-weight: 700; }

/* Cabeçalho do mês */
.month-nav {
    display: flex; align-items: center; justify-content: center;
    gap: 16px; margin-bottom: 12px;
}
.month-label { font-size: 1.1rem; font-weight: 700; color: #e6edf3; min-width: 180px; text-align: center; }

/* Grade do calendário */
.cal-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 6px; margin-bottom: 20px;
}
.cal-weekday {
    text-align: center; font-size: 0.62rem; font-weight: 700;
    color: #484f58; text-transform: uppercase; letter-spacing: 1px;
    padding: 4px 0; font-family: "Space Grotesk", sans-serif;
}
.cal-day {
    background: #161b22; border: 1px solid #21262d; border-radius: 10px;
    padding: 8px 4px 6px; text-align: center; min-height: 72px;
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    position: relative; transition: border-color 0.15s ease;
}
.cal-day.future  { background: #0d1117; border-color: #161b22; }
.cal-day.empty   { background: transparent; border-color: transparent; }
.cal-day.today   { border: 2px solid #B8F82F; box-shadow: 0 0 0 1px #B8F82F, 0 0 16px rgba(184,248,47,0.2); }
.cal-day.checked { background: rgba(184,248,47,0.1); border-color: rgba(184,248,47,0.4); }
.cal-day.bonus   { background: rgba(255,197,49,0.08); border-color: rgba(255,197,49,0.4); }
.cal-day.spawned { background: rgba(112,56,248,0.12); border-color: rgba(112,56,248,0.5); }
.cal-day.checked.bonus   { background: linear-gradient(135deg,rgba(184,248,47,0.12),rgba(255,197,49,0.1)); border-color: rgba(255,197,49,0.5); }
.cal-day.checked.spawned { background: linear-gradient(135deg,rgba(184,248,47,0.12),rgba(112,56,248,0.12)); border-color: rgba(112,56,248,0.5); }
.cal-day.rested { background: rgba(255,130,130,0.07); border-color: rgba(255,130,130,0.35); }

.day-num   { font-size: 0.78rem; font-weight: 700; color: #8b949e; line-height: 1; font-family: "JetBrains Mono", monospace; }
.day-num.today-num { color: #B8F82F; }
.day-icons { display: flex; gap: 3px; justify-content: center; flex-wrap: wrap; margin-top: 2px; }
.day-icon  { font-size: 0.85rem; line-height: 1; }
.streak-pip {
    position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%);
    font-size: 0.55rem; color: #F8D030; font-weight: 700; white-space: nowrap;
}
.special-marker {
    position: absolute; top: 3px; right: 4px;
    font-size: 0.6rem; color: #A1871F;
}

/* Resultado do check-in */
.result-card {
    border-radius: 16px; padding: 20px 24px; margin-bottom: 16px;
    border: 1px solid;
}
.result-card.success  { background: rgba(47,158,68,0.12); border-color: rgba(47,158,68,0.5); }
.result-card.spawn    { background: rgba(112,56,248,0.12); border-color: rgba(112,56,248,0.5); }
.result-card.spawned  { background: rgba(112,56,248,0.12); border-color: rgba(112,56,248,0.5); }
.result-card.bonus    { background: rgba(255,197,49,0.08); border-color: rgba(255,197,49,0.5); }
.result-card.levelup  { background: rgba(88,166,255,0.08); border-color: rgba(88,166,255,0.5); }
.result-card.evolution{ background: #1f0f2e; border-color: #BC8CFF; }
.result-card.rest     { background: rgba(255,130,130,0.08); border-color: rgba(255,130,130,0.5); }
.result-card.shield   { background: rgba(88,166,255,0.08); border-color: rgba(88,166,255,0.5); }
.result-title { font-size: 1rem; font-weight: 700; color: #e6edf3; margin-bottom: 8px; }
.result-body  { color: #8b949e; font-size: 0.85rem; }
.spawn-name   { font-size: 1.2rem; font-weight: 800; color: #A27DFA; }
.evo-arrow    { color: #BC8CFF; font-size: 1.1rem; margin: 0 8px; }
.evo-name-from{ color: #8b949e; font-weight: 700; }
.evo-name-to  { color: #BC8CFF; font-size: 1.1rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

today = _today_brt()
for k, v in [
    ("cal_year",  today.year),
    ("cal_month", today.month),
    ("checkin_result", None),
    ("rest_result", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Sessão inválida. Faça login novamente.")
    st.stop()

profile = get_cached_user_profile(user_id)
coins   = profile["coins"] if profile else 0

# ── Sidebar quest tracker ──────────────────────────────────────────────────────
with st.sidebar:
    render_quest_sidebar(user_id)

# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_coins = st.columns([3, 1])
with col_title:
    st.markdown("<p class='cal-title'>CALENDÁRIO</p>", unsafe_allow_html=True)
    st.markdown("<p class='cal-sub'>CHECK-IN DIÁRIO</p>", unsafe_allow_html=True)
with col_coins:
    st.markdown(
        f"<div style='text-align:right;margin-top:8px'>"
        f"<div style='display:inline-flex;align-items:center;gap:6px;"
        f"background:linear-gradient(135deg,#FFC531,#B38200);border-radius:9999px;"
        f"padding:6px 16px;font-size:0.95rem;font-weight:800;color:#0d1117'>"
        f"🪙 {coins:,}</div></div>",
        unsafe_allow_html=True,
    )

# ── Stats de streak ───────────────────────────────────────────────────────────

streak = get_cached_checkin_streak(user_id)

# Calcula totais do mês exibido
checkins_this_month = get_cached_monthly_checkins(user_id, today.year, today.month)
month_total         = len(checkins_this_month)
last_day            = calendar.monthrange(today.year, today.month)[1]
is_bonus_day        = today.day in (15, last_day)
already_checked     = today.day in checkins_this_month
next_milestone      = 3 - (streak % 3) if streak % 3 != 0 else 3

st.markdown(f"""
<div class='stat-row'>
  <div class='stat-card'>
    <div class='stat-val'>🔥 {streak}</div>
    <div class='stat-lbl'>Streak atual</div>
  </div>
  <div class='stat-card'>
    <div class='stat-val'>{month_total}</div>
    <div class='stat-lbl'>Check-ins este mês</div>
  </div>
  <div class='stat-card'>
    <div class='stat-val'>🪙 {coins:,}</div>
    <div class='stat-lbl'>Moedas totais</div>
  </div>
  <div class='stat-card'>
    <div class='stat-val'>{'⭐ Hoje!' if is_bonus_day else str(next_milestone)}</div>
    <div class='stat-lbl'>{'Dia especial' if is_bonus_day else 'Dias para spawn'}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Botão de check-in ─────────────────────────────────────────────────────────

already_rested = today.day in get_cached_monthly_rest_days(user_id, today.year, today.month)

col_checkin, col_rest = st.columns([3, 2])
with col_checkin:
    if already_checked:
        st.success("✅ Check-in de hoje já realizado! Volte amanhã.")
    else:
        bonus_hint  = " · 🎁 Dia especial — +1 XP Share!" if is_bonus_day else ""
        shield_hint = " · 🛡️ +1 Escudo de Streak!" if today.day in (7, 21) else ""
        streak_hint = f" · 🎲 Dia de streak #{streak+1}" if (streak + 1) % 3 == 0 else ""
        st.markdown(
            f"<div style='color:#8b949e;font-size:0.82rem;margin-bottom:8px'>"
            f"Recompensa: 🪙 +1 moeda{bonus_hint}{shield_hint}{streak_hint}</div>",
            unsafe_allow_html=True,
        )
        if st.button("✔ Fazer Check-in", type="primary", use_container_width=False):
            res = do_checkin(user_id)
            clear_user_cache(user_id, year=today.year, month=today.month)
            st.session_state.checkin_result = res
            if res.get("success"):
                new_ach = check_and_award_achievements(user_id)
                if new_ach:
                    pending = st.session_state.get("new_achievements_pending", [])
                    seen = {a["slug"] for a in pending}
                    st.session_state.new_achievements_pending = pending + [a for a in new_ach if a["slug"] not in seen]
                _m_done = update_mission_progress(user_id, "checkin")
                for _md in (_m_done or []):
                    st.toast(f"🎯 Missão concluída: {_md.get('icon','')} {_md.get('label','')} — {_md.get('reward_label','')}", icon="✅")
            st.rerun()

with col_rest:
    if already_rested:
        st.markdown(
            "<div style='color:#8b949e;font-size:0.82rem;margin-top:28px'>😴 Descanso registrado hoje</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='color:#8b949e;font-size:0.82rem;margin-bottom:8px'>"
            "Descansando? ❤️ +5 felicidade</div>",
            unsafe_allow_html=True,
        )
        if st.button("😴 Registrar Descanso", use_container_width=False):
            rr = register_rest(user_id)
            clear_checkin_cache(user_id, year=today.year, month=today.month)
            clear_team_cache(user_id)
            st.session_state.rest_result = rr
            st.rerun()

# ── Resultado do check-in ─────────────────────────────────────────────────────

res = st.session_state.checkin_result
if res:
    if res.get("already_done"):
        st.warning("Você já fez check-in hoje!")
    elif res.get("success"):
        # Card base: moeda + streak
        card_cls = "success"
        if res.get("spawned"):
            card_cls = "spawned"
        elif res.get("bonus_xp_share"):
            card_cls = "bonus"

        streak_fire = "🔥" * min(res["streak"], 7)
        st.markdown(
            f"<div class='result-card {card_cls}'>"
            f"<div class='result-title'>Check-in realizado! {streak_fire}</div>"
            f"<div class='result-body'>"
            f"🪙 +1 moeda &nbsp;·&nbsp; Streak: <b>{res['streak']} dia{'s' if res['streak'] != 1 else ''}</b>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        # XP Share bonus
        if res.get("bonus_xp_share"):
            st.markdown(
                "<div class='result-card bonus'>"
                "<div class='result-title'>🎁 Bônus do dia especial!</div>"
                "<div class='result-body'>Você ganhou <b>1× XP Share</b> 📡 — disponível na Mochila da Loja.</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # Streak Shield ativado
        if res.get("shield_used"):
            st.markdown(
                f"<div class='result-card shield'>"
                f"<div class='result-title'>🛡️ Escudo de Streak ativado!</div>"
                f"<div class='result-body'>Seu streak de <b>{res['streak']} dias</b> foi preservado pelo Escudo de Streak.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Streak Shield recebido (dias 7 e 21)
        if res.get("bonus_shield"):
            day_num = _today_brt().day
            st.markdown(
                f"<div class='result-card bonus'>"
                f"<div class='result-title'>🛡️ +1 Escudo de Streak recebido!</div>"
                f"<div class='result-body'>Bônus do dia {day_num} do mês — disponível na Mochila.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        if res.get("spawned"):
            pk      = res["spawned"]
            c       = get_type_color(pk.get("type1", "").lower() if pk.get("type1") else None)
            sp_path = pk.get("sprite_url", "")
            img_html = (
                sprite_img_tag(hq_sprite_url(sp_path), width=96, extra_style="image-rendering:pixelated")
                if sp_path else ""
            ) or "<div style='font-size:3rem'>❓</div>"
            is_shiny_spawn = pk.get("is_shiny", False)
            spawn_title = "🌟 Pokémon Shiny apareceu!" if is_shiny_spawn else "✨ Pokémon apareceu!"
            shiny_badge = "<span style='background:#FFD700;color:#000;font-size:0.65rem;font-weight:700;padding:2px 7px;border-radius:10px;margin-left:6px;letter-spacing:1px'>SHINY</span>" if is_shiny_spawn else ""
            st.markdown(
                f"<div class='result-card spawned' style='display:flex;align-items:center;gap:20px'>"
                f"<div>{img_html}</div>"
                f"<div>"
                f"<div class='result-title'>{spawn_title}</div>"
                f"<div class='spawn-name'>{pk['name']}{shiny_badge}</div>"
                f"<div class='result-body' style='margin-top:4px'>"
                f"#{str(pk['id']).zfill(4)} foi capturado automaticamente e adicionado à sua coleção!"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )

        # ── XP / Level-up / Evolução ───────────────────────────────────────────
        xp_res = res.get("xp_result") or {}
        if xp_res and not xp_res.get("error"):
            levels_gained = xp_res.get("levels_gained", 0)
            new_level     = xp_res.get("new_level", 0)
            new_xp        = xp_res.get("new_xp", 0)
            xp_to_next    = new_level * 100
            evolutions    = xp_res.get("evolutions", [])

            # XP ganho (sempre exibido se não houve erro)
            if levels_gained == 0:
                st.markdown(
                    f"<div class='result-card' style='background:#161b22;border-color:#30363d'>"
                    f"<div class='result-title'>⚡ +10 XP para seu Pokémon principal!</div>"
                    f"<div class='result-body'>"
                    f"XP: <b style='color:#58A6FF'>{new_xp}</b> / {xp_to_next} para o nível {new_level + 1}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            # Level-up
            if levels_gained > 0:
                old_level = xp_res.get("old_level", new_level - levels_gained)
                lvl_txt   = (
                    f"Nível <b style='color:#58A6FF'>{old_level}</b> → "
                    f"<b style='color:#58A6FF'>{new_level}</b>"
                    if levels_gained == 1
                    else f"Subiu <b style='color:#58A6FF'>{levels_gained} níveis</b> "
                         f"({old_level} → <b style='color:#58A6FF'>{new_level}</b>)"
                )
                st.markdown(
                    f"<div class='result-card levelup'>"
                    f"<div class='result-title'>🆙 Level Up!</div>"
                    f"<div class='result-body'>{lvl_txt} &nbsp;·&nbsp; "
                    f"XP: <b style='color:#58A6FF'>{new_xp}</b> / {xp_to_next} para o próximo nível"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            # Evoluções
            for evo in evolutions:
                evo_sprite      = evo.get("sprite_url", "")
                evo_from_sprite = evo.get("from_sprite_url", "")

                if evo.get("shed"):
                    shed_img = (
                        sprite_img_tag(
                            hq_sprite_url(evo_sprite), width=90,
                            extra_style="image-rendering:pixelated;filter:drop-shadow(0 0 12px #2ea043)",
                        )
                        if evo_sprite else ""
                    ) or "<div style='font-size:3rem'>👻</div>"
                    st.markdown(
                        f"<div class='result-card' style='background:rgba(46,160,67,0.1);"
                        f"border-color:rgba(46,160,67,0.6);display:flex;align-items:center;gap:20px'>"
                        f"<div>{shed_img}</div>"
                        f"<div>"
                        f"<div class='result-title'>👻 Shedinja capturado!</div>"
                        f"<div style='color:#2ea043;font-size:1.05rem;font-weight:800;margin-top:4px'>"
                        f"{evo['to_name']}</div>"
                        f"<div class='result-body' style='margin-top:6px'>"
                        f"A muda de {evo['from_name']} ganhou vida — adicionado à equipe!</div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state.team_shed_notice = {
                        "name":       evo["to_name"],
                        "from_name":  evo["from_name"],
                        "sprite_url": evo.get("sprite_url", ""),
                    }
                else:
                    _cal_from_img = (
                        sprite_img_tag(
                            hq_sprite_url(evo_from_sprite), width=80,
                            extra_style="image-rendering:pixelated",
                        )
                        if evo_from_sprite else "<div style='font-size:2.5rem;opacity:.6'>❓</div>"
                    )
                    _cal_to_img = (
                        sprite_img_tag(
                            hq_sprite_url(evo_sprite), width=80,
                            extra_style="image-rendering:pixelated",
                        )
                        if evo_sprite else "<div style='font-size:2.5rem'>🌟</div>"
                    )
                    _cal_from_name = evo["from_name"]
                    _cal_to_name   = evo["to_name"]
                    st.markdown(
                        "<style>"
                        "@keyframes lb-evo-in{"
                        "0%{opacity:0;transform:translateY(-10px) scale(.97)}"
                        "100%{opacity:1;transform:translateY(0) scale(1)}}"
                        "@keyframes lb-evo-glow{"
                        "0%{box-shadow:0 0 0 #BC8CFF00;border-color:#3d1f5e}"
                        "45%{box-shadow:0 0 35px #BC8CFF55,0 0 70px #BC8CFF22;border-color:#BC8CFF}"
                        "100%{box-shadow:0 0 14px #BC8CFF33;border-color:#BC8CFF}}"
                        "@keyframes lb-evo-from{"
                        "0%,25%{opacity:1;filter:brightness(1)}"
                        "60%{opacity:1;filter:brightness(8) drop-shadow(0 0 10px #fff)}"
                        "100%{opacity:0;filter:brightness(20);transform:scale(.8)}}"
                        "@keyframes lb-evo-arrow{"
                        "0%,35%{opacity:.25;transform:scale(1)}"
                        "65%{opacity:1;transform:scale(1.5)}"
                        "100%{opacity:.8;transform:scale(1.1)}}"
                        "@keyframes lb-evo-to{"
                        "0%,50%{opacity:0;filter:brightness(20) saturate(0);transform:scale(.7)}"
                        "70%{opacity:1;filter:brightness(5) drop-shadow(0 0 22px #BC8CFF);transform:scale(1.2)}"
                        "87%{filter:brightness(2) drop-shadow(0 0 12px #BC8CFF);transform:scale(1.0)}"
                        "100%{opacity:1;filter:drop-shadow(0 0 8px #BC8CFF77);transform:scale(1.0)}}"
                        "@keyframes lb-evo-text{"
                        "0%,58%{opacity:0;transform:translateX(-10px)}"
                        "100%{opacity:1;transform:translateX(0)}}"
                        "</style>"
                        "<div style='"
                        "background:linear-gradient(135deg,#1a0b2e 0%,#2a1050 50%,#1a0b2e 100%);"
                        "border-radius:16px;padding:20px 24px;margin-top:12px;"
                        "display:flex;align-items:center;gap:20px;"
                        "border:1.5px solid transparent;"
                        "animation:lb-evo-in .4s ease-out both,lb-evo-glow 2s ease-out both'>"
                        f"<div style='flex-shrink:0;animation:lb-evo-from 1.1s ease-in-out .2s both'>{_cal_from_img}</div>"
                        "<div style='color:#BC8CFF;font-size:2rem;font-weight:900;flex-shrink:0;"
                        "animation:lb-evo-arrow .7s ease .75s both'>→</div>"
                        f"<div style='flex-shrink:0;animation:lb-evo-to 1.1s ease-out .8s both'>{_cal_to_img}</div>"
                        "<div style='animation:lb-evo-text .5s ease-out 1.4s both'>"
                        "<div style='font-weight:800;color:#e6edf3;font-size:1.1rem'>🌟 Pokémon evoluiu!</div>"
                        "<div style='margin-top:6px'>"
                        f"<span style='color:#8b949e;font-weight:700'>{_cal_from_name}</span>"
                        "<span style='color:#BC8CFF;margin:0 10px;font-size:1.3rem'>→</span>"
                        f"<span style='color:#BC8CFF;font-size:1.1rem;font-weight:800'>{_cal_to_name}</span>"
                        "</div>"
                        "<div style='color:#8b949e;font-size:0.8rem;margin-top:4px'>Stats recalculados para a nova forma!</div>"
                        "</div></div>",
                        unsafe_allow_html=True,
                    )

            # XP Share distribution log
            xp_shared = xp_res.get("xp_share_distributed", [])
            if xp_shared:
                st.session_state.xp_share_log = xp_shared

    st.session_state.checkin_result = None

rr = st.session_state.rest_result
if rr:
    if rr.get("already_done"):
        st.warning("Você já registrou descanso hoje!")
    elif rr.get("success"):
        st.markdown(
            "<div class='result-card rest'>"
            "<div class='result-title'>😴 Descanso registrado!</div>"
            "<div class='result-body'>❤️ +5 felicidade para seu Pokémon principal. "
            "Recuperação é parte do treino!</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    elif rr.get("error"):
        st.error(f"Erro ao registrar descanso: {rr['error']}")
    st.session_state.rest_result = None

st.markdown("---")

def _calendar_view():
    # ── Navegação de mês ──────────────────────────────────────────────────────

    c_prev, c_label, c_next = st.columns([1, 4, 1])
    with c_prev:
        if st.button("◀", use_container_width=True):
            m = st.session_state.cal_month - 1
            y = st.session_state.cal_year
            if m < 1:
                m, y = 12, y - 1
            st.session_state.cal_month = m
            st.session_state.cal_year  = y
            st.rerun(scope="fragment")
    with c_label:
        st.markdown(
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;color:#e6edf3;"
            f"padding:6px 0'>{MONTH_PT[st.session_state.cal_month]} {st.session_state.cal_year}</div>",
            unsafe_allow_html=True,
        )
    with c_next:
        is_current = (st.session_state.cal_year == today.year and
                      st.session_state.cal_month == today.month)
        if st.button("▶", disabled=is_current, use_container_width=True):
            m = st.session_state.cal_month + 1
            y = st.session_state.cal_year
            if m > 12:
                m, y = 1, y + 1
            st.session_state.cal_month = m
            st.session_state.cal_year  = y
            st.rerun(scope="fragment")

    # ── Grade do calendário ───────────────────────────────────────────────────

    disp_year  = st.session_state.cal_year
    disp_month = st.session_state.cal_month
    checkins   = get_cached_monthly_checkins(user_id, disp_year, disp_month)
    rest_days  = get_cached_monthly_rest_days(user_id, disp_year, disp_month)
    last_day_m = calendar.monthrange(disp_year, disp_month)[1]
    weeks      = calendar.monthcalendar(disp_year, disp_month)  # Mon=0 … Sun=6

    # Cabeçalho de dias da semana
    header_html = "<div class='cal-grid'>"
    for wd in WEEKDAYS_PT:
        header_html += f"<div class='cal-weekday'>{wd}</div>"
    header_html += "</div>"
    st.markdown(header_html, unsafe_allow_html=True)

    # Células dos dias
    grid_html = "<div class='cal-grid'>"
    for week in weeks:
        for day in week:
            if day == 0:
                grid_html += "<div class='cal-day empty'></div>"
                continue

            cell_date  = datetime.date(disp_year, disp_month, day)
            is_today   = cell_date == today
            is_future  = cell_date > today
            is_special = day in (15, last_day_m)
            ck         = checkins.get(day)
            is_rest    = day in rest_days

            classes = ["cal-day"]
            if is_future:
                classes.append("future")
            if is_today:
                classes.append("today")
            if ck:
                classes.append("checked")
                if ck["bonus_item"]:
                    classes.append("bonus")
                if ck["spawned_species_id"]:
                    classes.append("spawned")
            elif is_rest:
                classes.append("rested")

            num_cls = "day-num today-num" if is_today else "day-num"
            is_shield_day = day in (7, 21)
            icons   = ""
            if ck:
                icons += "<span class='day-icon'>🪙</span>"
                if ck["bonus_item"]:
                    icons += "<span class='day-icon'>📡</span>"
                if ck["spawned_species_id"]:
                    icons += "<span class='day-icon'>🌟</span>"
                if is_rest:
                    icons += "<span class='day-icon'>😴</span>"
                if is_shield_day:
                    icons += "<span class='day-icon'>🛡️</span>"
            elif is_rest:
                icons += "<span class='day-icon'>😴</span>"
                if is_shield_day:
                    icons += "<span class='day-icon'>🛡️</span>"
            elif not is_future and is_special:
                icons += "<span class='day-icon' style='opacity:.35'>🎁</span>"
            if is_future and is_shield_day:
                icons += "<span class='day-icon' style='opacity:.5'>🛡️</span>"

            special_html = "<span class='special-marker'>★</span>" if is_special else ""
            streak_html  = (
                f"<span class='streak-pip'>🔥{ck['streak']}</span>"
                if ck and ck["streak"] >= 2 else ""
            )

            grid_html += (
                f"<div class='{' '.join(classes)}'>"
                f"{special_html}"
                f"<span class='{num_cls}'>{day}</span>"
                f"<div class='day-icons'>{icons}</div>"
                f"{streak_html}"
                f"</div>"
            )

    grid_html += "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)


_calendar_view()

# ── Legenda ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:8px'>
  <div style='display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#8b949e'>
    <div style='width:12px;height:12px;border-radius:3px;background:#1a472a;border:1px solid #2f9e44'></div> Check-in feito
  </div>
  <div style='display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#8b949e'>
    <div style='width:12px;height:12px;border-radius:3px;background:#1c1a0a;border:1px solid #A1871F'></div> 🎁 Dia especial (d15 / último dia)
  </div>
  <div style='display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#8b949e'>
    <div style='width:12px;height:12px;border-radius:3px;background:#1a1030;border:1px solid #7038F8'></div> 🌟 Pokémon capturado
  </div>
  <div style='display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#8b949e'>
    <div style='width:12px;height:12px;border-radius:3px;background:#2a1010;border:1px solid rgba(255,130,130,0.4)'></div> 😴 Dia de descanso
  </div>
  <div style='display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#8b949e'>
    ★ = dia com bônus potencial
  </div>
</div>
""", unsafe_allow_html=True)
