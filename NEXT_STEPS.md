# LimitBreak — Next Steps

> Updated: April 30, 2026 after full codebase audit.
>
> Goal: continue strengthening the workout → Pokémon feedback loop, then move into retention and social layers.

---

## Shipped — Priority 1 (✅ Complete)

All four items from the original Priority 1 plan are live in production.

| Feature | Release | Status |
|---|---|---|
| PR detection + bonus XP | 1A | ✅ `_detect_prs()` + `_get_exercise_bests()` in `db.py`; +50 XP/PR, max 3/session |
| Multi-type spawn affinity | 1B | ✅ `_ranked_spawn_types()` + `_spawn_multi_typed()` in `db.py` |
| Egg system | 2A | ✅ `user_eggs` table; milestones at 25/50/100 workouts; hatch in 5/8/12 sessions |
| Slot 1 passive abilities | 3A | ✅ `utils/abilities.py`; 5 abilities wired into `do_exercise_event()` |

Also shipped (not in original plan):

| Feature | Release | Status |
|---|---|---|
| Loot Box | 3A | ✅ `open_loot_box()` with rarity table; admin-giftable |
| Nature Mint | 3A | ✅ `use_nature_mint()` with stat recalc |
| Admin Panel | 4.0 | ✅ `pages/admin.py` with 5 tabs; restricted to `is_admin()` |
| Daily & Weekly Missions | B | ✅ `pages/missoes.py`; `user_missions` table; 6 daily + 4 weekly options; hooks in treino/batalha/calendario |
| UI/UX + Performance Shell | 4.1 | ✅ grouped sidebar, `pages/hub.py`, shared cache layer, targeted `st.fragment` use |

---

## Current Baseline (post-audit)

### What the workout loop delivers today

Every call to `do_exercise_event()` can produce:
- Base XP (capped at 300/day) with daily progress bar
- Slot 1 ability modifier (blaze, synchronize, pickup, pressure, compound-eyes)
- Personal record detection with +50 XP bonus (max 3/session)
- Type-ranked spawn attempt (multi-type affinity)
- Compound-eyes reroll on failed spawn
- Egg advancement + hatch reveal
- Egg grant at milestone workout counts (25/50/100)
- XP Share distribution to the rest of the team

### What the app shell delivers today

- Hidden Streamlit navigation with grouped custom sidebar in `app.py`
- Central authenticated landing page in `pages/hub.py`
- Shared cached user reads in `utils/app_cache.py`
- Resource-cached Supabase client in `utils/supabase_client.py`
- Fragment-based partial rerenders in isolated UI sections like hub and calendar

### Known gaps still open

- No friendship/happiness system → bypass `_BYPASS_LEVEL = 36` still used for trade/friendship evolutions
- No community challenge or guild layer
- No workout analytics or muscle balance indicator
- No trainer profile page
- No Pokémon trade system

---

## Next Priorities

### Priority A — Happiness / Friendship System

**Why now:** resolves an existing technical debt (`_BYPASS_LEVEL = 36`) semantically and adds an emotional dimension to the Pokémon bond. It also restores evolution accuracy for Gengar, Alakazam, Chansey, and Eevee branches.

**Design:**
- Add `happiness SMALLINT DEFAULT 70` to `user_pokemon`
- Increment happiness: +2 per level-up, +1 per workout, +1 per check-in
- Decrement: −5 if no activity in 7 days (checked lazily at next workout or check-in)
- Happiness >= 220 → unlock friendship-trigger evolutions (replace `_BYPASS_LEVEL = 36` for those cases)
- Happiness >= 180 → +5% XP bonus in `award_xp()`
- Happiness < 50 → −5% XP ("desmotivado" indicator)

**Schema:** `ALTER TABLE user_pokemon ADD COLUMN happiness SMALLINT DEFAULT 70;`

**Effort:** Medium | **Impact:** High

---

### ~~Priority B — Daily and Weekly Missions~~ ✅ SHIPPED

Implemented in `pages/missoes.py` + `utils/missions.py` + `user_missions` table.
- 6 daily options (3 drawn/day) + 4 weekly options (1 drawn/week)
- Rewards: XP, coins, random stone, random vitamin, loot box
- Hooks in `treino.py` (workout + pr), `batalha.py` (battle_win), `calendario.py` (checkin)
- Run `scripts/migrate_missions.sql` to create the table in Supabase

---

### Priority C — Gym Badges

**Why now:** creates a recognizable long-term progression spine. Extension of the existing achievements catalog — low net-new complexity.

**Design (8 badges, Kanto-themed):**
| Badge | Milestone |
|---|---|
| Pedra | 10 workout sessions |
| Cascata | 7-day check-in streak |
| Trovão | 5 PvP wins |
| Arco-íris | 25 Pokémon captured |
| Alma | 30-day workout streak |
| Pântano | 10 PRs detected |
| Vulcão | 10 Pokémon evolved |
| Terra | 100 workout sessions |

**Implementation:** subset of `CATALOG` in `utils/achievements.py` with distinct visual (badge sprite instead of shields.io). Display counter "Insígnias: 3/8" in `equipe.py` sidebar or profile area.

**Effort:** Medium | **Impact:** High

---

### Priority D — Rest Day Mechanic

**Why now:** low effort, high retention value. Prevents streak anxiety from causing app abandonment.

**Design:**
- Button in `calendario.py` or `treino.py`: "Registrar Descanso"
- Grants +5 happiness to slot 1 Pokémon
- Does not break check-in streak
- Displays a "recovery" note in the calendar grid

**Effort:** Low | **Impact:** Medium

---

### Priority E — Workout Analytics

**Why now:** fitness users are data-driven. Progression charts are retentive independent of gamification.

**Design:**
- Volume chart per exercise over time (sets × reps × kg)
- Max weight per exercise (personal best history)
- Weekly muscle group distribution (which body parts trained this week vs. last)
- All derived from existing `exercise_logs.sets_data` — no schema changes needed

**UI:** `st.line_chart` / `st.bar_chart` in `treino.py` or a new tab inside that page.

**Effort:** Medium | **Impact:** High

---

## Deferred (V2 / Social Layer)

These remain valuable but depend on the core loop being deeper first.

| Feature | Reason to defer |
|---|---|
| Pokémon trade system | Requires async proposal state + notification infra |
| Guild system | Requires group state management; social features land better with a larger user base |
| Community weekly challenge | Simpler than guilds, but still needs a weekly reset job |
| Trainer profile page | Good after gym badges and happiness exist to make it interesting |
| Rotation sharing | Nice-to-have; low adoption risk in current user base |

---

## Effort vs. Impact Summary

| Feature | Effort | Impact | Next? |
|---|---|---|---|
| Daily & weekly missions | Medium | Very High | ✅ Shipped |
| Rest Day mechanic | Low | Medium | 🟡 Candidate |
| Gym Badges | Medium | High | 🔴 Yes |
| Happiness / friendship | Medium | High | 🔴 Yes |
| Workout analytics | Medium | High | 🟠 Yes |
| Community challenge | High | High | 🔵 V2 |
| Trainer profile page | Medium | Medium | 🔵 After badges |
| Trade system | High | High | 🔵 V2 |
| Guilds | High | Very High | 🔵 V2 |
