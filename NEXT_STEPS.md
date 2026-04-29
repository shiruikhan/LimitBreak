# LimitBreak — Priority 1 Implementation Plan

> Updated: April 2026 after auditing `suggestions.md`.
>
> Goal: strengthen the workout -> Pokémon feedback loop before expanding into broader retention, social, or analytics systems.

---

## Audit Summary

Priority 1 in `suggestions.md` is cohesive. All four items extend the same core pipeline:

- workout is logged in `do_exercise_event()`
- XP is granted to the Pokémon in team slot 1
- the same event can trigger a themed spawn
- `pages/treino.py` already renders milestone and spawn feedback
- achievements already use a central catalog + stat snapshot model

Two of the four items are partially scaffolded today:

- **Type affinity** already exists, but only as a single dominant `body_part -> type` mapping in `utils/db.py`
- **PR celebration** can plug into the existing workout result cards and achievement system

Two items need fresh persistence and delivery paths:

- **Eggs** require a new user-facing progression table and hatch flow
- **Passive abilities** require species metadata, a seed/update script, and a constrained effect engine

Recommended delivery order:

1. **PR detection + richer spawn affinity**
2. **Egg system**
3. **Passive abilities**

Reason: ship the fastest/highest-feel wins first, then add retention, then add team strategy.

---

## Current Baseline

### Core systems already in place

| Area | Current state |
|---|---|
| `utils/db.py` | `do_exercise_event()` logs `workout_logs` + `exercise_logs`, applies the 300 XP daily cap, awards XP to slot 1, and rolls an exercise-themed spawn |
| `utils/db.py` | `_spawn_typed()` already filters `pokemon_species` by Pokémon type and falls back gracefully |
| `pages/treino.py` | Workout result cards already support XP, spawn, streak milestone, evolution, and achievement feedback |
| `utils/achievements.py` | Achievements are catalog-driven and easy to extend with new stat fields |
| `utils/db.py` | Team slot 1 lookup is already a stable integration point for workout rewards |

### Gaps to close for Priority 1

- No PR stat model or PR-specific achievements
- Spawn affinity chooses only one dominant type instead of aggregating the full workout
- No egg persistence, delivery rules, or hatch UI
- No `ability_slug` on `pokemon_species`
- No standardized workout reward payload for PRs, eggs, or abilities

---

## Delivery Principles

### Keep `do_exercise_event()` as the orchestration point

Priority 1 should build around the existing workout event instead of introducing parallel reward flows. The workout event should remain the single place that:

- computes workout-derived rewards
- applies slot 1 modifiers
- grants secondary progression
- returns a rich result payload for `pages/treino.py`

### Prefer query-first over schema-first where possible

For PR detection, the existing `exercise_logs.sets_data` JSON already contains enough detail to derive historical bests. Add denormalized columns only if performance becomes a measured problem.

### Ship in layers, not all at once

PRs and spawn affinity are low-risk extensions to the current flow. Eggs and abilities are broader systems and should only land after the workout feedback loop is already richer and stable.

---

## Release 1 — Workout Feedback Upgrade

### 1A. PR Detection + Bonus XP

**Outcome**

Every workout can surface personal records as a first-class reward moment, with explicit XP feedback and achievement progress.

**Audit decision**

Start without new `exercise_logs.max_weight` / `max_reps` columns. Derive bests from historical `sets_data` first. Only denormalize if queries become too slow in production.

**PR definition for v1**

- Primary PR: any set exceeds the user's previous best weight for the same exercise
- Tie-break PR: same best weight, but higher reps than the previous best at that weight
- Limit reward to one PR bonus per exercise per session
- Cap PR bonuses at 3 exercises per session to reduce trivial micro-loading abuse

**Backend work**

