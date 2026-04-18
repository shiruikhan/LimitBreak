import streamlit as st
from datetime import datetime, timedelta
import extra_streamlit_components as stx
from utils.supabase_client import get_supabase
from utils.db import get_user_pokemon_ids

# Mesmo key que app.py — acessa os mesmos cookies do browser
cookie_manager = stx.CookieManager(key="lb_cookies")

def _save_session(session):
    """Persiste o refresh_token em cookie por 30 dias."""
    exp = datetime.now() + timedelta(days=30)
    cookie_manager.set("lb_refresh_token", session.refresh_token,
                       expires_at=exp, key="save_on_login")

# ── Page style ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.brand-title {
    font-size: 3.5rem; font-weight: 900; letter-spacing: 4px;
    text-align: center; margin-bottom: 0;
    background: linear-gradient(90deg, #78C850, #A7DB8D);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.brand-sub {
    text-align: center; color: #8b949e; font-size: 0.95rem;
    margin-top: 4px; margin-bottom: 32px; letter-spacing: 1px;
}
.login-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 40px 36px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
}
/* Inputs */
.stTextInput > div > div > input {
    background-color: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #78C850 !important;
    box-shadow: 0 0 0 2px rgba(120,200,80,0.25) !important;
}
/* Buttons */
.stButton > button {
    width: 100% !important;
    background: linear-gradient(90deg, #4E8234, #78C850) !important;
    color: #fff !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    padding: 12px !important; font-size: 1rem !important;
    transition: transform 0.1s ease, opacity 0.2s ease !important;
}
.stButton > button:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }

/* Starter card grid */
.starter-grid { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-top: 16px; }
.starter-card {
    background: #161b22; border: 2px solid #30363d;
    border-radius: 12px; padding: 12px 16px;
    text-align: center; cursor: pointer; transition: all 0.2s ease;
    min-width: 90px;
}
.starter-card:hover { border-color: #78C850; transform: translateY(-3px); box-shadow: 0 8px 20px rgba(120,200,80,0.2); }
.starter-card.selected { border-color: #78C850; background: #1c2d16; }

div[data-testid="stTabs"] button { color: #8b949e !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #78C850 !important; border-bottom-color: #78C850 !important;
}
</style>
""", unsafe_allow_html=True)


_, center, _ = st.columns([1, 1.6, 1])
with center:
    st.markdown("<div class='brand-title'>LIMITBREAK</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-sub'>SUA ACADEMIA. SUA POKÉDEX.</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])

        # ── Login tab ──────────────────────────────────────────────────────────
        with tab_login:
            st.write("")
            email_l = st.text_input("E-mail", key="login_email", placeholder="treinador@email.com")
            senha_l = st.text_input("Senha", type="password", key="login_senha", placeholder="••••••••")
            st.write("")

            if st.button("Entrar", key="btn_login"):
                if not email_l or not senha_l:
                    st.warning("Preencha e-mail e senha.")
                else:
                    try:
                        client = get_supabase()
                        res = client.auth.sign_in_with_password({"email": email_l, "password": senha_l})
                        st.session_state.user          = res.user
                        st.session_state.user_id       = str(res.user.id)
                        st.session_state.access_token  = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        _save_session(res.session)

                        if not get_user_pokemon_ids(str(res.user.id)):
                            st.session_state.needs_starter = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao entrar: {e}")

        # ── Signup tab ─────────────────────────────────────────────────────────
        with tab_signup:
            st.write("")
            email_s = st.text_input("E-mail", key="signup_email", placeholder="treinador@email.com")
            senha_s = st.text_input("Senha", type="password", key="signup_senha", placeholder="Mínimo 6 caracteres")
            senha_s2 = st.text_input("Confirmar senha", type="password", key="signup_senha2", placeholder="••••••••")
            st.write("")

            if st.button("Criar conta", key="btn_signup"):
                if not email_s or not senha_s:
                    st.warning("Preencha todos os campos.")
                elif senha_s != senha_s2:
                    st.error("As senhas não coincidem.")
                elif len(senha_s) < 6:
                    st.error("Senha muito curta (mínimo 6 caracteres).")
                else:
                    try:
                        client = get_supabase()
                        res = client.auth.sign_up({"email": email_s, "password": senha_s})

                        if res.user:
                            st.session_state.user          = res.user
                            st.session_state.user_id       = str(res.user.id)
                            if res.session:
                                st.session_state.access_token  = res.session.access_token
                                st.session_state.refresh_token = res.session.refresh_token
                                _save_session(res.session)
                            st.session_state.needs_starter = True
                            st.rerun()
                        else:
                            st.info("Verifique seu e-mail para confirmar o cadastro.")
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")

        st.markdown("</div>", unsafe_allow_html=True)
