-- Etapa 4 de performance — índices para FKs apontadas pelo advisor do Supabase.
-- Aplicada em produção via MCP em 2026-06-11. Idempotente.

-- Beneficia assign_weekly_rival() / get_rival_status() (lookup por rival).
CREATE INDEX IF NOT EXISTS idx_user_profiles_weekly_rival_id
    ON user_profiles (weekly_rival_id)
    WHERE weekly_rival_id IS NOT NULL;

-- Beneficia leitura de contribuição e claim do desafio comunitário por usuário.
CREATE INDEX IF NOT EXISTS idx_wcp_user_id
    ON weekly_challenge_participants (user_id);
