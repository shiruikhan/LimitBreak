# LimitBreak — CLAUDE.md

## Visão do Produto

Aplicativo web (com futura conversão para Android) de acompanhamento de treinos de musculação com sistema de gamificação inspirado em Pokémon. O usuário progride no mundo real (treinos, frequência, carga) e isso reflete diretamente em sua jornada virtual (XP, evoluções, capturas, colecionismo).

---

## Divisão de Responsabilidades

| Área | Responsável |
|---|---|
| Sistema de gamificação (Pokémon, XP, capturas, loja, Pokédex) | **Silvio (este repositório)** |
| Banco de exercícios, planos de treino, biomecânica, GIFs | Outro desenvolvedor |

**Importante:** Não implementar lógica de exercícios/musculação neste repositório. O contrato entre as duas partes é via banco de dados — o sistema de treino grava os eventos (exercício realizado, check-in) e o sistema de gamificação os consome.

---

## Stack Técnica

- **Frontend/Backend:** Python + Streamlit
- **Banco de dados:** PostgreSQL hospedado no Supabase
- **Fonte de dados Pokémon:** PokéAPI (`https://pokeapi.co`)
- **Conexão ao banco:** `psycopg2`
- **Variáveis de ambiente:** `python-dotenv` (arquivo `.env` local, não versionado)

### Variáveis de ambiente necessárias (`.env`)
```
host=
port=
database=
user=
password=
```

---

## Estrutura de Arquivos

```
/
├── app_pokedex.py          # App Streamlit principal — Pokédex interativo
├── CLAUDE.md               # Este arquivo
├── README.md               # Visão geral do produto
├── scripts/
│   ├── seed_types.py       # Popula pokemon_types via PokéAPI (executar 1º)
│   ├── seed_pokedex.py     # Popula pokemon_species, pokemon_moves, pokemon_species_moves (executar 2º)
│   ├── seed_evolutions.py  # Popula pokemon_evolutions (executar 3º)
│   └── update_sprites.py   # Substitui URLs da PokéAPI por caminhos locais no banco
└── src/Pokemon/assets/
    ├── images/             # Sprites base (0001.png … 1025.png)
    ├── imagesHQ/           # Arte em alta qualidade (mesmo padrão de nome)
    ├── thumbnails/         # Thumbnails para cadeia evolutiva (0001.png … 1025.png)
    └── Others/
        └── damage-category-icons/1x/   # Physical.png, Special.png, Status.png
```

---

## Schema do Banco de Dados

### `pokemon_types`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID da PokéAPI (1–19, ignora ≥10000) |
| name | TEXT | Nome capitalizado (ex: "Fire") |
| slug | TEXT | Slug da API (ex: "fire") |

### `pokemon_species`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID Nacional do Pokédex (1–1025) |
| name | TEXT | Nome capitalizado |
| slug | TEXT | Slug da API |
| type1_id | INT FK | FK → pokemon_types |
| type2_id | INT FK | FK → pokemon_types (nullable) |
| base_experience | INT | XP base ao derrotar |
| sprite_url | TEXT | Caminho local: `/src/Pokemon/assets/images/XXXX.png` |
| sprite_shiny_url | TEXT | URL original da PokéAPI (shiny) |

### `pokemon_moves`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID da PokéAPI (filtrado: ≤10000) |
| name | TEXT | Nome formatado (ex: "Vine Whip") |
| slug | TEXT | Slug da API |
| type_id | INT FK | FK → pokemon_types |
| power | INT | Poder do golpe (nullable) |
| accuracy | INT | Precisão (nullable) |
| pp | INT | PP máximo |
| damage_class | TEXT | "physical", "special" ou "status" |

### `pokemon_species_moves`
| Coluna | Tipo | Descrição |
|---|---|---|
| species_id | INT FK | FK → pokemon_species |
| move_id | INT FK | FK → pokemon_moves |
| learn_method | TEXT | Método de aprendizado (seed filtra apenas "level-up") |
| level_learned_at | INT | Nível em que aprende o golpe |

> Constraint UNIQUE esperada: `(species_id, move_id, learn_method)` — necessária para o `ON CONFLICT DO NOTHING` do seed funcionar corretamente.

### `pokemon_evolutions`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID determinístico: `(from_id * 1000) + to_id` |
| from_species_id | INT FK | Pokémon pré-evolução |
| to_species_id | INT FK | Pokémon pós-evolução |
| min_level | INT | Nível mínimo (nullable) |
| trigger_name | TEXT | "level-up", "use-item", etc. |
| item_name | TEXT | Nome do item quando trigger = "use-item" (nullable) |

