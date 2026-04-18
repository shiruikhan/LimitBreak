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
- **Autenticação:** Supabase Auth via `supabase-py`
- **Fonte de dados Pokémon:** PokéAPI (`https://pokeapi.co`)
- **Conexão ao banco:** `psycopg2` (direto, não via REST)
- **Variáveis de ambiente:** `python-dotenv` (arquivo `.env` local, não versionado)

### Credenciais

**`.env`** — conexão PostgreSQL direta (nunca no git):
```
host=
port=
database=
user=
password=
```

**`.streamlit/secrets.toml`** — credenciais Supabase Auth (nunca no git):
```toml
[supabase]
url      = "https://SEU_PROJECT_ID.supabase.co"
anon_key = "sua_anon_key_aqui"
```

`SUPABASE_URL` e `SUPABASE_ANON_KEY` ficam no dashboard do Supabase em **Settings → API**.  
No Streamlit Cloud, configurar em **App settings → Secrets** (mesmo formato TOML).

**Nota:** Auth usa `supabase-py`; todas as queries de dados usam `psycopg2` direto. RLS está definido no SQL mas não é aplicado via psycopg2 (apenas via REST API).

---

## Estrutura de Arquivos

```
/
├── app.py                       # Entry point — roteamento de 3 estados (auth gate)
├── app_pokedex.py               # LEGADO — Pokédex standalone, manter apenas como referência
├── requirements.txt             # streamlit, psycopg2-binary, supabase, python-dotenv, requests
├── CLAUDE.md                    # Este arquivo
├── README.md                    # Visão geral do produto (para o GitHub)
├── pages/
│   ├── login.py                 # Login / Cadastro com Supabase Auth
│   ├── starter.py               # Seleção de Pokémon inicial (+ easter egg)
│   ├── pokedex.py               # Pokédex redesenhado (gradiente por tipo, move cards)
│   └── equipe.py                # Equipe ativa — 6 slots, moveset, promover, remover
├── utils/
│   ├── __init__.py
│   ├── type_colors.py           # Paleta de cores dos 18 tipos Pokémon
│   ├── db.py                    # Todas as queries psycopg2 (Pokédex + usuário)
│   └── supabase_client.py       # Supabase client singleton (somente Auth)
├── scripts/
│   ├── seed_types.py            # Popula pokemon_types via PokéAPI (executar 1º)
│   ├── seed_pokedex.py          # Popula pokemon_species, pokemon_moves, species_moves (2º)
│   ├── seed_evolutions.py       # Popula pokemon_evolutions (3º)
│   ├── seed_stats.py            # Popula base stats em pokemon_species via PokéAPI (4º)
│   ├── update_sprites.py        # Substitui URLs da PokéAPI por caminhos locais
│   └── create_user_tables.sql   # DDL das tabelas de usuário — executar no Supabase
└── src/Pokemon/assets/
    ├── images/                  # Sprites base (0001.png … 1025.png)
    ├── imagesHQ/                # Arte em alta qualidade (mesmo padrão de nome)
    ├── thumbnails/              # Thumbnails para cadeia evolutiva
    └── Others/
        ├── type-icons/png/      # Ícones de tipo (grass.png, fire.png, …)
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
| sprite_url | TEXT | Caminho local: `src/Pokemon/assets/images/XXXX.png` |
| sprite_shiny_url | TEXT | URL original da PokéAPI (shiny) |
| base_hp | SMALLINT | Base stat HP |
| base_attack | SMALLINT | Base stat Ataque |
| base_defense | SMALLINT | Base stat Defesa |
| base_sp_attack | SMALLINT | Base stat Ataque Especial |
| base_sp_defense | SMALLINT | Base stat Defesa Especial |
| base_speed | SMALLINT | Base stat Velocidade |

> Base stats populados via `scripts/seed_stats.py` após o seed principal.

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

> Constraint UNIQUE: `(species_id, move_id, learn_method)` — necessária para o `ON CONFLICT DO NOTHING` do seed.

### `pokemon_evolutions`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID determinístico: `(from_id * 1000) + to_id` |
| from_species_id | INT FK | Pokémon pré-evolução |
| to_species_id | INT FK | Pokémon pós-evolução |
| min_level | INT | Nível mínimo (nullable) |
| trigger_name | TEXT | "level-up", "use-item", etc. |
| item_name | TEXT | Nome do item quando trigger = "use-item" (nullable) |

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
| species_id | INT FK | Espécie (FK → pokemon_species) |
| level | INT | Nível atual (começa em 1) |
| xp | INT | XP acumulado |
| is_shiny | BOOL | |
| stat_hp | SMALLINT | HP individual (copiado dos base stats na captura) |
| stat_attack | SMALLINT | Ataque individual |
| stat_defense | SMALLINT | Defesa individual |
| stat_sp_attack | SMALLINT | Ataque Especial individual |
| stat_sp_defense | SMALLINT | Defesa Especial individual |
| stat_speed | SMALLINT | Velocidade individual |

> Os `stat_*` são copiados dos `base_*` da espécie no momento da captura/criação. No futuro podem ser modificados por itens ou evoluções.

### `user_team`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_id | UUID FK | |
| slot | INT | 1–6 (slot 1 = Pokémon principal) |
| user_pokemon_id | INT FK | FK → user_pokemon |

> Constraint PK: `(user_id, slot)`.

### `user_pokemon_moves`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_pokemon_id | INT FK | FK → user_pokemon (CASCADE DELETE) |
| slot | INT | 1–4 (até 4 moves equipados) |
| move_id | INT FK | FK → pokemon_moves |

> Constraint PK: `(user_pokemon_id, slot)`. Apenas moves com `level_learned_at <= level` podem ser equipados.

**Fórmula XP:** `level * 100` XP necessário para o próximo nível.

---

## Fluxo de Autenticação

```
app.py
  │
  ├─ user == None          → pages/login.py    (nav hidden)
  ├─ needs_starter == True → pages/starter.py  (nav hidden)
  └─ autenticado           → pages/pokedex.py + pages/equipe.py
