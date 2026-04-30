"""Compact sidebar quest tracker widget.

Call render_quest_sidebar(user_id) from inside a `with st.sidebar:` block on
any page to show live mission progress without navigating away.
"""
from __future__ import annotations
import datetime
import streamlit as st
from utils.db import get_user_missions

_CSS = """
<style>
.qt-wrap {
    background: rgba(22,27,34,0.9);
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 12px 14px 10px;
    margin: 10px 0 4px;
}
.qt-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px;
}
.qt-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 1rem; letter-spacing: 3px; color: #e6edf3;
}
.qt-summary {
    font-size: 0.62rem; color: #484f58;
    font-family: "JetBrains Mono", monospace;
}
.qt-section-label {
    font-size: 0.6rem; color: #8b949e;
    text-transform: uppercase; letter-spacing: 1.5px;
    margin: 8px 0 5px; font-weight: 700;
}
.qt-row {
    display: flex; align-items: center; gap: 5px;
    margin-bottom: 3px;
}
.qt-icon { font-size: 0.75rem; min-width: 14px; line-height: 1; }
.qt-label {
    font-size: 0.68rem; color: #c9d1d9;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; min-width: 0;
}
.qt-check-done  { font-size: 0.62rem; color: #B8F82F; font-weight: 700; }
.qt-check-claim { font-size: 0.62rem; color: #7e69ff; font-weight: 700; }
.qt-check-spent { font-size: 0.62rem; color: #484f58; }
.qt-bar-bg {
    background: #21262d; border-radius: 3px;
    height: 4px; overflow: hidden; margin-bottom: 6px;
}
.qt-bar-d { background: linear-gradient(90deg, #B8F82F, #7AB21A); height: 100%; border-radius: 3px; transition: width 0.3s; }
.qt-bar-w { background: linear-gradient(90deg, #7e69ff, #5b42e8); height: 100%; border-radius: 3px; transition: width 0.3s; }
.qt-divider { border: none; border-top: 1px solid #21262d; margin: 8px 0 6px; }
.qt-timer { font-size: 0.58rem; color: #484f58; font-family: "JetBrains Mono", monospace; margin-top: 2px; }
</style>
"""


def _time_until_midnight_brt() -> str:
    now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    midnight = (now_brt + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    secs = int((midnight - now_brt).total_seconds())
    h, rem = divmod(max(secs, 0), 3600)
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
    secs = int((next_monday - now_brt).total_seconds())
    d = secs // 86400
    h, rem = divmod(secs % 86400, 3600)
    m = rem // 60
    if d > 0:
        return f"{d}d {h:02d}:{m:02d}"
    return f"{h:02d}:{m:02d}"


def _mission_rows_html(missions: list[dict], bar_cls: str) -> str:
    parts = []
    for m in missions:
        icon = m.get("icon", "🎯")
        label = m.get("label", m.get("slug", ""))
        progress = m.get("progress", 0)
        target = m.get("target", 1)
        completed = m.get("completed", False)
        claimed = m.get("reward_claimed", False)
        pct = min(int(progress / target * 100), 100) if target > 0 else 100
        short = label[:26] + "…" if len(label) > 26 else label

        if claimed:
            badge = "<span class='qt-check-spent'>✓</span>"
        elif completed:
            badge = "<span class='qt-check-done'>★</span>"
        else:
            badge = f"<span class='qt-summary'>{progress}/{target}</span>"

        parts.append(
            f"<div class='qt-row'>"
            f"<span class='qt-icon'>{icon}</span>"
            f"<span class='qt-label'>{short}</span>"
            f"{badge}"
            f"</div>"
            f"<div class='qt-bar-bg'>"
            f"<div class='{bar_cls}' style='width:{pct}%'></div>"
            f"</div>"
        )
    return "".join(parts)


def render_quest_sidebar(user_id: str) -> None:
    """Renders a compact mission tracker. Must be called inside `with st.sidebar:`."""
    st.markdown(_CSS, unsafe_allow_html=True)

    missions = get_user_missions(user_id)
    daily = missions.get("daily", [])
    weekly = missions.get("weekly", [])

    d_done = sum(1 for m in daily if m.get("completed"))
    d_total = len(daily)
    w = weekly[0] if weekly else None
    w_pct = 0
    if w:
        tgt = w.get("target", 1)
        w_pct = min(int(w.get("progress", 0) / tgt * 100), 100) if tgt > 0 else 100

    html = [
        "<div class='qt-wrap'>",
        "<div class='qt-header'>",
        "<span class='qt-title'>Missões</span>",
        f"<span class='qt-summary'>{d_done}/{d_total} · {w_pct}%</span>",
        "</div>",
    ]

    if daily:
        html.append("<div class='qt-section-label'>📅 Diárias</div>")
        html.append(_mission_rows_html(daily, "qt-bar-d"))
        html.append(f"<div class='qt-timer'>↺ renova em {_time_until_midnight_brt()}</div>")

    if w:
        html.append("<hr class='qt-divider'>")
        html.append("<div class='qt-section-label'>📆 Semanal</div>")
        html.append(_mission_rows_html([w], "qt-bar-w"))
        html.append(f"<div class='qt-timer'>↺ renova em {_time_until_monday_brt()}</div>")

    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