---

## App Principal — `app_pokedex.py`

### Fluxo
1. Conexão ao banco via `@st.cache_resource` (singleton por sessão Streamlit)
2. Sidebar com selectbox de todos os 1.025 Pokémon
3. Ao selecionar: carrega detalhes, moveset e cadeia evolutiva
4. Layout em 3 colunas: info | imagem HQ | moveset (scroll)
5. Seção inferior: cadeia evolutiva completa com thumbnails e setas

### Funções principais
| Função | Descrição |
|---|---|
| `init_connection()` | Conexão ao Supabase, cacheada |
| `get_image_as_base64(path)` | Lê imagem local e converte para base64 para embutir no HTML |
| `get_all_pokemon()` | Lista todos os Pokémon (id, name) para o selectbox |
| `get_pokemon_details(id)` | Nome, sprite_url, type1, type2 |
| `get_pokemon_moves(id)` | Moveset por level-up ordenado por nível |
| `get_full_evolution_chain(id)` | CTE recursiva que encontra a família inteira — ancestors → base_pokemon → full_chain |

### Detalhe da CTE recursiva de evolução
A query usa dois CTEs recursivos encadeados:
1. `ancestors` — sobe na árvore para encontrar o Pokémon raiz (sem predecessores)
2. `full_chain` — desce a partir da raiz mapeando todos os filhos/netos

Isso permite exibir a cadeia completa independente de qual membro da família estiver selecionado (ex: selecionar Ivysaur mostra Bulbasaur → Ivysaur → Venusaur).

---

## Scripts de Seed — Ordem de Execução

Os scripts devem ser executados nesta ordem por causa das Foreign Keys:

```
1. python scripts/seed_types.py       # pokemon_types (sem dependências)
2. python scripts/seed_pokedex.py     # pokemon_moves + pokemon_species + pokemon_species_moves
3. python scripts/seed_evolutions.py  # pokemon_evolutions
4. python scripts/update_sprites.py   # atualiza sprite_url para caminhos locais
```

Todos os scripts usam `ON CONFLICT ... DO UPDATE` (upsert), portanto são **idempotentes** — podem ser reexecutados sem duplicar dados.

**Filtros aplicados nos seeds:**
- Tipos com `id ≥ 10000` são ignorados (tipagens especiais não oficiais: "unknown", "shadow")
- Moves com `id > 10000` são ignorados (Z-moves, Max moves)
- Moves do learnset com `id > 1000` são ignorados (moves de DLCs/futuras gerações)
- Apenas moveset via `"level-up"` é salvo (máquinas TM/HM e eggs não são usados)
- Evoluções: o `id` é gerado como `(from_id * 1000) + to_id` para garantir idempotência sem precisar de constraint composta

---

## Funcionalidades Planejadas (Gamificação)

### Implementado
- [x] Pokédex interativo com sprites, tipos, moveset e cadeia evolutiva
- [x] Seed completo: 1.025 Pokémon, ~900 moves, evoluções, tipagens

### A implementar (responsabilidade deste repo)
- [ ] Tela de criação de conta com escolha de Pokémon inicial (iniciais de todas as gerações)
- [ ] Sistema de XP: cada exercício realizado dá XP ao Pokémon ativo
- [ ] Evolução automática ao atingir o `min_level` da cadeia evolutiva
- [ ] Gerenciamento de equipe (até 6 Pokémon ativos + banco)
- [ ] Sistema de encontros: 25% de chance de spawn por exercício, com tipagem vinculada ao tipo de exercício
- [ ] Captura garantida (100%) quando o encontro ocorre
- [ ] Calendário de presença com recompensa de moedas por frequência
- [ ] Loja virtual: XP Share, skins regionais (Galar, Alola, etc.)
- [ ] Pokédex pessoal do usuário (capturados vs não capturados)

### Contrato com o outro dev (eventos esperados no banco)
O sistema de gamificação precisa consumir (ou ser notificado de) eventos gerados pelo módulo de treinos:
- Exercício completado (com tipo de musculação para definir tipagem do spawn)
- Check-in diário realizado

---

## Convenções de Código

