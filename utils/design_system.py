import html

import streamlit as st


_FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap">
"""

# Gradientes de título disponíveis em render_page_heading(tone=...)
_HEADING_TONES = {
    "lime":   "gradient-lime",
    "gold":   "gradient-gold",
    "red":    "gradient-red",
    "ember":  "gradient-ember",
    "purple": "gradient-purple",
    "blue":   "gradient-blue",
}


def inject_design_system(page_variant: str = "app") -> None:
    background = (
        "linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%)"
        if page_variant == "auth"
        else (
            "radial-gradient(1100px 700px at 85% -10%, rgba(184, 248, 47, 0.05), transparent 60%), "
            "linear-gradient(135deg, #0d1117 0%, #161b2e 55%, #0d1117 100%)"
        )
    )

    st.markdown(_FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(
        f"""
<style>
:root {{
    --color-lime: #B8F82F;
    --color-lime-dark: #7AB21A;
    --color-lime-light: #D4FC6B;
    --color-lime-glow: rgba(184, 248, 47, 0.18);
    --color-lime-ring: rgba(184, 248, 47, 0.15);
    --color-lime-shadow: rgba(184, 248, 47, 0.30);
    --color-gold: #FFC531;
    --color-ember: #FFB347;
    --color-red: #e94560;
    --color-purple: #BC8CFF;
    --color-blue: #58a6ff;
    --bg-base: #0d1117;
    --bg-sidebar: #0f172a;
    --bg-card: #161b22;
    --bg-surface: #21262d;
    --bg-login: #1a1a2e;
    --bg-border: #30363d;
    --bg-border-soft: #21262d;
    --surface-panel: rgba(15, 23, 42, 0.88);
    --surface-panel-lg: rgba(15, 23, 42, 0.82);
    --surface-sidebar: rgba(15, 23, 42, 0.92);
    --surface-brand: rgba(30, 41, 59, 0.96);
    --text-primary: #f8fafc;
    --text-body: #e6edf3;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --text-faint: #8b949e;
    --text-dim: #484f58;
    --text-kicker: #9fb3c8;
    --text-meta: #b8f82f;
    --color-success: #2ea043;
    --color-success-bg: rgba(46, 160, 67, 0.10);
    --color-success-border: rgba(46, 160, 67, 0.35);
    --color-warning: #f59e0b;
    --color-warning-bg: rgba(245, 158, 11, 0.14);
    --color-warning-border: rgba(245, 158, 11, 0.28);
    --color-danger: #f85149;
    --color-danger-bg: rgba(248, 81, 73, 0.08);
    --color-danger-border: rgba(248, 81, 73, 0.25);
    --color-info: #58a6ff;
    --color-info-bg: rgba(88, 166, 255, 0.06);
    --color-info-border: rgba(88, 166, 255, 0.25);
    --color-purple-bg: rgba(188, 140, 255, 0.08);
    --color-purple-border: rgba(188, 140, 255, 0.40);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 18px;
    --radius-2xl: 20px;
    --radius-3xl: 24px;
    --radius-full: 9999px;
    --shadow-sm: 0 4px 12px rgba(0, 0, 0, 0.25);
    --shadow-card: 0 12px 28px rgba(0, 0, 0, 0.25);
    --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.50);
    --shadow-hero: 0 18px 40px rgba(0, 0, 0, 0.28);
    --shadow-lime: 0 4px 12px rgba(184, 248, 47, 0.30);
    --shadow-lime-card: 0 8px 20px rgba(184, 248, 47, 0.20);
    --font-display: "Bebas Neue", sans-serif;
    --font-body: "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, monospace;
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
    font-family: var(--font-body);
    background: {background};
    background-attachment: fixed;
    color: var(--text-body);
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stAppViewContainer"] {{
    background: {background};
    background-attachment: fixed;
}}

p, li, label, div[data-testid="stMarkdownContainer"] {{
    color: var(--text-body);
}}

a {{
    color: var(--color-lime);
}}

hr {{
    border-color: var(--bg-border);
}}

/* ── Entrada suave de página ─────────────────────────────────────────────── */
@keyframes lb-fade-up {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: none; }}
}}
section.main .block-container,
[data-testid="stMainBlockContainer"] {{
    animation: lb-fade-up 0.35s ease-out both;
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0f172a 0%, #0d1117 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.14);
}}

[data-testid="stSidebar"] * {{
    color: var(--text-body) !important;
}}

div[data-testid="stSidebar"] details {{
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 14px;
    margin-bottom: 10px;
    padding: 2px 4px;
}}

