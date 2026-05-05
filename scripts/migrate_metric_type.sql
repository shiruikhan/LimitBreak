-- Migration: add metric_type to exercises
-- Run once in the Supabase SQL Editor.
-- Existing exercises default to 'weight' (backward compatible).

ALTER TABLE exercises
    ADD COLUMN IF NOT EXISTS metric_type TEXT NOT NULL DEFAULT 'weight'
        CHECK (metric_type IN ('weight', 'distance', 'time'));
