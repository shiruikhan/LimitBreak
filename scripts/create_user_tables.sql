-- ============================================================
-- LimitBreak — User tables migration
-- Execute no SQL Editor do Supabase (dashboard > SQL Editor)
-- ============================================================

-- 1. Perfil do jogador (1 linha por usuário)
CREATE TABLE IF NOT EXISTS user_profiles (
    id                  UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username            TEXT        NOT NULL DEFAULT 'Treinador',
    coins               INTEGER     NOT NULL DEFAULT 0,
    starter_pokemon_id  INTEGER     REFERENCES pokemon_species(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Pokémon capturados pelo usuário
CREATE TABLE IF NOT EXISTS user_pokemon (
    id          SERIAL      PRIMARY KEY,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    species_id  INTEGER     NOT NULL REFERENCES pokemon_species(id),
    level       INTEGER     NOT NULL DEFAULT 1  CHECK (level >= 1),
    xp          INTEGER     NOT NULL DEFAULT 0  CHECK (xp >= 0),
    is_shiny    BOOLEAN     NOT NULL DEFAULT FALSE,
    nickname    TEXT,
    caught_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Equipe ativa (até 6 slots por usuário)
CREATE TABLE IF NOT EXISTS user_team (
    user_id         UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    slot            INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 6),
    user_pokemon_id INTEGER NOT NULL REFERENCES user_pokemon(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, slot)
);

-- Índices para as queries mais comuns
CREATE INDEX IF NOT EXISTS idx_user_pokemon_user   ON user_pokemon(user_id);
CREATE INDEX IF NOT EXISTS idx_user_pokemon_species ON user_pokemon(species_id);
CREATE INDEX IF NOT EXISTS idx_user_team_user       ON user_team(user_id);

-- ============================================================
-- Row Level Security
-- Garante que cada usuário só veja/altere seus próprios dados
-- ============================================================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_pokemon  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_team     ENABLE ROW LEVEL SECURITY;

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

-- ============================================================
-- ATENÇÃO: Como o app usa psycopg2 com credenciais diretas,
-- o RLS acima NÃO é aplicado nas queries do Python.
-- Para aplicar RLS, migrar o acesso de dados para supabase-py.
-- Por enquanto, as policies protegem apenas o acesso via API REST.
-- ============================================================
