# LimitBreak — Next Steps Roadmap

> Based on project state as of April 2026.

---

## Phase 1 — Core Stability & Polish (Short-term)

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

## Phase 2 — Paldea Regional Forms (Medium-term)

- [ ] Research Paldea form IDs from PokéAPI
- [ ] Extend `seed_regional_species.py` to support Paldea forms
- [ ] Run seed + update sprites via `update_regional_sprites.py`
- [ ] Write and execute `migrate_paldea.sql` if schema changes are needed
- [ ] Verify spawn and capture mechanics work for new IDs

---

## Phase 3 — Exercise Module Integration (Blocked on partner dev)

This phase requires the external training module to emit events via `award_xp()`.

### 3.1 Contract Verification
- [ ] Agree on event payload format with partner developer
- [ ] Define which exercise events map to how much XP (e.g., sets completed, weight lifted)
- [ ] Document integration endpoint in CLAUDE.md

### 3.2 Type-based Spawns
- [ ] Map exercise categories to Pokémon types (e.g., chest → Fighting/Normal, legs → Ground/Rock)
- [ ] Extend `do_checkin` or create a new `do_exercise_event()` function that:
  - Awards XP based on exercise intensity
  - Rolls for a type-appropriate spawn instead of a random one
- [ ] Update `calendario.py` (or create `treino.py`) to display exercise-linked spawn results

### 3.3 Streak & Motivation Bonuses
- [ ] Consider milestone rewards tied to workout consistency (e.g., 10 consecutive workout days → rare spawn)
- [ ] Expose workout streak separately from check-in streak in the UI

---

## Phase 4 — Progression Depth (Long-term)

### 4.1 Competitive Improvements
- [ ] Add PvP battle request/challenge system (async — opponent accepts before battle runs)
- [ ] Implement seasonal leaderboard (top trainers by wins or Pokémon count)
- [ ] Add a rematch cooldown per opponent pair

### 4.2 Pokémon Interaction
- [ ] Add a "Happiness" mechanic — increases with check-ins and battles; unlocks friendship evolutions earlier than bypass level 36
- [ ] Held items (e.g., Metal Coat triggers Steel-type evolutions in battle context)

### 4.3 Collection & Colecionismo
- [ ] Shininess odds refinement — current implementation is flat; consider streak-based boosts
- [ ] Achievements / badges (e.g., "Caught 100 Pokémon", "Won 50 battles")
- [ ] Trade system between users (future — requires multi-user session coordination)

---

## Phase 5 — Mobile / Android Conversion

- [ ] Evaluate Streamlit limitations for mobile UX (tap targets, scrolling, viewport)
- [ ] Research conversion path: Streamlit → Flutter (Dart) or React Native
- [ ] Identify which backend logic (`db.py`, `award_xp`) can be reused as a standalone API
- [ ] Design REST/GraphQL layer wrapping current psycopg2 queries

---

## Ongoing / Infrastructure

- [ ] Set up automated DB backup schedule in Supabase (beyond default 7-day retention)
- [ ] Add basic error monitoring (e.g., Sentry or Streamlit Cloud logs review cadence)
- [ ] Keep `requirements.txt` pinned versions in sync with Streamlit Cloud runtime
- [ ] Review `extra-streamlit-components` version constraint quarterly (known instability)