div[data-testid="stSidebar"] details summary {{
    font-weight: 700;
}}

.stButton > button,
div[data-testid="stSidebar"] div.stButton > button {{
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.03em !important;
    border-radius: var(--radius-sm) !important;
    transition: opacity 0.15s ease, transform 0.1s ease !important;
}}

.stButton > button:hover,
div[data-testid="stSidebar"] div.stButton > button:hover {{
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, var(--color-lime), var(--color-lime-dark)) !important;
    color: var(--bg-base) !important;
    border: none !important;
    box-shadow: var(--shadow-lime) !important;
}}

.stButton > button[kind="secondary"] {{
    background: var(--bg-surface) !important;
    color: var(--text-body) !important;
    border: 1px solid var(--bg-border) !important;
}}

div[data-testid="stSidebar"] div.stButton > button {{
    justify-content: flex-start !important;
    background: var(--surface-sidebar) !important;
    border: 1px solid rgba(148, 163, 184, 0.16) !important;
    color: var(--text-body) !important;
}}

div[data-testid="stSidebar"] div.stButton > button:hover {{
    border-color: rgba(184, 248, 47, 0.42) !important;
    background: rgba(30, 41, 59, 0.98) !important;
}}

div[data-testid="stSidebar"] div.stButton:has(button[data-testid*="shell_logout"]) > button {{
    justify-content: center !important;
    color: var(--color-danger) !important;
    border-color: rgba(248, 81, 73, 0.25) !important;
}}

div[data-testid="stSidebar"] div.stButton:has(button[data-testid*="shell_logout"]) > button:hover {{
    background: rgba(248, 81, 73, 0.08) !important;
    border-color: rgba(248, 81, 73, 0.5) !important;
}}

div[data-testid="stTabs"] button {{
    font-family: var(--font-body) !important;
    color: var(--text-faint) !important;
    font-weight: 600 !important;
}}

div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: var(--color-lime) !important;
    border-bottom-color: var(--color-lime) !important;
}}

