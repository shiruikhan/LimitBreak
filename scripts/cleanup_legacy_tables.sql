-- ── cleanup_legacy_tables.sql ────────────────────────────────────────────────
-- Remove tabelas legadas que não são mais usadas pelo app.
--
-- Auditoria realizada em 2026-05-14:
--   • user_pokemons  — 0 rows, UUID PK, schema diferente de user_pokemon
--                      (que usa SERIAL PK e é a tabela ativa).
--                      Sem nenhuma FK externa apontando para ela.
--   • profiles       — já removida por migrate_consolidate_profiles.sql
--
-- Executar no SQL Editor do Supabase:
--   Supabase Dashboard → SQL Editor → New Query → colar e executar
-- ─────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS public.user_pokemons;
