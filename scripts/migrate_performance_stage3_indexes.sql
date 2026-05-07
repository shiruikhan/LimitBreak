-- ============================================================
-- LimitBreak — Etapa 3: índices para queries de treino e batalha
-- Execute no SQL Editor do Supabase
-- Idempotente: seguro rodar múltiplas vezes
-- ============================================================

-- Leituras por usuário + janela temporal (XP diário, rival semanal, histórico)
CREATE INDEX IF NOT EXISTS idx_workout_logs_user_completed_at
    ON workout_logs(user_id, completed_at);

-- Leituras globais por janela temporal (desafio semanal, leaderboard mensal)
CREATE INDEX IF NOT EXISTS idx_workout_logs_completed_at
    ON workout_logs(completed_at);

-- Junção frequente exercise_logs -> workout_logs com filtro por exercício
CREATE INDEX IF NOT EXISTS idx_exercise_logs_workout_exercise
    ON exercise_logs(workout_log_id, exercise_id);

-- Contagem diária de batalhas por desafiante
CREATE INDEX IF NOT EXISTS idx_user_battles_challenger_battled_at
    ON user_battles(challenger_id, battled_at);
