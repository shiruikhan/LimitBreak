# LimitBreak — Next Steps Roadmap

> Updated: April 2026. Phase 1 complete. Exercise module now owned by Silvio.

---

## Phase 1 — Core Stability & Polish ✅ DONE

### 1.1 Bug Fixes & UX Gaps
- [x] Ensure `batalha.py` handles edge case where a user has no Pokémon in slot 1 (empty team guard)
- [x] Add loading spinners or skeleton states to heavy pages (`pokedex_pessoal.py`, `equipe.py`)
- [x] Validate that `swap_team_slots` handles concurrent requests safely (double-click race condition)
- [x] Confirm `do_checkin` is idempotent under fast double-submission (Streamlit re-runs)

### 1.2 Pokédex Pessoal — Formas Regionais
- [x] Include the 42 regional forms (id > 10000) in the personal Pokédex grid
- [x] Add a "Regional Forms" generation chip to the progress bar section
- [x] Display region label (Alola / Galar / Hisui) on captured regional form cards

### 1.3 Equipe — Visual Improvements
- [x] Show Shedinja capture banner (shed mechanic) in `equipe.py` alongside the standard evolution notice
- [x] Display XP Share distribution log on team page (how much each Pokémon received)

---

## Phase 2 — Exercise Module 🏋️

**Silvio owns this end-to-end.** Full stack: DB schema → `db.py` functions → three new pages.

Three sub-features, each a separate page:
- **2A — Workout Library** (`pages/biblioteca.py`): Pokédex-style browsable grid of all exercises
- **2B — Workout Builder** (`pages/rotinas.py`): UI to compose and manage routine sheets
- **2C — Routine Log** (`pages/treino.py`): Date-specific session logging with "Import Default" from a routine

---

### 2.1 DB Schema — Already Populated ✅

Catalog tables:

| Table | Rows | Used for |
|---|---|---|
| `muscle_groups` | 22 | Anatomy label per muscle group |
| `exercises` | 152 | Catalog: `name`, `name_pt`, `target_muscles[]`, `body_parts[]`, `equipments[]`, `gif_url` |
| `workout_sheets` | 2 | Trainer-created plans assigned to a user |
| `workout_days` | 2 | Named days within a sheet |
| `workout_day_exercises` | 3 | Prescribed sets/reps per exercise per day |

Log tables already have gamification columns (applied 2026-04-27):

```sql
ALTER TABLE workout_logs ADD COLUMN xp_earned INT NOT NULL DEFAULT 0;
ALTER TABLE workout_logs ADD COLUMN spawned_species_id INT REFERENCES pokemon_species(id);
```

> **FK:** `workout_logs.user_id → user_profiles.id` (migrated via `migrate_consolidate_profiles.sql`). The legacy `profiles` table has been dropped.

**Type-spawn mapping** (hardcoded in `_BODY_PART_TYPE` in `db.py`):

| `body_parts` value | Pokémon type |
|---|---|
| chest, upper arms | Fighting |
| back | Dark |
| upper legs, lower legs | Ground |
| shoulders | Flying |
| waist | Steel |
| lower arms | Normal |
| neck | Rock |
| cardio | Water |

### 2.2 XP Formula

```
base_xp     = sets × reps × 2
volume_xp   = FLOOR(weight_kg / 10) × sets
total_xp    = base_xp + volume_xp
```

**Daily cap:** 300 XP per day from exercise (prevent farming). Check total `xp_earned` for `user_id` where `logged_at::date = today` before awarding.

Examples:
- 3 sets × 10 reps, 50 kg → `(3×10×2) + (5×3)` = 60 + 15 = **75 XP**
- 4 sets × 12 reps, 0 kg (bodyweight) → `(4×12×2) + 0` = **96 XP**

### 2.3 Backend — `utils/db.py` additions

Already implemented:

