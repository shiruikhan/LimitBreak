-- migrate_spawn_tiers.sql
-- Adiciona is_spawnable e rarity_tier à tabela pokemon_species.
-- Executar uma vez no SQL Editor do Supabase.

ALTER TABLE pokemon_species
  ADD COLUMN IF NOT EXISTS is_spawnable BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS rarity_tier  TEXT    NOT NULL DEFAULT 'common';

-- ── Rarity tier por base_experience ───────────────────────────────────────────
-- NULL / < 100  → common   (formas base, pokémon iniciais de linha 1)
-- 100–179       → uncommon (evoluções intermediárias)
-- 180–299       → rare     (evoluções finais com spawnable=TRUE)

UPDATE pokemon_species
SET rarity_tier = 'common'
WHERE base_experience IS NULL OR base_experience < 100;

UPDATE pokemon_species
SET rarity_tier = 'uncommon'
WHERE base_experience >= 100 AND base_experience < 180;

UPDATE pokemon_species
SET rarity_tier = 'rare'
WHERE base_experience >= 180 AND base_experience < 300;

-- Lendários/míticos (base_experience >= 300) ficam como 'rare' mas não são spawnáveis.
-- O seed_spawn_tiers.py refina isso via PokéAPI (is_legendary / is_mythical).
UPDATE pokemon_species
SET rarity_tier    = 'rare',
    is_spawnable   = FALSE
WHERE base_experience >= 300;

-- Formas regionais (id > 10000) seguem a mesma lógica do base_experience herdado.
-- Se base_experience for NULL nelas, já ficam 'common' + spawnable pela regra acima.
