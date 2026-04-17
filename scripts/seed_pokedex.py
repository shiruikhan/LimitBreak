import os
import requests
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("database")
DB_USER = os.getenv("user")
DB_PASS = os.getenv("password")

# --- CONFIGURAÇÃO DE LOTE ---
# Começamos com os 151 originais para não sobrecarregar a API no primeiro teste.
# Para pegar todos no futuro, você pode aumentar esse número (atualmente ~1025).
POKEMON_LIMIT = 1025

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def extract_id_from_url(url):
    """Extrai o ID numérico do final de uma URL da PokeAPI."""
    if not url: return None
    return int(url.rstrip("/").split("/")[-1])

def fetch_and_seed_moves(cursor):
    print("\n⚔️ Buscando Catálogo de Moves...")
    # Buscamos um limite alto para pegar todos os moves de uma vez
    response = requests.get("https://pokeapi.co/api/v2/move/?limit=1000")
    moves_list = response.json().get("results", [])
    
    insert_query = """
        INSERT INTO pokemon_moves (id, name, slug, type_id, power, accuracy, pp, damage_class)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name, type_id = EXCLUDED.type_id, power = EXCLUDED.power,
            accuracy = EXCLUDED.accuracy, pp = EXCLUDED.pp, damage_class = EXCLUDED.damage_class;
    """
    
    for item in moves_list:
        move_id = extract_id_from_url(item['url'])
        # A PokeAPI tem moves extras (Z-moves, Max moves) com IDs altíssimos. Filtramos os normais.
        if move_id > 10000: continue 
        
        move_data = requests.get(item['url']).json()
        
        slug = move_data['name']
        name = slug.replace("-", " ").title()
        type_id = extract_id_from_url(move_data['type']['url'])
        power = move_data.get('power')
        accuracy = move_data.get('accuracy')
        pp = move_data.get('pp')
        damage_class = move_data['damage_class']['name'] if move_data.get('damage_class') else None
        
        cursor.execute(insert_query, (move_id, name, slug, type_id, power, accuracy, pp, damage_class))
        print(f"Salvo Move: {name}")

def fetch_and_seed_pokemon(cursor):
    print(f"\n🐾 Buscando Pokémons e seus Movesets (Limite: {POKEMON_LIMIT})...")
    
    insert_species_query = """
        INSERT INTO pokemon_species (id, name, slug, type1_id, type2_id, base_experience, sprite_url, sprite_shiny_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name, type1_id = EXCLUDED.type1_id, type2_id = EXCLUDED.type2_id,
            base_experience = EXCLUDED.base_experience, sprite_url = EXCLUDED.sprite_url, sprite_shiny_url = EXCLUDED.sprite_shiny_url;
    """

    insert_learnset_query = """
        INSERT INTO pokemon_species_moves (species_id, move_id, learn_method, level_learned_at)
        VALUES (%s, %s, %s, %s)
        -- OBS: A restrição ON CONFLICT aqui dependerá de você ter uma constraint UNIQUE (species_id, move_id, learn_method)
        -- Caso não tenha, comente a linha abaixo para evitar erros no primeiro teste.
        ON CONFLICT DO NOTHING; 
    """

    for pokemon_id in range(1, POKEMON_LIMIT + 1):
        try:
            # 1. Busca os dados principais do Pokemon
            response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}/")
            if response.status_code != 200: continue
            p_data = response.json()
            
            slug = p_data['name']
            name = slug.capitalize()
            base_exp = p_data.get('base_experience', 0)
            sprite = p_data['sprites']['front_default']
            sprite_shiny = p_data['sprites']['front_shiny']
            
            # Tipos
            types = p_data['types']
            type1_id = extract_id_from_url(types[0]['type']['url'])
            type2_id = extract_id_from_url(types[1]['type']['url']) if len(types) > 1 else None
            
            # Inserir Species
            cursor.execute(insert_species_query, (pokemon_id, name, slug, type1_id, type2_id, base_exp, sprite, sprite_shiny))
            print(f"✅ Salvo Pokémon: {name}")

            # 2. Processar Moveset (Apenas golpes aprendidos por 'level-up')
            for move_entry in p_data['moves']:
                move_id = extract_id_from_url(move_entry['move']['url'])
                
                # Alguns moves da API são inválidos ou de DLCs futuras, garantimos que o ID é válido
                if move_id > 1000: continue 

                # Pegamos apenas a forma de aprendizado mais recente (última versão do jogo)
                latest_version_details = move_entry['version_group_details'][-1]
                learn_method = latest_version_details['move_learn_method']['name']
                level = latest_version_details['level_learned_at']
                
                # Para simplificar o LimitBreak, focamos em golpes aprendidos subindo de nível
                if learn_method == 'level-up':
                    cursor.execute(insert_learnset_query, (pokemon_id, move_id, learn_method, level))

        except Exception as e:
            print(f"❌ Erro ao processar Pokémon ID {pokemon_id}: {e}")

def run_seeder():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ordem de execução é importante por causa das chaves estrangeiras (Foreign Keys):
        # 1. Primeiro as tipagens (Já executado por você no script anterior)
        # 2. Segundo os Moves (precisam das tipagens)
        fetch_and_seed_moves(cursor)
        
        # 3. Terceiro as Espécies e seus Movesets (precisam das tipagens e dos moves)
        fetch_and_seed_pokemon(cursor)
        
        conn.commit()
        print("\n🎉 Sincronização de Pokédex e Movesets concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_seeder()