.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stTimeInput input,
.stSelectbox > div > div,
.stMultiselect > div > div {{
    background-color: var(--bg-card) !important;
    border: 1px solid var(--bg-border) !important;
    color: var(--text-body) !important;
    font-family: var(--font-body) !important;
    border-radius: var(--radius-sm) !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus,
.stDateInput input:focus,
.stTimeInput input:focus {{
    border-color: var(--color-lime) !important;
    box-shadow: 0 0 0 2px var(--color-lime-ring) !important;
}}

.stSelectbox label,
.stMultiselect label,
.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stDateInput label,
.stTimeInput label {{
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
}}

.stAlert {{
    border-radius: var(--radius-lg) !important;
    border: 1px solid rgba(148, 163, 184, 0.16) !important;
    background: rgba(15, 23, 42, 0.9) !important;
}}

/* ── Tipografia de página ────────────────────────────────────────────────── */
.lb-page-title {{
    font-family: var(--font-display);
    font-size: 2.4rem;
    font-weight: 400;
    letter-spacing: 0.18em;
    margin: 0;
    text-transform: uppercase;
    color: var(--text-primary);
}}

.lb-page-title.gradient-lime {{
    background: linear-gradient(90deg, var(--color-lime-light), var(--color-lime));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-title.gradient-gold {{
    background: linear-gradient(90deg, #ffdd7a, #ffc531);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-title.gradient-red {{
    background: linear-gradient(90deg, #e94560, #ff8099);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-title.gradient-ember {{
    background: linear-gradient(90deg, #FF7E6B, #FFB347);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-title.gradient-purple {{
    background: linear-gradient(90deg, #BC8CFF, #d8b4fe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-title.gradient-blue {{
    background: linear-gradient(90deg, #58a6ff, #9ecbff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.lb-page-subtitle {{
    color: var(--text-faint);
    font-size: 0.85rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 4px 0 0;
}}

.lb-kicker {{
    color: var(--text-kicker);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
}}

.lb-section-title {{
    color: var(--text-muted);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--bg-border);
    padding-bottom: 6px;
    margin: 20px 0 12px;
}}

/* ── Superfícies ─────────────────────────────────────────────────────────── */
.lb-card {{
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
    transition: transform 0.15s ease, border-color 0.2s ease;
}}

.lb-card.hoverable:hover {{
    transform: translateY(-2px);
    border-color: #484f58;
}}

.lb-panel {{
    background: var(--surface-panel-lg);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
    padding: 18px 18px 16px;
}}

.lb-panel-title {{
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 800;
    margin-bottom: 4px;
}}

.lb-panel-sub {{
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-bottom: 14px;
}}

.lb-hero {{
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.96));
    border: 1px solid rgba(184, 248, 47, 0.18);
    border-radius: 24px;
    padding: 28px 30px;
    margin-bottom: 18px;
    box-shadow: var(--shadow-hero);
}}

.lb-hero-title {{
    font-family: var(--font-display);
    font-size: 3rem;
    letter-spacing: 0.12em;
    color: var(--text-primary);
    margin: 0;
}}

.lb-hero-sub {{
    color: var(--text-muted);
    font-size: 0.95rem;
    margin: 8px 0 0;
    max-width: 760px;
}}

/* ── Tiles de métrica ────────────────────────────────────────────────────── */
.lb-stat-row {{
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}}

.lb-stat-tile {{
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-lg);
    padding: 14px 18px;
    flex: 1;
    min-width: 120px;
    transition: border-color 0.2s ease;
}}

.lb-stat-tile:hover {{
    border-color: #484f58;
}}

.lb-stat-tile .val {{
    font-family: var(--font-display);
    font-size: 1.7rem;
    color: var(--color-lime);
    letter-spacing: 0.08em;
    line-height: 1.1;
}}

.lb-stat-tile.tone-gold .val   {{ color: var(--color-ember); }}
.lb-stat-tile.tone-blue .val   {{ color: var(--color-blue); }}
.lb-stat-tile.tone-purple .val {{ color: var(--color-purple); }}
.lb-stat-tile.tone-red .val    {{ color: var(--color-red); }}

.lb-stat-tile .lbl {{
    font-size: 0.62rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    margin-top: 2px;
}}

/* ── Barras de progresso ─────────────────────────────────────────────────── */
.lb-progress {{
    background: var(--bg-surface);
    border-radius: var(--radius-full);
    height: 8px;
    overflow: hidden;
}}

.lb-progress > span {{
    display: block;
    height: 100%;
    border-radius: var(--radius-full);
    transition: width 0.4s ease;
    background: linear-gradient(90deg, var(--color-lime), var(--color-lime-dark));
}}

.lb-progress > span.blue   {{ background: linear-gradient(90deg, #58a6ff, #3b82f6); }}
.lb-progress > span.purple {{ background: linear-gradient(90deg, #7e69ff, #5b42e8); }}
.lb-progress > span.gold   {{ background: linear-gradient(90deg, #FFC531, #FFB347); }}
.lb-progress > span.red    {{ background: var(--color-danger); }}

/* ── Chips e badges ──────────────────────────────────────────────────────── */
.lb-chip {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: var(--radius-full);
    padding: 5px 10px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(30, 41, 59, 0.9);
    color: var(--text-secondary);
    font-size: 0.75rem;
    margin: 0 8px 8px 0;
}}

.lb-badge {{
    display: inline-block;
    background: var(--bg-surface);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-full);
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--color-lime);
    letter-spacing: 0.04em;
}}

/* ── Banners contextuais ─────────────────────────────────────────────────── */
.lb-banner {{
    border-radius: var(--radius-xl);
    padding: 14px 18px;
    margin-bottom: 14px;
    border: 1px solid var(--bg-border);
    background: var(--bg-card);
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.5;
}}

.lb-banner strong {{ color: var(--text-primary); }}
.lb-banner.success {{ background: var(--color-success-bg); border-color: var(--color-success-border); }}
.lb-banner.info    {{ background: var(--color-info-bg);    border-color: var(--color-info-border); }}
.lb-banner.warning {{ background: var(--color-warning-bg); border-color: var(--color-warning-border); }}
.lb-banner.danger  {{ background: var(--color-danger-bg);  border-color: var(--color-danger-border); }}
.lb-banner.purple  {{ background: var(--color-purple-bg);  border-color: var(--color-purple-border); }}
.lb-banner.lime    {{ background: rgba(184, 248, 47, 0.06); border-color: rgba(184, 248, 47, 0.18); }}
.lb-banner.lime strong {{ color: var(--color-lime); }}

/* ── Estado vazio ────────────────────────────────────────────────────────── */
.lb-empty-state {{
    text-align: center;
    padding: 42px 24px;
    color: var(--text-faint);
}}

.lb-empty-state .icon  {{ font-size: 3.2rem; margin-bottom: 12px; line-height: 1; }}
.lb-empty-state .title {{ font-size: 1rem; font-weight: 700; color: var(--text-body); margin-bottom: 8px; }}
.lb-empty-state .body  {{ font-size: 0.85rem; line-height: 1.6; max-width: 420px; margin: 0 auto; }}
.lb-empty-state .body strong {{ color: var(--color-lime); }}

/* ── Skeleton shimmer ────────────────────────────────────────────────────── */
@keyframes lb-shimmer {{
    0%   {{ background-position: 100% 0; }}
    100% {{ background-position: -100% 0; }}
}}

.lb-skeleton {{
    background: linear-gradient(90deg, var(--bg-card) 25%, var(--bg-surface) 37%, var(--bg-card) 63%);
    background-size: 400% 100%;
    animation: lb-shimmer 1.4s ease infinite;
    border-radius: var(--radius-md);
}}

/* ── Animação de evolução (compartilhada) ────────────────────────────────── */
@keyframes lb-evo-in {{
    0%   {{ opacity: 0; transform: translateY(-10px) scale(0.97); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes lb-evo-glow {{
    0%   {{ box-shadow: 0 0 0 #BC8CFF00; border-color: #3d1f5e; }}
    45%  {{ box-shadow: 0 0 35px #BC8CFF55, 0 0 70px #BC8CFF22; border-color: #BC8CFF; }}
    100% {{ box-shadow: 0 0 14px #BC8CFF33; border-color: #BC8CFF; }}
}}
@keyframes lb-evo-from {{
    0%, 25% {{ opacity: 1; filter: brightness(1); }}
    60%     {{ opacity: 1; filter: brightness(8) drop-shadow(0 0 10px #fff); }}
    100%    {{ opacity: 0; filter: brightness(20); transform: scale(0.8); }}
}}
@keyframes lb-evo-arrow {{
    0%, 35% {{ opacity: 0.25; transform: scale(1); }}
    65%     {{ opacity: 1;    transform: scale(1.5); }}
    100%    {{ opacity: 0.8;  transform: scale(1.1); }}
}}
@keyframes lb-evo-to {{
    0%, 50% {{ opacity: 0; filter: brightness(20) saturate(0); transform: scale(0.7); }}
    70%     {{ opacity: 1; filter: brightness(5) drop-shadow(0 0 22px #BC8CFF); transform: scale(1.2); }}
    87%     {{ filter: brightness(2) drop-shadow(0 0 12px #BC8CFF); transform: scale(1.0); }}
    100%    {{ opacity: 1; filter: drop-shadow(0 0 8px #BC8CFF77); transform: scale(1.0); }}
}}
@keyframes lb-evo-text {{
    0%, 58% {{ opacity: 0; transform: translateX(-10px); }}
    100%    {{ opacity: 1; transform: translateX(0); }}
}}

.lb-evo-banner {{
    background: linear-gradient(135deg, #1a0b2e 0%, #2a1050 50%, #1a0b2e 100%);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 20px;
    border: 1.5px solid transparent;
    animation: lb-evo-in 0.4s ease-out both, lb-evo-glow 2s ease-out both;
}}

.lb-evo-banner .evo-from  {{ flex-shrink: 0; animation: lb-evo-from 1.1s ease-in-out 0.2s both; }}
.lb-evo-banner .evo-arrow {{
    color: var(--color-purple);
    font-size: 2rem;
    font-weight: 900;
    flex-shrink: 0;
    animation: lb-evo-arrow 0.7s ease 0.75s both;
}}
.lb-evo-banner .evo-to   {{ flex-shrink: 0; animation: lb-evo-to 1.1s ease-out 0.8s both; }}
.lb-evo-banner .evo-text {{ animation: lb-evo-text 0.5s ease-out 1.4s both; }}
.lb-evo-banner .evo-title {{ font-weight: 800; color: var(--text-body); font-size: 1.1rem; }}
.lb-evo-banner .evo-names {{ margin-top: 6px; }}
.lb-evo-banner .evo-name-from {{ color: var(--text-faint); font-weight: 700; }}
.lb-evo-banner .evo-names .sep {{ color: var(--color-purple); margin: 0 10px; font-size: 1.3rem; }}
.lb-evo-banner .evo-name-to {{ color: var(--color-purple); font-size: 1.1rem; font-weight: 800; }}
.lb-evo-banner .evo-sub {{ color: var(--text-faint); font-size: 0.8rem; margin-top: 4px; }}

/* ── Badge de moedas ─────────────────────────────────────────────────────── */
.lb-coin-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #FFC531, #B38200);
    border-radius: var(--radius-full);
    padding: 6px 16px;
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--bg-base);
    font-family: var(--font-mono);
}}

/* ── Shell (sidebar custom) ──────────────────────────────────────────────── */
.shell-brand {{
    background: linear-gradient(135deg, rgba(30,41,59,0.96), rgba(15,23,42,0.96));
    border: 1px solid rgba(184,248,47,0.18);
    border-radius: 24px;
    padding: 16px 16px 14px;
    margin-bottom: 14px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
}}

.shell-brand-title {{
    font-family: var(--font-display);
    font-size: 2rem;
    letter-spacing: 0.18em;
    color: var(--text-primary);
    margin: 0;
}}

.shell-brand-sub {{
    color: var(--text-kicker);
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 700;
}}

.shell-section-label {{
    color: var(--text-muted);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 8px 0 10px;
}}

.shell-profile {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(15,23,42,0.9);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 16px;
    padding: 12px 14px;
    margin-top: 14px;
}}

.shell-profile-name {{
    font-weight: 700;
    font-size: 0.86rem;
    color: var(--text-primary);
}}

.shell-profile-meta {{
    color: var(--text-meta);
    font-size: 0.74rem;
    font-weight: 700;
}}

/* ── Responsividade mobile ───────────────────────────────────────────────── */
@media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"],
    section.main .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}

    .lb-page-title  {{ font-size: 1.8rem; }}
    .lb-hero        {{ padding: 20px 18px; }}
    .lb-hero-title  {{ font-size: 2.1rem; }}
    .lb-hero-sub    {{ font-size: 0.85rem; }}
    .lb-panel       {{ padding: 14px; }}
    .lb-stat-row    {{ gap: 8px; }}
    .lb-stat-tile   {{ min-width: calc(50% - 8px); padding: 10px 12px; }}
    .lb-stat-tile .val {{ font-size: 1.4rem; }}
    .lb-evo-banner  {{ flex-wrap: wrap; gap: 12px; padding: 16px; }}
    .shell-brand-title {{ font-size: 1.6rem; }}
}}

::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: var(--bg-base);
}}

::-webkit-scrollbar-thumb {{
    background: var(--bg-border);
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #484f58;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def render_page_heading(title: str, subtitle: str, *, tone: str = "lime", align: str = "left") -> None:
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    tone_class = _HEADING_TONES.get(tone, "gradient-lime")
    st.markdown(
        f"""
<div style="text-align:{align}">
  <p class="lb-page-subtitle" style="margin:0 0 2px">{safe_subtitle}</p>
  <p class="lb-page-title {tone_class}">{safe_title}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def coin_badge(value: int, icon: str = "🪙") -> str:
    return f"<div class='lb-coin-badge'>{icon} {value:,}</div>"


def stat_tile(label: str, value: str, *, tone: str = "lime") -> str:
    """HTML de um tile de métrica. Envolver uma sequência deles em
    `<div class='lb-stat-row'>...</div>`."""
    safe_label = html.escape(label)
    tone_cls = f" tone-{tone}" if tone != "lime" else ""
    return (
        f"<div class='lb-stat-tile{tone_cls}'>"
        f"<div class='val'>{value}</div>"
        f"<div class='lbl'>{safe_label}</div>"
        f"</div>"
    )


def render_empty_state(icon: str, title: str, body: str) -> None:
    """Estado vazio padronizado. `body` aceita HTML simples (strong, br)."""
    safe_title = html.escape(title)
    st.markdown(
        f"<div class='lb-empty-state'>"
        f"<div class='icon'>{icon}</div>"
        f"<div class='title'>{safe_title}</div>"
        f"<div class='body'>{body}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_evolution_animation(
    from_img_html: str,
    to_img_html: str,
    from_name: str,
    to_name: str,
    *,
    title: str = "🌟 Pokémon evoluiu!",
    subtitle: str = "Stats recalculados para a nova forma!",
) -> None:
    """Banner animado de evolução: o sprite antigo brilha e some, o novo surge
    com glow roxo. Keyframes ficam no CSS global (inject_design_system).

    `from_img_html`/`to_img_html` são tags <img> já resolvidas (sprite_img_tag).
    """
    safe_from = html.escape(from_name)
    safe_to = html.escape(to_name)
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    st.markdown(
        f"<div class='lb-evo-banner'>"
        f"<div class='evo-from'>{from_img_html}</div>"
        f"<div class='evo-arrow'>→</div>"
        f"<div class='evo-to'>{to_img_html}</div>"
        f"<div class='evo-text'>"
        f"<div class='evo-title'>{safe_title}</div>"
        f"<div class='evo-names'>"
        f"<span class='evo-name-from'>{safe_from}</span>"
        f"<span class='sep'>→</span>"
        f"<span class='evo-name-to'>{safe_to}</span>"
        f"</div>"
        f"<div class='evo-sub'>{safe_subtitle}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
