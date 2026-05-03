-- Migration: Rival Semanal
-- Adiciona colunas de rival semanal em user_profiles.
-- Executar no SQL Editor do Supabase.

ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS weekly_rival_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS rival_assigned_week DATE;
