import streamlit as st
from datetime import datetime, timedelta
import extra_streamlit_components as stx
from utils.app_cache import clear_user_cache, get_cached_user_pokemon_ids
from utils.supabase_client import get_supabase

cookie_manager = stx.CookieManager(key="lb_cookies_login")


def _save_session(session):
    exp = datetime.now() + timedelta(days=30)
    cookie_manager.set("lb_refresh_token", session.refresh_token,
                       expires_at=exp, key="save_on_login")


def _get_app_url() -> str:
    try:
        return st.secrets["app"]["url"]
    except Exception:
        return "http://localhost:8501"


def _start_oauth(provider: str, key_suffix: str):
    """Gera URL OAuth e redireciona o usuário ao provedor."""
    try:
        client = get_supabase()
        response = client.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": _get_app_url(),
            }
        })

        # Persiste o code_verifier no cookie antes do redirect (PKCE flow)
        verifier = getattr(response, "code_verifier", None)
        if verifier:
            exp = datetime.now() + timedelta(minutes=15)
            cookie_manager.set("lb_oauth_verifier", verifier,
                               expires_at=exp, key=f"set_v_{key_suffix}")

        # Meta-refresh imediato — o browser seta o cookie antes de navegar
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={response.url}">',
            unsafe_allow_html=True,
        )
        st.stop()
    except Exception as e:
        st.error(f"Erro ao iniciar login com {provider}: {e}")


# ── OAuth callback ─────────────────────────────────────────────────────────────
# O Supabase redireciona de volta com ?code=... após a autenticação do provedor.
_qp = st.query_params
_oauth_code = _qp.get("code")
_oauth_error = _qp.get("error")

if _oauth_error:
    _desc = _qp.get("error_description", _oauth_error)
    st.query_params.clear()
    st.error(f"Erro no login social: {_desc}")

elif _oauth_code:
    # Na primeira renderização o CookieManager pode não ter lido os cookies
    # ainda — fazemos um rerun para garantir a leitura correta.
    _verifier = cookie_manager.get("lb_oauth_verifier")
    if _verifier is None and not st.session_state.get("_oauth_retried"):
        st.session_state["_oauth_retried"] = True
        st.rerun()
    else:
        st.session_state.pop("_oauth_retried", None)
        if not _verifier:
            st.query_params.clear()
            st.error(
                "Sessão de autenticação expirada. Por favor, clique novamente em "
                "Google ou Discord para tentar de novo."
            )
        else:
            try:
                client = get_supabase()
                res = client.auth.exchange_code_for_session({
                    "auth_code": _oauth_code,
                    "code_verifier": _verifier,
                })
                st.query_params.clear()
                clear_user_cache()
                st.session_state.user = res.user
                st.session_state.user_id = str(res.user.id)
                st.session_state.access_token = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                _save_session(res.session)
                if not get_cached_user_pokemon_ids(str(res.user.id)):
                    st.session_state.needs_starter = True
                st.rerun()
            except Exception as e:
                st.query_params.clear()
                st.error(f"Erro ao completar login social: {e}")

# ── Page style ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');

.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }

.brand-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 3.5rem; font-weight: 400; letter-spacing: 4px;
    text-align: center; margin-bottom: 0;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
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
    border-color: #B8F82F !important;
    box-shadow: 0 0 0 2px rgba(184,248,47,0.15) !important;
}

/* Botão primário (Entrar / Criar conta) */
.stFormSubmitButton > button,
.stButton > button[kind="primary"] {
    width: 100% !important;
    background: linear-gradient(90deg, #7AB21A, #B8F82F) !important;
    color: #0d1117 !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    padding: 12px !important; font-size: 1rem !important;
    transition: transform 0.1s ease, opacity 0.2s ease !important;
}
.stFormSubmitButton > button:hover,
.stButton > button[kind="primary"]:hover {
    opacity: 0.9 !important; transform: translateY(-1px) !important;
}

/* Botões OAuth (secondary) */
.stButton > button[kind="secondary"] {
    width: 100% !important;
    background: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    padding: 11px !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    transition: border-color 0.15s ease, background 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #58a6ff !important;
    background: #1c2128 !important;
}

/* Divisor OAuth */
.oauth-divider {
    display: flex; align-items: center; gap: 12px;
    margin: 20px 0 16px;
}
.oauth-divider hr {
    flex: 1; border: none; border-top: 1px solid #30363d; margin: 0;
}
.oauth-divider span {
    color: #8b949e; font-size: 0.8rem; white-space: nowrap;
}

div[data-testid="stTabs"] button { color: #8b949e !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #B8F82F !important; border-bottom-color: #B8F82F !important;
}
</style>
""", unsafe_allow_html=True)


# ── Layout ─────────────────────────────────────────────────────────────────────
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
            with st.form("form_login"):
                email_l = st.text_input("E-mail", key="login_email",
                                        placeholder="treinador@email.com")
                senha_l = st.text_input("Senha", type="password", key="login_senha",
                                        placeholder="••••••••")
                st.write("")
                submitted_l = st.form_submit_button("Entrar", use_container_width=True)

            if submitted_l:
                if not email_l or not senha_l:
                    st.warning("Preencha e-mail e senha.")
                else:
                    try:
                        client = get_supabase()
                        res = client.auth.sign_in_with_password(
                            {"email": email_l, "password": senha_l}
                        )
                        st.session_state.user = res.user
                        st.session_state.user_id = str(res.user.id)
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        _save_session(res.session)
                        if not get_cached_user_pokemon_ids(str(res.user.id)):
                            st.session_state.needs_starter = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao entrar: {e}")

        # ── Signup tab ─────────────────────────────────────────────────────────
        with tab_signup:
            st.write("")
            with st.form("form_signup"):
                email_s = st.text_input("E-mail", key="signup_email",
                                        placeholder="treinador@email.com")
                senha_s = st.text_input("Senha", type="password", key="signup_senha",
                                        placeholder="Mínimo 6 caracteres")
                senha_s2 = st.text_input("Confirmar senha", type="password",
                                         key="signup_senha2", placeholder="••••••••")
                st.write("")
                submitted_s = st.form_submit_button("Criar conta", use_container_width=True)

            if submitted_s:
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
                            clear_user_cache()
                            st.session_state.user = res.user
                            st.session_state.user_id = str(res.user.id)
                            if res.session:
                                st.session_state.access_token = res.session.access_token
                                st.session_state.refresh_token = res.session.refresh_token
                                _save_session(res.session)
                            st.session_state.needs_starter = True
                            st.rerun()
                        else:
                            st.info("Verifique seu e-mail para confirmar o cadastro.")
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")

        # ── OAuth — botões compartilhados entre login e cadastro ───────────────
        st.markdown("""
        <div class="oauth-divider">
            <hr><span>ou continue com</span><hr>
        </div>
        """, unsafe_allow_html=True)

        col_g, col_d = st.columns(2)
        with col_g:
            if st.button(
                "🌐  Entrar com Google",
                key="oauth_google",
                use_container_width=True,
                type="secondary",
            ):
                _start_oauth("google", "g")

        with col_d:
            if st.button(
                "💬  Entrar com Discord",
                key="oauth_discord",
                use_container_width=True,
                type="secondary",
            ):
                _start_oauth("discord", "d")

        st.markdown(
            "<p style='text-align:center;color:#484f58;font-size:0.75rem;"
            "margin-top:16px;margin-bottom:0;'>"
            "Ao continuar você aceita os termos de uso do LimitBreak.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
