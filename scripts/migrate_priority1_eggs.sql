-- migrate_priority1_eggs.sql
-- Creates user_eggs table for the Release 2A egg system.
-- Safe to run multiple times (idempotent).

CREATE TABLE IF NOT EXISTS user_eggs (
    id               SERIAL PRIMARY KEY,
    user_id          UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    species_id       INT         NOT NULL REFERENCES pokemon_species(id),
    rarity           TEXT        NOT NULL DEFAULT 'common'
                                 CHECK (rarity IN ('common', 'uncommon', 'rare')),
    workouts_to_hatch INT        NOT NULL DEFAULT 5 CHECK (workouts_to_hatch > 0),
    workouts_done    INT         NOT NULL DEFAULT 0  CHECK (workouts_done >= 0),
    received_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    hatched_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_eggs_user_active
    ON user_eggs (user_id, hatched_at);

CREATE INDEX IF NOT EXISTS idx_user_eggs_user_received
    ON user_eggs (user_id, received_at);
