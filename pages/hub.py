import calendar

import streamlit as st

from utils.app_cache import (
    clear_inventory_cache,
    clear_user_cache,
    get_cached_checkin_streak,
    get_cached_daily_battle_count,
    get_cached_monthly_checkins,
    get_cached_user_achievements,
    get_cached_user_missions,
    get_cached_user_profile,
    get_cached_user_team,
)
from utils.db import (
    _MAX_BATTLES_PER_DAY, _today_brt,
    assign_weekly_rival, get_rival_status, sprite_img_tag,
    check_and_award_achievements, do_checkin,
    get_current_challenge, claim_weekly_challenge_reward,
    update_mission_progress,
    _EXERCISE_XP_DAILY_CAP, _WEEKEND_XP_MULTIPLIER, is_weekend_bonus,
)
from utils.achievements import GYM_BADGES
from utils.design_system import stat_tile
from utils.missions import get_mission


if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Sessão inválida. Faça login novamente.")
    st.stop()

st.markdown(
    """
<style>
.hub-event {
    background: linear-gradient(135deg, rgba(245,158,11,0.14), rgba(249,115,22,0.08));
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-xl);
    padding: 16px 18px;
    margin-bottom: 18px;
}
.hub-event-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
}
.hub-event-title {
    color: var(--text-primary);
    font-size: 0.98rem;
    font-weight: 800;
}
.hub-event-badge {
    display: inline-flex;
    align-items: center;
    border-radius: var(--radius-full);
    padding: 4px 10px;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.hub-event-badge.live {
    background: rgba(46,160,67,0.18);
    color: #9be9a8;
    border: 1px solid var(--color-success-border);
}
.hub-event-badge.soon {
    background: rgba(148,163,184,0.14);
    color: var(--text-secondary);
    border: 1px solid rgba(148,163,184,0.24);
}
.hub-event-copy {
    color: var(--text-secondary);
    font-size: 0.85rem;
    line-height: 1.5;
}
.hub-event-copy strong {
    color: var(--text-primary);
}

/* Gym badge mini-rack in hub */
.hub-gym-rack {
    background: var(--surface-panel-lg);
    border: 1px solid rgba(245,158,11,0.18);
    border-radius: var(--radius-xl);
    padding: 14px 18px;
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px;
}
.hub-gym-label {
    color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; white-space: nowrap;
    margin-right: 4px;
}
.hub-gym-count {
    color: var(--color-warning); font-size: 1rem; font-weight: 800;
    white-space: nowrap; margin-right: 12px;
}
.hub-gym-badges { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.hub-gym-dot {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    transition: transform 0.1s;
}
.hub-gym-dot:hover { transform: scale(1.2); }
.hub-gym-dot.locked { background: #1c2332; filter: grayscale(1) opacity(0.3); }

/* Rival banner */
.hub-rival {
    border-radius: var(--radius-xl);
    padding: 14px 20px;
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px;
}
.hub-rival.ahead   { background: var(--color-success-bg);  border: 1px solid var(--color-success-border); }
.hub-rival.behind  { background: rgba(255,136,0,0.08); border: 1px solid rgba(255,136,0,0.35); }
.hub-rival.tied    { background: rgba(148,163,184,0.07); border: 1px solid rgba(148,163,184,0.2); }
.hub-rival-label { font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; margin-bottom: 2px; }
.hub-rival-msg   { font-size: 0.88rem; color: var(--text-body); font-weight: 600; }
.hub-rival-sub   { font-size: 0.72rem; color: var(--text-faint); margin-top: 2px; }

/* Weekly challenge banner */
.hub-challenge {
    background: var(--color-info-bg);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-xl);
    padding: 16px 20px;
    margin-bottom: 18px;
}
.hub-challenge.done {
    background: var(--color-success-bg);
    border-color: var(--color-success-border);
}
.hub-challenge-label { font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; margin-bottom: 4px; }
.hub-challenge-title { font-size: 0.92rem; font-weight: 700; color: var(--text-body); margin-bottom: 8px; }
.hub-challenge-sub { font-size: 0.72rem; color: var(--text-faint); }
</style>
""",
    unsafe_allow_html=True,
)

profile = get_cached_user_profile(user_id)
trainer_name = profile["username"] if profile else "Treinador"
today = _today_brt()

