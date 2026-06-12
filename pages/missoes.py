import datetime
import html
import streamlit as st
from utils.app_cache import clear_user_cache, get_cached_user_missions
from utils.db import (
    claim_mission_reward,
    get_image_as_base64, get_user_team,
)
from utils.design_system import render_empty_state, render_page_heading

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.user_id

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.section-title {
    font-family: var(--font-display);
    font-size: 1.4rem; letter-spacing: 3px; color: var(--text-body);
    margin: 24px 0 12px; text-transform: uppercase;
}
.section-divider {
    border: none; border-top: 1px solid var(--bg-border-soft); margin: 0 0 16px;
}

/* Mission card */
.mission-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-lg);
    padding: 18px 20px 14px;
    margin-bottom: 12px;
    position: relative;
    transition: border-color 0.15s ease, transform 0.15s ease;
}
.mission-card:hover { transform: translateY(-1px); }
.mission-card.completed {
    border-color: rgba(184,248,47,0.5);
    background: rgba(184,248,47,0.04);
}
.mission-card.claimed {
    border-color: var(--bg-border-soft);
    opacity: 0.55;
}
.mission-card.weekly {
    border-color: rgba(126,105,255,0.4);
    background: rgba(126,105,255,0.05);
}
.mission-card.weekly.completed {
    border-color: rgba(126,105,255,0.7);
    background: rgba(126,105,255,0.1);
}

