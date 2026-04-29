-- Achievement system migration
-- Run once in Supabase SQL editor

CREATE TABLE IF NOT EXISTS user_achievements (
    id           SERIAL PRIMARY KEY,
    user_id      UUID    NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    achievement_slug TEXT NOT NULL,
    unlocked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, achievement_slug)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user
    ON user_achievements (user_id);
