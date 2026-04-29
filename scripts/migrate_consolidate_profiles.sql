-- migrate_consolidate_profiles.sql
-- Consolidates profiles table into user_profiles (sole dev ownership).
--
-- What this does:
--   1. Drops any FK constraints on workout_logs/workout_sheets that reference profiles
--   2. Adds a new FK: workout_logs.user_id → user_profiles.id
--   3. Drops the legacy profiles table
--
-- Run once in the Supabase SQL Editor.
-- Safe to re-run: each step uses IF EXISTS guards.

BEGIN;

-- ── Step 1: Drop FK constraints referencing profiles ──────────────────────────
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.conname, t.relname AS table_name
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE c.contype = 'f'
          AND c.confrelid = (
              SELECT oid FROM pg_class WHERE relname = 'profiles' LIMIT 1
          )
    LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I',
                       r.table_name, r.conname);
        RAISE NOTICE 'Dropped FK % on table %', r.conname, r.table_name;
    END LOOP;
END $$;

-- ── Step 2: Retarget workout_logs.user_id → user_profiles.id ─────────────────
-- Guard: only add if workout_logs exists and the constraint does not already exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class WHERE relname = 'workout_logs'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'workout_logs_user_id_fkey'
          AND conrelid = 'workout_logs'::regclass
    ) THEN
        ALTER TABLE workout_logs
            ADD CONSTRAINT workout_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK workout_logs.user_id → user_profiles.id';
    END IF;
END $$;

-- ── Step 3: Drop profiles table ───────────────────────────────────────────────
-- CASCADE removes any remaining dependent views or constraints.
DROP TABLE IF EXISTS profiles CASCADE;

COMMIT;