| Function | Description |
|---|---|
| `_spawn_typed(cur, user_id, type_slug)` | Typed spawn helper — filters `pokemon_species` by type; used by `do_exercise_event` and `do_checkin` |
| `get_daily_xp_from_exercise(user_id)` | Total `xp_earned` today from `workout_logs` — used for cap check |
| `do_exercise_event(user_id, exercises, day_id)` | Computes XP (with daily cap), calls `award_xp()`, rolls type-appropriate spawn (25% chance), writes `workout_logs` + `exercise_logs`. Returns `{xp_earned, capped, spawn_rolled, spawned, xp_result, error}` |
| `get_muscle_groups()` | `[{id, name}]` — `@st.cache_data` |
| `get_exercises(muscle_group_id, body_part, equipment)` | Full catalog or filtered — `@st.cache_data` |
| `get_distinct_body_parts()` | Sorted list of unique `body_parts` values across all exercises |
| `get_workout_days(user_id)` | All `workout_days` for sheets owned by the user, with sheet name |
| `get_day_exercises(day_id)` | Prescribed exercises for a day: `[{exercise_id, name_pt, sets, reps, gif_url, body_parts}]` |
| `get_workout_history(user_id, limit=30)` | Last N `workout_logs` joined with exercise names |
| `get_workout_streak(user_id)` | Count of consecutive calendar days with at least 1 log |

Still needed for Builder:

| Function | Description |
|---|---|
| `get_workout_sheets(user_id)` | `[{id, name, day_count}]` — sheets owned by the user |
| `create_workout_sheet(user_id, name)` | INSERT into `workout_sheets`; returns new `id` |
| `delete_workout_sheet(sheet_id)` | DELETE cascade (days + day_exercises) |
| `create_workout_day(sheet_id, name)` | INSERT into `workout_days`; returns new `id` |
| `delete_workout_day(day_id)` | DELETE cascade (day_exercises) |
| `add_exercise_to_day(day_id, exercise_id, sets, reps)` | INSERT into `workout_day_exercises` |
| `update_day_exercise(wde_id, sets, reps)` | UPDATE sets/reps for a prescribed exercise |
| `remove_exercise_from_day(wde_id)` | DELETE from `workout_day_exercises` |

### 2.4 Implementation Checklist

- [x] DB schema — catalog tables already populated (152 exercises, 22 muscle groups)
- [x] Migrations applied: `xp_earned` and `spawned_species_id` added to `workout_logs`
- [x] `migrate_consolidate_profiles.sql` — `workout_logs.user_id` FK migrated to `user_profiles`; `profiles` table dropped
- [x] `_spawn_typed(cur, user_id, type_slug)` — typed spawn helper in `db.py`
- [x] `get_daily_xp_from_exercise()`, `do_exercise_event()` in `db.py`
- [x] Read helpers: `get_muscle_groups()`, `get_exercises()`, `get_distinct_body_parts()`, `get_workout_days()`, `get_day_exercises()`, `get_workout_history()`, `get_workout_streak()`
- [x] Builder write helpers: `get_workout_sheets()`, `create_workout_sheet()`, `delete_workout_sheet()`, `create_workout_day()`, `delete_workout_day()`, `add_exercise_to_day()`, `update_day_exercise()`, `remove_exercise_from_day()`
- [ ] Create `pages/biblioteca.py` (see §2.5)
- [ ] Create `pages/rotinas.py` (see §2.6)
- [ ] Create `pages/treino.py` (see §2.7)
- [ ] Add "Biblioteca 📚", "Rotinas 📋", "Treino 🏋️" to nav order in `app.py` (after Calendário)
- [ ] Update `equipe.py` to handle `source="exercise"` spawn banners (reuse existing spawn display logic)

---

### 2.5 `pages/biblioteca.py` — Workout Library

Pokédex-style browsable catalog of all 152 exercises.