```

1. `app.py` checa `st.session_state.user`
2. Se `None` → `pages/login.py` — login ou cadastro via Supabase Auth
3. Login bem-sucedido → checa `get_user_pokemon_ids()`. Se vazio → `needs_starter = True`
4. `pages/starter.py` — 27 iniciais (Gen 1–9) + 2 secretos via easter egg
5. Confirmação cria `user_profiles` + `user_pokemon` (com stats copiados) + `user_team` slot 1
6. Navegação normal: Pokédex + Minha Equipe

---

## Páginas do App

### `pages/login.py`
- Tabs "Entrar" / "Criar conta"
- Autenticação via `supabase-py` (`sign_in_with_password` / `sign_up`)
- Armazena `user`, `user_id`, `access_token`, `refresh_token` em `session_state`
- Dispara `needs_starter = True` se o usuário não tem Pokémon

### `pages/starter.py`
- Grade de 27 iniciais (Gen 1–9), 9 por linha, com thumbnail e botão de seleção
- **Easter egg secreto:** clicar 7 vezes em qualquer área fora dos botões desbloqueia Cubone (#104) e Mimikyu (#778), exibidos com borda roxa
- Mecanismo do easter egg: botão invisível com label `\u2800` (Braille blank) + JS em `components.html(height=0)` que escuta cliques no `window.parent.document` e dispara `.click()` programaticamente após 7 acertos. Guard `window.parent._easterInit` evita listeners duplicados em reruns.
- Ao confirmar: chama `create_user_profile()` → cria perfil + Pokémon + slot de equipe

### `pages/pokedex.py`
- Sidebar com selectbox de todos os 1.025 Pokémon
- Header com gradiente dinâmico baseado nos tipos do Pokémon selecionado
- Layout: info + sprite HQ | move cards com ícone de tipo, classe de dano, power, accuracy
- Cadeia evolutiva completa via CTE recursiva
- Base stats exibidos como barras (quando populados via `seed_stats.py`)

### `pages/equipe.py`
- Grade de 6 slots; clique no card seleciona o Pokémon
- Ações: ⚔ Golpes / ↑ Promover para slot 1 / 🗑 Remover da equipe
- Painel de movimentos: coluna esquerda = 4 slots ativos (com ✕ para desquipar); coluna direita = lista de moves disponíveis pelo nível
- **Modo substituição:** se os 4 slots estão cheios, clicar em um novo move entra em modo "replace" — slots ficam amarelos e cada um exibe "↩ Slot X" para confirmação
- Moves já equipados aparecem acinzentados na lista de disponíveis

---

## Scripts de Seed — Ordem de Execução

```bash
python scripts/seed_types.py       # 1. pokemon_types (sem dependências)
python scripts/seed_pokedex.py     # 2. pokemon_moves + pokemon_species + species_moves
python scripts/seed_evolutions.py  # 3. pokemon_evolutions
python scripts/seed_stats.py       # 4. base stats em pokemon_species (PokéAPI, ~5 min)
python scripts/update_sprites.py   # 5. atualiza sprite_url para caminhos locais
```

O SQL das tabelas de usuário fica em `scripts/create_user_tables.sql` — executar uma única vez no SQL Editor do Supabase.

Todos os scripts são **idempotentes** — usam `ON CONFLICT ... DO UPDATE/NOTHING` e podem ser reexecutados sem duplicar dados. O `seed_stats.py` processa apenas espécies com `base_hp IS NULL`.

**Filtros aplicados nos seeds:**
- Tipos com `id ≥ 10000` ignorados (tipagens especiais: "unknown", "shadow")
- Moves com `id > 10000` ignorados (Z-moves, Max moves)
- Moves do learnset com `id > 1000` ignorados (DLCs/gerações futuras)
- Apenas moveset via `"level-up"` salvo (TM/HM e egg moves não são usados)
- ID de evolução gerado como `(from_id * 1000) + to_id` para idempotência

---

## Conexão ao Banco — Detalhe Técnico

A conexão psycopg2 é armazenada em `st.session_state._db_conn` (não em `@st.cache_resource`) para evitar que conexões expiradas sejam compartilhadas entre sessões diferentes.

```python
def get_connection():
    conn = st.session_state.get("_db_conn")
    if conn is None or conn.closed != 0:
        st.session_state._db_conn = _new_conn()
        return st.session_state._db_conn
    if conn.status != psycopg2.extensions.STATUS_READY:
        try:
            conn.rollback()
        except Exception:
            st.session_state._db_conn = _new_conn()
    return st.session_state._db_conn
