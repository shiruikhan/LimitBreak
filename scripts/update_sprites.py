import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("database")
DB_USER = os.getenv("user")
DB_PASS = os.getenv("password")

# --- CONFIGURAÇÃO DO CAMINHO ---
# Este é o prefixo que será salvo no banco antes do nome do arquivo.
# Dependendo de como você configurar o Vite/Next.js no front-end, talvez precise 
# mudar isso para "/assets/images/" ou algo similar.
BASE_WEB_PATH = "/src/Pokemon/assets/images/"

# Total de Pokémon base no banco
POKEMON_LIMIT = 1025

def update_local_sprites():
    print("Substituindo URLs da PokéAPI por caminhos locais...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        )
        cursor = conn.cursor()

        # Query de atualização simples
        update_query = """
            UPDATE pokemon_species 
            SET sprite_url = %s 
            WHERE id = %s;
        """

        for pokemon_id in range(1, POKEMON_LIMIT + 1):
            # Formata o ID para ter 4 dígitos (ex: 1 vira "0001", 25 vira "0025")
            file_name = f"{str(pokemon_id).zfill(4)}.png"
            
            # Monta o caminho final: "/src/Pokemon/assets/images/0001.png"
            full_path = f"{BASE_WEB_PATH}{file_name}"
            
            cursor.execute(update_query, (full_path, pokemon_id))
            
            # Feedback no terminal a cada 100 registros
            if pokemon_id % 100 == 0:
                print(f"✅ Atualizados {pokemon_id} sprites...")

        # Salva as alterações de uma vez só
        conn.commit()
        print("\n🎉 Todos os caminhos de sprites base atualizados com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro na operação do banco de dados: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    update_local_sprites()