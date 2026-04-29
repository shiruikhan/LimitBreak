import os
import streamlit as st
import streamlit.components.v1 as components
from utils.db import create_user_profile, get_image_as_base64

BASE_DIR = os.getcwd()

# ── Pokémon lists ──────────────────────────────────────────────────────────────

STARTERS_BASE = [
    (1,   "Gen 1 · Bulbasaur"),  (4,   "Gen 1 · Charmander"), (7,   "Gen 1 · Squirtle"),
    (152, "Gen 2 · Chikorita"),  (155, "Gen 2 · Cyndaquil"),  (158, "Gen 2 · Totodile"),
    (252, "Gen 3 · Treecko"),    (255, "Gen 3 · Torchic"),    (258, "Gen 3 · Mudkip"),
    (387, "Gen 4 · Turtwig"),    (390, "Gen 4 · Chimchar"),   (393, "Gen 4 · Piplup"),
    (495, "Gen 5 · Snivy"),      (498, "Gen 5 · Tepig"),      (501, "Gen 5 · Oshawott"),
    (650, "Gen 6 · Chespin"),    (653, "Gen 6 · Fennekin"),   (656, "Gen 6 · Froakie"),
    (722, "Gen 7 · Rowlet"),     (725, "Gen 7 · Litten"),     (728, "Gen 7 · Popplio"),
    (810, "Gen 8 · Grookey"),    (813, "Gen 8 · Scorbunny"),  (816, "Gen 8 · Sobble"),
    (906, "Gen 9 · Sprigatito"), (909, "Gen 9 · Fuecoco"),    (912, "Gen 9 · Quaxly"),
]

# Secret Pokémon unlocked by the easter egg
STARTERS_SECRET = [
    (104, "??? · Cubone"),
    (778, "??? · Mimikyu"),
]

# ── Session state defaults ─────────────────────────────────────────────────────

for key, val in [("selected_starter", None), ("easter_clicks", 0), ("easter_unlocked", False)]:
    if key not in st.session_state:
        st.session_state[key] = val

easter_unlocked: bool = st.session_state.easter_unlocked
STARTERS = STARTERS_BASE + (STARTERS_SECRET if easter_unlocked else [])

# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d1117 0%, #1a1a2e 60%, #0d1117 100%); }
.brand-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 3.5rem; font-weight: 400; letter-spacing: 4px; text-align: center; margin-bottom: 0;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.brand-sub { text-align: center; color: #8b949e; font-size: 0.95rem; margin-top: 4px; margin-bottom: 32px; }
.stTextInput > div > div > input {
    background-color: #0d1117 !important; border: 1px solid #30363d !important;
    border-radius: 8px !important; color: #e6edf3 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #B8F82F !important; box-shadow: 0 0 0 2px rgba(184,248,47,0.20) !important;
}

/* Easter egg hidden trigger — moved off-screen, never visible to the user */
button[data-easter="true"] {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Easter egg: hidden trigger button ─────────────────────────────────────────
# Label uses the Braille blank (U+2800) — visually empty, uniquely identifiable by JS.
_EASTER_LABEL = "\u2800"

if not easter_unlocked:
    if st.button(_EASTER_LABEL, key="ee_btn"):
        st.session_state.easter_clicks += 1
        if st.session_state.easter_clicks >= 7:
            st.session_state.easter_unlocked = True
        st.rerun()

    # JS runs inside a 0-height iframe.
    # It listens for clicks on the PARENT document (the actual Streamlit app).
    # Clicks that land outside any [data-testid="stButton"] element are counted.
    # After every such click, it finds our hidden button (by its braille-blank text)
    # and fires a programmatic .click() on it — which Streamlit processes normally.
    # The _easterInit guard on window.parent ensures the listener is added only once
    # even across Streamlit reruns (the parent window persists).
    components.html("""
<script>
(function () {
    var par = window.parent;

    // Apply the data attribute to the hidden button so CSS can hide it
    function tagEasterButton() {
        var btns = par.document.querySelectorAll(
            '[data-testid="stButton"] button[kind="secondary"]'
        );
        btns.forEach(function (btn) {
            var p = btn.querySelector('p');
            if (p && p.textContent === '\u2800') {
                btn.setAttribute('data-easter', 'true');
            }
        });
    }

    // Programmatically click the hidden easter button
    function fireEasterBtn() {
        var btns = par.document.querySelectorAll(
            '[data-testid="stButton"] button[kind="secondary"]'
        );
        for (var i = 0; i < btns.length; i++) {
            var p = btns[i].querySelector('p');
            if (p && p.textContent === '\u2800') {
                btns[i].click();
                return;
            }
        }
    }

    // Tag the button on load and after every rerun (MutationObserver)
    tagEasterButton();
    var mo = new MutationObserver(tagEasterButton);
    mo.observe(par.document.body, { childList: true, subtree: true });

    // Register the click listener only once per page lifetime
    if (!par._easterInit) {
        par._easterInit = true;
        par._easterBlanks = 0;

        par.document.addEventListener('click', function (e) {
            // Ignore clicks that land on any Streamlit button
            if (e.target.closest('[data-testid="stButton"]')) return;
            // Ignore the iframe element itself
            if (e.target.tagName === 'IFRAME') return;

            par._easterBlanks++;

            // Cap at 7 to avoid triggering after already unlocked
            if (par._easterBlanks <= 7) {
                fireEasterBtn();
            }
        }, true); // capture phase — runs before any other handler
    }
})();
</script>
""", height=0)

# ── Page content ───────────────────────────────────────────────────────────────

st.markdown("<div class='brand-title'>LIMITBREAK</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='brand-sub'>BEM-VINDO, TREINADOR — ESCOLHA SEU COMPANHEIRO</div>",
    unsafe_allow_html=True,
)

username = st.text_input("Seu nome de treinador", placeholder="Ash Ketchum", key="trainer_name")

st.markdown("---")
st.markdown("##### Escolha seu Pokémon inicial:")
st.write("")

def _thumb_b64(pokemon_id: int) -> str | None:
    path = os.path.join(
        BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
        f"{str(pokemon_id).zfill(4)}.png",
    )
    return get_image_as_base64(path)


COLS_PER_ROW = 9
for row_start in range(0, len(STARTERS), COLS_PER_ROW):
    row  = STARTERS[row_start : row_start + COLS_PER_ROW]
    cols = st.columns(len(row))
    for col, (pid, label) in zip(cols, row):
        with col:
            b64      = _thumb_b64(pid)
            selected = st.session_state.selected_starter == pid
            is_secret = label.startswith("???")
            border   = "#B8F82F" if selected else ("#8b2be2" if is_secret else "#30363d")
            bg       = "#1c2d16" if selected else ("#1a0a2e" if is_secret else "#161b22")
            img_tag  = (
                f"<img src='data:image/png;base64,{b64}' width='64'>"
                if b64 else "<div style='font-size:2rem;text-align:center'>❓</div>"
            )
            name = label.split("·")[1].strip()

            st.markdown(
                f"<div style='border:2px solid {border};border-radius:10px;background:{bg};"
                f"padding:8px;text-align:center'>"
                f"{img_tag}"
                f"<br><small style='color:#e6edf3;font-size:0.7rem'>{name}</small></div>",
                unsafe_allow_html=True,
            )
            if st.button("Escolher", key=f"s_{pid}", use_container_width=True):
                st.session_state.selected_starter = pid
                st.rerun()

st.write("")

if st.session_state.selected_starter:
    sel_label = next((l for i, l in STARTERS if i == st.session_state.selected_starter), "")
    sel_name  = sel_label.split("·")[1].strip()
    is_secret = sel_label.startswith("???")
    if is_secret:
        st.success(f"✨ Escolha incomum... **{sel_name}** (#{st.session_state.selected_starter})")
    else:
        st.success(f"✅ Selecionado: **{sel_name}** (#{st.session_state.selected_starter})")

st.write("")
can_confirm = bool(st.session_state.selected_starter and username.strip())
if st.button("Começar jornada →", disabled=not can_confirm, use_container_width=False):
    try:
        create_user_profile(
            st.session_state.user_id,
            username.strip(),
            st.session_state.selected_starter,
        )
        st.session_state.needs_starter    = False
        st.session_state.selected_starter = None
        st.session_state.easter_clicks    = 0
        st.session_state.easter_unlocked  = False
        # Reset parent-window easter state so it works fresh on next onboarding
        components.html("""
<script>
if (window.parent) {
    window.parent._easterInit   = false;
    window.parent._easterBlanks = 0;
}
</script>""", height=0)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao criar perfil: {e}")