SECTION_CARDS = [
    {
        "title": "Treinador",
        "desc": "Gerencie equipe, missões e progresso do treinador.",
        "icon": "⚔️",
        "links": [
            ("Minha Equipe", "pages/equipe.py"),
            ("Ovos", "pages/ovos.py"),
            ("Conquistas", "pages/conquistas.py"),
            ("Missões", "pages/missoes.py"),
        ],
    },
    {
        "title": "Batalha",
        "desc": "Entre na arena, acompanhe ranking e refine seu time.",
        "icon": "🥊",
        "links": [
            ("Arena", "pages/batalha.py"),
            ("Ranking", "pages/leaderboard.py"),
        ],
    },
    {
        "title": "Treinos",
        "desc": "Mantenha constância, registre exercícios e ganhe recompensas.",
        "icon": "🏋️",
        "links": [
            ("Calendário", "pages/calendario.py"),
            ("Treino", "pages/treino.py"),
            ("Rotinas", "pages/rotinas.py"),
            ("Biblioteca", "pages/biblioteca.py"),
        ],
    },
    {
        "title": "Pokédex e Itens",
        "desc": "Explore espécies, acompanhe a coleção e abra sua mochila direto do hub.",
        "icon": "📖",
        "links": [
            ("Pokédex", "pages/pokedex.py"),
            ("Minha Pokédex", "pages/pokedex_pessoal.py"),
            ("Loja", "pages/loja.py"),
            ("Mochila", "pages/mochila.py"),
        ],
    },
]


def _run_hub_checkin() -> None:
    res = do_checkin(user_id)
    clear_user_cache(user_id, year=today.year, month=today.month)
    st.session_state.hub_checkin_result = res
    if res.get("success"):
        new_ach = check_and_award_achievements(user_id)
        if new_ach:
            pending = st.session_state.get("new_achievements_pending", [])
            seen = {a["slug"] for a in pending}
            st.session_state.new_achievements_pending = pending + [a for a in new_ach if a["slug"] not in seen]
        for mission in (update_mission_progress(user_id, "checkin") or []):
            st.toast(
                f"🎯 Missão concluída: {mission.get('icon', '')} {mission.get('label', '')} — {mission.get('reward_label', '')}",
                icon="✅",
            )
    st.rerun()


def _render_hub_checkin_feedback() -> None:
    res = st.session_state.get("hub_checkin_result")
    if not res:
        return

    if res.get("already_done"):
        st.warning("Você já fez check-in hoje!")
    elif res.get("success"):
        streak = res.get("streak", 0)
        extra_rewards: list[str] = []
        if res.get("bonus_xp_share"):
            extra_rewards.append("1 XP Share")
        if res.get("bonus_shield"):
            extra_rewards.append("1 Escudo de Streak")
        if res.get("spawned"):
            extra_rewards.append(f"{res['spawned']['name']} capturado")

        message = f"Check-in realizado no hub: +1 moeda e streak em {streak} dia{'s' if streak != 1 else ''}."
        if extra_rewards:
            message += " Extras: " + ", ".join(extra_rewards) + "."
        st.success(message)

    st.session_state.hub_checkin_result = None


