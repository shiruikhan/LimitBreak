import os
import streamlit as st
import psycopg2
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS E CSS
# ==========================================
st.set_page_config(layout="wide", page_title="LimitBreak Pokédex", page_icon="🏋️‍♂️")
load_dotenv()
base_dir = os.getcwd()
_GITHUB_ASSETS_CDN = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master"

# CSS Customizado com Efeitos de Hover
st.markdown("""
    <style>
    .poke-title { text-align: center; font-size: 3rem; font-weight: bold; color: #555; text-transform: uppercase; margin-bottom: 0px;}
    .poke-subtitle { text-align: center; font-size: 1rem; color: #fff; background-color: #78C850; padding: 4px 12px; border-radius: 15px; display: inline-block; margin-bottom: 30px;}
    .info-label { font-weight: bold; color: #666; width: 60px; display: inline-block; margin-bottom: 15px; }
    .tag { color: white; padding: 4px 12px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-right: 5px; margin-bottom: 5px; display: inline-block; }
    
    /* Cores de Tipos */
    .bg-grass { background-color: #78C850; }
    .bg-poison { background-color: #A040A0; }
    
    /* Container com Scroll para os Moves */
    .moves-container {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 10px;
    }
    
    /* Scrollbar customizada */
    .moves-container::-webkit-scrollbar { width: 6px; }
    .moves-container::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
    
    /* Cartão de Golpe com Efeito Hover e Transições Suaves */
    .move-card {
        background-color: #f8f9fa;
        border-left: 5px solid #78C850;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        color: #333;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    
    .move-card:hover {
        transform: translateX(-5px) scale(1.02); 
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border-left: 5px solid #A040A0;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO E HELPERS DE IMAGEM
# ==========================================
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=os.getenv("host"), port=os.getenv("port"), dbname=os.getenv("database"),
        user=os.getenv("user"), password=os.getenv("password")
    )

conn = init_connection()

@st.cache_data
def get_asset_src(path):
    if path.startswith(("http://", "https://")):
        return path
    if os.path.isfile(path):
        norm = path.replace("\\", "/")
        if "assets/" in norm:
            rel = norm.split("assets/", 1)[1]
            return f"{_GITHUB_ASSETS_CDN}/assets/{rel}"
    norm = path.replace("\\", "/")
    if "assets/" in norm:
        rel = norm.split("assets/", 1)[1]
        return f"{_GITHUB_ASSETS_CDN}/assets/{rel}"
    return None

# ==========================================
# 3. QUERIES SQL
# ==========================================
@st.cache_data
def get_all_pokemon():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM pokemon_species ORDER BY id;")
        return cur.fetchall()

def get_pokemon_details(pokemon_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.name, p.sprite_url, t1.name as type1, t2.name as type2
            FROM pokemon_species p
            LEFT JOIN pokemon_types t1 ON p.type1_id = t1.id
            LEFT JOIN pokemon_types t2 ON p.type2_id = t2.id
            WHERE p.id = %s;
        """, (pokemon_id,))
        return cur.fetchone()