```
┌──────────────────────────────────────────────────────┐
│  Biblioteca 📚                                        │
├────────────────┬─────────────────┬───────────────────┤
│  🔍 Buscar     │  Grupo Muscular ▾│  Equipamento ▾   │
├────────────────┴─────────────────┴───────────────────┤
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │
│  │ [GIF]  │  │ [GIF]  │  │ [GIF]  │  │ [GIF]  │     │
│  │ Supino │  │ Agach. │  │ Remada │  │ Rosca  │     │
│  │ Peito  │  │ Glútes │  │ Costas │  │ Bíceps │     │
│  │ ⚔️ Luta│  │ 🌍 Solo│  │ 🌑 Somb│  │ ⚪ Norm│     │
│  └────────┘  └────────┘  └────────┘  └────────┘     │
│  ... (grid 4 colunas, paginado ou scroll)            │
└──────────────────────────────────────────────────────┘
```

**Cards:** exercise name (pt), body part tags, Pokémon type badge (color from `type_colors.py`), animated GIF thumbnail (from `gif_url`).

**Filters (sidebar or top row):**
- Text search on `name_pt` and `name`
- Multiselect muscle group (from `get_muscle_groups()`)
- Multiselect body part (from `get_distinct_body_parts()`)
- Multiselect equipment

**Detail expand (click card or expander):** full GIF, target muscles list, equipment, type affinity explanation (e.g. "Exercícios de peito invocam Pokémon do tipo Lutador").

No write operations on this page — read-only catalog.

---

### 2.6 `pages/rotinas.py` — Workout Builder

UI to create and manage `workout_sheets` and their `workout_days`.

```
┌──────────────────────────────────────────────────────┐
│  Rotinas 📋          [ + Nova Rotina ]               │
├──────────────────────────────────────────────────────┤
│  ▼ Rotina A (3 dias)                     [🗑 Deletar]│
│    ▼ Dia 1 — Peito e Tríceps             [🗑]        │
│       Supino Reto       3 × 10   [✏ Editar] [🗑]    │
│       Tríceps Pulley    3 × 12   [✏ Editar] [🗑]    │
│       [ + Adicionar Exercício ]                      │
│    ▶ Dia 2 — Costas e Bíceps             [🗑]        │
│    [ + Adicionar Dia ]                               │
│  ▶ Rotina B (2 dias)                     [🗑 Deletar]│
└──────────────────────────────────────────────────────┘
```

**Flows:**
- **Nova Rotina:** text input for sheet name → `create_workout_sheet()`
- **Adicionar Dia:** text input for day name within a sheet → `create_workout_day()`
- **Adicionar Exercício:** searchable selectbox from full catalog (filtered same as Library) + number inputs for default sets/reps → `add_exercise_to_day()`
- **Editar:** inline number inputs for sets/reps → `update_day_exercise()`
- **Deletar:** confirm before calling delete functions (cascade-safe)

Sets/reps here are **prescribed defaults** used by the log page's "Import Default" feature, not actual logged values.

---

### 2.7 `pages/treino.py` — Routine Log

Date-specific workout session logging.

```
┌──────────────────────────────────────────────────────┐
│  Treino 🏋️    Streak: N dias  |  XP hoje: NNN / 300 │
├──────────────────────────────────────────────────────┤
│  📅 Data: [date picker — hoje por padrão]            │
│  Rotina: [selectbox]  Dia: [selectbox]               │
│                              [ ⬇ Importar Padrão ]  │
├──────────────────────────────────────────────────────┤
│  Exercício        Sets  Reps  Peso (kg)  [🗑]        │
│  Supino Reto       3    10    50.0       [🗑]        │
│  Tríceps Pulley    3    12     0.0       [🗑]        │
│  [ + Adicionar Exercício ]                           │
├──────────────────────────────────────────────────────┤
│                              [ ✅ Registrar Treino ] │
├──────────────────────────────────────────────────────┤
│  Resultado: +XX XP  |  [spawn card if rolled]        │
├──────────────────────────────────────────────────────┤
│  Histórico (últimos 7 dias)                          │
│  ┌──────────┬────────────┬──────┬──────┬────────┐   │
│  │ Data     │ Exercício  │ Sets │ Reps │ XP     │   │
│  └──────────┴────────────┴──────┴──────┴────────┘   │
└──────────────────────────────────────────────────────┘
```

