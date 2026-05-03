import streamlit as st

from utils.app_cache import (
    clear_user_cache,
    get_cached_checkin_streak,
    get_cached_daily_battle_count,
    get_cached_user_achievements,
    get_cached_user_missions,
    get_cached_user_profile,
    get_cached_user_team,
)
from utils.db import (
    _MAX_BATTLES_PER_DAY, _today_brt,
    assign_weekly_rival, get_rival_status, get_image_as_base64,
    get_current_challenge, claim_weekly_challenge_reward,
)
from utils.achievements import GYM_BADGES
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
.hub-hero {
    background: linear-gradient(135deg, rgba(30,41,59,0.96), rgba(15,23,42,0.96));
    border: 1px solid rgba(184,248,47,0.18);
    border-radius: 24px;
    padding: 28px 30px;
    margin-bottom: 18px;
    box-shadow: 0 18px 40px rgba(0,0,0,0.28);
}
.hub-kicker {
    font-size: 0.72rem;
    color: #9fb3c8;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 8px;
    font-weight: 700;
}
.hub-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 3rem;
    letter-spacing: 0.12em;
    color: #f8fafc;
    margin: 0;
}
.hub-sub {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 8px 0 0;
    max-width: 760px;
}
.hub-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}
.hub-stat {
    background: rgba(15,23,42,0.88);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 18px;
    padding: 18px 16px;
}
.hub-stat-label {
    color: #94a3b8;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin-bottom: 10px;
    font-weight: 700;
}
.hub-stat-value {
    color: #f8fafc;
    font-size: 1.8rem;
    font-weight: 800;
}
.hub-panel {
    background: rgba(15,23,42,0.82);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 20px;
    padding: 18px 18px 16px;
    height: 100%;
}
.hub-panel-title {
    color: #f8fafc;
    font-size: 1rem;
    font-weight: 800;
    margin-bottom: 4px;
}
.hub-panel-sub {
    color: #94a3b8;
    font-size: 0.8rem;
    margin-bottom: 14px;
}
.hub-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 5px 10px;
    border: 1px solid rgba(148,163,184,0.18);
    background: rgba(30,41,59,0.9);
    color: #cbd5e1;
    font-size: 0.75rem;
    margin: 0 8px 8px 0;
}

