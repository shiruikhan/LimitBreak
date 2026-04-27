# LimitBreak — Next Steps Roadmap

> Updated: April 2026. Phase 1 complete.

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

## Phase 2 — Paldea Regional Forms (Medium-term)

**Paldea forms to add (4 canonical):**
| Slug (PokéAPI) | Base # | Notes |
|---|---|---|
| `wooper-paldea` | 194 | Evolves → Clodsire (#980), NOT Quagsire |
| `tauros-paldea-combat` | 128 | Fighting-type |
| `tauros-paldea-blaze` | 128 | Fighting/Fire |
| `tauros-paldea-aqua` | 128 | Fighting/Water |

### Known Risks Before Starting

> **Risk 1 — HybridShivam CDN has no Gen 9 sprites.**
> The CDN (`HybridShivam/Pokemon`) only covers up to Gen 8. For all 4 Paldea forms, `update_regional_sprites.py` will report "not found" and fall back to the PokéAPI CDN URL. This is safe (the fallback works) but means `seed_regional_species.py` should NOT blindly set the HybridShivam URL as it currently does — it writes the URL unconditionally without a HEAD check. Fix: pass `verify_cdn=True` flag or always use PokéAPI URL as default for Paldea entries in `REGIONAL_FORMS`, then run `update_regional_sprites.py` to promote to HybridShivam if/when available.

> **Risk 2 — Tauros multi-variant breaks `hybrid_url()` assumption.**
> `update_regional_sprites.py:79` constructs `{base_id:04d}-{Region}.png` — three Tauros variants all map to `0128-Paldea.png`. Even if HybridShivam adds the sprites later, there's no way to disambiguate variants with the current naming pattern. For now, both scripts must be extended with a `hybrid_name_override` field (e.g., `"0128-Paldea-Combat.png"`) or simply kept on PokéAPI CDN permanently.

> **Risk 3 — Wooper-paldea evolution chain conflict.**
> `pokemon_evolutions` already contains Wooper (#194) → Quagsire (#195). The Paldea form must get its own evolution row pointing to Clodsire (#980). Verify Clodsire is already in `pokemon_species` (it should be, id=980 ≤ 1025). Do NOT update the existing Wooper→Quagsire row; insert a new row keyed to `wooper-paldea`'s PokéAPI ID.

> **Risk 4 — Name generation from slug produces ugly strings.**
> `form_slug.replace("-", " ").title()` turns `tauros-paldea-combat` → `"Tauros Paldea Combat"`. Consider adding a `display_name` override map in the seed script for cleaner names like `"Tauros (Paldea Combat)"`.

### Implementation Checklist
- [ ] Verify Clodsire (#980) exists in `pokemon_species` via direct SQL before seeding
- [ ] Add 4 Paldea entries to `REGIONAL_FORMS` list in `seed_regional_species.py` with a `paldea` region tag
- [ ] Add display name overrides for Tauros variants in the seed script
- [ ] Run `seed_regional_species.py` — expect all 4 to seed with PokéAPI CDN sprites (HybridShivam fallback expected to fail)
- [ ] Run `update_regional_sprites.py` — confirm 4 Paldea forms report "not found" and keep PokéAPI URL (no action needed)
- [ ] Manually insert Wooper-paldea → Clodsire evolution row in `pokemon_evolutions`
- [ ] Write `migrate_paldea.sql` only if schema changes are needed (currently none anticipated)
- [ ] Verify spawn and capture mechanics work for new IDs (use Pokédex Pessoal + manual capture test)
- [ ] Update `pokedex_pessoal.py` Paldea chip count once forms are seeded

### Rollback
All seed scripts use `ON CONFLICT DO UPDATE` — to revert, run:
```sql
DELETE FROM pokemon_species_moves WHERE species_id IN (SELECT id FROM pokemon_species WHERE slug LIKE '%-paldea%');
DELETE FROM pokemon_species WHERE slug LIKE '%-paldea%';
```

---

## Phase 3 — Exercise Module Integration (Blocked on partner dev)

This phase requires the external training module to emit events via `award_xp()`.

### 3.1 Contract Verification
- [ ] Agree on event payload format with partner developer
- [ ] Define which exercise events map to how much XP (e.g., sets completed, weight lifted)
- [ ] Document integration endpoint in CLAUDE.md

> **Unblocking tip:** Build `do_exercise_event()` as a stub that accepts the agreed payload and calls `award_xp()` — UI and calendar display work can proceed independently before the partner integration is ready. Create `pages/treino.py` with a manual XP award form gated behind a dev flag for testing.

### 3.2 Type-based Spawns
- [ ] Map exercise categories to Pokémon types (e.g., chest → Fighting/Normal, legs → Ground/Rock)
- [ ] Create `do_exercise_event(user_id, category, intensity)` that:
  - Awards XP based on exercise intensity
  - Rolls for a type-appropriate spawn instead of a random one
  - Reuses the spawn logic already in `do_checkin()` — extract into `_roll_spawn(user_id, type_filter=None)`
- [ ] Update `calendario.py` (or create `treino.py`) to display exercise-linked spawn results

> **Risk:** `do_checkin` currently inlines the spawn roll logic. Extracting `_roll_spawn()` before Phase 3 avoids duplicating the query and the `award_xp` call pattern. Consider doing this refactor as a Phase 2.5 task when Phase 2 is complete, before the partner integration starts.

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
  - **Note:** bypass level is `_BYPASS_LEVEL = 36` in `db.py`. Happiness would lower this threshold per-Pokémon, not globally.
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

> **Key constraint:** `award_xp()` is already self-contained with no Streamlit dependencies. It can be extracted to a standalone service with minimal refactoring. `get_connection()` uses `st.session_state` for connection caching — this needs to be replaced with a connection pool (e.g., `psycopg2.pool`) when moving off Streamlit.

---

## Ongoing / Infrastructure

- [ ] Set up automated DB backup schedule in Supabase (beyond default 7-day retention)
- [ ] Add basic error monitoring (e.g., Sentry or Streamlit Cloud logs review cadence)
- [ ] Keep `requirements.txt` pinned versions in sync with Streamlit Cloud runtime
- [ ] Review `extra-streamlit-components` version constraint quarterly (known instability)
- [ ] Pin `extra-streamlit-components` to a specific commit SHA if minor version bumps keep breaking cookie behavior
