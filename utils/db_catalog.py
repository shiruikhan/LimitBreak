"""utils/db_catalog.py — Queries de catálogo somente-leitura do LimitBreak.

Contém:
  - Pokédex nacional (get_all_pokemon, get_all_pokemon_with_types,
    get_pokemon_details, get_pokemon_moves, get_full_evolution_chain)

Todas as funções são somente-leitura e cacheadas com @st.cache_data.
Depende apenas de db_core.
"""

import streamlit as st
from utils.db_core import get_connection


# ── Pokédex queries ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_pokemon() -> list[tuple]:
    with get_connection().cursor() as cur:
        cur.execute("SELECT id, name FROM pokemon_species ORDER BY id;")
        return cur.fetchall()


@st.cache_data(ttl=3600, show_spinner=False)
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


@st.cache_data(show_spinner=False)
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


@st.cache_data(ttl=3600, show_spinner=False)
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


@st.cache_data(ttl=3600, show_spinner=False)
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
                   fc.min_level, fc.trigger_name, fc.item_name,
                   p1.sprite_url, p2.sprite_url
            FROM full_chain fc
            JOIN pokemon_species p1 ON fc.from_species_id = p1.id
            JOIN pokemon_species p2 ON fc.to_species_id = p2.id;
        """, {"id": pokemon_id})
        return cur.fetchall()