- [ ] Add a helper in `utils/db.py` to normalize `sets_data` into comparable `(max_weight, max_reps_at_max_weight)` values
- [ ] Add a query helper that fetches prior bests for the current user and submitted `exercise_id`s
- [ ] Extend `do_exercise_event()` to compare current bests vs. history before finalizing the result payload
- [ ] Return `prs` in the workout result, e.g. `[{exercise_id, exercise_name, old_weight, new_weight, new_reps}]`
- [ ] Award `+50 XP` per PR bonus through the same post-commit path already used for first-workout bonus XP
- [ ] Extend achievement stats with `pr_count`
- [ ] Add `pr_first` and `pr_10` to `utils/achievements.py`

**UI work**

- [ ] Add a yellow PR celebration card in `pages/treino.py`
- [ ] If slot 1 exists, show its sprite inside the PR card as the "celebration" anchor
- [ ] Surface newly unlocked PR achievements through the existing pending achievement flow

**Acceptance criteria**

- Logging a heavier set than any previous log returns a PR entry and awards the bonus
- Matching weight with more reps also counts as a PR
- Repeating the same result twice does not re-award a PR
- The workout still succeeds even if PR comparison fails; only the PR reward should degrade gracefully

### 1B. Multi-Type Spawn Affinity

**Outcome**

Workout choice meaningfully influences what can spawn, using the entire session instead of only one dominant body part.

**Audit decision**

Do not add `pokemon_types` to `exercises` yet. The current data model already has `body_parts`; a mapping layer in code is enough for v1 and keeps the catalog easier to maintain.

**Design for v1**

- Replace the single `_BODY_PART_TYPE` mapping with a multi-type mapping, e.g. one body part can contribute more than one Pokémon type
- Aggregate all submitted exercises into weighted candidate types
- Attempt spawn selection using the strongest candidate types first
- Fall back to the current random/non-typed behavior if no match is available

**Backend work**

- [ ] Replace `_BODY_PART_TYPE` with a structure that supports `body_part -> [type_slug, ...]`
- [ ] Add a helper in `utils/db.py` that returns `candidate_types` ranked by workout frequency
- [ ] Update `do_exercise_event()` to pass the ranked type candidates into spawn selection
- [ ] Extend `_spawn_typed()` or wrap it with a new helper that tries several candidate types in order
- [ ] Return `spawn_context`, e.g. `{"body_parts": [...], "candidate_types": [...], "chosen_type": "ground"}`

**UI work**

- [ ] Update `pages/treino.py` spawn copy to explain why the spawn matched the workout
- [ ] Update `pages/biblioteca.py` and exercise detail copy to reflect multi-type affinity instead of a one-type badge only

**Acceptance criteria**

- Mixed workouts can generate more than one valid candidate type
- Leg day no longer competes with chest day for a single global dominant type
- Spawn behavior remains stable when an exercise has no mapped body parts

---

## Release 2 — Egg System

### 2A. Deliver a retention loop tied to workout completion

**Outcome**

Users receive hidden-species eggs at workout milestones and return to train again to hatch them.

**Audit decision**

For v1, keep egg delivery rules simple and observable:

- use **workout count milestones** first
- defer volume-based or streak-based egg grants until the basic loop feels good
- keep egg progress tied to completed workout sessions, not individual exercises

**Schema**

- [ ] Add `user_eggs` with: `id`, `user_id`, `species_id`, `rarity`, `workouts_to_hatch`, `workouts_done`, `received_at`, `hatched_at`
- [ ] Add indexes on `(user_id, hatched_at)` and `(user_id, received_at)`

**Backend work**

- [ ] Add grant logic in `utils/db.py` for milestones `25`, `50`, and `100` workouts
- [ ] Hide the egg species until hatch; store `species_id` at egg creation time
- [ ] Increment all pending eggs after a successful workout commit
- [ ] Hatch eggs whose progress reaches the threshold by calling `capture_pokemon()`
- [ ] Return `eggs_granted` and `eggs_hatched` in the workout result payload
- [ ] Re-run achievement checks after hatch because collection milestones may change

**UI work**

- [ ] Show pending eggs in `pages/equipe.py` instead of creating a new page immediately
- [ ] Add compact egg cards with rarity, progress bar, and remaining workouts
- [ ] Show a hatch result banner after a workout when one or more eggs hatch

