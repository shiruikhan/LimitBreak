import os
import base64
import random
import datetime
import calendar as cal_module
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_DB_PARAMS: dict | None = None


def _db_params() -> dict:
    global _DB_PARAMS
    if _DB_PARAMS is None:
        _DB_PARAMS = dict(
            host=os.getenv("host"),
            port=os.getenv("port"),
            dbname=os.getenv("database"),
            user=os.getenv("user"),
            password=os.getenv("password"),
        )
    return _DB_PARAMS


def _new_conn():
    return psycopg2.connect(**_db_params())


def get_connection():
    """Returns a live psycopg2 connection stored per Streamlit session.
    Reconnects automatically if the server closed the connection.
    """
    conn = st.session_state.get("_db_conn")
    if conn is None or conn.closed != 0:
        st.session_state._db_conn = _new_conn()
        return st.session_state._db_conn
    # Roll back any aborted transaction so the connection is reusable
    if conn.status != psycopg2.extensions.STATUS_READY:
        try:
            conn.rollback()
        except Exception:
            st.session_state._db_conn = _new_conn()
    return st.session_state._db_conn


@st.cache_data
def get_image_as_base64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


# ── Pokédex queries ────────────────────────────────────────────────────────────

@st.cache_data
def get_all_pokemon() -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("SELECT id, name FROM pokemon_species ORDER BY id;")
        return cur.fetchall()


@st.cache_data
def get_all_pokemon_with_types() -> list[dict]:
    """Retorna todos os 1.025 Pokémon com tipos e sprite — cacheado globalmente."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.sprite_url,
                   t1.name AS type1, t1.slug AS type1_slug,
                   t2.name AS type2, t2.slug AS type2_slug
            FROM pokemon_species p
            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
            LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
            ORDER BY p.id;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "name": r[1], "sprite_url": r[2],
                "type1": r[3], "type1_slug": r[4],
                "type2": r[5], "type2_slug": r[6],
            }
            for r in rows
        ]


def get_pokemon_details(pokemon_id: int) -> tuple | None:
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.sprite_url, p.sprite_shiny_url,
                   t1.name AS type1, t2.name AS type2, p.base_experience,
                   p.base_hp, p.base_attack, p.base_defense,
                   p.base_sp_attack, p.base_sp_defense, p.base_speed
            FROM pokemon_species p
            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
            LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
            WHERE p.id = %s;
        """, (pokemon_id,))
        return cur.fetchone()


