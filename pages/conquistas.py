import streamlit as st
from utils.app_cache import get_cached_user_achievements
from utils.db import check_and_award_achievements
from utils.achievements import CATALOG, CATEGORY_META, GYM_BADGES, badge_url

# ── Auth guard ────────────────────────────────────────────────────────────────

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Faça login para ver suas conquistas.")
    st.stop()

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.cq-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.cq-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px;
          letter-spacing: 2px; text-transform: uppercase; }

/* Progress bar */
.cq-progress-wrap { margin: 12px 0 20px; }
.cq-progress-track {
    background: #161b22; border-radius: 99px; height: 8px;
    border: 1px solid #21262d; overflow: hidden;
}
.cq-progress-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #B8F82F, #7AB21A);
    transition: width 0.4s ease;
}
.cq-progress-label {
    font-size: 0.75rem; color: #8b949e; margin-top: 6px;
    font-family: "JetBrains Mono", monospace;
}
.cq-progress-label span { color: #B8F82F; font-weight: 700; }

/* New-unlock banner */
.cq-new-banner {
    background: rgba(184,248,47,0.08); border: 1px solid rgba(184,248,47,0.3);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;
}
.cq-new-banner-title {
    font-family: "Bebas Neue", sans-serif; font-size: 1.1rem;
    color: #B8F82F; letter-spacing: 2px; margin-bottom: 10px;
}
.cq-loot-rows { display: flex; flex-direction: column; gap: 8px; }
.cq-loot-row {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px 12px;
}
.cq-loot-ach { font-size: 0.85rem; color: #e6edf3; font-weight: 600; }
.cq-loot-reward {
    font-size: 0.8rem; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; white-space: nowrap;
}
.cq-loot-common  { background: rgba(184,248,47,0.15); color: #B8F82F; border: 1px solid rgba(184,248,47,0.35); }
.cq-loot-rare    { background: rgba(59,130,246,0.15);  color: #60a5fa; border: 1px solid rgba(59,130,246,0.35); }
.cq-loot-ultra   { background: rgba(168,85,247,0.15);  color: #c084fc; border: 1px solid rgba(168,85,247,0.35); }

/* Achievement grid */
.ach-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px; margin-top: 12px;
}
.ach-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 14px;
    padding: 16px; display: flex; flex-direction: column; gap: 10px;
    transition: border-color 0.2s, transform 0.15s;
}
.ach-card:hover { border-color: #30363d; transform: translateY(-2px); }
.ach-card.unlocked { border-color: #30363d; }
.ach-card.locked   { opacity: 0.45; }

.ach-badge-img {
    width: 100%; height: auto; border-radius: 6px;
    display: block; image-rendering: auto;
}
.ach-body { display: flex; flex-direction: column; gap: 4px; }
.ach-icon-row { display: flex; align-items: center; gap: 8px; }
.ach-icon { font-size: 1.3rem; }
.ach-new-pill {
    background: #B8F82F; color: #0d1117; font-size: 0.55rem;
    font-weight: 700; letter-spacing: 1.5px; padding: 2px 7px;
    border-radius: 99px; text-transform: uppercase; font-family: "Space Grotesk", sans-serif;
}
.ach-desc { font-size: 0.8rem; color: #8b949e; line-height: 1.4; margin: 0; }
.ach-date { font-size: 0.7rem; color: #484f58;
            font-family: "JetBrains Mono", monospace; margin: 0; }
.ach-date.unlocked { color: #B8F82F; }

/* Category stat chips below tabs */
.cat-stats { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.cat-chip {
    font-size: 0.7rem; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; letter-spacing: 0.5px;
}

/* Gym badge rack */
.gym-rack {
    display: flex; flex-wrap: wrap; gap: 16px;
    background: rgba(15,23,42,0.7); border: 1px solid rgba(245,158,11,0.2);
    border-radius: 20px; padding: 24px 28px; margin-bottom: 20px;
    align-items: center;
}
.gym-rack-title {
    font-family: "Bebas Neue", sans-serif; font-size: 0.75rem;
    color: #f59e0b; letter-spacing: 3px; text-transform: uppercase;
    width: 100%; margin-bottom: 4px;
}
.gym-badge-wrap {
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    cursor: default;
}
.gym-badge-circle {
    width: 56px; height: 56px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem;
    border: 2px solid transparent;
    transition: transform 0.15s, box-shadow 0.15s;
}
.gym-badge-circle.unlocked {
    box-shadow: 0 0 14px 3px var(--badge-glow);
    border-color: var(--badge-color);
}
.gym-badge-circle.locked {
    background: #1c2332 !important;
    filter: grayscale(1) opacity(0.35);
}
.gym-badge-label {
    font-size: 0.62rem; color: #94a3b8; font-weight: 600;
    letter-spacing: 0.04em; text-align: center; max-width: 64px;
}
.gym-badge-label.unlocked { color: #f59e0b; }
.gym-badge-progress {
    font-family: "Bebas Neue", sans-serif; font-size: 1.1rem;
    color: #f59e0b; letter-spacing: 2px; margin-left: auto;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# ── Check for newly unlocked achievements ─────────────────────────────────────

# Merge any achievements triggered by event pages (list[dict] with slug+loot)
pending: list[dict] = st.session_state.pop("new_achievements_pending", [])
# Also run a fresh check on page load (catches anything missed)
fresh: list[dict] = check_and_award_achievements(user_id)
seen_slugs = {a["slug"] for a in pending}
all_new: list[dict] = pending + [a for a in fresh if a["slug"] not in seen_slugs]
all_new_slugs = {a["slug"] for a in all_new}

# ── Load data ─────────────────────────────────────────────────────────────────

unlocked: dict[str, object] = get_cached_user_achievements(user_id)
total = len(CATALOG)
earned = len(unlocked)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<p class="cq-sub">LimitBreak</p>', unsafe_allow_html=True)
st.markdown('<p class="cq-title">Conquistas</p>', unsafe_allow_html=True)

pct = int(earned / total * 100) if total else 0
st.markdown(f"""
<div class="cq-progress-wrap">
  <div class="cq-progress-track">
    <div class="cq-progress-fill" style="width:{pct}%"></div>
  </div>
  <p class="cq-progress-label">
    <span>{earned}</span> / {total} desbloqueadas &nbsp;·&nbsp; <span>{pct}%</span>
  </p>
</div>
""", unsafe_allow_html=True)

# ── New-unlock banner ─────────────────────────────────────────────────────────

if all_new:
    _rarity_css = {"common": "cq-loot-common", "rare": "cq-loot-rare", "ultra_rare": "cq-loot-ultra"}
    _rarity_icon = {"common": "🎁", "rare": "💙", "ultra_rare": "💜"}

    rows_html = ""
    for item in all_new:
        slug = item["slug"]
        if slug not in CATALOG:
            continue
        ach = CATALOG[slug]
        loot = item.get("loot", {})
        rarity = loot.get("rarity", "common")
        loot_label = loot.get("label", "")
        loot_icon = _rarity_icon.get(rarity, "🎁")
        loot_css = _rarity_css.get(rarity, "cq-loot-common")
        rows_html += (
            f'<div class="cq-loot-row">'
            f'<span class="cq-loot-ach">{ach["icon"]} {ach["name"]}</span>'
            f'<span class="cq-loot-reward {loot_css}">{loot_icon} {loot_label}</span>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="cq-new-banner">
      <div class="cq-new-banner-title">🎉 NOVA CONQUISTA + LOOT BOX!</div>
      <div class="cq-loot-rows">{rows_html}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Tab filter ────────────────────────────────────────────────────────────────

cat_order = ["todas"] + list(CATEGORY_META.keys())
cat_labels = {"todas": "🏅 Todas"} | {
    k: f"{v['icon']} {v['display']}" for k, v in CATEGORY_META.items()
}

tabs = st.tabs([cat_labels[c] for c in cat_order])

# ── Renderer ──────────────────────────────────────────────────────────────────

def _date_str(dt) -> str:
    if dt is None:
        return ""
    try:
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(dt)


def _render_grid(slugs: list[str]) -> None:
    if not slugs:
        st.markdown('<p style="color:#484f58;font-size:0.9rem;">Nenhuma conquista nesta categoria.</p>',
                    unsafe_allow_html=True)
        return

    cards_html = ""
    for slug in slugs:
        if slug not in CATALOG:
            continue
        ach = CATALOG[slug]
        is_unlocked = slug in unlocked
        is_new = slug in all_new_slugs
        unlock_dt = unlocked.get(slug)

        card_cls = "unlocked" if is_unlocked else "locked"
        img_src = badge_url(slug, is_unlocked)
        new_pill = '<span class="ach-new-pill">NOVO</span>' if is_new else ""
        date_cls = "unlocked" if is_unlocked else ""
        date_txt = (
            f"🔓 {_date_str(unlock_dt)}" if is_unlocked else "🔒 Bloqueado"
        )

        # Mantemos o código legível, mas removemos as quebras de linha no final
        cards_html += f"""
        <div class="ach-card {card_cls}">
            <img class="ach-badge-img" src="{img_src}" loading="lazy" alt="{ach['name']}">
            <div class="ach-body">
                <div class="ach-icon-row">
                    <span class="ach-icon">{ach['icon']}</span>
                    {new_pill}
                </div>
                <p class="ach-desc">{ach['description']}</p>
                <p class="ach-date {date_cls}">{date_txt}</p>
            </div>
        </div>
        """.replace('\n', '')

    st.markdown(f'<div class="ach-grid">{cards_html}</div>', unsafe_allow_html=True)


def _render_gym_rack() -> None:
    """Render the 8 Kanto gym badges as a visual badge rack."""
    earned_slugs = {b["slug"] for b in GYM_BADGES if b["slug"] in unlocked}
    count = len(earned_slugs)
    total = len(GYM_BADGES)

    badges_html = ""
    for b in GYM_BADGES:
        slug = b["slug"]
        is_unlocked = slug in unlocked
        color = b["color"]
        css_cls = "unlocked" if is_unlocked else "locked"
        glow = color + "88"
        bg_style = f"background:{color}22;" if is_unlocked else ""
        style = (
            f"style='--badge-color:{color};--badge-glow:{glow};{bg_style}'"
            if is_unlocked
            else "style=''"
        )
        label_cls = "unlocked" if is_unlocked else ""
        tooltip = b["desc"]
        badges_html += (
            f"<div class='gym-badge-wrap' title='{tooltip}'>"
            f"<div class='gym-badge-circle {css_cls}' {style}>{b['icon']}</div>"
            f"<span class='gym-badge-label {label_cls}'>{b['name']}</span>"
            f"</div>"
        )

    st.markdown(
        f"""
<div class="gym-rack">
  <div style="display:flex;align-items:center;width:100%;margin-bottom:8px">
    <span class="gym-rack-title">Insígnias de Ginásio — Kanto</span>
    <span class="gym-badge-progress">{count}/{total}</span>
  </div>
  {badges_html}
</div>
""",
        unsafe_allow_html=True,
    )


def _category_progress(cat: str) -> tuple[int, int]:
    cat_slugs = [s for s, a in CATALOG.items() if a["category"] == cat]
    done = sum(1 for s in cat_slugs if s in unlocked)
    return done, len(cat_slugs)


# ── Render tabs ───────────────────────────────────────────────────────────────

for tab, cat_key in zip(tabs, cat_order):
    with tab:
        if cat_key == "todas":
            slugs = list(CATALOG.keys())
            # Sort: new first, then unlocked by date desc, then locked
            def _sort_key(s):
                if s in all_new_slugs:
                    return (0, "")
                if s in unlocked:
                    dt = unlocked[s]
                    return (1, str(dt))
                return (2, s)
            slugs.sort(key=_sort_key)
        else:
            meta = CATEGORY_META[cat_key]
            slugs = [s for s, a in CATALOG.items() if a["category"] == cat_key]
            done, total_cat = _category_progress(cat_key)
            chip_color = meta["color"]
            st.markdown(
                f'<div class="cat-stats">'
                f'<span class="cat-chip" style="background:#{chip_color}22;color:#{chip_color};'
                f'border:1px solid #{chip_color}44;">'
                f'{done}/{total_cat} desbloqueadas</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if cat_key == "ginasio":
                _render_gym_rack()

        _render_grid(slugs)
