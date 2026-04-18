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
[data-testid="stSidebar"] { background-color: #0d1117 !important; }
[data-testid="stSidebarNav"] a { color: #e6edf3 !important; }
[data-testid="stSidebarNav"] a:hover { color: #78C850 !important; }
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
        st.Page("pages/pokedex.py",         title="Pokédex",        icon="📖"),
        st.Page("pages/pokedex_pessoal.py", title="Minha Pokédex",  icon="🗂️"),
        st.Page("pages/equipe.py",          title="Minha Equipe",   icon="⚔️"),
        st.Page("pages/loja.py",            title="Loja",           icon="🛒"),
        st.Page("pages/calendario.py",      title="Calendário",     icon="📅"),
    ])

pg.run()