def get_pokemon_moves(pokemon_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.name, sm.level_learned_at, m.damage_class 
            FROM pokemon_moves m
            JOIN pokemon_species_moves sm ON m.id = sm.move_id
            WHERE sm.species_id = %s
            ORDER BY sm.level_learned_at ASC;
        """, (pokemon_id,))
        return cur.fetchall()

def get_full_evolution_chain(pokemon_id):
    """
    Busca a árvore genealógica inteira do Pokémon usando uma CTE Recursiva (SQL Avançado).
    Encontra quem é o 'Pai Original' e depois mapeia todas as suas evoluções pra frente.
    """
    with conn.cursor() as cur:
        query = """
        WITH RECURSIVE ancestors AS (
            SELECT from_species_id as id FROM pokemon_evolutions WHERE to_species_id = %(id)s
            UNION
            SELECT e.from_species_id FROM pokemon_evolutions e
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
        SELECT 
            fc.from_species_id, p1.name as from_name, 
            fc.to_species_id, p2.name as to_name, 
            fc.min_level, fc.trigger_name, fc.item_name
        FROM full_chain fc
        JOIN pokemon_species p1 ON fc.from_species_id = p1.id
        JOIN pokemon_species p2 ON fc.to_species_id = p2.id;
        """
        cur.execute(query, {'id': pokemon_id})
        return cur.fetchall()

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
pokemon_list = get_all_pokemon()
pokemon_dict = {f"{str(p[0]).zfill(3)} - {p[1]}": p[0] for p in pokemon_list}

selected_option = st.sidebar.selectbox("🔍 Selecione um Pokémon", options=list(pokemon_dict.keys()))
selected_id = pokemon_dict[selected_option]

if selected_id:
    details = get_pokemon_details(selected_id)
    name, sprite_url, type1, type2 = details
    moves = get_pokemon_moves(selected_id)
    
    # CABEÇALHO
    st.markdown(f"<div class='poke-title'>{name}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'><div class='poke-subtitle'>Espécie Base Pokémon</div></div>", unsafe_allow_html=True)
    
    st.write("")
    
    # 3 COLUNAS PRINCIPAIS
    col_info, col_img, col_moves = st.columns([1, 1.5, 1.5])
    
    # --- COLUNA ESQUERDA (INFORMAÇÕES LIMPAS) ---
    with col_info:
        st.write("")
        st.write("")
        st.markdown(f"<div><span class='info-label'>ID</span> <b>#{selected_id}</b></div>", unsafe_allow_html=True)
        
        type_html = f"<div><span class='info-label'>Type</span>"
        type_html += f"<span class='tag bg-grass'>{type1}</span>" if type1 else ""
        type_html += f"<span class='tag bg-poison'>{type2}</span>" if type2 else ""
        type_html += "</div>"
        st.markdown(type_html, unsafe_allow_html=True)

    # --- COLUNA CENTRAL (IMAGEM HQ) ---
    with col_img:
        hq_path = sprite_url.replace("/images/", "/imagesHQ/")
        image_path = os.path.join(base_dir, hq_path.lstrip('/'))
        _, center_img, _ = st.columns([1, 4, 1])
        with center_img:
            try:
                st.image(image_path, width=350)
            except:
                st.warning("Imagem HQ não encontrada.")

    # --- COLUNA DIREITA (MOVESET CORRIGIDO) ---
    with col_moves:
        st.markdown("<h4 style='color: #666; margin-bottom: 15px;'>Movepool (Level Up)</h4>", unsafe_allow_html=True)
        
        if moves:
            moves_html = "<div class='moves-container'>"
            for move in moves:
                m_name, m_level, m_class = move
                
                icon_tag = ""
                if m_class:
                    icon_name = f"{m_class.capitalize()}.png"
                    icon_path = os.path.join(base_dir, "src", "Pokemon", "assets", "Others", "damage-category-icons", "1x", icon_name)
                    icon_src = get_asset_src(icon_path)
                    if icon_src:
                        icon_tag = f"<img src='{icon_src}' width='20' style='margin-left: 10px;'>"
                
                # CORREÇÃO: Escrito tudo em uma única linha, sem identação, para não quebrar a formatação do Markdown
                moves_html += f"<div class='move-card'><div style='font-weight: bold; color: #78C850; width: 50px;'>Lv. {m_level}</div><div style='font-weight: bold; font-size: 1.1rem; flex-grow: 1;'>{m_name}</div>{icon_tag}</div>"
                
            moves_html += "</div>"
            st.markdown(moves_html, unsafe_allow_html=True)
        else:
            st.write("Nenhum golpe mapeado.")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- PARTE INFERIOR: CADEIA EVOLUTIVA COMPLETA E DINÂMICA ---
    st.markdown("<div style='text-align: center;'><span class='tag bg-grass' style='font-size: 1.2rem; padding: 6px 20px;'>EVOLUTION CHAIN</span></div><br><br>", unsafe_allow_html=True)
    
    evolutions = get_full_evolution_chain(selected_id)
    
    if evolutions:
        # Lógica para mapear a família inteira e agrupar por estágios
        nodes = {e[0]: e[1] for e in evolutions}
        nodes.update({e[2]: e[3] for e in evolutions})
        
        to_ids = set(e[2] for e in evolutions)
        root_id = next((id for id in nodes if id not in to_ids), list(nodes.keys())[0])
        
        stages = [[root_id]]
        current_stage = [root_id]
        
        while True:
            next_stage = []
            for node in current_stage:
                children = [e[2] for e in evolutions if e[0] == node]
                for child in children:
                    if child not in next_stage:
                        next_stage.append(child)
            if not next_stage:
                break
            stages.append(next_stage)
            current_stage = next_stage
            
        num_stages = len(stages)
        
        # Cria colunas espaçadas de acordo com a quantidade de estágios
        col_ratios = []
        for i in range(num_stages):
            col_ratios.append(2) # Coluna da Imagem
            if i < num_stages - 1:
                col_ratios.append(1) # Coluna da Seta
                
        evo_cols = st.columns(col_ratios)
        
        # Desenha a cadeia
        for i, stage_nodes in enumerate(stages):
            col_idx = i * 2
            
            with evo_cols[col_idx]:
                for p_id in stage_nodes:
                    p_name = nodes[p_id]
                    thumb_path = os.path.join(base_dir, "src", "Pokemon", "assets", "thumbnails", f"{str(p_id).zfill(4)}.png")
                    thumb_src = get_asset_src(thumb_path)

                    img_html = f"<img src='{thumb_src}' width='100'>" if thumb_src else "📷"
                    color = "#78C850" if p_id == selected_id else "#888" # Destaca em verde quem está selecionado
                    
                    st.markdown(f"<div style='text-align: center;'>{img_html}<br><b style='color: {color};'>#{p_id} {p_name.upper()}</b></div>", unsafe_allow_html=True)
                    st.write("") # Espaçamento se houver múltiplos filhos (ex: Eevee)
            
            # Desenha as setas (se não for a última coluna)
            if i < num_stages - 1:
                with evo_cols[col_idx + 1]:
                    child_id = stages[i+1][0]
                    edge = next((e for e in evolutions if e[0] == stage_nodes[0] and e[2] == child_id), None)
                    cond = f"Lv {edge[4]}+" if (edge and edge[4]) else "Item"
                    
                    st.markdown(f"<div style='text-align: center; margin-top: 40px; color: #aaa; font-size: 0.9rem;'>{cond}<br><span style='font-size: 2rem;'>→</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center; color: #888;'>Este Pokémon é estágio único.</div>", unsafe_allow_html=True)