**"Import Default" flow:**
1. User selects Rotina + Dia in the dropdowns
2. Clicks "⬇ Importar Padrão" → calls `get_day_exercises(day_id)`, populates the exercise table with prescribed sets/reps
3. All rows remain editable (sets, reps, weight) before submission
4. User can add extra exercises manually or delete any row

**"Registrar Treino" flow:**
1. Builds `exercises` list from the current table state
2. Calls `do_exercise_event(user_id, exercises, day_id)` where `day_id` is the selected routine day (or `None` for a free session)
3. Shows inline result card (same pattern as `calendario.py`): XP earned, cap indicator, spawn card if triggered
4. Sets `st.session_state.team_evo_notice` / `st.session_state.xp_share_log` as needed

**Other details:**
- Date picker defaults to today; can log past sessions (no re-submit guard needed — multiple logs per day allowed, only XP cap enforced server-side)
- Daily XP cap progress bar: XP hoje / 300 (orange when > 200, red when capped)
- Workout streak counter at top (independent of check-in streak, from `get_workout_streak()`)
- Free session: skip Rotina/Dia selectors; show only the exercise table + "Adicionar Exercício"

### 2.8 Milestone Rewards

- [ ] 7-day workout streak → guaranteed spawn (no roll)
- [ ] 30-day streak → guaranteed shiny spawn (set `is_shiny=True` in capture)
- [ ] First workout → +50 bonus XP one-time

---

## Phase 3 — Progression Depth (Long-term)

### 3.1 Competitive Improvements
- [ ] Add PvP battle request/challenge system (async — opponent accepts before battle runs)
- [ ] Implement seasonal leaderboard (top trainers by wins or Pokémon count)
- [ ] Add a rematch cooldown per opponent pair

### 3.2 Pokémon Interaction
- [ ] Add a "Happiness" mechanic — increases with check-ins and battles; unlocks friendship evolutions earlier than bypass level 36
  - **Note:** bypass level is `_BYPASS_LEVEL = 36` in `db.py`. Happiness would lower this threshold per-Pokémon, not globally.
- [ ] Held items (e.g., Metal Coat triggers Steel-type evolutions in battle context)

### 3.3 Collection & Colecionismo
- [ ] Shininess odds refinement — current implementation is flat; consider streak-based boosts
- [ ] Achievements / badges (e.g., "Caught 100 Pokémon", "Won 50 battles")
- [ ] Trade system between users (future — requires multi-user session coordination)

---

## Phase 4 — Mobile / Android Conversion

- [ ] Evaluate Streamlit limitations for mobile UX (tap targets, scrolling, viewport)
- [ ] Research conversion path: Streamlit → Flutter (Dart) or React Native
- [ ] Identify which backend logic (`db.py`, `award_xp`) can be reused as a standalone API
- [ ] Design REST/GraphQL layer wrapping current psycopg2 queries

> **Key constraint:** `award_xp()` is already self-contained with no Streamlit dependencies. It can be extracted to a standalone service with minimal refactoring. `get_connection()` uses `st.session_state` for connection caching — this needs to be replaced with a connection pool (e.g., `psycopg2.pool`) when moving off Streamlit.

---

## Ongoing / Infrastructure

- [ ] Set up automated DB backup schedule in Supabase (beyond default 7-day retention)
- [ ] Add basic error monitoring (e.g., Sentry or Streamlit Cloud logs review cadence)
- [ ] Keep `requirements.txt` pinned versions in sync with Streamlit Cloud runtime
- [ ] Review `extra-streamlit-components` version constraint quarterly (known instability)
- [ ] Pin `extra-streamlit-components` to a specific commit SHA if minor version bumps keep breaking cookie behavior