def get_pokemon_moves(pokemon_id: int) -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT m.name, sm.level_learned_at, m.damage_class,
                   t.name AS type_name, m.power, m.accuracy
            FROM pokemon_moves m
            JOIN pokemon_species_moves sm ON m.id = sm.move_id
            LEFT JOIN pokemon_types t ON m.type_id = t.id
            WHERE sm.species_id = %s AND sm.learn_method = 'level-up'
            ORDER BY sm.level_learned_at ASC;
        """, (pokemon_id,))
        return cur.fetchall()


def get_full_evolution_chain(pokemon_id: int) -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("""
            WITH RECURSIVE ancestors AS (
                SELECT from_species_id AS id
                FROM pokemon_evolutions WHERE to_species_id = %(id)s
                UNION
                SELECT e.from_species_id
                FROM pokemon_evolutions e
                INNER JOIN ancestors a ON e.to_species_id = a.id
            ),
            base_pokemon AS (
                SELECT id FROM ancestors
                UNION
                SELECT %(id)s
                ORDER BY id ASC LIMIT 1
            ),
            full_chain AS (
                SELECT e.from_species_id, e.to_species_id, e.min_level, e.trigger_name, e.item_name
                FROM pokemon_evolutions e
                WHERE e.from_species_id = (SELECT id FROM base_pokemon)
                UNION
                SELECT e.from_species_id, e.to_species_id, e.min_level, e.trigger_name, e.item_name
                FROM pokemon_evolutions e
                INNER JOIN full_chain fc ON e.from_species_id = fc.to_species_id
            )
            SELECT fc.from_species_id, p1.name,
                   fc.to_species_id, p2.name,
                   fc.min_level, fc.trigger_name, fc.item_name
            FROM full_chain fc
            JOIN pokemon_species p1 ON fc.from_species_id = p1.id
            JOIN pokemon_species p2 ON fc.to_species_id = p2.id;
        """, {"id": pokemon_id})
        return cur.fetchall()


# ── User / team queries ────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict | None:
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT id, username, coins, starter_pokemon_id
                FROM user_profiles WHERE id = %s;
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "username": row[1], "coins": row[2], "starter_pokemon_id": row[3]}
    except Exception:
        return None


def create_user_profile(user_id: str, username: str, starter_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profiles (id, username, starter_pokemon_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (user_id, username, starter_id))

            # Add starter to user_pokemon, copying base stats as individual stats
            cur.execute("""
                INSERT INTO user_pokemon (
                    user_id, species_id, level, xp,
                    stat_hp, stat_attack, stat_defense,
                    stat_sp_attack, stat_sp_defense, stat_speed
                )
                SELECT %s, %s, 1, 0,
                       base_hp, base_attack, base_defense,
                       base_sp_attack, base_sp_defense, base_speed
                FROM pokemon_species WHERE id = %s
                RETURNING id;
            """, (user_id, starter_id, starter_id))
            up_id = cur.fetchone()[0]

            # Put starter in team slot 1
            cur.execute("""
                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                VALUES (%s, 1, %s)
                ON CONFLICT (user_id, slot) DO UPDATE SET user_pokemon_id = EXCLUDED.user_pokemon_id;
            """, (user_id, up_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e


def get_user_team(user_id: str) -> list[dict]:
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT ut.slot, up.id, up.species_id, p.name, p.sprite_url,
                       up.level, up.xp, t1.name AS type1, t2.name AS type2,
                       up.stat_hp, up.stat_attack, up.stat_defense,
                       up.stat_sp_attack, up.stat_sp_defense, up.stat_speed,
                       p.base_hp, p.base_attack, p.base_defense,
                       p.base_sp_attack, p.base_sp_defense, p.base_speed
                FROM user_team ut
                JOIN user_pokemon up ON ut.user_pokemon_id = up.id
                JOIN pokemon_species p ON up.species_id = p.id
                LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
                WHERE ut.user_id = %s
                ORDER BY ut.slot ASC;
            """, (user_id,))
            rows = cur.fetchall()
            return [
                {
                    "slot": r[0], "user_pokemon_id": r[1], "species_id": r[2],
                    "name": r[3], "sprite_url": r[4], "level": r[5], "xp": r[6],
                    "type1": r[7], "type2": r[8],
                    "stat_hp": r[9],  "stat_attack": r[10], "stat_defense": r[11],
                    "stat_sp_attack": r[12], "stat_sp_defense": r[13], "stat_speed": r[14],
                    "base_hp": r[15], "base_attack": r[16], "base_defense": r[17],
                    "base_sp_attack": r[18], "base_sp_defense": r[19], "base_speed": r[20],
                }
                for r in rows
            ]
    except Exception:
        return []


