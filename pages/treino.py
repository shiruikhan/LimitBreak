import datetime
import os
import uuid
import streamlit as st
from utils.db import (
    get_workout_sheets, get_sheet_days, get_day_exercises_for_builder,
    get_exercises, do_exercise_event,
    get_daily_xp_from_exercise, get_workout_streak, get_workout_history,
    get_image_as_base64, _today_brt, check_and_award_achievements,
    update_mission_progress,
)
from utils.type_colors import get_type_color
from utils.abilities import get_ability_description as _get_ability_desc, WORKOUT_ABILITIES as _WORKOUT_ABILITIES
from utils.quest_tracker import render_quest_sidebar

if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.user_id
BASE_DIR = os.getcwd()
_DAILY_CAP = 300

# ── session state ─────────────────────────────────────────────────────────────
for _k, _v in [
    ("workout_rows", []),
    ("workout_result", None),
    ("adding_workout_ex", False),
    ("workout_date", _today_brt()),
    ("workout_sheet_id", None),
    ("workout_day_id", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── sidebar quest tracker ─────────────────────────────────────────────────────
with st.sidebar:
    render_quest_sidebar(user_id)

# ── catalog ───────────────────────────────────────────────────────────────────
all_exercises = get_exercises()
ex_name_map = {ex["id"]: ex["name_pt"] or ex["name"] for ex in all_exercises}
ex_id_options = [ex["id"] for ex in all_exercises]

# ── styles (reused from calendario pattern) ───────────────────────────────────
st.markdown("""
<style>
.tr-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #FF7E6B, #FFB347);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase;
}
.tr-sub { color: #8b949e; font-size: 0.85rem; margin: 0 0 4px; letter-spacing: 2px; text-transform: uppercase; }

.tr-stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.tr-stat-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 14px;
    padding: 12px 18px; flex: 1; min-width: 120px;
}
.tr-stat-val { font-family: "Bebas Neue", sans-serif; font-size: 1.7rem; color: #FFB347; letter-spacing: 2px; }
.tr-stat-lbl { font-size: 0.62rem; color: #8b949e; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-top: 2px; }

.cap-bar-bg {
    background: #21262d; border-radius: 9999px; height: 8px; overflow: hidden; margin-top: 6px;
}
.cap-bar-fill { height: 100%; border-radius: 9999px; transition: width 0.3s ease; }
.cap-bar-fill.ok    { background: linear-gradient(90deg, #2ea043, #58A6FF); }
.cap-bar-fill.warn  { background: linear-gradient(90deg, #FFB347, #FF7E6B); }
.cap-bar-fill.full  { background: #f85149; }

.result-card {
    border-radius: 14px; padding: 14px 18px; margin-bottom: 10px; border: 1px solid;
}
.result-card.success   { background: rgba(47,158,68,0.12); border-color: rgba(47,158,68,0.5); }
.result-card.spawned   { background: rgba(112,56,248,0.12); border-color: rgba(112,56,248,0.5); }
.result-card.shiny     { background: rgba(255,215,0,0.10); border-color: rgba(255,215,0,0.6); }
.result-card.levelup   { background: rgba(88,166,255,0.08); border-color: rgba(88,166,255,0.5); }
.result-card.evolution { background: #1f0f2e; border-color: #BC8CFF; }
.result-card.milestone { background: rgba(255,179,71,0.12); border-color: rgba(255,179,71,0.55); }
.result-card.pr       { background: rgba(234,179,8,0.10);  border-color: rgba(234,179,8,0.55); }
.result-card.egg-hatch { background: rgba(236,72,153,0.10); border-color: rgba(236,72,153,0.5); }
.result-card.ability  { background: rgba(168,85,247,0.08); border-color: rgba(168,85,247,0.4); }
.pr-row { display:flex; justify-content:space-between; align-items:center; margin:4px 0; font-size:0.85rem; }
.pr-name { color:#e6edf3; font-weight:600; }
.pr-weight { color:#FDE047; font-weight:700; }
.egg-hatch-name { font-size:1.05rem; font-weight:800; color:#f472b6; margin-top:4px; }
.ability-row { font-size:0.82rem; color:#c4b5fd; margin-top:4px; }
.result-title { font-size: 1rem; font-weight: 700; color: #e6edf3; margin-bottom: 6px; }
.result-body  { color: #8b949e; font-size: 0.85rem; }
.spawn-name   { font-size: 1.15rem; font-weight: 800; color: #A27DFA; }
.evo-arrow    { color: #BC8CFF; font-size: 1.05rem; margin: 0 8px; }
.evo-name-from{ color: #8b949e; font-weight: 700; }
.evo-name-to  { color: #BC8CFF; font-size: 1.05rem; font-weight: 800; }

.history-row {
    display: flex; justify-content: space-between; align-items: center;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 8px 14px; margin-bottom: 6px; font-size: 0.85rem;
}
.history-row b { color: #e6edf3; }
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────────────────────────
streak = get_workout_streak(user_id)
xp_today = get_daily_xp_from_exercise(user_id)
xp_pct = min(xp_today / _DAILY_CAP, 1.0)
cap_cls = "full" if xp_today >= _DAILY_CAP else ("warn" if xp_today > 200 else "ok")

st.markdown("<p class='tr-title'>TREINO 🏋️</p>", unsafe_allow_html=True)
st.markdown("<p class='tr-sub'>REGISTRO DE SESSÃO</p>", unsafe_allow_html=True)

st.markdown(f"""
<div class='tr-stat-row'>
  <div class='tr-stat-card'>
    <div class='tr-stat-val'>🔥 {streak}</div>
    <div class='tr-stat-lbl'>Streak de treino</div>
  </div>
  <div class='tr-stat-card' style='flex:2'>
    <div class='tr-stat-val'>{xp_today} / {_DAILY_CAP} XP</div>
    <div class='tr-stat-lbl'>Cap diário de exercício</div>
    <div class='cap-bar-bg'>
      <div class='cap-bar-fill {cap_cls}' style='width:{xp_pct*100:.0f}%'></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── routine selector ──────────────────────────────────────────────────────────
sheets = get_workout_sheets(user_id)
sheet_options = [None] + [s["id"] for s in sheets]
sheet_name_map = {s["id"]: s["name"] for s in sheets}


def _fmt_sheet(sid):
    if sid is None:
        return "— Treino livre —"
    return sheet_name_map.get(sid, "")


col_date, col_sheet, col_day, col_imp = st.columns([1.2, 1.5, 1.5, 1.2])
with col_date:
    workout_date = st.date_input(
        "📅 Data",
        value=st.session_state.workout_date,
        max_value=_today_brt(),
    )
    st.session_state.workout_date = workout_date

with col_sheet:
    sheet_idx = sheet_options.index(st.session_state.workout_sheet_id) if st.session_state.workout_sheet_id in sheet_options else 0
    sel_sheet = st.selectbox(
        "Rotina",
        options=sheet_options,
        index=sheet_idx,
        format_func=_fmt_sheet,
    )
    if sel_sheet != st.session_state.workout_sheet_id:
        st.session_state.workout_sheet_id = sel_sheet
        st.session_state.workout_day_id = None
        st.rerun()

with col_day:
    if sel_sheet:
        days = get_sheet_days(sel_sheet)
        day_options = [None] + [d["id"] for d in days]
        day_name_map = {d["id"]: d["name"] for d in days}
        day_idx = day_options.index(st.session_state.workout_day_id) if st.session_state.workout_day_id in day_options else 0
        sel_day = st.selectbox(
            "Dia",
            options=day_options,
            index=day_idx,
            format_func=lambda did: "Selecione…" if did is None else day_name_map.get(did, ""),
        )
        st.session_state.workout_day_id = sel_day
    else:
        st.selectbox("Dia", options=["—"], disabled=True)
        sel_day = None
        st.session_state.workout_day_id = None

with col_imp:
    st.write("")
    st.write("")
    if st.button(
        "⬇ Importar Padrão",
        disabled=not bool(sel_day),
        use_container_width=True,
        help="Adiciona os exercícios prescritos para o dia selecionado",
    ):
        prescribed = get_day_exercises_for_builder(sel_day)
        for p in prescribed:
            st.session_state.workout_rows.append({
                "row_id":      str(uuid.uuid4()),
                "exercise_id": p["exercise_id"],
                "name":        p["name"],
                "sets":        p["sets"],
                "reps":        p["reps"],
                "weight":      0.0,
            })
        st.rerun()

st.divider()

# ── exercise table ────────────────────────────────────────────────────────────
hc1, hc2, hc3, hc4, hc5 = st.columns([3, 1, 1, 1.2, 0.6])
with hc1: st.markdown("**Exercício**")
with hc2: st.markdown("**Sets**")
with hc3: st.markdown("**Reps**")
with hc4: st.markdown("**Peso (kg)**")
with hc5: st.markdown(" ")

if not st.session_state.workout_rows:
    st.caption("Nenhum exercício adicionado. Use **Importar Padrão** ou **Adicionar Exercício**.")

for row in st.session_state.workout_rows:
    rid = row["row_id"]
    rc1, rc2, rc3, rc4, rc5 = st.columns([3, 1, 1, 1.2, 0.6])
    with rc1:
        st.write(row["name"])
    with rc2:
        st.number_input(
            "Sets", min_value=1, max_value=20,
            value=int(row.get("sets", 3)),
            key=f"w_sets_{rid}", label_visibility="collapsed",
        )
    with rc3:
        st.number_input(
            "Reps", min_value=1, max_value=100,
            value=int(row.get("reps", 10)),
            key=f"w_reps_{rid}", label_visibility="collapsed",
        )
    with rc4:
        st.number_input(
            "Peso", min_value=0.0, max_value=999.0, step=2.5,
            value=float(row.get("weight", 0.0)),
            key=f"w_weight_{rid}", label_visibility="collapsed",
            format="%.1f",
        )
    with rc5:
        if st.button("🗑", key=f"w_rm_{rid}", help="Remover exercício"):
            st.session_state.workout_rows = [
                r for r in st.session_state.workout_rows if r["row_id"] != rid
            ]
            for suf in ("sets", "reps", "weight"):
                st.session_state.pop(f"w_{suf}_{rid}", None)
            st.rerun()

# ── add exercise form ─────────────────────────────────────────────────────────
if st.session_state.adding_workout_ex:
    with st.form("form_workout_add_ex", clear_on_submit=True):
        sel_ex_id = st.selectbox(
            "Exercício",
            options=ex_id_options,
            format_func=lambda eid: ex_name_map.get(eid, str(eid)),
        )
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            init_sets = st.number_input("Sets", min_value=1, max_value=20, value=3)
        with ac2:
            init_reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
        with ac3:
            init_weight = st.number_input("Peso (kg)", min_value=0.0, max_value=999.0, step=2.5, value=0.0, format="%.1f")
        af1, af2 = st.columns(2)
        with af1:
            ok_add = st.form_submit_button("Adicionar", type="primary", use_container_width=True)
        with af2:
            cancel_add = st.form_submit_button("Cancelar", use_container_width=True)
    if ok_add:
        st.session_state.workout_rows.append({
            "row_id":      str(uuid.uuid4()),
            "exercise_id": int(sel_ex_id),
            "name":        ex_name_map.get(int(sel_ex_id), str(sel_ex_id)),
            "sets":        int(init_sets),
            "reps":        int(init_reps),
            "weight":      float(init_weight),
        })
        st.session_state.adding_workout_ex = False
        st.rerun()
    elif cancel_add:
        st.session_state.adding_workout_ex = False
        st.rerun()
else:
    if st.button("＋ Adicionar Exercício"):
        st.session_state.adding_workout_ex = True
        st.rerun()

st.divider()

# ── register ──────────────────────────────────────────────────────────────────
has_rows = len(st.session_state.workout_rows) > 0

if st.button(
    "✅ Registrar Treino",
    type="primary",
    use_container_width=True,
    disabled=not has_rows,
):
    payload = []
    for row in st.session_state.workout_rows:
        rid = row["row_id"]
        sets = int(st.session_state.get(f"w_sets_{rid}", row.get("sets", 1)))
        reps = int(st.session_state.get(f"w_reps_{rid}", row.get("reps", 1)))
        weight = float(st.session_state.get(f"w_weight_{rid}", row.get("weight", 0.0)))
        payload.append({
            "exercise_id": row["exercise_id"],
            "sets_data":   [{"reps": reps, "weight": weight} for _ in range(sets)],
            "notes":       None,
        })
    res = do_exercise_event(user_id, payload, day_id=st.session_state.workout_day_id)
    st.session_state.workout_result = res
    if not res.get("error"):
        new_ach = check_and_award_achievements(user_id)
        if new_ach:
            pending = st.session_state.get("new_achievements_pending", [])
            seen = {a["slug"] for a in pending}
            st.session_state.new_achievements_pending = pending + [a for a in new_ach if a["slug"] not in seen]
        # Mission progress
        sets_total = sum(
            int(st.session_state.get(f"w_sets_{r['row_id']}", r.get("sets", 1)))
            for r in st.session_state.workout_rows
        )
        max_weight = max(
            (float(st.session_state.get(f"w_weight_{r['row_id']}", r.get("weight", 0.0)))
             for r in st.session_state.workout_rows),
            default=0.0,
        )
        newly_done = update_mission_progress(user_id, "workout", {
            "sets_total": sets_total,
            "max_weight": max_weight,
            "xp_earned":  res.get("xp_earned", 0),
        })
        prs = res.get("prs") or []
        if prs:
            update_mission_progress(user_id, "pr", {"count": len(prs)})
        if newly_done:
            st.session_state["missions_newly_done"] = newly_done
        for row in st.session_state.workout_rows:
            rid = row["row_id"]
            for suf in ("sets", "reps", "weight"):
                st.session_state.pop(f"w_{suf}_{rid}", None)
        st.session_state.workout_rows = []
    st.rerun()

# ── result display ────────────────────────────────────────────────────────────
res = st.session_state.workout_result
if res:
    if res.get("error") and not res.get("xp_earned"):
        st.error(f"⚠ {res['error']}")
    else:
        xp_gained = res.get("xp_earned", 0)
        cap_note = " (limite diário aplicado)" if res.get("capped") else ""
        st.markdown(
            f"<div class='result-card success'>"
            f"<div class='result-title'>✅ Treino registrado! +{xp_gained} XP{cap_note}</div>"
            f"<div class='result-body'>Sessão salva e XP concedido ao seu Pokémon principal.</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # PR celebration card
        prs = res.get("prs") or []
        if prs:
            pr_rows_html = ""
            for pr in prs:
                old_w = pr["old_weight"]
                new_w = pr["new_weight"]
                reps  = pr["new_reps"]
                arrow = f"{old_w:.1f} → {new_w:.1f} kg" if old_w > 0 else f"{new_w:.1f} kg (primeiro registro)"
                pr_rows_html += (
                    f"<div class='pr-row'>"
                    f"<span class='pr-name'>{pr['exercise_name']}</span>"
                    f"<span class='pr-weight'>{arrow} &nbsp;×{reps}</span>"
                    f"</div>"
                )
            pr_xp_note = f"+{len(prs) * 50} XP bônus"
            st.markdown(
                f"<div class='result-card pr'>"
                f"<div class='result-title'>🏅 Recorde Pessoal! {pr_xp_note}</div>"
                f"{pr_rows_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Ability activation card
        abilfx = res.get("ability_effects") or {}
        if abilfx:
            aslug = abilfx.get("slug", "")
            adesc = _get_ability_desc(aslug) or ""
            notes = []
            if "blaze_xp_after" in abilfx:
                diff = abilfx["blaze_xp_after"] - abilfx["blaze_xp_before"]
                notes.append(f"+{diff} XP bônus (Blaze)")
            if "synchronize_bonus_xp" in abilfx:
                notes.append(f"+{abilfx['synchronize_bonus_xp']} XP bônus para a equipe (Synchronize)")
            if "pickup_item" in abilfx:
                notes.append(f"Item obtido: {abilfx['pickup_item']} (Pickup)")
            if "compound_eyes_rerolled" in abilfx:
                notes.append("Spawn rerrolado (Compound Eyes)")
            if "pressure_type" in abilfx:
                notes.append(f"Spawn focado em {abilfx['pressure_type']} (Pressure)")
            notes_html = "".join(f"<div class='ability-row'>• {n}</div>" for n in notes)
            if notes:
                st.markdown(
                    f"<div class='result-card ability'>"
                    f"<div class='result-title'>⚡ Habilidade ativa: {aslug}</div>"
                    f"{notes_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Egg hatch banner
        hatched = res.get("eggs_hatched") or []
        for egg in hatched:
            hatch_sprite = egg.get("sprite_url", "")
            hatch_b64 = get_image_as_base64(hatch_sprite) if hatch_sprite else None
            hatch_img = (
                f"<img src='data:image/png;base64,{hatch_b64}' "
                f"style='width:80px;image-rendering:pixelated'>"
                if hatch_b64 else "<div style='font-size:2.4rem'>🐣</div>"
            )
            rarity_label = egg.get("rarity", "common").upper()
            st.markdown(
                f"<div class='result-card egg-hatch' style='display:flex;align-items:center;gap:16px'>"
                f"<div>{hatch_img}</div>"
                f"<div>"
                f"<div class='result-title'>🥚 Ovo chocou! ({rarity_label})</div>"
                f"<div class='egg-hatch-name'>{egg['name']}</div>"
                f"<div class='result-body' style='margin-top:4px'>"
                f"#{str(egg['species_id']).zfill(4)} foi capturado e adicionado à sua coleção!</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            st.session_state.team_spawn_notice = {
                "source":     "egg_hatch",
                "name":       egg["name"],
                "id":         egg["species_id"],
                "sprite_url": egg.get("sprite_url", ""),
                "type1":      egg.get("type1"),
            }

        # Egg grant notification
        granted = res.get("eggs_granted") or []
        for eg in granted:
            st.markdown(
                f"<div class='result-card' style='background:rgba(16,185,129,0.08);"
                f"border-color:rgba(16,185,129,0.4)'>"
                f"<div class='result-title'>🥚 Novo ovo recebido! ({eg['rarity'].upper()})</div>"
                f"<div class='result-body'>Treine mais {eg['workouts_to_hatch']} vezes para chocar.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Milestone banners
        milestone = res.get("milestone")
        streak_val = res.get("streak", 0)
        if milestone == "first_workout":
            bonus_xp = res.get("milestone_xp", 50)
            st.markdown(
                f"<div class='result-card milestone'>"
                f"<div class='result-title'>🎉 Primeiro treino! +{bonus_xp} XP bônus</div>"
                f"<div class='result-body'>Parabéns por começar sua jornada! "
                f"Bônus de XP concedido fora do cap diário.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif milestone and milestone.startswith("streak_"):
            if streak_val >= 30 and streak_val % 30 == 0:
                st.markdown(
                    f"<div class='result-card milestone'>"
                    f"<div class='result-title'>🌟 {streak_val} dias de streak! Spawn shiny garantido!</div>"
                    f"<div class='result-body'>Dedicação lendária — um Pokémon shiny aparece durante o treino!</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            elif streak_val >= 7 and streak_val % 7 == 0:
                st.markdown(
                    f"<div class='result-card milestone'>"
                    f"<div class='result-title'>🔥 {streak_val} dias de streak! Spawn garantido!</div>"
                    f"<div class='result-body'>Uma semana de consistência — um Pokémon aparece durante o treino!</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Spawn — one card per captured Pokémon (up to _MAX_DAILY_SPAWNS per day)
        for pk in res.get("spawned") or []:
            is_shiny  = pk.get("is_shiny", False)
            sp_path   = pk.get("sprite_url", "")
            b64       = None
            if sp_path:
                if sp_path.startswith("http"):
                    b64 = get_image_as_base64(sp_path)
                else:
                    full = os.path.join(BASE_DIR, sp_path.lstrip("/\\"))
                    hq   = full.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")
                    b64  = get_image_as_base64(hq) or get_image_as_base64(full)
            shiny_filter = "filter:drop-shadow(0 0 10px gold) saturate(1.6)" if is_shiny else ""
            img_html = (
                f"<img src='data:image/png;base64,{b64}' style='width:88px;image-rendering:pixelated;{shiny_filter}'>"
                if b64 else "<div style='font-size:2.6rem'>❓</div>"
            )
            shiny_badge = " ✨ <span style='color:#FFD700;font-weight:800'>SHINY</span>" if is_shiny else ""
            card_cls    = "shiny" if is_shiny else "spawned"
            spawn_title = "🌟 Pokémon SHINY apareceu!" if is_shiny else "✨ Pokémon apareceu durante o treino!"
            pk_name = pk["name"]
            pk_id   = pk["id"]
            st.markdown(
                f"<div class='result-card {card_cls}' style='display:flex;align-items:center;gap:18px'>"
                f"<div>{img_html}</div>"
                f"<div>"
                f"<div class='result-title'>{spawn_title}</div>"
                f"<div class='spawn-name'>{pk_name}{shiny_badge}</div>"
                f"<div class='result-body' style='margin-top:4px'>"
                f"#{str(pk_id).zfill(4)} foi capturado e adicionado à sua coleção.</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            st.session_state.team_spawn_notice = {
                "source":     "exercise",
                "name":       pk_name,
                "id":         pk_id,
                "sprite_url": pk.get("sprite_url", ""),
                "type1":      pk.get("type1"),
            }

        # XP / level-up / evolution
        xp_res = res.get("xp_result") or {}
        if xp_res and not xp_res.get("error"):
            levels_gained = xp_res.get("levels_gained", 0)
            new_level     = xp_res.get("new_level", 0)
            new_xp        = xp_res.get("new_xp", 0)
            xp_to_next    = new_level * 100
            evolutions    = xp_res.get("evolutions", [])

            if levels_gained == 0:
                st.markdown(
                    f"<div class='result-card' style='background:#161b22;border-color:#30363d'>"
                    f"<div class='result-title'>⚡ +{xp_gained} XP para o Pokémon principal</div>"
                    f"<div class='result-body'>"
                    f"XP: <b style='color:#58A6FF'>{new_xp}</b> / {xp_to_next} para o nível {new_level + 1}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                old_level = xp_res.get("old_level", new_level - levels_gained)
                lvl_txt   = (
                    f"Nível <b style='color:#58A6FF'>{old_level}</b> → "
                    f"<b style='color:#58A6FF'>{new_level}</b>"
                    if levels_gained == 1
                    else f"Subiu <b style='color:#58A6FF'>{levels_gained} níveis</b> "
                         f"({old_level} → <b style='color:#58A6FF'>{new_level}</b>)"
                )
                st.markdown(
                    f"<div class='result-card levelup'>"
                    f"<div class='result-title'>🆙 Level Up!</div>"
                    f"<div class='result-body'>{lvl_txt} &nbsp;·&nbsp; "
                    f"XP: <b style='color:#58A6FF'>{new_xp}</b> / {xp_to_next} para o próximo nível"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            for evo in evolutions:
                evo_b64    = None
                evo_sprite = evo.get("sprite_url", "")
                if evo_sprite:
                    if evo_sprite.startswith("http"):
                        evo_b64 = get_image_as_base64(evo_sprite)
                    else:
                        evo_full = os.path.join(BASE_DIR, evo_sprite.lstrip("/\\"))
                        evo_hq   = evo_full.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")
                        evo_b64  = get_image_as_base64(evo_hq) or get_image_as_base64(evo_full)
                evo_img = (
                    f"<img src='data:image/png;base64,{evo_b64}' "
                    f"style='width:88px;image-rendering:pixelated;filter:drop-shadow(0 0 12px #BC8CFF)'>"
                    if evo_b64 else "<div style='font-size:2.6rem'>🌟</div>"
                )

                if evo.get("shed"):
                    st.markdown(
                        f"<div class='result-card' style='background:rgba(46,160,67,0.1);"
                        f"border-color:rgba(46,160,67,0.6);display:flex;align-items:center;gap:18px'>"
                        f"<div>{evo_img}</div>"
                        f"<div>"
                        f"<div class='result-title'>👻 Shedinja capturado!</div>"
                        f"<div style='color:#2ea043;font-size:1.05rem;font-weight:800;margin-top:4px'>"
                        f"{evo['to_name']}</div>"
                        f"<div class='result-body' style='margin-top:6px'>"
                        f"A muda de {evo['from_name']} ganhou vida — adicionado à equipe!</div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state.team_shed_notice = {
                        "name":       evo["to_name"],
                        "from_name":  evo["from_name"],
                        "sprite_url": evo.get("sprite_url", ""),
                    }
                else:
                    st.markdown(
                        f"<div class='result-card evolution' "
                        f"style='display:flex;align-items:center;gap:18px'>"
                        f"<div>{evo_img}</div>"
                        f"<div>"
                        f"<div class='result-title'>🌟 Seu Pokémon evoluiu!</div>"
                        f"<div style='margin-top:6px'>"
                        f"<span class='evo-name-from'>{evo['from_name']}</span>"
                        f"<span class='evo-arrow'>→</span>"
                        f"<span class='evo-name-to'>{evo['to_name']}</span>"
                        f"</div>"
                        f"<div class='result-body' style='margin-top:6px'>"
                        f"Stats recalculados para a nova forma!</div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state.team_evo_notice = {
                        "from_name":  evo["from_name"],
                        "to_name":    evo["to_name"],
                        "sprite_url": evo.get("sprite_url", ""),
                    }

            xp_shared = xp_res.get("xp_share_distributed", [])
            if xp_shared:
                st.session_state.xp_share_log = xp_shared

        # Mission completion banner
        newly_done = st.session_state.pop("missions_newly_done", None)
        if newly_done:
            for md in newly_done:
                micon  = md.get("icon", "🎯")
                mlabel = md.get("label", md.get("slug", ""))
                mreward = md.get("reward_label", "")
                st.markdown(
                    f"<div style='background:rgba(184,248,47,0.08);border:1px solid rgba(184,248,47,0.35);"
                    f"border-radius:12px;padding:12px 18px;margin-top:8px'>"
                    f"<span style='font-weight:700;color:#B8F82F'>🎯 Missão concluída!</span> "
                    f"{micon} {mlabel}"
                    f"<span style='float:right;font-size:0.75rem;color:#8b949e'>Recompensa: {mreward}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.session_state.workout_result = None

# ── history ───────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Histórico (últimos 7 dias)")

history = get_workout_history(user_id, limit=30)
seven_days_ago = _today_brt() - datetime.timedelta(days=7)
recent = []
for h in history:
    completed = h.get("completed_at")
    if completed is None:
        continue
    d = completed.date() if hasattr(completed, "date") else completed
    if d >= seven_days_ago:
        recent.append((d, h))

if not recent:
    st.caption("Nenhum treino registrado nos últimos 7 dias.")
else:
    for d, h in recent:
        date_str = d.strftime("%d/%m/%Y")
        day_name = h.get("day_name") or "Treino livre"
        ex_count = h.get("exercise_count") or 0
        ex_word  = "exercício" if ex_count == 1 else "exercícios"
        spawn_badge = " 🌟" if h.get("spawned_species_id") else ""
        st.markdown(
            f"<div class='history-row'>"
            f"<span><b>{date_str}</b> &nbsp;·&nbsp; {day_name}{spawn_badge}</span>"
            f"<span style='color:#888'>{ex_count} {ex_word} &nbsp;·&nbsp; "
            f"<b style='color:#58A6FF'>+{h.get('xp_earned', 0)} XP</b></span>"
            f"</div>",
            unsafe_allow_html=True,
        )
