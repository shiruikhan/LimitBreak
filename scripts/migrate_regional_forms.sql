-- Migration: Regional Forms system
-- Run once in Supabase SQL Editor after create_user_tables.sql

-- Catalog: one row per available regional form skin
CREATE TABLE IF NOT EXISTS pokemon_regional_forms (
    id           SERIAL PRIMARY KEY,
    shop_item_id INT REFERENCES shop_items(id),
    species_id   INT REFERENCES pokemon_species(id),
    region       TEXT NOT NULL,   -- 'alola', 'galar', 'hisui', 'paldea'
    form_slug    TEXT NOT NULL,   -- PokéAPI slug, e.g. 'marowak-alola'
    sprite_url   TEXT,            -- Direct URL from PokéAPI sprites CDN
    name         TEXT NOT NULL,   -- Display name, e.g. 'Marowak de Alola'
    UNIQUE (species_id, region),
    UNIQUE (form_slug)
);

-- Applied forms: one active form per user Pokémon (cosmetic only)
CREATE TABLE IF NOT EXISTS user_pokemon_forms (
    user_pokemon_id INT PRIMARY KEY REFERENCES user_pokemon(id) ON DELETE CASCADE,
    regional_form_id INT NOT NULL REFERENCES pokemon_regional_forms(id),
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