def get_user_pokemon_ids(user_id: str) -> set[int]:
    """Returns set of species_id that the user owns."""
    try:
        with get_connection().cursor() as cur:
            cur.execute(
                "SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s;",
                (user_id,)
            )
            return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def capture_pokemon(user_id: str, species_id: int) -> bool:
    """Adds Pokémon to user collection and team (if slot available). Returns True on success."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_pokemon (
                    user_id, species_id, level, xp,
                    stat_hp, stat_attack, stat_defense,
                    stat_sp_attack, stat_sp_defense, stat_speed
                )
                SELECT %s, %s, 1, 0,
                       base_hp, base_attack, base_defense,
                       base_sp_attack, base_sp_defense, base_speed
                FROM pokemon_species WHERE id = %s
                RETURNING id;
            """, (user_id, species_id, species_id))
            up_id = cur.fetchone()[0]

            # Fill first available team slot (1-6)
            cur.execute("""
                SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;
            """, (user_id,))
            used = {r[0] for r in cur.fetchall()}
            free = next((s for s in range(1, 7) if s not in used), None)
            if free:
                cur.execute("""
                    INSERT INTO user_team (user_id, slot, user_pokemon_id)
                    VALUES (%s, %s, %s);
                """, (user_id, free, up_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def set_team_slot(user_id: str, slot: int, user_pokemon_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, slot) DO UPDATE SET user_pokemon_id = EXCLUDED.user_pokemon_id;
            """, (user_id, slot, user_pokemon_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def remove_from_team(user_id: str, slot: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_team WHERE user_id = %s AND slot = %s;",
                (user_id, slot)
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def swap_team_slots(user_id: str, slot_a: int, slot_b: int) -> bool:
    """Swaps two team slots using a temporary slot to avoid PK conflicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s;", (user_id, slot_a))
            row_a = cur.fetchone()
            cur.execute("SELECT user_pokemon_id FROM user_team WHERE user_id=%s AND slot=%s;", (user_id, slot_b))
            row_b = cur.fetchone()

            if not row_a or not row_b:
                return False

            # Swap via temp slot 99
            cur.execute("UPDATE user_team SET slot=99 WHERE user_id=%s AND slot=%s;", (user_id, slot_a))
            cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=%s;", (slot_a, user_id, slot_b))
            cur.execute("UPDATE user_team SET slot=%s WHERE user_id=%s AND slot=99;", (slot_b, user_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


# ── Move management ────────────────────────────────────────────────────────────

def get_available_moves(species_id: int, level: int) -> list[dict]:
    """All level-up moves the Pokémon can know at its current level."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT m.id, m.name, sm.level_learned_at, m.damage_class,
                       t.name AS type_name, m.power, m.accuracy
                FROM pokemon_moves m
                JOIN pokemon_species_moves sm ON m.id = sm.move_id
                LEFT JOIN pokemon_types t ON m.type_id = t.id
                WHERE sm.species_id = %s
                  AND sm.learn_method = 'level-up'
                  AND sm.level_learned_at <= %s
                ORDER BY sm.level_learned_at ASC;
            """, (species_id, level))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0], "name": r[1], "level_learned_at": r[2],
                    "damage_class": r[3], "type_name": r[4],
                    "power": r[5], "accuracy": r[6],
                }
                for r in rows
            ]
    except Exception:
        return []


def get_active_moves(user_pokemon_id: int) -> list[dict]:
    """The 4 equipped moves for a user's Pokémon, ordered by slot."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT upm.slot, m.id, m.name, m.damage_class,
                       t.name AS type_name, m.power, m.accuracy
                FROM user_pokemon_moves upm
                JOIN pokemon_moves m ON upm.move_id = m.id
                LEFT JOIN pokemon_types t ON m.type_id = t.id
                WHERE upm.user_pokemon_id = %s
                ORDER BY upm.slot;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            return [
                {
                    "slot": r[0], "id": r[1], "name": r[2],
                    "damage_class": r[3], "type_name": r[4],
                    "power": r[5], "accuracy": r[6],
                }
                for r in rows
            ]
    except Exception:
        return []


def equip_move(user_pokemon_id: int, slot: int, move_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_pokemon_moves (user_pokemon_id, slot, move_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_pokemon_id, slot)
                DO UPDATE SET move_id = EXCLUDED.move_id;
            """, (user_pokemon_id, slot, move_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def unequip_move(user_pokemon_id: int, slot: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_pokemon_moves WHERE user_pokemon_id = %s AND slot = %s;",
                (user_pokemon_id, slot),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


# ── Stat boosts (itens da loja) ────────────────────────────────────────────────

# Stats válidos — usados como whitelist antes de interpolar no nome da coluna
_VALID_STATS = frozenset({"hp", "attack", "defense", "sp_attack", "sp_defense", "speed"})


def apply_stat_boost(user_pokemon_id: int, stat: str, delta: int, source_item: str) -> bool:
    """Aplica um boost permanente a um stat do Pokémon do usuário.

    Registra o histórico em user_pokemon_stat_boosts e atualiza o valor
    efetivo em user_pokemon.stat_<stat> — tudo na mesma transação.

    Args:
        user_pokemon_id: ID do user_pokemon a ser modificado.
        stat:            Nome do stat ('hp', 'attack', 'defense',
                         'sp_attack', 'sp_defense', 'speed').
        delta:           Variação (positiva para buff, negativa para nerf).
        source_item:     Nome do item que causou a alteração (ex: 'HP Up').

    Returns:
        True em caso de sucesso, False em caso de erro.
    """
    if stat not in _VALID_STATS:
        raise ValueError(f"Stat inválido: '{stat}'. Válidos: {sorted(_VALID_STATS)}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Registra o boost no histórico auditável
            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, delta, source_item))

            # Atualiza o valor efetivo (stat é validado pela whitelist acima — seguro interpolar)
            cur.execute(f"""
                UPDATE user_pokemon
                SET stat_{stat} = COALESCE(stat_{stat}, 0) + %s
                WHERE id = %s;
            """, (delta, user_pokemon_id))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def get_stat_boosts(user_pokemon_id: int) -> list[dict]:
    """Retorna o histórico completo de boosts de um Pokémon, do mais antigo ao mais recente."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT id, stat, delta, source_item, applied_at
                FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s
                ORDER BY applied_at ASC;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "stat": r[1],
                    "delta": r[2],
                    "source_item": r[3],
                    "applied_at": r[4],
                }
                for r in rows
            ]
    except Exception:
        return []


def get_stat_boost_summary(user_pokemon_id: int) -> dict:
    """Retorna o total acumulado de boosts por stat para um Pokémon.

    Exemplo de retorno:
        {'hp': 20, 'attack': 10, 'defense': 0, ...}
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT stat, COALESCE(SUM(delta), 0) AS total
                FROM user_pokemon_stat_boosts
                WHERE user_pokemon_id = %s
                GROUP BY stat;
            """, (user_pokemon_id,))
            rows = cur.fetchall()
            summary = {s: 0 for s in _VALID_STATS}
            for stat, total in rows:
                summary[stat] = total
            return summary
    except Exception:
        return {s: 0 for s in _VALID_STATS}


# ── Loja ──────────────────────────────────────────────────────────────────────

@st.cache_data
def get_shop_items() -> list[dict]:
    """Retorna o catálogo completo da loja — cacheado globalmente."""
    with get_connection().cursor() as cur:
        cur.execute("""
            SELECT id, slug, name, description, category,
                   price, effect_stat, effect_value, icon
            FROM shop_items
            ORDER BY category, price;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "slug": r[1], "name": r[2], "description": r[3],
                "category": r[4], "price": r[5], "effect_stat": r[6],
                "effect_value": r[7], "icon": r[8],
            }
            for r in rows
        ]


