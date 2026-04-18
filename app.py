import streamlit as st

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

for key, default in [("user", None), ("user_id", None), ("access_token", None),
                     ("refresh_token", None), ("needs_starter", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.user is None:
    # Not authenticated
    pg = st.navigation(
        [st.Page("pages/login.py", title="Login", icon="🔐")],
        position="hidden",
    )
elif st.session_state.needs_starter:
    # Authenticated but no Pokémon yet — must pick a starter
    pg = st.navigation(
        [st.Page("pages/starter.py", title="Escolha seu Inicial", icon="🌿")],
        position="hidden",
    )
else:
    # Fully onboarded
    pg = st.navigation([
        st.Page("pages/pokedex.py",         title="Pokédex",        icon="📖"),
        st.Page("pages/pokedex_pessoal.py", title="Minha Pokédex",  icon="🗂️"),
        st.Page("pages/equipe.py",          title="Minha Equipe",   icon="⚔️"),
    ])

pg.run()
