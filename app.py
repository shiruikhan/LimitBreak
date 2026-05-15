import html as _html
import streamlit as st
from datetime import datetime, timedelta
import extra_streamlit_components as stx

from utils.design_system import inject_design_system
from utils.app_cache import (
    clear_missions_cache,
    get_cached_is_admin,
    get_cached_user_pokemon_ids,
    get_cached_user_profile,
)
from utils.db import ensure_current_user_missions, get_current_mission_periods
from utils.supabase_client import get_supabase

st.set_page_config(
    page_title="LimitBreak",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_design_system("app")

# ── Cookie manager ─────────────────────────────────────────────────────────────
# Deve ser instanciado antes de qualquer lógica de estado.
cookie_manager = stx.CookieManager(key="lb_cookies")

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in [("user", None), ("user_id", None), ("access_token", None),
                     ("refresh_token", None), ("needs_starter", False),
                     ("missions_bootstrap_token", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Restauração automática de sessão via cookie ────────────────────────────────
# Se o usuário não está logado mas tem um refresh_token salvo no browser,
# restaura a sessão silenciosamente sem precisar digitar senha novamente.
if st.session_state.user is None:
    saved_refresh = cookie_manager.get("lb_refresh_token")
    if saved_refresh:
        try:
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
                if not get_cached_user_pokemon_ids(str(res.user.id)):
                    st.session_state.needs_starter = True
        except Exception:
            # Refresh token inválido ou expirado — limpa o cookie
            cookie_manager.delete("lb_refresh_token", key="delete_on_fail")

# ── Starter gate ───────────────────────────────────────────────────────────────
# Só consulta o banco uma vez por sessão. Após checar, grava a flag
# "starter_checked" no session_state para não repetir a query em cada rerender.
if st.session_state.user is not None and not st.session_state.needs_starter:
    if not st.session_state.get("starter_checked"):
        if not get_cached_user_pokemon_ids(st.session_state.user_id):
            st.session_state.needs_starter = True
        st.session_state.starter_checked = True

# ── Mission bootstrap ──────────────────────────────────────────────────────────
# Garante a existência das missões em um ponto controlado do fluxo, mantendo
# sidebar e página de missões como leitura pura durante o render.
if st.session_state.user is not None:
    today, week_start = get_current_mission_periods()
    mission_bootstrap_token = (
        st.session_state.user_id,
        today.isoformat(),
        week_start.isoformat(),
    )
    if st.session_state.get("missions_bootstrap_token") != mission_bootstrap_token:
        ensure_current_user_missions(st.session_state.user_id)
        clear_missions_cache(st.session_state.user_id)
        st.session_state.missions_bootstrap_token = mission_bootstrap_token


def _page_meta(path: str, title: str, icon: str) -> dict:
    return {"path": path, "title": title, "icon": icon}


def _build_app_pages(user_id: str) -> tuple[dict, list[tuple[str, list[dict]]]]:
    groups: list[tuple[str, list[dict]]] = [
        ("Hub", [
            _page_meta("pages/hub.py", "Hub", "🏠"),
        ]),
        ("Treinador", [
            _page_meta("pages/equipe.py", "Minha Equipe", "⚔️"),
            _page_meta("pages/ovos.py", "Ovos", "🥚"),
            _page_meta("pages/conquistas.py", "Conquistas", "🏅"),
            _page_meta("pages/missoes.py", "Missões", "🎯"),
        ]),
        ("Batalha", [
            _page_meta("pages/batalha.py", "Arena", "🥊"),
            _page_meta("pages/leaderboard.py", "Ranking", "🏆"),
        ]),
        ("Treinos", [
            _page_meta("pages/calendario.py", "Calendário", "📅"),
            _page_meta("pages/treino.py", "Treino", "🏋️"),
            _page_meta("pages/rotinas.py", "Rotinas", "📋"),
            _page_meta("pages/biblioteca.py", "Biblioteca", "📚"),
        ]),
        ("Pokédex", [
            _page_meta("pages/pokedex.py", "Pokédex", "📖"),
            _page_meta("pages/pokedex_pessoal.py", "Minha Pokédex", "🗂️"),
        ]),
        ("Loja", [
            _page_meta("pages/loja.py", "Loja", "🛒"),
            _page_meta("pages/mochila.py", "Mochila", "🎒"),
        ]),
    ]
    if get_cached_is_admin(user_id):
        groups.append(("Admin", [_page_meta("pages/admin.py", "Admin", "⚙️")]))

    nav_pages = {
        label: [st.Page(page["path"], title=page["title"], icon=page["icon"]) for page in pages]
        for label, pages in groups
    }
    return nav_pages, groups


def _render_sidebar_shell(groups: list[tuple[str, list[dict]]], user_id: str) -> None:
    with st.sidebar:
        st.markdown(
            """
<div class="shell-brand">
  <div class="shell-brand-sub">Sua academia. Sua Pokédex.</div>
  <div class="shell-brand-title">LIMITBREAK</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='shell-section-label'>Navegação</div>", unsafe_allow_html=True)
        for label, pages in groups:
            with st.expander(label, expanded=label in {"Hub", "Treinador", "Treinos"}):
                for page in pages:
                    if st.button(
                        f"{page['icon']} {page['title']}",
                        key=f"nav::{page['path']}",
                        use_container_width=True,
                    ):
                        st.switch_page(page["path"])

        profile = get_cached_user_profile(user_id)
        if profile:
            _safe_name  = _html.escape(str(profile["username"]))
            _safe_coins = f"{profile['coins']:,}"
            st.markdown(
                f"""
<div class="shell-profile">
  <div style="font-size:1.35rem">🧢</div>
  <div>
    <div class="shell-profile-name">{_safe_name}</div>
    <div class="shell-profile-meta">🪙 {_safe_coins}</div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        if st.button("↩ Sair", key="shell_logout", use_container_width=True):
            try:
                get_supabase().auth.sign_out()
            except Exception:
                pass
            cookie_manager.delete("lb_refresh_token", key="shell_delete_cookie")
            for k in ["user", "user_id", "access_token", "refresh_token",
                      "needs_starter", "starter_checked"]:
                st.session_state[k] = None
            st.rerun()

# ── Toast de conquistas ────────────────────────────────────────────────────────
# Mostra notificação flutuante quando novos achievements foram desbloqueados.
# Usa uma chave derivada dos slugs para mostrar apenas uma vez por evento.
_pending_ach = st.session_state.get("new_achievements_pending", [])
if _pending_ach and st.session_state.user is not None:
    _toast_key = "_ach_toast_" + "_".join(
        a.get("slug", "") for a in _pending_ach[:5]
    )
    if not st.session_state.get(_toast_key):
        count = len(_pending_ach)
        if count == 1:
            _name = _pending_ach[0].get("slug", "conquista").replace("_", " ")
            st.toast(f"🏅 Nova conquista: {_name}!", icon="🎉")
        else:
            st.toast(f"🎉 {count} novas conquistas desbloqueadas!", icon="🏅")
        st.session_state[_toast_key] = True

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
    nav_pages, nav_groups = _build_app_pages(st.session_state.user_id)
    _render_sidebar_shell(nav_groups, st.session_state.user_id)
    pg = st.navigation(nav_pages, position="hidden")

pg.run()
