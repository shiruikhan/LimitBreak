import html

import streamlit as st


_FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap">
"""


def inject_design_system(page_variant: str = "app") -> None:
    background = (
        "linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%)"
        if page_variant == "auth"
        else "#0d1117"
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
    --bg-base: #0d1117;
    --bg-sidebar: #0f172a;
    --bg-card: #161b22;
    --bg-surface: #21262d;
    --bg-login: #1a1a2e;
    --bg-border: #30363d;
    --surface-panel: rgba(15, 23, 42, 0.88);
    --surface-panel-lg: rgba(15, 23, 42, 0.82);
    --surface-sidebar: rgba(15, 23, 42, 0.92);
    --surface-brand: rgba(30, 41, 59, 0.96);
    --text-primary: #f8fafc;
    --text-body: #e6edf3;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --text-faint: #8b949e;
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
    color: var(--text-body);
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stAppViewContainer"] {{
    background: {background};
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

.lb-card {{
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
}}

.lb-panel {{
    background: var(--surface-panel-lg);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
}}

.lb-hero {{
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.96));
    border: 1px solid rgba(184, 248, 47, 0.18);
    border-radius: 24px;
    box-shadow: var(--shadow-hero);
}}

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
    tone_class = "gradient-gold" if tone == "gold" else "gradient-lime"
    st.markdown(
        f"""
<div style="text-align:{align}">
  <p class="lb-page-title {tone_class}">{safe_title}</p>
  <p class="lb-page-subtitle">{safe_subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def coin_badge(value: int, icon: str = "🪙") -> str:
    return f"<div class='lb-coin-badge'>{icon} {value:,}</div>"
