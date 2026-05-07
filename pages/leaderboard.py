import datetime
import streamlit as st
from utils.app_cache import get_cached_user_profile
from utils.db import (
    sprite_img_tag,
    get_leaderboard_pokemon_count,
    get_leaderboard_checkin_streak,
    get_leaderboard_workout_xp,
    _today_brt,
)

MONTH_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.lb-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.lb-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px; letter-spacing: 2px; text-transform: uppercase; }

.month-nav {
    display: flex; align-items: center; justify-content: center;
    gap: 16px; margin-bottom: 20px;
}
.month-label {
    font-size: 1.1rem; font-weight: 700; color: #e6edf3;
    min-width: 200px; text-align: center;
}

.lb-table {
    width: 100%; border-collapse: collapse; margin-top: 8px;
}
.lb-table th {
    font-size: 0.65rem; font-weight: 700; color: #484f58;
    text-transform: uppercase; letter-spacing: 2px;
    padding: 8px 12px; border-bottom: 1px solid #21262d; text-align: left;
}
.lb-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 12px; border-bottom: 1px solid #161b22;
    transition: background 0.15s;
}
.lb-row:hover { background: #161b22; border-radius: 8px; }
.lb-row.is-me { background: rgba(184,248,47,0.07); border-radius: 8px; border: 1px solid rgba(184,248,47,0.2); margin: 2px 0; }

.lb-rank {
    font-family: "Bebas Neue", sans-serif; font-size: 1.5rem;
    letter-spacing: 2px; min-width: 36px; text-align: center;
}
.lb-rank.gold   { color: #FFD700; }
.lb-rank.silver { color: #C0C0C0; }
.lb-rank.bronze { color: #CD7F32; }
.lb-rank.other  { color: #484f58; }

.lb-sprite { width: 48px; height: 48px; object-fit: contain; image-rendering: pixelated; }
.lb-sprite-placeholder { width: 48px; height: 48px; }

.lb-info { flex: 1; min-width: 0; }
.lb-username { font-weight: 700; font-size: 0.95rem; color: #e6edf3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-pokemon  { font-size: 0.75rem; color: #8b949e; }
.lb-pokemon span { color: #B8F82F; font-weight: 700; }

.lb-value {
    font-family: "Bebas Neue", sans-serif; font-size: 1.6rem;
    letter-spacing: 2px; color: #B8F82F; min-width: 60px; text-align: right;
}
.lb-value-unit { font-size: 0.6rem; color: #484f58; text-transform: uppercase; letter-spacing: 1px; display: block; }

.lb-empty {
    text-align: center; color: #484f58; padding: 40px 0;
    font-size: 0.9rem; letter-spacing: 1px;
}
.lb-me-badge {
    background: rgba(184,248,47,0.15); color: #B8F82F;
    font-size: 0.6rem; font-weight: 700; letter-spacing: 1px;
    padding: 2px 6px; border-radius: 4px; text-transform: uppercase;
    border: 1px solid rgba(184,248,47,0.3);
}
</style>
""", unsafe_allow_html=True)

# ── Auth guard ────────────────────────────────────────────────────────────────

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Faça login para ver o ranking.")
    st.stop()

profile = get_cached_user_profile(user_id)

# ── Session state ─────────────────────────────────────────────────────────────

today = _today_brt()
for k, v in [("lb_year", today.year), ("lb_month", today.month)]:
    if k not in st.session_state:
        st.session_state[k] = v

year  = st.session_state.lb_year
month = st.session_state.lb_month

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<p class="lb-sub">LimitBreak</p>', unsafe_allow_html=True)
st.markdown('<p class="lb-title">Ranking</p>', unsafe_allow_html=True)

# ── Month navigation ──────────────────────────────────────────────────────────

col_prev, col_label, col_next = st.columns([1, 4, 1])

with col_prev:
    if st.button("◀", key="lb_prev", use_container_width=True):
        d = datetime.date(year, month, 1) - datetime.timedelta(days=1)
        st.session_state.lb_year  = d.year
        st.session_state.lb_month = d.month
        st.rerun()

with col_label:
    st.markdown(
        f'<div class="month-nav"><span class="month-label">{MONTH_PT[month]} {year}</span></div>',
        unsafe_allow_html=True,
    )

with col_next:
    at_current = (year == today.year and month == today.month)
    if st.button("▶", key="lb_next", use_container_width=True, disabled=at_current):
        d = datetime.date(year, month, 28) + datetime.timedelta(days=4)
        st.session_state.lb_year  = d.year
        st.session_state.lb_month = d.month
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_xp, tab_streak, tab_dex = st.tabs([
    "🏋️ XP de Treino",
    "🔥 Streak de Check-in",
    "📦 Coleção Pokémon",
])

# ── Shared renderer ───────────────────────────────────────────────────────────

def _rank_class(i: int) -> str:
    return ["gold", "silver", "bronze"][i] if i < 3 else "other"


def _rank_symbol(i: int) -> str:
    return ["🥇", "🥈", "🥉"][i] if i < 3 else str(i + 1)


def _render_leaderboard(rows: list[dict], unit: str) -> None:
    if not rows:
        st.markdown('<div class="lb-empty">Nenhum dado para este período.</div>', unsafe_allow_html=True)
        return

    for i, row in enumerate(rows):
        uid       = str(row["user_id"])
        is_me     = uid == user_id
        rank_cls  = _rank_class(i)
        symbol    = _rank_symbol(i)
        username  = row["username"] or "Treinador"
        value     = int(row["value"])
        lead_name = row.get("lead_pokemon") or "—"
        lead_lvl  = row.get("lead_level") or "?"
        me_cls    = " is-me" if is_me else ""
        lead_sprite = row.get("lead_sprite") or ""

        if lead_sprite:
            sprite_html = (
                sprite_img_tag(
                    lead_sprite,
                    width=56,
                    extra_style="height:56px;object-fit:contain",
                )
                or '<div class="lb-sprite-placeholder"></div>'
            )
        else:
            sprite_html = '<div class="lb-sprite-placeholder"></div>'

        me_badge = '<span class="lb-me-badge">Você</span> ' if is_me else ""

        st.markdown(f"""
        <div class="lb-row{me_cls}">
            <div class="lb-rank {rank_cls}">{symbol}</div>
            {sprite_html}
            <div class="lb-info">
                <div class="lb-username">{me_badge}{username}</div>
                <div class="lb-pokemon">Lv.<span>{lead_lvl}</span> {lead_name}</div>
            </div>
            <div class="lb-value">
                {value:,}
                <span class="lb-value-unit">{unit}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab: XP de treino ─────────────────────────────────────────────────────────

with tab_xp:
    st.markdown(f"##### XP ganho em treinos — {MONTH_PT[month]} {year}")
    rows_xp = get_leaderboard_workout_xp(year, month)
    _render_leaderboard(rows_xp, "XP")

# ── Tab: Streak de check-in ───────────────────────────────────────────────────

with tab_streak:
    st.markdown(f"##### Melhor streak de check-in — {MONTH_PT[month]} {year}")
    rows_streak = get_leaderboard_checkin_streak(year, month)
    _render_leaderboard(rows_streak, "dias")

# ── Tab: Coleção Pokémon ──────────────────────────────────────────────────────

with tab_dex:
    st.markdown("##### Total de Pokémon capturados (coleção completa)")
    rows_dex = get_leaderboard_pokemon_count()
    _render_leaderboard(rows_dex, "pkm")