**Acceptance criteria**

- The first milestone egg is granted exactly once
- Each completed workout increments all pending eggs by one
- Hatch rewards still work if the team is full; the new Pokémon can fall back to the bench via existing capture behavior
- The user can understand egg progress without opening a separate workflow

---

## Release 3 — Slot 1 Passive Abilities

### 3A. Add strategic team choice to workouts

**Outcome**

The Pokémon in slot 1 changes how a workout session pays out, making team composition matter before the user even battles.

**Audit decision**

Do not attempt a full franchise-faithful ability engine in v1. Start with a curated whitelist of workout-safe abilities and keep their effects inside the workout/reward loop.

**Scope constraints for v1**

- `ability_slug` lives on `pokemon_species`
- only the Pokémon in **slot 1** applies an ability
- only abilities that affect workout rewards ship in the first pass
- avoid first-pass abilities that require new battle cooldown systems or broad economy rewrites

**Backend work**

- [ ] Add nullable `ability_slug` to `pokemon_species`
- [ ] Create `utils/abilities.py` as a small registry of supported ability effects
- [ ] Add a seed/update script for species abilities, ideally via PokéAPI-backed ingestion
- [ ] Add a helper to fetch slot 1 Pokémon + species ability in one query
- [ ] Extend `do_exercise_event()` to evaluate abilities after base rewards are computed and before the final result payload is returned
- [ ] Return `ability_effects` in the workout result, e.g. XP bonus, egg boost, reroll used, etc.

**Recommended v1 ability set**

- `blaze`: `+15%` XP on high-intensity workouts (`raw_xp >= 200`)
- `synchronize`: boosts XP Share distribution for the rest of the team
- `pickup`: small chance for an extra post-workout item if inventory plumbing is already straightforward
- `pressure`: increases chance to spawn from the top ranked workout affinity type
- `compound-eyes`: reroll one failed spawn attempt before giving up

**UI work**

- [ ] Show slot 1 ability text in `pages/equipe.py`
- [ ] Show ability activation notes in the workout result card stack in `pages/treino.py`

**Acceptance criteria**

- Slot 1 is the only source of passive workout effects
- Unsupported or null abilities are a no-op
- Workout logging remains deterministic enough to debug from the result payload

---

## Cross-Cutting Tasks

### Result payload cleanup

Priority 1 adds several new reward channels. Standardize the `do_exercise_event()` response so `pages/treino.py` does not need ad hoc conditionals for each feature.

Target payload additions:

- [ ] `prs`
- [ ] `spawn_context`
- [ ] `eggs_granted`
- [ ] `eggs_hatched`
- [ ] `ability_effects`

### Suggested migration/scripts breakdown

- [ ] `scripts/migrate_priority1_pr_support.sql` only if PR denormalization becomes necessary
- [ ] `scripts/migrate_priority1_eggs.sql`
- [ ] `scripts/migrate_priority1_abilities.sql`
- [ ] `scripts/seed_species_abilities.py`

### Testing focus

- [ ] PR detection: heavier weight, same weight/higher reps, duplicate submissions
- [ ] Spawn affinity: mixed-muscle workouts, unmapped exercises, empty typed pool fallback
- [ ] Eggs: grant once, advance once per workout, hatch at threshold, full team fallback
- [ ] Abilities: null ability, supported ability, slot 1 swap changing the applied effect

---

## Recommended Execution Order

1. **Release 1A: PR detection**
2. **Release 1B: multi-type spawn affinity**
3. **Release 2A: egg persistence + hatch UI**
4. **Release 3A: slot 1 passive abilities**

This sequence keeps the first release tightly focused on the product's core promise: a real-world workout should immediately create a memorable virtual consequence.

---

## Explicitly Deferred

These remain valuable, but should not interrupt Priority 1 delivery:

- Happiness / friendship evolutions
- Daily and weekly missions
- Gym badges
- Community or guild systems
- Advanced workout analytics

Those systems become more valuable after the workout reward loop itself is deeper, more emotional, and easier to reason about.