/* Gym badge mini-rack in hub */
.hub-gym-rack {
    background: rgba(15,23,42,0.82);
    border: 1px solid rgba(245,158,11,0.18);
    border-radius: 18px;
    padding: 14px 18px;
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px;
}
.hub-gym-label {
    color: #94a3b8; font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; white-space: nowrap;
    margin-right: 4px;
}
.hub-gym-count {
    color: #f59e0b; font-size: 1rem; font-weight: 800;
    white-space: nowrap; margin-right: 12px;
}
.hub-gym-badges { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.hub-gym-dot {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    transition: transform 0.1s;
}
.hub-gym-dot.locked { background: #1c2332; filter: grayscale(1) opacity(0.3); }

/* Rival banner */
.hub-rival {
    border-radius: 18px;
    padding: 14px 20px;
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px;
}
.hub-rival.ahead   { background: rgba(46,160,67,0.1);  border: 1px solid rgba(46,160,67,0.35); }
.hub-rival.behind  { background: rgba(255,136,0,0.08); border: 1px solid rgba(255,136,0,0.35); }
.hub-rival.tied    { background: rgba(148,163,184,0.07); border: 1px solid rgba(148,163,184,0.2); }
.hub-rival-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; margin-bottom: 2px; }
.hub-rival-msg   { font-size: 0.88rem; color: #e6edf3; font-weight: 600; }
.hub-rival-sub   { font-size: 0.72rem; color: #8b949e; margin-top: 2px; }

/* Weekly challenge banner */
.hub-challenge {
    background: rgba(88,166,255,0.06);
    border: 1px solid rgba(88,166,255,0.25);
    border-radius: 18px;
    padding: 16px 20px;
    margin-bottom: 18px;
}
.hub-challenge.done {
    background: rgba(46,160,67,0.08);
    border-color: rgba(46,160,67,0.35);
}
.hub-challenge-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;
    letter-spacing: 0.18em; font-weight: 700; margin-bottom: 4px; }
.hub-challenge-title { font-size: 0.92rem; font-weight: 700; color: #e6edf3; margin-bottom: 8px; }
.hub-challenge-bar-wrap { background: #21262d; border-radius: 9999px; height: 8px;
    overflow: hidden; margin-bottom: 6px; }
.hub-challenge-bar { height: 100%; border-radius: 9999px; transition: width 0.3s ease; }
.hub-challenge-sub { font-size: 0.72rem; color: #8b949e; }
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


def _render_snapshot() -> None:
    team = get_cached_user_team(user_id)
    streak = get_cached_checkin_streak(user_id)
    battles_used = get_cached_daily_battle_count(user_id)
    remaining = max(0, _MAX_BATTLES_PER_DAY - battles_used)
    missions = get_cached_user_missions(user_id)
    daily = missions.get("daily", [])
    daily_done = sum(1 for mission in daily if mission.get("completed"))
    coins = profile["coins"] if profile else 0

    st.markdown(
        f"""
<div class="hub-grid">
  <div class="hub-stat">
    <div class="hub-stat-label">Moedas</div>
    <div class="hub-stat-value">🪙 {coins:,}</div>
  </div>
  <div class="hub-stat">
    <div class="hub-stat-label">Equipe</div>
    <div class="hub-stat-value">{len(team)}/6</div>
  </div>
  <div class="hub-stat">
    <div class="hub-stat-label">Streak</div>
    <div class="hub-stat-value">🔥 {streak}</div>
  </div>
  <div class="hub-stat">
    <div class="hub-stat-label">Arena Hoje</div>
    <div class="hub-stat-value">{remaining}/{_MAX_BATTLES_PER_DAY}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

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
<div class="hub-panel">
  <div class="hub-panel-title">Rotina do dia</div>
  <div class="hub-panel-sub">Acesse as áreas mais usadas sem depender da sidebar.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button("📅 Fazer check-in", use_container_width=True):
                st.switch_page("pages/calendario.py")
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
<div class="hub-panel">
  <div class="hub-panel-title">Missões diárias</div>
  <div class="hub-panel-sub" style="margin-bottom:10px">{daily_label} · {today.strftime("%d/%m")}</div>
  {mission_rows_html if mission_rows_html else "<div style='color:#8b949e;font-size:0.8rem'>Nenhuma missão carregada.</div>"}
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
<div class="hub-panel">
  <div class="hub-panel-title">{section['icon']} {section['title']}</div>
  <div class="hub-panel-sub">{section['desc']}</div>
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
<div class="hub-hero">
  <div class="hub-kicker">Dashboard</div>
  <h1 class="hub-title">LIMITBREAK COMMAND</h1>
  <p class="hub-sub">Bem-vindo, {trainer_name}. Use este hub para navegar entre treino, batalha, equipe e colecao com menos cliques e menos ruído visual.</p>
</div>
""",
    unsafe_allow_html=True,
)

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
        b64 = get_image_as_base64(rival["rival_sprite"])
        if b64:
            sprite_html = (
                f"<img src='data:image/png;base64,{b64}' "
                f"style='width:40px;height:40px;object-fit:contain;image-rendering:pixelated'>"
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
    bar_color   = "#2ea043" if completed else "#58a6ff"
    css_extra   = " done" if completed else ""

    goal_type   = ch.get("goal_type", "total_xp")
    unit        = "XP" if goal_type == "total_xp" else ("sessões" if goal_type == "total_workouts" else "séries")
    progress_text = f"{current:,} / {goal_val:,} {unit} &nbsp;·&nbsp; 🥚 Recompensa: 1 ovo"

    st.markdown(
        f"<div class='hub-challenge{css_extra}'>"
        f"<div class='hub-challenge-label'>🌍 Desafio da Semana</div>"
        f"<div class='hub-challenge-title'>Meta: {ch['description']}</div>"
        f"<div class='hub-challenge-bar-wrap'>"
        f"<div class='hub-challenge-bar' style='width:{pct:.1f}%;background:{bar_color}'></div>"
        f"</div>"
        f"<div class='hub-challenge-sub'>{progress_text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if completed and not claimed and contributed > 0:
        if st.button("🥚 Coletar Ovo do Desafio", use_container_width=False):
            ok, msg, reward = claim_weekly_challenge_reward(user_id)
            clear_user_cache()
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
