-- Migration: remove regional form shop/catalog tables
-- Regional forms are now standard Pokémon entities in pokemon_species.
-- Their acquisition uses the existing capture/spawn logic (do_checkin, capture_pokemon).
-- The shop-item and catalog tables are no longer needed.

DROP TABLE IF EXISTS user_pokemon_forms;
DROP TABLE IF EXISTS pokemon_regional_forms;
