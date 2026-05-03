-- Release 6: Happiness / Friendship system
-- Run this migration in the Supabase SQL Editor.

-- 1. Add happiness column to user_pokemon (default 70, capped 0–255 in app)
ALTER TABLE user_pokemon
    ADD COLUMN IF NOT EXISTS happiness SMALLINT NOT NULL DEFAULT 70;

-- 2. Add min_happiness to pokemon_evolutions so friendship-gated evolutions
--    can be distinguished from plain level-up evolutions.
ALTER TABLE pokemon_evolutions
    ADD COLUMN IF NOT EXISTS min_happiness SMALLINT DEFAULT NULL;

-- 3. Mark friendship-based evolutions: those stored as trigger_name='level-up'
--    with no min_level (PokéAPI uses min_happiness condition for these).
--    Examples: Pichu→Pikachu, Cleffa→Clefairy, Togepi→Togetic, Golbat→Crobat,
--              Chansey→Blissey, Riolu→Lucario, Eevee→Espeon/Umbreon, etc.
UPDATE pokemon_evolutions
SET min_happiness = 220
WHERE trigger_name = 'level-up'
  AND min_level IS NULL
  AND min_happiness IS NULL;

-- 4. Rest-day tracking table (does NOT break check-in streak)
CREATE TABLE IF NOT EXISTS user_rest_days (
    id          SERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    rest_date   DATE NOT NULL,
    UNIQUE (user_id, rest_date)
);

CREATE INDEX IF NOT EXISTS idx_user_rest_days_user_date
    ON user_rest_days (user_id, rest_date);