```

---

## CTE Recursiva de Evolução — Detalhe

A query usa três CTEs encadeados:
1. `ancestors` — sobe na árvore para encontrar o Pokémon raiz
2. `base_pokemon` — seleciona o id mais baixo (a raiz)
3. `full_chain` — desce a partir da raiz mapeando toda a família

Permite exibir a cadeia completa independente do membro selecionado (ex: Ivysaur mostra Bulbasaur → Ivysaur → Venusaur).

---

## Convenções de Código

- Nomes de arquivos de sprite: `XXXX.png` com ID zero-padded de 4 dígitos (`0001.png`, `0025.png`)
- `sprite_url` armazena caminho relativo à raiz: `src/Pokemon/assets/images/XXXX.png`
- Imagens HQ: `src/Pokemon/assets/imagesHQ/` — o app troca via `.replace("/images/", "/imagesHQ/")`
- Queries SQL usam `%s` (psycopg2) — nunca f-strings com valores diretos
- Cores de tipo ficam em `utils/type_colors.py` como dict `TYPE_COLORS[slug] = {bg, light, dark, text}`

---

## Como Iniciar o App

```bash
pip install -r requirements.txt

# 1. Criar .env com as credenciais PostgreSQL
# 2. Criar .streamlit/secrets.toml com as credenciais Supabase
# 3. Executar scripts/create_user_tables.sql no SQL Editor do Supabase
# 4. (Primeira vez) Executar os scripts de seed na ordem acima
streamlit run app.py
```

---

## Estado Atual do Projeto (abril 2026)

**Fase:** MVP funcional com auth, Pokédex, equipe e movimentos.

### Implementado
- [x] Pokédex completo: sprites, tipos, moveset por nível, cadeia evolutiva, base stats (após seed)
- [x] Seed completo: 1.025 Pokémon, ~900 moves, evoluções, tipagens, base stats
- [x] Autenticação: login, cadastro, sessão persistente via Supabase Auth
- [x] Onboarding: seleção de Pokémon inicial (27 + 2 secretos via easter egg)
- [x] Equipe: 6 slots, promover para principal, remover
- [x] Movimentos: 4 slots equipáveis por Pokémon, respeitando nível, modo substituição
- [x] Stats individuais em `user_pokemon` (copiados dos base stats na captura)

### A implementar
- [ ] Sistema de XP: exercício realizado → XP para o Pokémon ativo
- [ ] Evolução automática ao atingir `min_level` da cadeia evolutiva
- [ ] Sistema de encontros: 25% de chance de spawn por exercício, tipagem vinculada ao tipo de treino
- [ ] Captura garantida (100%) quando o encontro ocorre
- [ ] Pokédex pessoal: capturados vs não capturados
- [ ] Calendário de presença com recompensa de moedas por frequência
- [ ] Loja virtual: XP Share, skins regionais (Galar, Alola, etc.)

### Contrato com o outro dev (eventos esperados no banco)
- Exercício completado (com tipo de musculação → define tipagem do spawn)
- Check-in diário realizado
