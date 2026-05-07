-- Migration: standardize workout_sheets metadata columns used by the app.
-- Run once in the Supabase SQL Editor.
--
-- Contract after this migration:
--   - workout_sheets.created_by UUID NOT NULL REFERENCES user_profiles(id)
--   - workout_sheets.updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = ANY(current_schemas(false))
          AND table_name = 'workout_sheets'
    ) THEN
        ALTER TABLE workout_sheets
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

        UPDATE workout_sheets
        SET created_by = user_id
        WHERE created_by IS NULL;

        UPDATE workout_sheets
        SET updated_at = NOW()
        WHERE updated_at IS NULL;

        ALTER TABLE workout_sheets
            ALTER COLUMN created_by SET NOT NULL,
            ALTER COLUMN updated_at SET NOT NULL,
            ALTER COLUMN updated_at SET DEFAULT NOW();
    END IF;
END $$;