- Nomes de arquivos de sprite: `XXXX.png` com ID zero-padded de 4 dígitos (`0001.png`, `0025.png`)
- `sprite_url` no banco armazena caminho relativo a partir da raiz do projeto: `/src/Pokemon/assets/images/XXXX.png`
- Imagens HQ ficam em `/src/Pokemon/assets/imagesHQ/` com o mesmo padrão de nome — o app faz a troca via `.replace("/images/", "/imagesHQ/")`
- CSS de tipos Pokémon usa classes `.bg-{tipo}` (ex: `.bg-grass`, `.bg-poison`) — expandir conforme necessidade
- Queries SQL com parâmetros usam `%s` (psycopg2) — nunca f-strings com valores diretos

---

## Estrutura de Arquivos (atualizada)

```
/
├── app.py                      # Entry point — st.navigation, auth gate
├── app_pokedex.py              # LEGADO — Pokédex standalone (manter como referência)
├── requirements.txt            # streamlit, psycopg2-binary, supabase, python-dotenv, requests
├── CLAUDE.md
├── pages/
│   ├── login.py                # Login / Cadastro com Supabase Auth + seleção de starter
│   ├── pokedex.py              # Pokédex redesenhado (gradiente por tipo, moves com ícones)
│   └── equipe.py               # Equipe ativa — 6 slots, promover principal, remover
├── utils/
│   ├── __init__.py
│   ├── type_colors.py          # Paleta de cores dos 18 tipos Pokémon
│   ├── db.py                   # Todas as queries psycopg2 (Pokédex + usuário)
│   └── supabase_client.py      # Supabase client (somente Auth)
└── scripts/
    ├── seed_types.py
    ├── seed_pokedex.py
    ├── seed_evolutions.py
    ├── update_sprites.py
    └── create_user_tables.sql  # Executar no SQL Editor do Supabase antes de usar o app
```

### Credenciais

**`.env`** — apenas conexão PostgreSQL direta:
```
host=
port=
database=
user=
password=
```

**`.streamlit/secrets.toml`** — credenciais Supabase (nunca no `.env`, nunca no git):
```toml
[supabase]
url      = "https://SEU_PROJECT_ID.supabase.co"
anon_key = "sua_anon_key_aqui"
```

Ambos os arquivos estão no `.gitignore`.  
`SUPABASE_URL` e `SUPABASE_ANON_KEY` ficam no dashboard do Supabase em **Settings → API**.  
No Streamlit Cloud, as secrets são configuradas em **App settings → Secrets** (mesmo formato TOML).

---

## Tabelas de Usuário (novas)

### `user_profiles`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID PK | Referência a `auth.users` |
| username | TEXT | Nome do treinador |
| coins | INT | Moedas acumuladas |
| starter_pokemon_id | INT FK | Pokémon inicial escolhido |

### `user_pokemon`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | Dono do Pokémon |
| species_id | INT FK | Espécie |
| level | INT | Nível atual (começa em 1) |
| xp | INT | XP acumulado |
| is_shiny | BOOL | |

### `user_team`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_id | UUID | FK |
| slot | INT | 1–6 (slot 1 = Pokémon principal) |
| user_pokemon_id | INT FK | Pokémon na equipe |

**Fórmula XP:** `level * 100` XP necessário para o próximo nível.

---

## Fluxo de Autenticação

1. `app.py` checa `st.session_state.user`
2. Se `None` → carrega `pages/login.py` (hidden nav)
3. Login/Signup via `supabase-py` → armazena `user`, `user_id`, `access_token`, `refresh_token` em `session_state`
4. Novo usuário (`needs_starter=True`) → tela de seleção de starter (27 opções, Gen 1–9)
5. Seleção cria `user_profiles` + primeiro `user_pokemon` + `user_team` slot 1
6. Navegação normal: Pokédex + Minha Equipe

**Nota:** Auth usa `supabase-py`; todas as queries de dados usam `psycopg2` direto. RLS está definido no SQL mas não é aplicado via psycopg2 (apenas via REST API).

---

## Como iniciar o app

```bash
pip install -r requirements.txt

# 1. Configure o .env com as credenciais
# 2. Execute o SQL de migração no Supabase
# 3. Inicie o app
streamlit run app.py
```

---

## Estado Atual do Projeto

**Fase:** MVP com auth e Pokédex funcional.

- Auth completo: login, cadastro, seleção de starter
- Pokédex redesenhado: gradiente por tipo, type icons, move cards com power/accuracy, evolution chain melhorada, toggle shiny, botão capturar
- Equipe: 6 slots, promover para principal (slot 1), remover, XP bar, moedas
- Sem lógica de XP por treino ainda (aguarda módulo do outro dev)
