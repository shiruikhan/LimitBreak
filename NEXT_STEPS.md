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

**Silvio owns this end-to-end.** No external dependency. Full stack: DB schema → `db.py` functions → `pages/treino.py`.

### 2.1 DB Schema — Already Populated ✅

The catalog tables already exist with data from the other developer's app and are shared:

| Table | Rows | Used for |
|---|---|---|
| `muscle_groups` | 22 | Anatomy images per muscle group |
| `exercises` | 152 | Catalog: `name`, `name_pt`, `target_muscles[]`, `body_parts[]`, `equipments[]`, `gif_url` |
| `workout_sheets` | 2 | Trainer-created plans assigned to a user |
| `workout_days` | 2 | Named days within a sheet |
| `workout_day_exercises` | 3 | Prescribed sets/reps per exercise per day |

The log tables existed but were empty and needed two gamification columns — **already applied via MCP migrations**:

```sql
-- Applied 2026-04-27
ALTER TABLE workout_logs ADD COLUMN xp_earned INT NOT NULL DEFAULT 0;
ALTER TABLE workout_logs ADD COLUMN spawned_species_id INT REFERENCES pokemon_species(id);
```

> **FK note:** `workout_logs.user_id → profiles.id` (other dev's user table). `do_exercise_event()` handles this by upserting a `profiles` row before inserting the log — safe, non-destructive.

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

| Function | Description |
|---|---|
| `get_exercise_categories()` | `[{id, name, slug, type_affinity}]` — `@st.cache_data` |
| `get_exercises(category_id=None)` | Full catalog or filtered by category — `@st.cache_data` |
| `do_exercise_event(user_id, exercise_id, sets, reps, weight_kg)` | Computes XP (with daily cap), calls `award_xp()`, rolls type-appropriate spawn (25% chance), writes `user_workout_logs`. Returns `{xp_earned, capped, spawn_rolled, spawned, xp_result}` |
| `get_workout_history(user_id, limit=30)` | Last N logs joined with exercise name and category |
| `get_workout_streak(user_id)` | Count of consecutive calendar days with at least 1 log |
| `get_daily_xp_from_exercise(user_id)` | Total `xp_earned` today from `user_workout_logs` — used for cap check |
| `_roll_spawn_typed(user_id, type_slug)` | Refactor of spawn logic from `do_checkin()` — adds optional `type_slug` filter; returns `species_id \| None` |

> **Refactor note:** extract spawn roll from `do_checkin()` into `_roll_spawn_typed(user_id, type_slug=None)` so both check-in and exercise share the same logic. When `type_slug` is provided, filter `pokemon_species` by `type1_id` or `type2_id`.

### 2.4 Implementation Checklist

- [x] DB schema — catalog tables already populated (152 exercises, 22 muscle groups)
- [x] Migrations applied: `xp_earned` and `spawned_species_id` added to `workout_logs`
- [x] `_spawn_typed(cur, user_id, type_slug)` — typed spawn helper in `db.py`
- [x] `get_daily_xp_from_exercise()`, `do_exercise_event()` in `db.py`
- [x] Read helpers: `get_muscle_groups()`, `get_exercises()`, `get_distinct_body_parts()`, `get_workout_days()`, `get_day_exercises()`, `get_workout_history()`, `get_workout_streak()`
- [ ] Create `pages/treino.py` (see §2.5)
- [ ] Add "Treino 🏋️" to nav order in `app.py` (after Calendário)
- [ ] Update `equipe.py` to handle `source="exercise"` spawn banners (reuse existing spawn display logic)

### 2.5 `pages/treino.py` — Layout

```
┌─────────────────────────────────────────────────────┐
│  Treino 🏋️         Streak: N dias  |  XP hoje: Nnn │
├─────────────────────────────────────────────────────┤
│  Categoria ▾   Exercício ▾   Sets  Reps  Peso (kg) │
│                                          [ Registrar ]│
├─────────────────────────────────────────────────────┤
│  Resultado:  +XX XP  |  [spawn card if rolled]      │
├─────────────────────────────────────────────────────┤
│  Histórico (últimos 7 dias)                         │
│  ┌──────────┬────────────┬──────┬──────┬────────┐  │
│  │ Data     │ Exercício  │ Sets │ Reps │ XP     │  │
│  └──────────┴────────────┴──────┴──────┴────────┘  │
└─────────────────────────────────────────────────────┘
```

- Category selectbox filters the exercise dropdown
- "Registrar" calls `do_exercise_event()` and shows inline result (same card pattern as `calendario.py`)
- Daily XP cap indicator: progress bar (XP hoje / 300)
- Workout streak shown at top (separate from check-in streak)

### 2.6 Milestone Rewards

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
