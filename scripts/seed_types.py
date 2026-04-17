import os
import requests
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configurações do Banco de Dados via .env
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("database")
DB_USER = os.getenv("user")
DB_PASS = os.getenv("password")

# URL Base da PokeAPI
# Ao invés de buscar um por um, pegamos a lista completa passando um limit=50 
# (atualmente existem 19 tipos oficiais na API, 50 cobre com folga)
API_URL = "https://pokeapi.co/api/v2/type/?limit=50"

def fetch_pokemon_types():
    print("Buscando tipagens na PokéAPI...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        types_data = response.json().get("results", [])
        
        records = []
        for type_info in types_data:
            # A API retorna {"name": "normal", "url": "https://pokeapi.co/api/v2/type/1/"}
            slug = type_info["name"]
            name = slug.capitalize()
            
            # Extrai o ID diretamente do final da URL
            url = type_info["url"]
            type_id = int(url.rstrip("/").split("/")[-1])
            
            # Tipos com ID acima de 10000 são tipagens extras não oficiais em jogos padrão (ex: 'unknown', 'shadow')
            # Se quiser inseri-los também, basta remover essa verificação.
            if type_id < 10000:
                records.append((type_id, name, slug))
                
        return records
    except Exception as e:
        print(f"❌ Erro ao buscar dados na API: {e}")
        return []

def seed_database(records):
    print("Conectando ao banco de dados Supabase...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor()

        # Query de Inserção usando Upsert (ON CONFLICT) 
        # Isso garante que se você rodar o script duas vezes, ele não duplicará dados nem gerará erro de Primary Key
        insert_query = """
            INSERT INTO pokemon_types (id, name, slug)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug;
        """

        for record in records:
            cursor.execute(insert_query, record)
            print(f"✅ Inserido/Atualizado: {record[1]} (ID: {record[0]})")

        # Salva as alterações
        conn.commit()
        cursor.close()
        print("🎉 Sincronização concluída com sucesso!")

    except Exception as e:
        print(f"❌ Erro na operação do banco de dados: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    types_to_insert = fetch_pokemon_types()
    if types_to_insert:
        seed_database(types_to_insert)
    else:
        print("Nenhuma tipagem encontrada para inserir.")