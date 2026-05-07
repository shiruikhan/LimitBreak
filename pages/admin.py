import uuid
import streamlit as st
from utils.app_cache import clear_catalog_cache, get_cached_exercises
from utils.db import (
    is_admin, get_all_users, admin_update_user, admin_delete_user,
    set_admin_role, get_system_logs, get_global_stats, log_admin_action,
    admin_gift_loot_box, admin_create_exercise,
)
from utils.supabase_client import get_supabase_admin

_GIF_BUCKET = "exercise-gifs"


def _upload_exercise_gif(uploaded_file) -> tuple[bool, str]:
    """Uploads a GIF to Supabase Storage and returns (ok, public_url_or_error)."""
    try:
        client = get_supabase_admin()
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file_bytes = uploaded_file.read()
        client.storage.from_(_GIF_BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": uploaded_file.type or "image/gif"},
        )
        public_url = client.storage.from_(_GIF_BUCKET).get_public_url(filename)
        return True, public_url
    except Exception as e:
        return False, str(e)

# ── Auth guard ─────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id or not is_admin(user_id):
    st.error("⛔ Acesso restrito a administradores.")
    st.stop()

# ── Page styles ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.admin-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
    border: 1px solid #ff6b35;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}
.admin-header h1 { color: #ff6b35; margin: 0; font-family: "Bebas Neue", sans-serif;
    font-size: 2rem; letter-spacing: 2px; }
