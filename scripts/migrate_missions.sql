-- Migration: create user_missions table for daily/weekly mission system (Priority B)
-- Run once in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS user_missions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    mission_slug    TEXT        NOT NULL,
    mission_type    TEXT        NOT NULL CHECK (mission_type IN ('daily', 'weekly')),
    period_start    DATE        NOT NULL,   -- for daily: the date; for weekly: monday of the week
    target          INT         NOT NULL,
    progress        INT         NOT NULL DEFAULT 0,
    completed       BOOL        NOT NULL DEFAULT FALSE,
    reward_claimed  BOOL        NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One mission slug per user per period
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_missions_period
    ON user_missions (user_id, mission_slug, period_start);

-- Fast lookup for active missions
CREATE INDEX IF NOT EXISTS idx_user_missions_user_period
    ON user_missions (user_id, period_start DESC);
