import streamlit as st
from utils.db import (
    get_workout_builder_tree, create_workout_sheet, update_workout_sheet, delete_workout_sheet,
    create_workout_day, delete_workout_day,
    add_exercise_to_day,
    update_day_exercise, remove_exercise_from_day,
    get_exercises,
)

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.user.id

# ── session state defaults ────────────────────────────────────────────────────
for _k, _v in [
    ("adding_day_to", None),
    ("adding_ex_to", None),
    ("editing_sheet", None),
    ("editing_wde", None),
    ("confirm_delete", None),
    ("show_new_sheet_form", False),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── exercise catalog ──────────────────────────────────────────────────────────
all_exercises     = get_exercises()
exercise_map      = {ex["id"]: ex["name_pt"] or ex["name"] for ex in all_exercises}
exercise_ids      = [ex["id"] for ex in all_exercises]
exercise_metric   = {ex["id"]: ex.get("metric_type", "weight") for ex in all_exercises}

_RO_METRIC_LABELS = {"weight": "Reps", "distance": "km (por intervalo)", "time": "min (por set)"}
_RO_METRIC_ICONS  = {"weight": "🏋️", "distance": "📏", "time": "⏱️"}

# ── header ────────────────────────────────────────────────────────────────────
col_title, col_new = st.columns([5, 1])
with col_title:
    st.title("Rotinas 📋")
with col_new:
    st.write("")
    if st.button("＋ Nova Rotina", use_container_width=True, type="primary"):
        st.session_state.show_new_sheet_form = not st.session_state.show_new_sheet_form
        st.rerun()

# ── new sheet form ────────────────────────────────────────────────────────────
if st.session_state.show_new_sheet_form:
    with st.form("form_new_sheet", clear_on_submit=True):
        new_name = st.text_input("Nome da rotina", placeholder="ex: PPL, Full Body, ABC…")
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            submitted_sheet = st.form_submit_button("Criar", type="primary", use_container_width=True)
        with col_cancel:
            cancelled_sheet = st.form_submit_button("Cancelar", use_container_width=True)
    if submitted_sheet:
        if new_name.strip():
            new_id, err = create_workout_sheet(user_id, new_name.strip())
            if new_id:
                st.success(f"Rotina **{new_name.strip()}** criada!")
                st.session_state.show_new_sheet_form = False
                st.rerun()
            else:
                st.error(f"Erro ao criar rotina: {err}")
        else:
            st.session_state.show_new_sheet_form = False
            st.rerun()
    elif cancelled_sheet:
        st.session_state.show_new_sheet_form = False
        st.rerun()

# ── sheets list ───────────────────────────────────────────────────────────────
sheets = get_workout_builder_tree(user_id)

if not sheets:
    st.info("Nenhuma rotina criada ainda. Clique em **＋ Nova Rotina** para começar.", icon="📋")
    st.stop()

for sheet in sheets:
    sid = sheet["id"]
    day_word = "dia" if sheet["day_count"] == 1 else "dias"
    expander_label = f"**{sheet['name']}** — {sheet['day_count']} {day_word}"

    with st.expander(expander_label, expanded=True):
        # ── sheet actions ─────────────────────────────────────────────────────
        confirm_sheet = ("sheet", sid)
        if st.session_state.confirm_delete == confirm_sheet:
            st.warning(f"Deletar **{sheet['name']}** e todos os dias/exercícios?")
            cy, cn, _ = st.columns([1, 1, 4])
            with cy:
                if st.button("Confirmar", key=f"yes_s_{sid}", type="primary"):
                    ok, err = delete_workout_sheet(sid)
                    st.session_state.confirm_delete = None
                    if err:
                        st.error(f"Erro ao deletar rotina: {err}")
                        st.stop()
                    st.rerun()
            with cn:
                if st.button("Cancelar", key=f"no_s_{sid}"):
                    st.session_state.confirm_delete = None
                    st.rerun()
        else:
            _, col_edit_s, col_del_s = st.columns([4, 1, 1])
            with col_edit_s:
                if st.button("✏ Editar rotina", key=f"edit_s_{sid}", use_container_width=True):
                    st.session_state.editing_sheet = sid
                    st.session_state.confirm_delete = None
                    st.rerun()
            with col_del_s:
                if st.button("🗑 Deletar rotina", key=f"del_s_{sid}", use_container_width=True):
                    st.session_state.editing_sheet = None
                    st.session_state.confirm_delete = confirm_sheet
                    st.rerun()

        if st.session_state.editing_sheet == sid:
            with st.form(f"form_edit_sheet_{sid}"):
                edited_sheet_name = st.text_input("Nome da rotina", value=sheet["name"])
                sf1, sf2 = st.columns(2)
                with sf1:
                    save_sheet = st.form_submit_button("Salvar", type="primary", use_container_width=True)
                with sf2:
                    cancel_sheet = st.form_submit_button("Cancelar", use_container_width=True)
            if save_sheet:
                if edited_sheet_name.strip():
                    ok, err = update_workout_sheet(user_id, sid, edited_sheet_name.strip())
                    if err:
                        st.error(f"Erro ao editar rotina: {err}")
                        st.stop()
                    if ok:
                        st.success("Rotina atualizada com sucesso!")
                st.session_state.editing_sheet = None
                st.rerun()
            elif cancel_sheet:
                st.session_state.editing_sheet = None
                st.rerun()

        st.divider()

        # ── days ──────────────────────────────────────────────────────────────
        days = sheet.get("days", [])

        for day in days:
            did = day["id"]
            ex_word = "exercício" if day["exercise_count"] == 1 else "exercícios"

            # day header row
            col_dname, col_ddel = st.columns([5, 1])
            with col_dname:
                st.markdown(
                    f"**{day['name']}** "
                    f"<span style='color:#888;font-size:12px'>— {day['exercise_count']} {ex_word}</span>",
                    unsafe_allow_html=True,
                )
            with col_ddel:
                confirm_day = ("day", did)
                if st.session_state.confirm_delete == confirm_day:
                    if st.button("✓ Sim", key=f"yes_d_{did}", type="primary"):
                        ok, err = delete_workout_day(did)
                        st.session_state.confirm_delete = None
                        if err:
                            st.error(f"Erro ao deletar dia: {err}")
                            st.stop()
                        st.rerun()
                else:
                    if st.button("🗑", key=f"del_d_{did}", help="Deletar dia"):
                        st.session_state.confirm_delete = confirm_day
                        st.rerun()

            if st.session_state.confirm_delete == confirm_day:
                st.warning(f"Deletar **{day['name']}** e todos os exercícios?")
                if st.button("Cancelar", key=f"no_d_{did}"):
                    st.session_state.confirm_delete = None
                    st.rerun()

            # ── exercises in this day ─────────────────────────────────────────
            day_exs = day.get("exercises", [])

            if not day_exs:
                st.caption("Sem exercícios prescritos.")

            for wde in day_exs:
                wid = wde["id"]

                _wde_metric = wde.get("metric_type", exercise_metric.get(wde["exercise_id"], "weight"))
                _wde_mlbl   = _RO_METRIC_LABELS.get(_wde_metric, "Reps")
                _wde_icon   = _RO_METRIC_ICONS.get(_wde_metric, "")

                if st.session_state.editing_wde == wid:
                    # inline edit form
                    with st.form(f"form_edit_{wid}"):
                        ec1, ec2, ec3, ec4, ec5 = st.columns([3, 1, 1, 1, 1])
                        with ec1:
                            st.write(wde["name"])
                        with ec2:
                            new_sets = st.number_input(
                                "Sets", min_value=1, max_value=20,
                                value=wde["sets"], label_visibility="collapsed",
                            )
                        with ec3:
                            new_reps = st.number_input(
                                _wde_mlbl, min_value=1, max_value=10000,
                                value=wde["reps"], label_visibility="collapsed",
                            )
                        with ec4:
                            saved_ex = st.form_submit_button("✓", use_container_width=True)
                        with ec5:
                            cancelled_ex = st.form_submit_button("✕", use_container_width=True)
                    if saved_ex:
                        _, err = update_day_exercise(wid, int(new_sets), int(new_reps))
                        if err:
                            st.error(f"Erro ao salvar: {err}")
                            st.stop()
                        st.session_state.editing_wde = None
                        st.rerun()
                    elif cancelled_ex:
                        st.session_state.editing_wde = None
                        st.rerun()
                else:
                    # display row
                    dc1, dc2, dc3, dc4 = st.columns([3, 2, 1, 1])
                    with dc1:
                        st.write(f"{_wde_icon} {wde['name']}")
                    with dc2:
                        st.write(f"{wde['sets']} × {wde['reps']} {_wde_mlbl.split()[0]}")
                    with dc3:
                        if st.button("✏", key=f"edit_{wid}", help="Editar"):
                            st.session_state.editing_wde = wid
                            st.rerun()
                    with dc4:
                        if st.button("🗑", key=f"rm_{wid}", help="Remover"):
                            _, err = remove_exercise_from_day(wid)
                            if err:
                                st.error(f"Erro ao remover: {err}")
                                st.stop()
                            st.rerun()

            # ── add exercise form ─────────────────────────────────────────────
            if st.session_state.adding_ex_to == did:
                with st.form(f"form_add_ex_{did}", clear_on_submit=True):
                    sel_ex_id = st.selectbox(
                        "Exercício",
                        options=exercise_ids,
                        format_func=lambda eid: f"{_RO_METRIC_ICONS.get(exercise_metric.get(eid,'weight'),'')} {exercise_map.get(eid, str(eid))}",
                    )
                    _add_metric = exercise_metric.get(int(sel_ex_id), "weight")
                    _add_mlbl   = _RO_METRIC_LABELS.get(_add_metric, "Reps")
                    _add_max    = 999 if _add_metric != "weight" else 100
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        add_sets = st.number_input("Sets", min_value=1, max_value=20, value=3)
                    with ac2:
                        add_reps = st.number_input(_add_mlbl, min_value=1, max_value=_add_max, value=10 if _add_metric == "weight" else 1)
                    af1, af2 = st.columns(2)
                    with af1:
                        ok_ex = st.form_submit_button("Adicionar", type="primary", use_container_width=True)
                    with af2:
                        cancel_ex = st.form_submit_button("Cancelar", use_container_width=True)
                if ok_ex:
                    _, err = add_exercise_to_day(did, int(sel_ex_id), int(add_sets), int(add_reps))
                    if err:
                        st.error(f"Erro ao adicionar exercício: {err}")
                        st.stop()
                    st.session_state.adding_ex_to = None
                    st.rerun()
                elif cancel_ex:
                    st.session_state.adding_ex_to = None
                    st.rerun()
            else:
                if st.button("＋ Adicionar Exercício", key=f"add_ex_{did}"):
                    st.session_state.adding_ex_to = did
                    st.rerun()

            st.markdown("---")

        # ── add day form ──────────────────────────────────────────────────────
        if st.session_state.adding_day_to == sid:
            with st.form(f"form_add_day_{sid}", clear_on_submit=True):
                new_day_name = st.text_input("Nome do dia", placeholder="ex: Peito e Tríceps…")
                df1, df2 = st.columns(2)
                with df1:
                    ok_day = st.form_submit_button("Criar", type="primary", use_container_width=True)
                with df2:
                    cancel_day = st.form_submit_button("Cancelar", use_container_width=True)
            if ok_day:
                if new_day_name.strip():
                    new_did, err = create_workout_day(sid, new_day_name.strip())
                    if err:
                        st.error(f"Erro ao criar dia: {err}")
                        st.stop()
                st.session_state.adding_day_to = None
                st.rerun()
            elif cancel_day:
                st.session_state.adding_day_to = None
                st.rerun()
        else:
            if st.button("＋ Adicionar Dia", key=f"add_day_{sid}"):
                st.session_state.adding_day_to = sid
                st.rerun()