.mission-icon { font-size: 1.5rem; margin-right: 8px; }
.mission-label {
    font-size: 0.95rem; font-weight: 700; color: var(--text-body);
    display: inline; vertical-align: middle;
}
.mission-reward {
    font-size: 0.75rem; color: var(--text-faint);
    margin-top: 6px; letter-spacing: 0.5px;
}
.progress-label {
    font-size: 0.68rem; color: var(--text-dim); margin-top: 4px;
    text-align: right; font-family: var(--font-mono);
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _time_until_midnight_brt() -> str:
    now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    midnight = (now_brt + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    secs = max(int((midnight - now_brt).total_seconds()), 0)
    h, rem = divmod(secs, 3600)
    m = rem // 60
    return f"{h:02d}:{m:02d}"


def _time_until_monday_brt() -> str:
    now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    days_ahead = (7 - now_brt.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = (now_brt + datetime.timedelta(days=days_ahead)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    secs = max(int((next_monday - now_brt).total_seconds()), 0)
    d = secs // 86400
    h, rem = divmod(secs % 86400, 3600)
    m = rem // 60
    if d > 0:
        return f"{d}d {h:02d}:{m:02d}"
    return f"{h:02d}:{m:02d}"


# ── Header ────────────────────────────────────────────────────────────────────

render_page_heading("Missões", "Progressão diária")

# ── Load missions ─────────────────────────────────────────────────────────────

missions = get_cached_user_missions(user_id)
daily   = missions.get("daily", [])
weekly  = missions.get("weekly", [])


def _mission_card_html(m: dict, mtype: str) -> str:
    slug        = m.get("slug", "")
    icon        = html.escape(str(m.get("icon", "🎯")))
    label       = html.escape(str(m.get("label", slug)))
    reward_lbl  = html.escape(str(m.get("reward_label", "")))
    progress    = m.get("progress", 0)
    target      = m.get("target", 1)
    completed   = m.get("completed", False)
    claimed     = m.get("reward_claimed", False)

    pct = min(int(progress / target * 100), 100) if target > 0 else 100
    extra_cls = "claimed" if claimed else ("completed" if completed else "")
    card_cls  = f"mission-card {mtype} {extra_cls}".strip()

    fill_cls  = "daily" if mtype == "daily" else "weekly"

    status_badge = ""
    if claimed:
        status_badge = "<span style='float:right;font-size:0.7rem;color:var(--text-dim);font-weight:700'>✓ Coletada</span>"
    elif completed:
        status_badge = "<span style='float:right;font-size:0.7rem;color:var(--color-lime);font-weight:700'>✅ Completa</span>"

    bar_tone = "" if fill_cls == "daily" else "purple"
    return (
        f"<div class='{card_cls}'>"
        f"{status_badge}"
        f"<span class='mission-icon'>{icon}</span>"
        f"<span class='mission-label'>{label}</span>"
        f"<div class='mission-reward'>Recompensa: <span class='lb-badge'>{reward_lbl}</span></div>"
        f"<div class='lb-progress' style='margin-top:10px'>"
        f"<span class='{bar_tone}' style='width:{pct}%'></span>"
        f"</div>"
        f"<div class='progress-label'>{progress} / {target}</div>"
        f"</div>"
    )


def _show_claim_result(result: dict) -> None:
    rtype  = result.get("type", "")
    label  = result.get("label", "")
    body   = ""

    if rtype == "coins":
        body = f"🪙 {label} adicionados à sua conta."
    elif rtype == "xp":
        xp_res = result.get("xp_result") or {}
        levels = xp_res.get("levels_gained", 0)
        body   = f"⚡ {label} concedidos ao seu Pokémon principal."
        if levels:
            body += f" Subiu {levels} nível{'s' if levels > 1 else ''}!"
    elif rtype == "stone":
        stone = result.get("slug", "").replace("-", " ").title()
        body  = f"💎 {stone} adicionada à sua Mochila."
    elif rtype == "vitamin":
        vit  = result.get("slug", "").replace("-", " ").title()
        body = f"💊 {vit} adicionada à sua Mochila."
    elif rtype == "loot_box":
        body = "🎁 Loot Box adicionada à sua Mochila! Abra na Loja."
    else:
        body = label

    st.markdown(
        f"<div class='lb-banner lime'><div>"
        f"<strong>🎉 Recompensa coletada!</strong><br>{body}"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ── Summary bar ───────────────────────────────────────────────────────────────

d_done  = sum(1 for m in daily  if m.get("completed"))
d_total = len(daily)
w       = weekly[0] if weekly else None
w_pct   = 0
if w:
    _tgt = w.get("target", 1)
    w_pct = min(int(w.get("progress", 0) / _tgt * 100), 100) if _tgt > 0 else 100

_d_bar_pct = int(d_done / d_total * 100) if d_total else 0

st.markdown(
    f"""
<div class='lb-stat-row'>
  <div class='lb-stat-tile' style='min-width:160px'>
    <div class='val'>{d_done}/{d_total}</div>
    <div class='lbl'>Diárias</div>
    <div class='lb-progress' style='height:6px;margin-top:8px'>
      <span style='width:{_d_bar_pct}%'></span>
    </div>
    <div style='font-size:0.6rem;color:var(--text-dim);margin-top:4px;font-family:var(--font-mono)'>
      ↺ renova em {_time_until_midnight_brt()}
    </div>
  </div>
  <div class='lb-stat-tile tone-purple' style='min-width:160px'>
    <div class='val'>{w_pct}%</div>
    <div class='lbl'>Semanal</div>
    <div class='lb-progress' style='height:6px;margin-top:8px'>
      <span class='purple' style='width:{w_pct}%'></span>
    </div>
    <div style='font-size:0.6rem;color:var(--text-dim);margin-top:4px;font-family:var(--font-mono)'>
      ↺ renova em {_time_until_monday_brt()}
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Daily missions ────────────────────────────────────────────────────────────

st.markdown("<div class='section-title'>📅 Missões Diárias</div>", unsafe_allow_html=True)
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

if not daily:
    render_empty_state("🎯", "Nenhuma missão diária", "Tente recarregar a página.")
else:
    for m in daily:
        mid       = m["id"]
        completed = m.get("completed", False)
        claimed   = m.get("reward_claimed", False)

        st.markdown(_mission_card_html(m, "daily"), unsafe_allow_html=True)

        if completed and not claimed:
            if st.button(
                f"🎁 Coletar recompensa",
                key=f"claim_daily_{mid}",
                type="primary",
                use_container_width=False,
            ):
                ok, msg, reward = claim_mission_reward(user_id, mid)
                if ok and reward:
                    clear_user_cache(user_id)
                    st.toast("🎉 Recompensa coletada!", icon="✅")
                    _show_claim_result(reward)
                    st.rerun()
                else:
                    st.error(msg)

# ── Weekly mission ────────────────────────────────────────────────────────────

st.markdown("<div class='section-title'>📆 Missão Semanal</div>", unsafe_allow_html=True)
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

if not weekly:
    render_empty_state("📆", "Nenhuma missão semanal", "Tente recarregar a página.")
else:
    for m in weekly:
        mid       = m["id"]
        completed = m.get("completed", False)
        claimed   = m.get("reward_claimed", False)
        pstart    = m.get("period_start")

        week_label = ""
        if pstart:
            import datetime
            week_end = pstart + datetime.timedelta(days=6)
            week_label = f"Semana de {pstart.strftime('%d/%m')} a {week_end.strftime('%d/%m')}"

        if week_label:
            st.caption(week_label)

        st.markdown(_mission_card_html(m, "weekly"), unsafe_allow_html=True)

        if completed and not claimed:
            if st.button(
                f"🎁 Coletar recompensa semanal",
                key=f"claim_weekly_{mid}",
                type="primary",
                use_container_width=False,
            ):
                ok, msg, reward = claim_mission_reward(user_id, mid)
                if ok and reward:
                    clear_user_cache(user_id)
                    st.toast("🎉 Recompensa semanal coletada!", icon="✅")
                    _show_claim_result(reward)
                    st.rerun()
                else:
                    st.error(msg)

# ── Tip ───────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"⏱ Diárias renovam em **{_time_until_midnight_brt()}** · "
    f"Semanal renova em **{_time_until_monday_brt()}** (horário de Brasília)"
)