def get_user_inventory(user_id: str) -> dict[int, int]:
    """Retorna {item_id: quantity} para os itens que o usuário possui (quantity > 0)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT item_id, quantity FROM user_inventory
                WHERE user_id = %s AND quantity > 0;
            """, (user_id,))
            return {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        return {}


def buy_item(user_id: str, item_id: int) -> tuple[bool, str]:
    """Compra um item: debita moedas e adiciona ao inventário.

    Returns:
        (True, mensagem_sucesso) ou (False, mensagem_erro)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Preço do item
            cur.execute("SELECT name, price FROM shop_items WHERE id = %s;", (item_id,))
            row = cur.fetchone()
            if not row:
                return False, "Item não encontrado."
            item_name, price = row

            # Saldo do usuário (FOR UPDATE trava a linha contra compras simultâneas)
            cur.execute(
                "SELECT coins FROM user_profiles WHERE id = %s FOR UPDATE;",
                (user_id,)
            )
            profile = cur.fetchone()
            if not profile:
                return False, "Perfil não encontrado."
            if profile[0] < price:
                return False, f"Moedas insuficientes. Você tem {profile[0]} 🪙, precisa de {price} 🪙."

            # Debita moedas
            cur.execute(
                "UPDATE user_profiles SET coins = coins - %s WHERE id = %s;",
                (price, user_id)
            )

            # Adiciona ao inventário (upsert)
            cur.execute("""
                INSERT INTO user_inventory (user_id, item_id, quantity)
                VALUES (%s, %s, 1)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = user_inventory.quantity + 1;
            """, (user_id, item_id))

        conn.commit()
        return True, f"**{item_name}** comprado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao comprar: {e}"


def use_stat_item(user_id: str, item_id: int, user_pokemon_id: int) -> tuple[bool, str]:
    """Usa uma vitamina de stat em um Pokémon da equipe do usuário.

    Debita 1 unidade do inventário, aplica o boost e registra o histórico
    em user_pokemon_stat_boosts — tudo na mesma transação.

    Returns:
        (True, mensagem_sucesso) ou (False, mensagem_erro)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Detalhes do item
            cur.execute("""
                SELECT name, category, effect_stat, effect_value
                FROM shop_items WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()
            if not item:
                return False, "Item não encontrado."
            iname, category, stat, value = item
            if category != "stat_boost" or not stat or not value:
                return False, "Este item não pode ser usado diretamente."
            if stat not in _VALID_STATS:
                return False, "Stat inválido."

            # Verifica ownership do Pokémon
            cur.execute(
                "SELECT id FROM user_pokemon WHERE id = %s AND user_id = %s;",
                (user_pokemon_id, user_id)
            )
            if not cur.fetchone():
                return False, "Pokémon não encontrado na sua coleção."

            # Verifica inventário (FOR UPDATE trava contra uso duplo)
            cur.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_id = %s FOR UPDATE;
            """, (user_id, item_id))
            inv = cur.fetchone()
            if not inv or inv[0] < 1:
                return False, "Você não possui este item."

            # Debita inventário
            cur.execute("""
                UPDATE user_inventory SET quantity = quantity - 1
                WHERE user_id = %s AND item_id = %s;
            """, (user_id, item_id))

            # Registra histórico do boost
            cur.execute("""
                INSERT INTO user_pokemon_stat_boosts (user_pokemon_id, stat, delta, source_item)
                VALUES (%s, %s, %s, %s);
            """, (user_pokemon_id, stat, value, iname))

            # Aplica no stat efetivo (stat validado pela whitelist acima)
            cur.execute(f"""
                UPDATE user_pokemon
                SET stat_{stat} = COALESCE(stat_{stat}, 0) + %s
                WHERE id = %s;
            """, (value, user_pokemon_id))

        conn.commit()
        stat_label = {
            "hp": "HP", "attack": "Ataque", "defense": "Defesa",
            "sp_attack": "Atq. Especial", "sp_defense": "Def. Especial", "speed": "Velocidade",
        }.get(stat, stat)
        return True, f"+{value} {stat_label} aplicado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao usar item: {e}"


# ── Calendário / Check-in ──────────────────────────────────────────────────────

def get_monthly_checkins(user_id: str, year: int, month: int) -> dict:
    """Retorna dados de check-in do mês para renderizar o calendário.

    Returns:
        {
            day_number: {
                "streak": int,
                "coins": int,
                "bonus_item": bool,       # ganhou XP Share
                "spawned_species_id": int | None,
            }
        }
    """
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT
                    EXTRACT(DAY FROM checked_date)::int AS day,
                    streak,
                    coins_earned,
                    bonus_item_id IS NOT NULL AS has_bonus,
                    spawned_species_id
                FROM user_checkins
                WHERE user_id = %s
                  AND EXTRACT(YEAR  FROM checked_date) = %s
                  AND EXTRACT(MONTH FROM checked_date) = %s;
            """, (user_id, year, month))
            return {
                r[0]: {
                    "streak": r[1],
                    "coins": r[2],
                    "bonus_item": r[3],
                    "spawned_species_id": r[4],
                }
                for r in cur.fetchall()
            }
    except Exception:
        return {}


def get_checkin_streak(user_id: str) -> int:
    """Retorna o streak atual (dias consecutivos até hoje ou ontem)."""
    try:
        with get_connection().cursor() as cur:
            cur.execute("""
                SELECT checked_date, streak
                FROM user_checkins
                WHERE user_id = %s
                ORDER BY checked_date DESC
                LIMIT 1;
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return 0
            last_date, last_streak = row
            today     = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            if last_date in (today, yesterday):
                return last_streak
            return 0
    except Exception:
        return 0


def do_checkin(user_id: str) -> dict:
    """Executa o check-in diário do usuário.

    Regras:
    - 1 moeda por dia (UNIQUE constraint bloqueia duplicatas)
    - Dia 15 e último dia do mês: +1 XP Share
    - Streak múltiplo de 3: 25% de chance de capturar um Pokémon
      aleatório que o usuário ainda não possui (nível 5)

    Returns:
        {
            "success":       bool,
            "already_done":  bool,
            "streak":        int,
            "coins_earned":  int,
            "bonus_xp_share": bool,
            "spawn_rolled":  bool,   # True se o dado foi lançado
            "spawned": {id, name, sprite_url, type1} | None,
        }
    """
    conn    = get_connection()
    today   = datetime.date.today()
    result  = {
        "success": False, "already_done": False,
        "streak": 0, "coins_earned": 0,
        "bonus_xp_share": False, "spawn_rolled": False, "spawned": None,
    }

    try:
        with conn.cursor() as cur:

            # ── Streak ────────────────────────────────────────────────────────
            yesterday = today - datetime.timedelta(days=1)
            cur.execute("""
                SELECT checked_date, streak FROM user_checkins
                WHERE user_id = %s ORDER BY checked_date DESC LIMIT 1;
            """, (user_id,))
            last = cur.fetchone()
            if last and last[0] == yesterday:
                streak = last[1] + 1
            else:
                streak = 1

            # ── Bonus de meio/fim de mês? ─────────────────────────────────────
            last_day      = cal_module.monthrange(today.year, today.month)[1]
            is_bonus_day  = today.day in (15, last_day)
            bonus_item_id = None
            if is_bonus_day:
                cur.execute("SELECT id FROM shop_items WHERE slug = 'xp-share';")
                row = cur.fetchone()
                bonus_item_id = row[0] if row else None

            # ── INSERT check-in (UNIQUE bloqueia duplicata) ───────────────────
            try:
                cur.execute("""
                    INSERT INTO user_checkins
                        (user_id, checked_date, streak, coins_earned, bonus_item_id)
                    VALUES (%s, %s, %s, 1, %s);
                """, (user_id, today, streak, bonus_item_id))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                result["already_done"] = True
                return result

            # ── +1 moeda ──────────────────────────────────────────────────────
            cur.execute(
                "UPDATE user_profiles SET coins = coins + 1 WHERE id = %s;",
                (user_id,)
            )

            # ── XP Share nos dias especiais ───────────────────────────────────
            if bonus_item_id:
                cur.execute("""
                    INSERT INTO user_inventory (user_id, item_id, quantity)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (user_id, item_id)
                    DO UPDATE SET quantity = user_inventory.quantity + 1;
                """, (user_id, bonus_item_id))
                result["bonus_xp_share"] = True

            # ── Spawn em múltiplo de 3 ────────────────────────────────────────
            spawned_species_id = None
            if streak % 3 == 0:
                result["spawn_rolled"] = True
                if random.random() < 0.25:
                    # Pokémon que o usuário ainda não possui
                    cur.execute("""
                        SELECT id FROM pokemon_species
                        WHERE id NOT IN (
                            SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = %s
                        )
                        ORDER BY RANDOM() LIMIT 1;
                    """, (user_id,))
                    spawn_row = cur.fetchone()
                    if spawn_row:
                        spawned_species_id = spawn_row[0]

                        # Captura o Pokémon (nível 5)
                        cur.execute("""
                            INSERT INTO user_pokemon (
                                user_id, species_id, level, xp,
                                stat_hp, stat_attack, stat_defense,
                                stat_sp_attack, stat_sp_defense, stat_speed
                            )
                            SELECT %s, %s, 5, 0,
                                   base_hp, base_attack, base_defense,
                                   base_sp_attack, base_sp_defense, base_speed
                            FROM pokemon_species WHERE id = %s
                            RETURNING id;
                        """, (user_id, spawned_species_id, spawned_species_id))
                        up_id = cur.fetchone()[0]

                        # Slot de equipe livre, se houver
                        cur.execute(
                            "SELECT slot FROM user_team WHERE user_id = %s ORDER BY slot;",
                            (user_id,)
                        )
                        used = {r[0] for r in cur.fetchall()}
                        free = next((s for s in range(1, 7) if s not in used), None)
                        if free:
                            cur.execute("""
                                INSERT INTO user_team (user_id, slot, user_pokemon_id)
                                VALUES (%s, %s, %s);
                            """, (user_id, free, up_id))

                        # Atualiza o registro do check-in com o spawn
                        cur.execute("""
                            UPDATE user_checkins SET spawned_species_id = %s
                            WHERE user_id = %s AND checked_date = %s;
                        """, (spawned_species_id, user_id, today))

                        # Busca dados do Pokémon para o resultado
                        cur.execute("""
                            SELECT p.id, p.name, p.sprite_url,
                                   t1.name AS type1
                            FROM pokemon_species p
                            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
                            WHERE p.id = %s;
                        """, (spawned_species_id,))
                        pdata = cur.fetchone()
                        if pdata:
                            result["spawned"] = {
                                "id": pdata[0], "name": pdata[1],
                                "sprite_url": pdata[2], "type1": pdata[3],
                            }

        conn.commit()
        result.update({
            "success": True,
            "streak":  streak,
            "coins_earned": 1,
        })
        return result

    except Exception as e:
        conn.rollback()
        result["error"] = str(e)
        return result