.admin-header p  { color: #8b949e; margin: 0.25rem 0 0; font-size: 0.85rem; }

.stat-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.stat-card .val { font-size: 1.8rem; font-weight: 700; color: #ff6b35; line-height: 1; }
.stat-card .lbl { font-size: 0.75rem; color: #8b949e; margin-top: 0.25rem; }

.user-row {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
}
.badge-admin { background: #ff6b35; color: #0d1117; border-radius: 4px;
    padding: 1px 7px; font-size: 0.7rem; font-weight: 700; }
.badge-user  { background: #21262d; color: #8b949e; border-radius: 4px;
    padding: 1px 7px; font-size: 0.7rem; }

.log-row { border-left: 3px solid #30363d; padding-left: 0.75rem; margin-bottom: 0.4rem; }
.log-row.admin-action { border-color: #ff6b35; }
.log-row.delete { border-color: #f85149; }
.log-time { color: #8b949e; font-size: 0.72rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="admin-header">
  <h1>⚙️ PAINEL ADMIN</h1>
  <p>Gestão de usuários, logs e dados globais — acesso restrito</p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_overview, tab_users, tab_gift, tab_exercises, tab_logs = st.tabs(["📊 Visão Geral", "👥 Usuários", "🎁 Gift Loot Box", "📝 Exercícios", "📋 Logs do Sistema"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    stats = get_global_stats()

    metrics = [
        ("Usuários",         stats.get("total_users", 0),    "👤"),
        ("Admins",           stats.get("total_admins", 0),   "🛡️"),
        ("Pokémon capturados", stats.get("total_pokemon", 0), "⚡"),
        ("Treinos",          stats.get("total_workouts", 0), "🏋️"),
        ("Check-ins",        stats.get("total_checkins", 0), "📅"),
        ("Batalhas",         stats.get("total_battles", 0),  "🥊"),
        ("Moedas em circulação", stats.get("total_coins", 0), "🪙"),
        ("Ativos (7 dias)",  stats.get("active_7d", 0),      "🟢"),
    ]

    cols = st.columns(4)
    for i, (label, value, icon) in enumerate(metrics):
        with cols[i % 4]:
            st.markdown(f"""
            <div class="stat-card">
              <div class="val">{icon} {value:,}</div>
              <div class="lbl">{label}</div>
            </div>
            """, unsafe_allow_html=True)
        if i % 4 == 3 and i < len(metrics) - 1:
            cols = st.columns(4)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — User Management
# ══════════════════════════════════════════════════════════════════════════════
with tab_users:
    search = st.text_input("🔍 Buscar por nome ou e-mail", key="admin_user_search", placeholder="Digite para filtrar...")
    users = get_all_users(search.strip())

    if not users:
        st.info("Nenhum usuário encontrado.")
    else:
        st.caption(f"{len(users)} usuário(s) encontrado(s)")

    for u in users:
        uid       = u["id"]
        username  = u["username"] or "(sem nome)"
        email     = u["email"] or ""
        coins     = u["coins"] or 0
        is_adm    = u["is_admin"]
        poke_cnt  = u["pokemon_count"]
        wk_cnt    = u["workout_count"]
        badge_html = '<span class="badge-admin">ADMIN</span>' if is_adm else '<span class="badge-user">USER</span>'
        created   = str(u["created_at"])[:10] if u["created_at"] else "—"
        last_in   = str(u["last_sign_in_at"])[:10] if u["last_sign_in_at"] else "nunca"

        with st.expander(f"{badge_html} **{username}** — {email}  |  🪙 {coins}  |  ⚡ {poke_cnt} pkm  |  🏋️ {wk_cnt} treinos", expanded=False):
            st.markdown(f"**ID:** `{uid}`  \n**Criado em:** {created}  \n**Último login:** {last_in}")

            col_edit, col_role, col_del = st.columns([3, 2, 1])

            with col_edit:
                with st.form(key=f"edit_{uid}"):
                    new_name  = st.text_input("Username", value=username, key=f"un_{uid}")
                    new_coins = st.number_input("Moedas", value=int(coins), min_value=0, step=10, key=f"cn_{uid}")
                    if st.form_submit_button("💾 Salvar"):
                        ok, msg = admin_update_user(uid, new_name, new_coins)
                        log_admin_action(user_id, "edit_user", target_type="user",
                                         target_id=uid,
                                         details={"username": new_name, "coins": new_coins})
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            with col_role:
                st.markdown("**Papel**")
                if is_adm:
                    if uid != user_id:
                        if st.button("🔻 Revogar Admin", key=f"revoke_{uid}"):
                            ok, msg = set_admin_role(user_id, uid, grant=False)
                            if ok:
                                st.success(msg); st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.caption("(você mesmo)")
                else:
                    if st.button("🛡️ Tornar Admin", key=f"grant_{uid}"):
                        ok, msg = set_admin_role(user_id, uid, grant=True)
                        if ok:
                            st.success(msg); st.rerun()
                        else:
                            st.error(msg)

            with col_del:
                st.markdown("**Remover**")
                if uid != user_id:
                    confirm_key = f"confirm_del_{uid}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False

                    if not st.session_state[confirm_key]:
                        if st.button("🗑️", key=f"del_btn_{uid}", help="Deletar usuário"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning("Confirmar?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Sim", key=f"del_yes_{uid}"):
                                ok, msg = admin_delete_user(user_id, uid)
                                st.session_state[confirm_key] = False
                                if ok:
                                    st.success(msg); st.rerun()
                                else:
                                    st.error(msg)
                        with c2:
                            if st.button("❌ Não", key=f"del_no_{uid}"):
                                st.session_state[confirm_key] = False
                                st.rerun()
                else:
                    st.caption("—")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Gift Loot Box
# ══════════════════════════════════════════════════════════════════════════════
with tab_gift:
    st.markdown("### 🎁 Enviar Loot Box para Usuário")
    st.caption("Entrega Loot Boxes na mochila do usuário. A abertura passa a ser manual na aba Mochila.")

    all_users_gift = get_all_users("")
    user_options = {f"{u['username'] or '(sem nome)'} — {u['email'] or u['id']}": u["id"] for u in all_users_gift}

    gift_target_label = st.selectbox("Usuário destinatário", options=list(user_options.keys()), key="gift_target")
    gift_count = st.number_input("Quantidade de loot boxes", min_value=1, max_value=10, value=1, step=1, key="gift_count")

    if st.button("🎁 Enviar", key="gift_send_btn", type="primary"):
        target_uid = user_options[gift_target_label]
        ok, msg, results = admin_gift_loot_box(user_id, target_uid, int(gift_count))
        if ok:
            st.success(msg)
            for loot in results:
                st.markdown(
                    f'• <strong>{loot["label"]}</strong> adicionado à mochila',
                    unsafe_allow_html=True,
                )
        else:
            st.error(msg)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Exercises
# ══════════════════════════════════════════════════════════════════════════════
_VALID_BODY_PARTS = [
    "Peitoral", "Braços", "Antebraços", "Costas", "Ombros",
    "Coxas", "Pernas", "Cintura", "Pescoço", "Cardio",
]

with tab_exercises:
    st.markdown("### 📝 Criar Exercício")

    with st.form("create_exercise_form"):
        col_en, col_pt = st.columns(2)
        with col_en:
            ex_name    = st.text_input("Nome (inglês) *", placeholder="Barbell Bench Press")
        with col_pt:
            ex_name_pt = st.text_input("Nome (português) *", placeholder="Supino com Barra")

        col_bp, col_eq = st.columns(2)
        with col_bp:
            ex_body_parts = st.multiselect(
                "Partes do corpo *",
                options=_VALID_BODY_PARTS,
                help="Define a afinidade de tipo Pokémon para spawns temáticos",
            )
        with col_eq:
            ex_equipments_raw = st.text_input(
                "Equipamentos (separados por vírgula)",
                placeholder="barbell, bench",
            )

        ex_muscles_raw = st.text_input(
            "Músculos alvo (separados por vírgula)",
            placeholder="pectorals, triceps, anterior deltoid",
        )

        ex_gif_file = st.file_uploader(
            "GIF do exercício (opcional)",
            type=["gif", "png", "jpg", "jpeg", "webp"],
            help=f"Enviado para o bucket '{_GIF_BUCKET}' no Supabase Storage.",
        )

        submitted = st.form_submit_button("➕ Criar Exercício", type="primary")

    if submitted:
        muscles = [m.strip() for m in ex_muscles_raw.split(",") if m.strip()]
        equips  = [e.strip() for e in ex_equipments_raw.split(",") if e.strip()]

        gif_url = None
        if ex_gif_file is not None:
            upload_ok, upload_result = _upload_exercise_gif(ex_gif_file)
            if not upload_ok:
                st.error(f"Falha ao enviar GIF: {upload_result}")
                st.stop()
            gif_url = upload_result

        ok, msg, new_id = admin_create_exercise(
            ex_name, ex_name_pt, muscles, ex_body_parts, equips, gif_url,
        )
        if ok:
            clear_catalog_cache()
            log_admin_action(
                user_id, "create_exercise",
                target_type="exercise", target_id=str(new_id),
                details={"name": ex_name, "name_pt": ex_name_pt},
            )
            st.success(msg)
        else:
            st.error(msg)

    st.divider()
    st.markdown("### 📋 Exercícios cadastrados")
    exercises = get_cached_exercises()
    st.caption(f"{len(exercises)} exercício(s) no catálogo")

    ex_search = st.text_input("🔍 Buscar", placeholder="Nome do exercício...", key="admin_ex_search")
    filtered = [
        e for e in exercises
        if not ex_search or ex_search.lower() in (e["name"] or "").lower()
        or ex_search.lower() in (e["name_pt"] or "").lower()
    ]

    for ex in filtered[:100]:
        label = ex["name_pt"] or ex["name"]
        with st.expander(f"#{ex['id']} — {label}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**EN:** {ex['name']}")
                st.markdown(f"**PT:** {ex['name_pt'] or '—'}")
                st.markdown(f"**Partes do corpo:** {', '.join(ex['body_parts'] or [])}")
            with c2:
                st.markdown(f"**Músculos:** {', '.join(ex['target_muscles'] or [])}")
                st.markdown(f"**Equipamentos:** {', '.join(ex['equipments'] or [])}")
            if ex["gif_url"]:
                st.markdown(f"**GIF:** [{ex['gif_url'][:60]}...]({ex['gif_url']})")

    if len(filtered) > 100:
        st.caption(f"Mostrando 100 de {len(filtered)} resultados — refine a busca.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — System Logs
# ══════════════════════════════════════════════════════════════════════════════
with tab_logs:
    fc1, fc2, fc3 = st.columns([2, 2, 1])
    with fc1:
        action_f = st.text_input("Filtrar por ação", key="log_action_filter", placeholder="ex: delete_user")
    with fc2:
        user_f   = st.text_input("Filtrar por usuário", key="log_user_filter", placeholder="username")
    with fc3:
        limit_f  = st.number_input("Limite", value=100, min_value=10, max_value=500, step=10, key="log_limit")

    logs = get_system_logs(limit=int(limit_f),
                           action_filter=action_f.strip(),
                           user_filter=user_f.strip())

    if not logs:
        st.info("Nenhum log encontrado.")
    else:
        st.caption(f"{len(logs)} registro(s)")
        for log in logs:
            action    = log["action"]
            username  = log["username"] or "sistema"
            ts        = str(log["created_at"])[:19].replace("T", " ") if log["created_at"] else "—"
            t_type    = log["target_type"] or ""
            t_id      = log["target_id"] or ""
            details   = log["details"] or {}

            css_class = "log-row"
            if "admin" in action:
                css_class += " admin-action"
            elif "delete" in action:
                css_class += " delete"

            target_str = f" → {t_type} `{t_id}`" if t_type else ""
            detail_str = f"  `{details}`" if details else ""

            st.markdown(f"""
            <div class="{css_class}">
              <strong>{action}</strong>{target_str} &nbsp;
              <span style="color:#8b949e">por <strong>{username}</strong></span>
              {detail_str}<br>
              <span class="log-time">{ts}</span>
            </div>
            """, unsafe_allow_html=True)
