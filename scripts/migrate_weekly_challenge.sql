-- Migration: Desafio Comunitário Semanal
-- Cria tabelas de desafio semanal e participantes.
-- Executar no SQL Editor do Supabase.

CREATE TABLE IF NOT EXISTS weekly_challenges (
  id                  SERIAL PRIMARY KEY,
  week_start          DATE NOT NULL UNIQUE,
  goal_type           TEXT NOT NULL,          -- 'total_xp' | 'total_workouts' | 'total_sets'
  goal_value          INT  NOT NULL,
  current_value       INT  NOT NULL DEFAULT 0,
  reward_item_slug    TEXT NOT NULL,
  reward_quantity     INT  NOT NULL DEFAULT 1,
  completed           BOOL NOT NULL DEFAULT FALSE,
  reward_distributed  BOOL NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS weekly_challenge_participants (
  challenge_id   INT  REFERENCES weekly_challenges(id) ON DELETE CASCADE,
  user_id        UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  contributed    INT  NOT NULL DEFAULT 0,
  reward_claimed BOOL NOT NULL DEFAULT FALSE,
  PRIMARY KEY (challenge_id, user_id)
);
