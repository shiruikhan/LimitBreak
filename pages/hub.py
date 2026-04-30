import streamlit as st

from utils.app_cache import (
    get_cached_checkin_streak,
    get_cached_daily_battle_count,
    get_cached_user_missions,
    get_cached_user_profile,
    get_cached_user_team,
)
from utils.db import _MAX_BATTLES_PER_DAY, _today_brt


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
        "title": "Pokédex",
        "desc": "Explore espécies e acompanhe a coleção pessoal.",
        "icon": "📖",
        "links": [
            ("Pokédex", "pages/pokedex.py"),
            ("Minha Pokédex", "pages/pokedex_pessoal.py"),
            ("Loja", "pages/loja.py"),
        ],
    },
]


@st.fragment
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
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("📅 Fazer check-in", use_container_width=True):
                st.switch_page("pages/calendario.py")
        with col_b:
            if st.button("⚔️ Abrir equipe", use_container_width=True):
                st.switch_page("pages/equipe.py")
        with col_c:
            if st.button("🥊 Ir para arena", use_container_width=True):
                st.switch_page("pages/batalha.py")
    with right:
        st.markdown(
            f"""
<div class="hub-panel">
  <div class="hub-panel-title">Missões diárias</div>
  <div class="hub-panel-sub">Progresso atual de hoje.</div>
  <span class="hub-chip">✅ {daily_done}/{len(daily)} concluídas</span>
  <span class="hub-chip">📅 {today.strftime("%d/%m/%Y")}</span>
</div>
""",
            unsafe_allow_html=True,
        )


@st.fragment
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
st.write("")
_render_sections()
