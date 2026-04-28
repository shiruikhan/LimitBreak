import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="LimitBreak",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global dark theme override
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ── Global base ─────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0d1117;
    color: #e6edf3;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebarNav"] a { color: #e6edf3 !important; }
[data-testid="stSidebarNav"] a:hover { color: #B8F82F !important; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

/* ── Global buttons ──────────────────────────────────────────────────────── */
.stButton > button {
    font-family: "Space Grotesk", sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.5px !important;
    border-radius: 8px !important;
    transition: opacity 0.15s ease, transform 0.1s ease !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #B8F82F, #7AB21A) !important;
    color: #0d1117 !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(184,248,47,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
}

/* ── Global tabs ─────────────────────────────────────────────────────────── */
div[data-testid="stTabs"] button {
    font-family: "Space Grotesk", sans-serif !important;
    color: #8b949e !important;
    font-weight: 600 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #B8F82F !important;
    border-bottom-color: #B8F82F !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stMultiselect > div > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
    font-family: "Space Grotesk", sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #B8F82F !important;
    box-shadow: 0 0 0 2px rgba(184,248,47,0.15) !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>
""", unsafe_allow_html=True)

# ── Cookie manager ─────────────────────────────────────────────────────────────
# Deve ser instanciado antes de qualquer lógica de estado.
import extra_streamlit_components as stx
cookie_manager = stx.CookieManager(key="lb_cookies")

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in [("user", None), ("user_id", None), ("access_token", None),
                     ("refresh_token", None), ("needs_starter", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Restauração automática de sessão via cookie ────────────────────────────────
# Se o usuário não está logado mas tem um refresh_token salvo no browser,
# restaura a sessão silenciosamente sem precisar digitar senha novamente.
if st.session_state.user is None:
    saved_refresh = cookie_manager.get("lb_refresh_token")
    if saved_refresh:
        try:
            from utils.supabase_client import get_supabase
            from utils.db import get_user_pokemon_ids
            client = get_supabase()
            res = client.auth.refresh_session(saved_refresh)
            if res and res.user and res.session:
                st.session_state.user          = res.user
                st.session_state.user_id       = str(res.user.id)
                st.session_state.access_token  = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                # Renova o cookie com o novo refresh_token (rotação automática)
                _exp = datetime.now() + timedelta(days=30)
                cookie_manager.set("lb_refresh_token", res.session.refresh_token,
                                   expires_at=_exp, key="refresh_on_restore")
                # Verifica se o usuário ainda precisa escolher starter
                if not get_user_pokemon_ids(str(res.user.id)):
                    st.session_state.needs_starter = True
        except Exception:
            # Refresh token inválido ou expirado — limpa o cookie
            cookie_manager.delete("lb_refresh_token", key="delete_on_fail")

# ── Navegação ──────────────────────────────────────────────────────────────────
if st.session_state.user is None:
    pg = st.navigation(
        [st.Page("pages/login.py", title="Login", icon="🔐")],
        position="hidden",
    )
elif st.session_state.needs_starter:
    pg = st.navigation(
        [st.Page("pages/starter.py", title="Escolha seu Inicial", icon="🌿")],
        position="hidden",
    )
else:
    pg = st.navigation([
        st.Page("pages/equipe.py",          title="Minha Equipe",   icon="⚔️"),
        st.Page("pages/batalha.py",         title="Arena",          icon="🥊"),
        st.Page("pages/pokedex.py",         title="Pokédex",        icon="📖"),
        st.Page("pages/pokedex_pessoal.py", title="Minha Pokédex",  icon="🗂️"),
        st.Page("pages/loja.py",            title="Loja",           icon="🛒"),
        st.Page("pages/calendario.py",      title="Calendário",     icon="📅"),
        st.Page("pages/biblioteca.py",      title="Biblioteca",     icon="📚"),
        st.Page("pages/rotinas.py",         title="Rotinas",        icon="📋"),
        st.Page("pages/treino.py",          title="Treino",         icon="🏋️"),
    ])

pg.run()
