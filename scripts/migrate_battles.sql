-- ============================================================
-- LimitBreak — Migração: Sistema de Batalhas
-- Execute no SQL Editor do Supabase
-- Idempotente: seguro rodar múltiplas vezes
-- ============================================================

-- Registro de batalhas realizadas
CREATE TABLE IF NOT EXISTS user_battles (
    id                      SERIAL      PRIMARY KEY,
    challenger_id           UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    opponent_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    challenger_pokemon_id   INTEGER     NOT NULL REFERENCES user_pokemon(id),
    opponent_pokemon_id     INTEGER     NOT NULL REFERENCES user_pokemon(id),
    winner_id               UUID        REFERENCES auth.users(id),   -- NULL = empate
    result                  TEXT        NOT NULL CHECK (result IN ('challenger_win', 'opponent_win', 'draw')),
    challenger_xp_earned    INTEGER     NOT NULL DEFAULT 0,
    opponent_xp_earned      INTEGER     NOT NULL DEFAULT 0,
    coins_earned            INTEGER     NOT NULL DEFAULT 0,          -- moedas do vencedor
    turn_count              INTEGER     NOT NULL DEFAULT 0,
    battled_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Log de turnos de cada batalha
CREATE TABLE IF NOT EXISTS user_battle_turns (
    id                      SERIAL  PRIMARY KEY,
    battle_id               INTEGER NOT NULL REFERENCES user_battles(id) ON DELETE CASCADE,
    turn_number             INTEGER NOT NULL,
    attacker_pokemon_id     INTEGER NOT NULL REFERENCES user_pokemon(id),
    move_name               TEXT    NOT NULL,
    move_power              INTEGER NOT NULL DEFAULT 0,
    damage                  INTEGER NOT NULL DEFAULT 0,
    challenger_hp_remaining INTEGER NOT NULL,
    opponent_hp_remaining   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_battles_challenger ON user_battles(challenger_id);
CREATE INDEX IF NOT EXISTS idx_battles_opponent   ON user_battles(opponent_id);
CREATE INDEX IF NOT EXISTS idx_battles_turns      ON user_battle_turns(battle_id);

ALTER TABLE user_battles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_battle_turns ENABLE ROW LEVEL SECURITY;

-- Usuário vê batalhas em que participou (como desafiante ou oponente)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_battles' AND policyname = 'participant_select_battles'
    ) THEN
        CREATE POLICY "participant_select_battles" ON user_battles FOR SELECT
            USING (auth.uid() = challenger_id OR auth.uid() = opponent_id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_battles' AND policyname = 'challenger_insert_battles'
    ) THEN
        CREATE POLICY "challenger_insert_battles" ON user_battles FOR INSERT
            WITH CHECK (auth.uid() = challenger_id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_battle_turns' AND policyname = 'participant_select_turns'
    ) THEN
        CREATE POLICY "participant_select_turns" ON user_battle_turns FOR SELECT
            USING (EXISTS (
                SELECT 1 FROM user_battles b
                WHERE b.id = battle_id
                  AND (b.challenger_id = auth.uid() OR b.opponent_id = auth.uid())
            ));
    END IF;
END $$;
