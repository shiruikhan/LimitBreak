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

# Limite para a Geração 1
POKEMON_LIMIT = 1025

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def extract_id_from_url(url):
    if not url: return None
    return int(url.rstrip("/").split("/")[-1])

def process_evolution_node(node, cursor):
    """
    Função recursiva que navega na árvore de evoluções.
    'node' é o estágio atual do Pokémon.
    """
    from_species_id = extract_id_from_url(node['species']['url'])
    from_species_name = node['species']['name'].capitalize()

    # O array 'evolves_to' contém todas as próximas formas (ex: Eevee tem várias aqui)
    for evolution in node['evolves_to']:
        to_species_id = extract_id_from_url(evolution['species']['url'])
        to_species_name = evolution['species']['name'].capitalize()

        # Filtramos para salvar apenas as evoluções da Gen 1 (IDs <= 151)
        if from_species_id <= POKEMON_LIMIT and to_species_id <= POKEMON_LIMIT:
            
            # Pegamos os detalhes da evolução (nível, item, etc)
            details = evolution['evolution_details'][0] if evolution['evolution_details'] else {}
            
            trigger_name = details.get('trigger', {}).get('name') if details.get('trigger') else None
            min_level = details.get('min_level')
            item_name = details.get('item', {}).get('name') if details.get('item') else None

            # Como a PokéAPI não tem um ID único para a "Ação de Evoluir", 
            # criamos um ID numérico determinístico juntando os dois IDs.
            # Ex: Bulbasaur(1) evoluindo para Ivysaur(2) ganha o ID 1002.
            # Isso evita que o banco duplique registros se você rodar o script duas vezes.
            evo_id = (from_species_id * 1000) + to_species_id

            insert_query = """
                INSERT INTO pokemon_evolutions (id, from_species_id, to_species_id, min_level, trigger_name, item_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    min_level = EXCLUDED.min_level,
                    trigger_name = EXCLUDED.trigger_name,
                    item_name = EXCLUDED.item_name;
            """
            
            cursor.execute(insert_query, (evo_id, from_species_id, to_species_id, min_level, trigger_name, item_name))
            
            if trigger_name == 'level-up' and min_level:
                print(f"🧬 {from_species_name} -> {to_species_name} (Nv. {min_level})")
            elif trigger_name == 'use-item' and item_name:
                print(f"💎 {from_species_name} -> {to_species_name} (Item: {item_name})")
            else:
                print(f"✨ {from_species_name} -> {to_species_name} (Outro: {trigger_name})")

        # 🔄 RECURSIVIDADE: Chama a função para o próximo estágio (ex: Ivysaur -> Venusaur)
        process_evolution_node(evolution, cursor)

def fetch_and_seed_evolutions():
    print("Buscando cadeias evolutivas na PokéAPI...")
    session = requests.Session()
    conn = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # A Geração 1 está contida aproximadamente nas primeiras 78 cadeias evolutivas
        response = session.get("https://pokeapi.co/api/v2/evolution-chain/?limit=1000", timeout=10)
        chains = response.json().get("results", [])
        
        for chain_link in chains:
            try:
                chain_data = session.get(chain_link['url'], timeout=10).json()
                # Passa a raiz da árvore (O Pokémon base, ex: Bulbasaur, Charmander) para a função recursiva
                process_evolution_node(chain_data['chain'], cursor)
            except Exception as e:
                print(f"⚠️ Erro ao processar a cadeia {chain_link['url']}: {e}")

        conn.commit()
        print("\n🎉 Linhas Evolutivas sincronizadas com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
        session.close()

if __name__ == "__main__":
    fetch_and_seed_evolutions()