def _render_snapshot() -> None:
    team = get_cached_user_team(user_id)
    streak = get_cached_checkin_streak(user_id)
    battles_used = get_cached_daily_battle_count(user_id)
    remaining = max(0, _MAX_BATTLES_PER_DAY - battles_used)
    missions = get_cached_user_missions(user_id)
    checkins_this_month = get_cached_monthly_checkins(user_id, today.year, today.month)
    already_checked = today.day in checkins_this_month
    last_day = calendar.monthrange(today.year, today.month)[1]
    is_bonus_day = today.day in (15, last_day)
    daily = missions.get("daily", [])
    daily_done = sum(1 for mission in daily if mission.get("completed"))
    coins = profile["coins"] if profile else 0

    tiles = (
        stat_tile("Moedas", f"🪙 {coins:,}", tone="gold")
        + stat_tile("Equipe", f"{len(team)}/6")
        + stat_tile("Streak", f"🔥 {streak}", tone="gold")
        + stat_tile("Arena Hoje", f"{remaining}/{_MAX_BATTLES_PER_DAY}", tone="red" if remaining == 0 else "blue")
    )
    st.markdown(f"<div class='lb-stat-row'>{tiles}</div>", unsafe_allow_html=True)

    # ── Gym badge mini-rack ────────────────────────────────────────────────────
    try:
        user_achievements = get_cached_user_achievements(user_id)
        gym_earned = sum(1 for b in GYM_BADGES if b["slug"] in user_achievements)
        gym_total = len(GYM_BADGES)
        dots_html = ""
        for b in GYM_BADGES:
            is_unlocked = b["slug"] in user_achievements
            b_name = b["name"]
            b_desc = b["desc"]
            b_icon = b["icon"]
            css_cls = "hub-gym-dot"
            if is_unlocked:
                color = b["color"]
                style = f"background:{color}33;border:1.5px solid {color};"
            else:
                style = ""
                css_cls += " locked"
            dots_html += f"<div class='{css_cls}' style='{style}' title='{b_name}: {b_desc}'>{b_icon}</div>"

        st.markdown(
            f"""
<div class="hub-gym-rack">
  <span class="hub-gym-label">Insígnias</span>
  <span class="hub-gym-count">{gym_earned}/{gym_total}</span>
  <div class="hub-gym-badges">{dots_html}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown(
            """
<div class="lb-panel">
  <div class="lb-panel-title">Rotina do dia</div>
  <div class="lb-panel-sub">Acesse as áreas mais usadas sem depender da sidebar.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        _render_hub_checkin_feedback()
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            checkin_label = "✅ Check-in realizado" if already_checked else "📅 Fazer check-in"
            if st.button(checkin_label, use_container_width=True, disabled=already_checked):
                _run_hub_checkin()
            if not already_checked and is_bonus_day:
                st.caption("Hoje tem bônus especial no check-in.")
        with col_b:
            if st.button("⚔️ Abrir equipe", use_container_width=True):
                st.switch_page("pages/equipe.py")
        with col_c:
            if st.button("🥊 Ir para arena", use_container_width=True):
                st.switch_page("pages/batalha.py")
        with col_d:
            if st.button("🎒 Abrir mochila", use_container_width=True):
                st.switch_page("pages/mochila.py")
    with right:
        mission_rows_html = ""
        for m in daily:
            cat = get_mission(m["slug"])
            if not cat:
                continue
            prog   = m["progress"]
            target = m["target"]
            pct    = min(prog / target * 100, 100) if target else 100
            done   = m["completed"]
            claimed = m.get("reward_claimed", False)

            if claimed:
                bar_color = "#30363d"
                label_color = "#484f58"
                status_icon = "✓"
            elif done:
                bar_color = "#B8F82F"
                label_color = "#B8F82F"
                status_icon = "✅"
            else:
                bar_color = "#58a6ff"
                label_color = "#e6edf3"
                status_icon = cat["icon"]

            reward_label = cat["reward_label"]
            mission_rows_html += (
                f"<div style='display:grid;grid-template-columns:18px 1fr;gap:8px;"
                f"align-items:start;margin-bottom:9px'>"
                f"<span style='font-size:0.9rem;line-height:1.4'>{status_icon}</span>"
                f"<div>"
                f"<div style='font-size:0.72rem;color:{label_color};font-weight:600;"
                f"line-height:1.3;margin-bottom:3px'>{cat['label']}</div>"
                f"<div style='background:#21262d;border-radius:9999px;height:4px;overflow:hidden'>"
                f"<div style='background:{bar_color};height:100%;width:{pct:.0f}%;"
                f"border-radius:9999px'></div>"
                f"</div>"
                f"<div style='font-size:0.6rem;color:#8b949e;margin-top:2px'>"
                f"{prog}/{target} &nbsp;·&nbsp; {reward_label}</div>"
                f"</div></div>"
            )

        daily_label = (
            f"<span style='color:#B8F82F;font-weight:700'>{daily_done}/{len(daily)} completas</span>"
            if daily_done > 0 else f"0/{len(daily)} completas"
        )

        st.markdown(
            f"""
<div class="lb-panel">
  <div class="lb-panel-title">Missões diárias</div>
  <div class="lb-panel-sub" style="margin-bottom:10px">{daily_label} · {today.strftime("%d/%m")}</div>
  {mission_rows_html if mission_rows_html else "<div style='color:var(--text-faint);font-size:0.8rem'>Nenhuma missão carregada.</div>"}
</div>
""",
            unsafe_allow_html=True,
        )


def _render_weekend_bonus_banner() -> None:
    weekend_live = is_weekend_bonus()
    base_cap = _EXERCISE_XP_DAILY_CAP
    boosted_cap = _EXERCISE_XP_DAILY_CAP * _WEEKEND_XP_MULTIPLIER
    badge_cls = "live" if weekend_live else "soon"
    badge_label = "Ativo Agora" if weekend_live else "Recorrente"
    copy = (
        f"Toda sexta, sábado e domingo, os <strong>treinos</strong> concedem "
        f"<strong>{_WEEKEND_XP_MULTIPLIER}x XP</strong> para todos e o limite diário "
        f"de XP de treino sobe de <strong>{base_cap}</strong> para <strong>{boosted_cap}</strong>."
    )
    if weekend_live:
        copy += " O bônus já está valendo hoje."

    st.markdown(
        f"""
<div class="hub-event">
  <div class="hub-event-head">
    <div class="hub-event-title">Final de Semana em Dobro</div>
    <span class="hub-event-badge {badge_cls}">{badge_label}</span>
  </div>
  <div class="hub-event-copy">{copy}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_sections() -> None:
    cols = st.columns(2)
    for idx, section in enumerate(SECTION_CARDS):
        with cols[idx % 2]:
            st.markdown(
                f"""
<div class="lb-panel">
  <div class="lb-panel-title">{section['icon']} {section['title']}</div>
  <div class="lb-panel-sub">{section['desc']}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            link_cols = st.columns(2)
            for link_idx, (label, path) in enumerate(section["links"]):
                with link_cols[link_idx % 2]:
                    if st.button(label, key=f"hub_{path}", use_container_width=True):
                        st.switch_page(path)


st.markdown(
    f"""
<div class="lb-hero">
  <div class="lb-kicker">Dashboard</div>
  <h1 class="lb-hero-title">LIMITBREAK COMMAND</h1>
  <p class="lb-hero-sub">Bem-vindo, {trainer_name}. Use este hub para navegar entre treino, batalha, equipe e coleção com menos cliques e menos ruído visual.</p>
</div>
""",
    unsafe_allow_html=True,
)

_render_weekend_bonus_banner()
_render_snapshot()

# ── Rival Semanal ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _get_rival_data(uid: str) -> dict:
    return assign_weekly_rival(uid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_rival_status(uid: str) -> dict:
    return get_rival_status(uid)


def _render_rival_banner() -> None:
    rival = _get_rival_status(user_id)
    if not rival or "rival_username" not in rival:
        return

    rival_username = rival["rival_username"]
    my_xp = rival["my_xp"]
    rival_xp = rival["rival_xp"]
    diff = rival["diff"]

    if diff > 5:
        css_cls = "ahead"
        icon = "⚔️"
        msg = f"Você está <b>{diff} XP à frente</b> de {rival_username}! Mantenha o ritmo."
    elif diff < -5:
        css_cls = "behind"
        icon = "⚠️"
        msg = f"{rival_username} está <b>{abs(diff)} XP à sua frente</b>! Treine para superar."
    else:
        css_cls = "tied"
        icon = "🤝"
        msg = f"Empate técnico com {rival_username} — próximo treino decide."

    sprite_html = ""
    if rival.get("rival_sprite"):
        sprite_html = sprite_img_tag(
            rival["rival_sprite"],
            width=40,
            extra_style="height:40px;object-fit:contain;image-rendering:pixelated",
        )

    st.markdown(
        f"<div class='hub-rival {css_cls}'>"
        f"{sprite_html}"
        f"<div>"
        f"<div class='hub-rival-label'>Rival da Semana {icon}</div>"
        f"<div class='hub-rival-msg'>{msg}</div>"
        f"<div class='hub-rival-sub'>Você: {my_xp} XP &nbsp;·&nbsp; {rival_username}: {rival_xp} XP (esta semana)</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# Trigger rival assignment (cached 5 min — avoids hitting DB every rerun)
try:
    rival_info = _get_rival_data(user_id)
    if rival_info.get("won_last_week"):
        st.toast(
            f"🏆 Você venceu seu rival da semana passada! +{rival_info['bonus_coins']} moedas",
            icon="🥇",
        )
except Exception:
    pass

_render_rival_banner()

# ── Desafio Comunitário Semanal ────────────────────────────────────────────────

def _render_challenge_banner() -> None:
    ch = get_current_challenge(user_id)
    if not ch:
        return

    goal_val    = ch["goal_value"]
    current     = ch["current_value"]
    completed   = ch["completed"]
    contributed = ch["user_contributed"]
    claimed     = ch["reward_claimed"]
    pct         = min(current / goal_val * 100, 100) if goal_val else 100
    bar_tone    = "" if completed else " blue"
    css_extra   = " done" if completed else ""

    goal_type   = ch.get("goal_type", "total_xp")
    unit        = "XP" if goal_type == "total_xp" else ("sessões" if goal_type == "total_workouts" else "séries")
    progress_text = f"{current:,} / {goal_val:,} {unit} &nbsp;·&nbsp; 🥚 Recompensa: 1 ovo"

    st.markdown(
        f"<div class='hub-challenge{css_extra}'>"
        f"<div class='hub-challenge-label'>🌍 Desafio da Semana</div>"
        f"<div class='hub-challenge-title'>Meta: {ch['description']}</div>"
        f"<div class='lb-progress' style='margin-bottom:6px'>"
        f"<span class='{bar_tone.strip()}' style='width:{pct:.1f}%'></span>"
        f"</div>"
        f"<div class='hub-challenge-sub'>{progress_text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if completed and not claimed and contributed > 0:
        if st.button("🥚 Coletar Ovo do Desafio", use_container_width=False):
            ok, msg, reward = claim_weekly_challenge_reward(user_id)
            clear_inventory_cache(user_id)
            if ok:
                st.toast(msg, icon="🥚")
            else:
                st.error(msg)
            st.rerun()
    elif completed and claimed:
        st.caption("✅ Ovo coletado.")
    elif completed and contributed == 0:
        st.caption("Você não contribuiu esta semana.")


_render_challenge_banner()

st.write("")
_render_sections()
