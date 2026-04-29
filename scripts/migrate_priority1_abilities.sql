-- migrate_priority1_abilities.sql
-- Adds ability_slug column to pokemon_species for Release 3A passive abilities.
-- Safe to run multiple times (idempotent).

ALTER TABLE pokemon_species
    ADD COLUMN IF NOT EXISTS ability_slug TEXT;
