-- Remove a tabela legada user_pokemons (schema antigo com UUID PK, current_xp,
-- is_in_party), nunca usada pelo app. 0 rows verificado em 2026-06-11.
-- A tabela ativa é user_pokemon (SERIAL PK).
-- Aplicada em produção via MCP em 2026-06-11. Idempotente.

DROP TABLE IF EXISTS user_pokemons;
