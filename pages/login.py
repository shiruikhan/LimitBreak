import streamlit as st
from utils.supabase_client import get_supabase
from utils.db import get_user_profile, create_user_profile, get_all_pokemon, get_image_as_base64
import os

BASE_DIR = os.getcwd()

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

STARTERS = [
    # (id, "Gen N - Nome")
    (1, "Gen 1 · Bulbasaur"), (4, "Gen 1 · Charmander"), (7, "Gen 1 · Squirtle"),
    (152, "Gen 2 · Chikorita"), (155, "Gen 2 · Cyndaquil"), (158, "Gen 2 · Totodile"),
    (252, "Gen 3 · Treecko"), (255, "Gen 3 · Torchic"), (258, "Gen 3 · Mudkip"),
    (387, "Gen 4 · Turtwig"), (390, "Gen 4 · Chimchar"), (393, "Gen 4 · Piplup"),
    (495, "Gen 5 · Snivy"), (498, "Gen 5 · Tepig"), (501, "Gen 5 · Oshawott"),
    (650, "Gen 6 · Chespin"), (653, "Gen 6 · Fennekin"), (656, "Gen 6 · Froakie"),
    (722, "Gen 7 · Rowlet"), (725, "Gen 7 · Litten"), (728, "Gen 7 · Popplio"),
    (810, "Gen 8 · Grookey"), (813, "Gen 8 · Scorbunny"), (816, "Gen 8 · Sobble"),
    (906, "Gen 9 · Sprigatito"), (909, "Gen 9 · Fuecoco"), (912, "Gen 9 · Quaxly"),
]


def _thumb(pokemon_id: int) -> str | None:
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "thumbnails", f"{str(pokemon_id).zfill(4)}.png")
    return get_image_as_base64(path)


# ── Starter selection screen ───────────────────────────────────────────────────
def _show_starter_selection():
    st.markdown("<div class='brand-title'>LIMITBREAK</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-sub'>Escolha seu Pokémon inicial</div>", unsafe_allow_html=True)

    if "selected_starter" not in st.session_state:
        st.session_state.selected_starter = None

    # Username input
    username = st.text_input("Seu nome de treinador", placeholder="Ash Ketchum", key="trainer_name")

    st.markdown("##### Escolha seu companheiro de treino:")

    # Build starter grid with radio-style selection
    cols_per_row = 9
    for row_start in range(0, len(STARTERS), cols_per_row):
        row = STARTERS[row_start:row_start + cols_per_row]
        cols = st.columns(len(row))
        for col, (pid, label) in zip(cols, row):
            with col:
                b64 = _thumb(pid)
                selected = st.session_state.selected_starter == pid
                border = "#78C850" if selected else "#30363d"
                bg = "#1c2d16" if selected else "#161b22"
                img_tag = f"<img src='data:image/png;base64,{b64}' width='64'>" if b64 else "❓"
                name = label.split("·")[1].strip()
                st.markdown(
                    f"<div style='border:2px solid {border};border-radius:10px;background:{bg};"
                    f"padding:8px;text-align:center;cursor:pointer'>"
                    f"{img_tag}<br><small style='color:#e6edf3;font-size:0.7rem'>{name}</small></div>",
                    unsafe_allow_html=True,
                )
                if st.button("Escolher", key=f"starter_{pid}"):
                    st.session_state.selected_starter = pid
                    st.rerun()

    st.write("")
    if st.session_state.selected_starter:
        sel_name = next((l.split("·")[1].strip() for i, l in STARTERS if i == st.session_state.selected_starter), "")
        st.success(f"✅ Selecionado: **{sel_name}** (#{st.session_state.selected_starter})")

    if st.button("Começar jornada →", disabled=not (st.session_state.selected_starter and username)):
        try:
            create_user_profile(
                st.session_state.user_id,
                username,
                st.session_state.selected_starter,
            )
            st.session_state.needs_starter = False
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar perfil: {e}")


# ── Login / Signup ─────────────────────────────────────────────────────────────
if st.session_state.get("needs_starter"):
    _show_starter_selection()
    st.stop()

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
                        st.session_state.user = res.user
                        st.session_state.user_id = res.user.id
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token

                        # Check if profile exists
                        profile = get_user_profile(res.user.id)
                        if not profile:
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
                            st.session_state.user = res.user
                            st.session_state.user_id = res.user.id
                            if res.session:
                                st.session_state.access_token = res.session.access_token
                                st.session_state.refresh_token = res.session.refresh_token
                            st.session_state.needs_starter = True
                            st.rerun()
                        else:
                            st.info("Verifique seu e-mail para confirmar o cadastro.")
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")

        st.markdown("</div>", unsafe_allow_html=True)
