-- ============================================================
-- LimitBreak — Migração v2
-- Aplicar em bancos já existentes (criados com create_user_tables.sql anterior)
-- Execute no SQL Editor do Supabase
-- Idempotente: seguro rodar múltiplas vezes
-- ============================================================

-- 1. user_profiles: adicionar xp_share_expires_at
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS xp_share_expires_at TIMESTAMPTZ;

-- 2. user_pokemon: adicionar colunas de stats individuais
ALTER TABLE user_pokemon
    ADD COLUMN IF NOT EXISTS stat_hp         SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stat_attack     SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stat_defense    SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stat_sp_attack  SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stat_sp_defense SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stat_speed      SMALLINT NOT NULL DEFAULT 0;

-- 3. user_inventory: criar se não existir
CREATE TABLE IF NOT EXISTS user_inventory (
    user_id  UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id  INTEGER NOT NULL REFERENCES shop_items(id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_id)
);

ALTER TABLE user_inventory ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_inventory' AND policyname = 'owner_all_inventory'
    ) THEN
        CREATE POLICY "owner_all_inventory" ON user_inventory FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_inventory_user ON user_inventory(user_id);

-- 4. user_checkins: criar tabela correta se não existir
--    (substitui user_daily_checkins que tinha nomes de colunas diferentes)
CREATE TABLE IF NOT EXISTS user_checkins (
    id                 SERIAL  PRIMARY KEY,
    user_id            UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    checked_date       DATE    NOT NULL,
    streak             INTEGER NOT NULL DEFAULT 1,
    coins_earned       INTEGER NOT NULL DEFAULT 1,
    bonus_item_id      INTEGER REFERENCES shop_items(id),
    spawned_species_id INTEGER REFERENCES pokemon_species(id),
    UNIQUE (user_id, checked_date)
);

ALTER TABLE user_checkins ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_checkins' AND policyname = 'owner_all_checkins'
    ) THEN
        CREATE POLICY "owner_all_checkins" ON user_checkins FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_checkins_user ON user_checkins(user_id);

-- 5. Migrar dados de user_daily_checkins para user_checkins (se a tabela antiga existir)
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'user_daily_checkins'
    ) THEN
        INSERT INTO user_checkins (user_id, checked_date, streak, coins_earned, spawned_species_id)
        SELECT
            user_id,
            checked_at,
            streak,
            COALESCE(coins_earned, 1),
            spawned_species_id
        FROM user_daily_checkins
        ON CONFLICT (user_id, checked_date) DO NOTHING;

        RAISE NOTICE 'Dados migrados de user_daily_checkins para user_checkins. Verifique e remova a tabela antiga manualmente se correto.';
    END IF;
END $$;
