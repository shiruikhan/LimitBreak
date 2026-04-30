import datetime
import streamlit as st
from utils.app_cache import clear_user_cache, get_cached_user_missions
from utils.db import (
    claim_mission_reward,
    get_image_as_base64, get_user_team,
)

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.user_id

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.missions-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.missions-sub {
    color: #8b949e; font-size: 0.85rem; margin: 0 0 20px;
    letter-spacing: 2px; text-transform: uppercase;
}

.section-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 1.4rem; letter-spacing: 3px; color: #e6edf3;
    margin: 24px 0 12px; text-transform: uppercase;
}
.section-divider {
    border: none; border-top: 1px solid #21262d; margin: 0 0 16px;
}

/* Mission card */
.mission-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 18px 20px 14px;
    margin-bottom: 12px;
    position: relative;
    transition: border-color 0.15s ease;
}
.mission-card.completed {
    border-color: rgba(184,248,47,0.5);
    background: rgba(184,248,47,0.04);
}
.mission-card.claimed {
    border-color: #21262d;
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
    font-size: 0.95rem; font-weight: 700; color: #e6edf3;
    display: inline; vertical-align: middle;
}
.mission-reward {
    font-size: 0.75rem; color: #8b949e;
    margin-top: 6px; letter-spacing: 0.5px;
}
.reward-badge {
    display: inline-block;
    background: #21262d; border: 1px solid #30363d;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.72rem; font-weight: 700; color: #B8F82F;
    letter-spacing: 0.5px;
}

/* Progress bar */
.progress-wrap {
    background: #21262d; border-radius: 6px;
    height: 8px; margin-top: 10px; overflow: hidden;
}
.progress-fill {
    height: 100%; border-radius: 6px;
    transition: width 0.3s ease;
}
.progress-fill.daily  { background: linear-gradient(90deg, #B8F82F, #7AB21A); }
.progress-fill.weekly { background: linear-gradient(90deg, #7e69ff, #5b42e8); }
.progress-label {
    font-size: 0.68rem; color: #484f58; margin-top: 4px;
    text-align: right; font-family: "JetBrains Mono", monospace;
}

/* Claim result card */
.claim-card {
    background: rgba(184,248,47,0.08);
    border: 1px solid rgba(184,248,47,0.35);
    border-radius: 12px; padding: 14px 18px; margin-top: 8px;
}
.claim-title { font-weight: 700; color: #B8F82F; font-size: 0.9rem; }
.claim-body  { color: #8b949e; font-size: 0.82rem; margin-top: 4px; }

/* Empty state */
.empty-missions {
    background: #161b22; border: 1px dashed #30363d;
    border-radius: 16px; padding: 32px; text-align: center;
    color: #484f58; font-size: 0.9rem;
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

st.markdown("""
<p class='missions-sub'>Progressão diária</p>
<h1 class='missions-title'>Missões</h1>
""", unsafe_allow_html=True)

# ── Load missions ─────────────────────────────────────────────────────────────

missions = get_cached_user_missions(user_id)
daily   = missions.get("daily", [])
weekly  = missions.get("weekly", [])


def _mission_card_html(m: dict, mtype: str) -> str:
    slug        = m.get("slug", "")
    icon        = m.get("icon", "🎯")
    label       = m.get("label", slug)
    reward_lbl  = m.get("reward_label", "")
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
        status_badge = "<span style='float:right;font-size:0.7rem;color:#484f58;font-weight:700'>✓ Coletada</span>"
    elif completed:
        status_badge = "<span style='float:right;font-size:0.7rem;color:#B8F82F;font-weight:700'>✅ Completa</span>"

    return f"""
<div class='{card_cls}'>
    {status_badge}
    <span class='mission-icon'>{icon}</span>
    <span class='mission-label'>{label}</span>
    <div class='mission-reward'>Recompensa: <span class='reward-badge'>{reward_lbl}</span></div>
    <div class='progress-wrap'>
        <div class='progress-fill {fill_cls}' style='width:{pct}%'></div>
    </div>
    <div class='progress-label'>{progress} / {target}</div>
</div>
"""


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
        f"<div class='claim-card'>"
        f"<div class='claim-title'>🎉 Recompensa coletada!</div>"
        f"<div class='claim-body'>{body}</div>"
        f"</div>",
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
<div style='display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap'>
  <div style='flex:1;min-width:160px;background:#161b22;border:1px solid #30363d;
              border-radius:14px;padding:14px 18px'>
    <div style='font-family:"Bebas Neue",sans-serif;font-size:1.6rem;
                color:#B8F82F;letter-spacing:2px'>{d_done}/{d_total}</div>
    <div style='font-size:0.62rem;color:#8b949e;text-transform:uppercase;
                letter-spacing:2px;font-weight:700;margin-top:2px'>Diárias</div>
    <div style='background:#21262d;border-radius:4px;height:6px;margin-top:8px;overflow:hidden'>
      <div style='width:{_d_bar_pct}%;height:100%;border-radius:4px;
                  background:linear-gradient(90deg,#B8F82F,#7AB21A)'></div>
    </div>
    <div style='font-size:0.6rem;color:#484f58;margin-top:4px;font-family:"JetBrains Mono",monospace'>
      ↺ renova em {_time_until_midnight_brt()}
    </div>
  </div>
  <div style='flex:1;min-width:160px;background:#161b22;border:1px solid #30363d;
              border-radius:14px;padding:14px 18px'>
    <div style='font-family:"Bebas Neue",sans-serif;font-size:1.6rem;
                color:#7e69ff;letter-spacing:2px'>{w_pct}%</div>
    <div style='font-size:0.62rem;color:#8b949e;text-transform:uppercase;
                letter-spacing:2px;font-weight:700;margin-top:2px'>Semanal</div>
    <div style='background:#21262d;border-radius:4px;height:6px;margin-top:8px;overflow:hidden'>
      <div style='width:{w_pct}%;height:100%;border-radius:4px;
                  background:linear-gradient(90deg,#7e69ff,#5b42e8)'></div>
    </div>
    <div style='font-size:0.6rem;color:#484f58;margin-top:4px;font-family:"JetBrains Mono",monospace'>
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
    st.markdown("<div class='empty-missions'>Nenhuma missão diária disponível. Tente recarregar a página.</div>", unsafe_allow_html=True)
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
                    clear_user_cache()
                    st.toast("🎉 Recompensa coletada!", icon="✅")
                    _show_claim_result(reward)
                    st.rerun()
                else:
                    st.error(msg)

# ── Weekly mission ────────────────────────────────────────────────────────────

st.markdown("<div class='section-title'>📆 Missão Semanal</div>", unsafe_allow_html=True)
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

if not weekly:
    st.markdown("<div class='empty-missions'>Nenhuma missão semanal disponível. Tente recarregar a página.</div>", unsafe_allow_html=True)
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
                    clear_user_cache()
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
