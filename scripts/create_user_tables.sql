-- ============================================================
-- LimitBreak — User tables migration
-- Execute no SQL Editor do Supabase (dashboard > SQL Editor)
-- ============================================================

-- 1. Perfil do jogador (1 linha por usuário)
CREATE TABLE IF NOT EXISTS user_profiles (
    id                   UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username             TEXT        NOT NULL DEFAULT 'Treinador',
    coins                INTEGER     NOT NULL DEFAULT 0,
    starter_pokemon_id   INTEGER     REFERENCES pokemon_species(id),
    xp_share_expires_at  TIMESTAMPTZ,                        -- NULL = inativo
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Pokémon capturados pelo usuário
CREATE TABLE IF NOT EXISTS user_pokemon (
    id              SERIAL      PRIMARY KEY,
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    species_id      INTEGER     NOT NULL REFERENCES pokemon_species(id),
    level           INTEGER     NOT NULL DEFAULT 1  CHECK (level >= 1),
    xp              INTEGER     NOT NULL DEFAULT 0  CHECK (xp >= 0),
    is_shiny        BOOLEAN     NOT NULL DEFAULT FALSE,
    nickname        TEXT,
    caught_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Stats individuais: copiados dos base stats na captura; atualizados por vitaminas e evoluções
    stat_hp         SMALLINT    NOT NULL DEFAULT 0,
    stat_attack     SMALLINT    NOT NULL DEFAULT 0,
    stat_defense    SMALLINT    NOT NULL DEFAULT 0,
    stat_sp_attack  SMALLINT    NOT NULL DEFAULT 0,
    stat_sp_defense SMALLINT    NOT NULL DEFAULT 0,
    stat_speed      SMALLINT    NOT NULL DEFAULT 0
);

-- 3. Equipe ativa (até 6 slots por usuário)
CREATE TABLE IF NOT EXISTS user_team (
    user_id         UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    slot            INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 6),
    user_pokemon_id INTEGER NOT NULL REFERENCES user_pokemon(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, slot)
);

-- 4. Moves equipados (até 4 por Pokémon)
CREATE TABLE IF NOT EXISTS user_pokemon_moves (
    user_pokemon_id INTEGER NOT NULL REFERENCES user_pokemon(id) ON DELETE CASCADE,
    slot            INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 4),
    move_id         INTEGER NOT NULL REFERENCES pokemon_moves(id),
    PRIMARY KEY (user_pokemon_id, slot)
);

-- 5. Histórico de boosts permanentes de stat (aplicados via itens da loja)
--
--    Cada linha registra uma modificação individual. O valor efetivo do stat
--    fica em user_pokemon.stat_*, que é atualizado atomicamente junto com o
--    INSERT aqui. Este histórico serve como auditoria e para exibir o detalhamento
--    de cada boost na interface.
CREATE TABLE IF NOT EXISTS user_pokemon_stat_boosts (
    id               SERIAL      PRIMARY KEY,
    user_pokemon_id  INTEGER     NOT NULL REFERENCES user_pokemon(id) ON DELETE CASCADE,
    stat             TEXT        NOT NULL CHECK (stat IN ('hp','attack','defense','sp_attack','sp_defense','speed')),
    delta            SMALLINT    NOT NULL,               -- positivo = buff, negativo = nerf
    source_item      TEXT        NOT NULL,               -- nome do item que causou a alteração
    applied_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Inventário do usuário
CREATE TABLE IF NOT EXISTS user_inventory (
    user_id  UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id  INTEGER NOT NULL REFERENCES shop_items(id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_id)
);

-- 7. Check-ins diários
CREATE TABLE IF NOT EXISTS user_checkins (
    id                 SERIAL      PRIMARY KEY,
    user_id            UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    checked_date       DATE        NOT NULL,
    streak             INTEGER     NOT NULL DEFAULT 1,
    coins_earned       INTEGER     NOT NULL DEFAULT 1,
    bonus_item_id      INTEGER     REFERENCES shop_items(id),   -- NULL se não houve bônus
    spawned_species_id INTEGER     REFERENCES pokemon_species(id),
    UNIQUE (user_id, checked_date)
);

-- Índices para as queries mais comuns
CREATE INDEX IF NOT EXISTS idx_user_pokemon_user    ON user_pokemon(user_id);
CREATE INDEX IF NOT EXISTS idx_user_pokemon_species ON user_pokemon(species_id);
CREATE INDEX IF NOT EXISTS idx_user_team_user        ON user_team(user_id);
CREATE INDEX IF NOT EXISTS idx_stat_boosts_pokemon   ON user_pokemon_stat_boosts(user_pokemon_id);
CREATE INDEX IF NOT EXISTS idx_user_checkins_user    ON user_checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_user_inventory_user   ON user_inventory(user_id);

-- ============================================================
-- Row Level Security
-- Garante que cada usuário só veja/altere seus próprios dados
-- ============================================================

ALTER TABLE user_profiles            ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_pokemon             ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_team                ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_pokemon_moves       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_pokemon_stat_boosts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_inventory           ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_checkins            ENABLE ROW LEVEL SECURITY;

-- user_profiles
CREATE POLICY "owner_select_profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "owner_insert_profile" ON user_profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "owner_update_profile" ON user_profiles FOR UPDATE USING (auth.uid() = id);

-- user_pokemon
CREATE POLICY "owner_select_pokemon" ON user_pokemon FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "owner_insert_pokemon" ON user_pokemon FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "owner_update_pokemon" ON user_pokemon FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "owner_delete_pokemon" ON user_pokemon FOR DELETE USING (auth.uid() = user_id);

-- user_team
CREATE POLICY "owner_all_team" ON user_team FOR ALL USING (auth.uid() = user_id);

-- user_pokemon_moves (acesso via user_pokemon)
CREATE POLICY "owner_all_moves" ON user_pokemon_moves FOR ALL
    USING (EXISTS (
        SELECT 1 FROM user_pokemon up
        WHERE up.id = user_pokemon_id AND up.user_id = auth.uid()
    ));

-- user_pokemon_stat_boosts (acesso via user_pokemon)
CREATE POLICY "owner_all_stat_boosts" ON user_pokemon_stat_boosts FOR ALL
    USING (EXISTS (
        SELECT 1 FROM user_pokemon up
        WHERE up.id = user_pokemon_id AND up.user_id = auth.uid()
    ));

-- user_inventory
CREATE POLICY "owner_all_inventory" ON user_inventory FOR ALL USING (auth.uid() = user_id);

-- user_checkins
CREATE POLICY "owner_all_checkins" ON user_checkins FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- ATENÇÃO: Como o app usa psycopg2 com credenciais diretas,
-- o RLS acima NÃO é aplicado nas queries do Python.
-- Para aplicar RLS, migrar o acesso de dados para supabase-py.
-- Por enquanto, as policies protegem apenas o acesso via API REST.
-- ============================================================
