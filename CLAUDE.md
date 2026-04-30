# LimitBreak — CLAUDE.md

## Visão do Produto

Aplicativo web (com futura conversão para Android) de acompanhamento de treinos de musculação com sistema de gamificação inspirado em Pokémon. O usuário progride no mundo real (treinos, frequência, carga) e isso reflete diretamente em sua jornada virtual (XP, evoluções, capturas, colecionismo).

---

## Divisão de Responsabilidades

| Área | Responsável |
|---|---|
| Sistema de gamificação (Pokémon, XP, capturas, loja, Pokédex) | **Silvio (este repositório)** |
| Módulo de exercícios (tabelas, lógica, `pages/treino.py`) | **Silvio (este repositório)** |

---

## Stack Técnica

- **Frontend/Backend:** Python + Streamlit
- **Banco de dados:** PostgreSQL hospedado no Supabase
- **Autenticação:** Supabase Auth via `supabase-py`
- **Fonte de dados Pokémon:** PokéAPI (`https://pokeapi.co`)
- **Conexão ao banco:** `psycopg2` (direto, não via REST)
- **Sessão persistente:** `extra-streamlit-components` (CookieManager)
- **Imagens em produção:** GitHub CDN público `raw.githubusercontent.com/HybridShivam/Pokemon`

### Dependências (`requirements.txt`)
```
streamlit>=1.44.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
requests>=2.31.0
supabase>=2.0.0
extra-streamlit-components>=0.1.71
```

---

## Credenciais e Segredos

### Desenvolvimento local — `.env`
Nunca versionado. Usado por `python-dotenv` como **fallback** quando `st.secrets` não encontra a seção `[database]`:
```
host=
port=
database=
user=
password=
```

### Desenvolvimento local — `.streamlit/secrets.toml`
Nunca versionado:
```toml
[supabase]
url      = "https://SEU_PROJECT_ID.supabase.co"
anon_key = "sua_anon_key_aqui"

[database]
host     = "aws-X-REGION.pooler.supabase.com"
port     = "6543"
name     = "postgres"
user     = "postgres.SEU_PROJECT_ID"
password = "sua_senha"
```

### Produção — Streamlit Cloud
Em **App settings → Secrets**, colar o mesmo conteúdo do `secrets.toml`.  
Credenciais disponíveis em: Supabase → **Settings → API** (supabase) e **Settings → Database → Connection pooling** (database).

**Nota:** `_db_params()` em `db.py` tenta `st.secrets["database"]` primeiro; se não existir, cai para `os.getenv()`. Isso garante que ambos os ambientes funcionem sem mudança de código.

---

## Estrutura de Arquivos

```
/
├── app.py                       # Entry point — auth gate, restauração de sessão via cookie, navegação
├── app_pokedex.py               # LEGADO — Pokédex standalone, manter apenas como referência
├── requirements.txt
├── CLAUDE.md                    # Este arquivo
├── pages/
│   ├── login.py                 # Login / Cadastro + salva cookie de sessão
│   ├── starter.py               # Seleção de Pokémon inicial (27 + 2 easter egg)
│   ├── equipe.py                # Equipe ativa (página inicial) + banco de Pokémon
│   ├── batalha.py               # Arena PvP — desafiar outros usuários
│   ├── conquistas.py            # Sistema de conquistas — 23 badges em 5 categorias
│   ├── leaderboard.py           # Ranking — XP de treino / streak de check-in / coleção Pokémon
│   ├── pokedex.py               # Pokédex nacional completo
│   ├── pokedex_pessoal.py       # Pokédex pessoal — capturados vs não capturados
│   ├── loja.py                  # Loja de itens + mochila com uso de itens (inclui loot box e nature mint)
│   ├── calendario.py            # Check-in diário + calendário mensal
│   ├── biblioteca.py            # Biblioteca de exercícios — catálogo Pokédex-style (152 exercícios)
│   ├── rotinas.py               # Workout Builder — criar/editar fichas e dias de treino
│   ├── treino.py                # Routine Log — registro de sessão com Import Default
│   └── admin.py                 # Painel administrativo — restrito a is_admin(); 5 tabs
├── utils/
│   ├── __init__.py
│   ├── type_colors.py           # Paleta de cores dos 18 tipos Pokémon
│   ├── achievements.py          # Catálogo de conquistas (CATALOG, CATEGORY_META, badge_url)
│   ├── abilities.py             # Registro de habilidades passivas de treino (Release 3A)
│   ├── db.py                    # TODAS as queries psycopg2 — ver seção abaixo
│   └── supabase_client.py       # Supabase client (somente Auth) — lê st.secrets
└── scripts/
    ├── seed_types.py                         # Popula pokemon_types (executar 1º)
    ├── seed_pokedex.py                       # Popula pokemon_species, pokemon_moves, species_moves (2º)
    ├── seed_evolutions.py                    # Popula pokemon_evolutions (3º)
    ├── seed_stats.py                         # Popula base stats em pokemon_species via PokéAPI (4º)
    ├── seed_shop_items.py                    # Popula/atualiza nomes e descrições de shop_items via PokéAPI
    ├── seed_regional_species.py              # Popula pokemon_species + moves para as 42 formas regionais
    ├── seed_pokemon_instances.py             # Semeia IV/EV/Nature para todos os user_pokemon; recalcula stat_* (idempotente)
    ├── seed_species_abilities.py             # Popula abilities em pokemon_species via PokéAPI (Release 3A)
    ├── audit_team_stats.py                   # Audita e sincroniza stat_* da equipe ativa (--dry-run / --user-id)
    ├── retroactive_loot.py                   # Concede loot boxes retroativos a usuários existentes
    ├── migrate_drop_regional_catalog.sql     # Remove pokemon_regional_forms e user_pokemon_forms (executar no Supabase)
    ├── migrate_battles.sql                   # Cria user_battles e user_battle_turns (executar no Supabase)
    ├── migrate_regional_forms.sql            # Migração auxiliar de formas regionais (executar no Supabase)
    ├── migrate_v2.sql                        # Migrações v2 diversas (executar no Supabase)
    ├── migrate_consolidate_profiles.sql      # Retarget workout_logs FK → user_profiles; remove tabela profiles legada
    ├── migrate_achievements.sql              # Cria user_achievements (executar no Supabase)
    ├── seed_regional_forms.py                # Seed alternativo de formas regionais (deprecado — usar seed_regional_species.py)
    ├── update_sprites.py                     # Substitui URLs da PokéAPI por caminhos locais (espécies normais)
    ├── update_regional_sprites.py            # Substitui URLs de sprites para formas regionais via CDN HybridShivam
    └── create_user_tables.sql                # DDL completo das tabelas de usuário — executar no Supabase
```

> `src/Pokemon/` é um **submódulo git** apontando para `HybridShivam/Pokemon`. Em produção (Streamlit Cloud) o submódulo não é clonado — `get_image_as_base64()` faz fallback automático para o CDN público do repositório.

---

## Schema do Banco de Dados

### Tabelas de catálogo (somente leitura pelo app)

#### `pokemon_types`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID da PokéAPI (1–19, ignora ≥10000) |
| name | TEXT | Nome capitalizado ("Fire") |
| slug | TEXT | Slug da API ("fire") |

#### `pokemon_species`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID Nacional do Pokédex (1–1025) para espécies normais; ID PokéAPI da forma (>10000) para formas regionais |
| name | TEXT | Nome capitalizado |
| slug | TEXT | Slug da API |
| type1_id / type2_id | INT FK | FK → pokemon_types (type2 nullable) |
| base_experience | INT | XP base |
| sprite_url | TEXT | Caminho local `src/Pokemon/assets/images/XXXX.png` para espécies normais (id ≤ 1025); URL HybridShivam CDN `assets/images/{NNNN}-{Region}.png` para formas regionais (id > 10000) |
| sprite_shiny_url | TEXT | URL PokéAPI (shiny) |
| base_hp/attack/defense/sp_attack/sp_defense/speed | SMALLINT | Base stats — populados por `seed_stats.py` (normais) ou `seed_regional_species.py` (regionais) |

> **Formas regionais (id > 10000):** 42 formas (16 Alola, 15 Galar, 10 Hisui + 1 extra) registradas como espécies plenas. Sprites: HybridShivam CDN — `assets/images/{NNNN}-{Region}.png` (ex: `0026-Alola.png`). Adquiridas pelas mesmas mecânicas de qualquer Pokémon: spawn em check-in, captura via Pokédex. Não há item de loja nem evolução por item para formas regionais.

#### `pokemon_moves`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | ID da PokéAPI (≤10000) |
| name | TEXT | Nome formatado |
| slug | TEXT | Slug da API |
| type_id | INT FK | FK → pokemon_types |
| power / accuracy / pp | INT | Atributos do golpe (nullable) |
| damage_class | TEXT | "physical", "special" ou "status" |

#### `pokemon_species_moves`
| Coluna | Tipo |
|---|---|
| species_id | INT FK |
| move_id | INT FK |
| learn_method | TEXT | Apenas "level-up" é importado |
| level_learned_at | INT |

> Constraint UNIQUE: `(species_id, move_id, learn_method)`

#### `pokemon_evolutions`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | `(from_id * 1000) + to_id` |
| from_species_id | INT FK | Pré-evolução |
| to_species_id | INT FK | Pós-evolução |
| min_level | INT | Nível mínimo (nullable) |
| trigger_name | TEXT | "level-up", "use-item", etc. |
| item_name | TEXT | Slug do item quando trigger = "use-item" (ex: "fire-stone") |

#### `shop_items`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| slug | TEXT UNIQUE | Identificador canônico (ex: "fire-stone", "hp-up") |
| name | TEXT | Nome exibido |
| description | TEXT | Descrição do efeito |
| icon | TEXT | Emoji |
| category | TEXT | "stone", "stat_boost", "other" |
| price | INT | Preço em moedas |
| effect_stat | TEXT | Para stat_boost: 'hp', 'attack', etc. (nullable) |
| effect_value | INT | Valor do boost para stat_boost (nullable) |

#### `muscle_groups`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | |
| name | TEXT | Nome do grupo muscular |

#### `exercises`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INT PK | |
| name | TEXT | Nome em inglês |
| name_pt | TEXT | Nome em português |
| target_muscles | TEXT[] | Músculos alvo |
| body_parts | TEXT[] | Partes do corpo (usadas para mapeamento de tipo Pokémon) |
| equipments | TEXT[] | Equipamentos necessários |
| gif_url | TEXT | URL do GIF demonstrativo |

#### `workout_sheets`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK | FK → user_profiles.id |
| name | TEXT | Nome do plano |

#### `workout_days`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID PK | |
| workout_sheet_id | UUID FK | |
| name | TEXT | Nome do dia (ex: "Peito e Tríceps") |

#### `workout_day_exercises`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID PK | |
| workout_day_id | UUID FK | |
| exercise_id | INT FK | |
| sets | INT | |
| reps | INT | |

---

### Tabelas de usuário (leitura e escrita)

#### `user_profiles`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID PK | Referência a `auth.users` |
| username | TEXT | Nome do treinador |
| coins | INT | Moedas acumuladas |
| starter_pokemon_id | INT FK | Pokémon inicial escolhido |
| xp_share_expires_at | TIMESTAMPTZ | Data/hora de expiração do XP Share ativo (nullable) |

#### `user_pokemon`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | |
| species_id | INT FK | Espécie atual (muda na evolução) |
| level | INT | Começa em 1 |
| xp | INT | XP acumulado dentro do nível atual |
| is_shiny | BOOL | |
| stat_hp/attack/defense/sp_attack/sp_defense/speed | SMALLINT | Stats efetivos — calculados pela fórmula padrão Pokémon (base + IV + EV + nature + vitaminas) |
| iv_hp/attack/defense/sp_attack/sp_defense/speed | SMALLINT | IVs individuais 0–31, gerados aleatoriamente na captura |
| ev_hp/attack/defense/sp_attack/sp_defense/speed | SMALLINT | EVs individuais 0–252 (total ≤ 510), gerados aleatoriamente na captura |
| nature | TEXT | Natureza (uma das 25 padrão), gerada aleatoriamente na captura |

> **Fórmula de stat:** `((2×base + iv + ev//4) × level) // 100 + 5` para não-HP; `+ level + 10` para HP; multiplicado pelo modificador de nature (+10%/−10%) quando aplicável.
> **Pokémon no banco:** `user_pokemon` que não aparecem em `user_team` = banco/depósito. Nunca deletar `user_pokemon` diretamente — apenas remover de `user_team`.

#### `user_team`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_id | UUID FK | |
| slot | INT | 1–6 (slot 1 = principal) |
| user_pokemon_id | INT FK | FK → user_pokemon |

> PK: `(user_id, slot)`. Máximo de 6 Pokémon.

#### `user_pokemon_moves`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_pokemon_id | INT FK | CASCADE DELETE |
| slot | INT | 1–4 |
| move_id | INT FK | |

> PK: `(user_pokemon_id, slot)`. Só moves com `level_learned_at <= level` podem ser equipados.

#### `user_pokemon_stat_boosts`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_pokemon_id | INT FK | CASCADE DELETE |
| stat | TEXT | 'hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed' |
| delta | SMALLINT | Valor aplicado |
| source_item | TEXT | Slug do item causador |
| applied_at | TIMESTAMPTZ | |

> Tabela de auditoria. O valor efetivo está em `user_pokemon.stat_*`. Consultada por `_recalc_stats_on_evolution()` para preservar boosts ao evoluir.

#### `user_inventory`
| Coluna | Tipo | Descrição |
|---|---|---|
| user_id | UUID FK | |
| item_id | INT FK | FK → shop_items |
| quantity | INT | |

> PK: `(user_id, item_id)`.

#### `user_checkins`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | |
| checked_date | DATE | Data do check-in (UNIQUE por usuário) |
| streak | INT | Streak consecutivo no momento do check-in |
| coins_earned | INT | Moedas ganhas (normalmente 1) |
| bonus_item_id | INT FK | FK → shop_items (nullable) — item bônus nos dias 15 e último do mês |
| spawned_species_id | INT FK | Pokémon que apareceu neste check-in (nullable) |

> **Atenção:** nome da tabela é `user_checkins` (não `user_daily_checkins`) e a coluna de data é `checked_date` (não `checked_at`). O item bônus é FK para `shop_items` (int), não slug texto.

#### `user_battles`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| challenger_id | UUID FK | Usuário que iniciou a batalha |
| opponent_id | UUID FK | Usuário desafiado |
| challenger_pokemon_id | INT FK | user_pokemon do desafiante (slot 1 no momento) |
| opponent_pokemon_id | INT FK | user_pokemon do oponente (slot 1 no momento) |
| winner_id | UUID FK | nullable — NULL = empate |
| result | TEXT | 'challenger_win', 'opponent_win', 'draw' |
| challenger_xp_earned / opponent_xp_earned | INT | XP ganho por cada lado |
| coins_earned | INT | Moedas ganhas pelo vencedor |
| turn_count | INT | Número de turnos da batalha |
| battled_at | TIMESTAMPTZ | |

#### `user_battle_turns`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| battle_id | INT FK | CASCADE DELETE |
| turn_number | INT | |
| attacker_pokemon_id | INT FK | user_pokemon que atacou |
| move_name / move_power | TEXT/INT | Move usado |
| damage | INT | Dano causado |
| challenger_hp_remaining / opponent_hp_remaining | INT | HP após o turno |

#### `workout_logs`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | FK → user_profiles.id (ON DELETE CASCADE) |
| day_id | UUID FK | FK → workout_days (nullable — NULL = treino livre) |
| xp_earned | INT | XP concedido ao Pokémon do slot 1 nesta sessão |
| spawned_species_id | INT FK | Pokémon spawnado nesta sessão (nullable) |
| duration_minutes | INT | Duração da sessão em minutos (nullable) |
| completed_at | TIMESTAMPTZ | Timestamp de conclusão (coluna é `completed_at`, não `logged_at`) |

#### `exercise_logs`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| workout_log_id | INT FK | CASCADE DELETE |
| exercise_id | INT FK | |
| sets_data | JSONB | `[{"reps": int, "weight": float}]` |
| notes | TEXT | Anotação livre (nullable) |

---

## Funções de `utils/db.py`

### Conexão
| Função | Descrição |
|---|---|
| `_db_params()` | Lê credenciais: `st.secrets["database"]` primeiro, fallback para `.env` |
| `get_connection()` | Retorna conexão psycopg2 por sessão (`st.session_state._db_conn`); reconecta se fechada ou em estado de erro |
| `get_image_as_base64(path)` | Converte imagem local para base64; aceita URLs HTTP; **fallback automático para CDN HybridShivam/Pokemon** quando arquivo não encontrado localmente |
| `_today_brt()` | Retorna `datetime.date` de hoje no fuso BRT (UTC-3) |

### Catálogo Pokémon
| Função | Descrição |
|---|---|
| `get_all_pokemon()` | `[(id, name)]` — para selectbox |
| `get_all_pokemon_with_types()` | `[{id, name, sprite_url, type1, type1_slug, type2, type2_slug}]` — cacheado |
| `get_pokemon_details(id)` | Tupla com 13 campos: `(id, name, sprite_url, sprite_shiny_url, type1, type2, base_xp, base_hp, base_atk, base_def, base_spa, base_spd, base_spe)` |
| `get_pokemon_moves(id)` | Moveset level-up ordenado por nível |
| `get_full_evolution_chain(id)` | CTE recursiva — retorna toda a família independente do membro selecionado |

### Usuário / perfil
| Função | Descrição |
|---|---|
| `get_user_profile(user_id)` | `{id, username, coins, starter_pokemon_id}` |
| `get_user_pokemon_ids(user_id)` | `set[species_id]` — IDs de espécies que o usuário possui |
| `create_user_profile(user_id, username, starter_id)` | Cria perfil + user_pokemon + slot 1 da equipe, copiando base stats |
| `capture_pokemon(user_id, species_id)` | Adiciona Pokémon à coleção; insere na equipe se < 6 slots |

### Equipe e banco
| Função | Descrição |
|---|---|
| `get_user_team(user_id)` | Lista de dicts com todos os dados do slot: stat_*, base_*, level, xp, tipos |
| `get_user_bench(user_id)` | Pokémon do usuário fora da equipe ativa, ordenados por level desc |
| `add_to_team(user_id, user_pokemon_id)` | Adiciona ao primeiro slot livre; retorna `(bool, msg)` |
| `remove_from_team(user_id, slot)` | Remove da `user_team` (NÃO deleta `user_pokemon`) |
| `swap_team_slots(user_id, slot_a, slot_b)` | Troca dois slots via slot temporário 99 |
| `set_team_slot(user_id, slot, user_pokemon_id)` | Upsert direto em um slot |

### Movimentos
| Função | Descrição |
|---|---|
| `get_available_moves(species_id, level)` | Moves aprendíveis até o nível informado |
| `get_active_moves(user_pokemon_id)` | Moves equipados (slots 1–4) |
| `equip_move(user_pokemon_id, slot, move_id)` | Upsert em user_pokemon_moves |
| `unequip_move(user_pokemon_id, slot)` | Remove do slot |

### Stats, IVs/EVs/Nature e boosts
| Função | Descrição |
|---|---|
| `apply_stat_boost(user_pokemon_id, stat, delta, source_item)` | INSERT em stat_boosts + UPDATE stat_* atomicamente; valida `stat` contra whitelist `_VALID_STATS`; retorna `False` silenciosamente se o cap de `_MAX_STAT_BOOSTS_PER_STAT = 5` for atingido |
| `get_stat_boosts(user_pokemon_id)` | Histórico completo |
| `get_stat_boost_summary(user_pokemon_id)` | `{stat: total_delta}` |
| `_recalc_stats_on_evolution(cur, user_pokemon_id)` | **Interno.** Força recálculo completo usando `_sync_user_pokemon_stats()` após evolução |
| `_stored_user_pokemon_stats(cur, user_pokemon_id)` | **Interno.** Retorna `list[int]` com os seis stat_* armazenados |
| `_expected_user_pokemon_stats(cur, user_pokemon_id)` | **Interno.** Calcula os seis stats esperados pela fórmula (base + IV + EV + nature + boosts) |
| `_sync_user_pokemon_stats(cur, user_pokemon_id)` | **Interno.** Compara stored vs. expected; atualiza banco se divergirem; retorna `bool` |

**Constantes de stats:**
- `_STAT_ORDER = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")`
- `_GENETIC_COLUMNS` — nomes das 13 colunas de IV/EV/nature em `user_pokemon`
- `_ALL_NATURES` — 25 naturezas padrão Pokémon
- `_NATURE_EFFECTS` — dict `{slug: (boosted_stat, nerfed_stat)}` para as 20 naturezas não-neutras

> **Cap de vitaminas:** `_MAX_STAT_BOOSTS_PER_STAT = 5` — máximo 5 usos de vitaminas por stat por Pokémon. `use_stat_item()` retorna mensagem de erro em português se o limite for atingido; `apply_stat_boost()` retorna `False` na mesma condição.

### XP, XP Share e evolução automática
| Função | Descrição |
|---|---|
| `award_xp(user_pokemon_id, amount, source, _distributing=False)` | **Ponto de integração com o módulo de treinos.** Concede XP, processa loop de level-up (fórmula: `level × 100`), detecta evoluções por nível (até 3 por chamada), recalcula stats. Se XP Share ativo e `_distributing=False`, distribui 30% do XP para os demais Pokémon da equipe via `_distribute_xp_share()`. Retorna `{levels_gained, old_level, new_level, new_xp, evolutions, xp_share_distributed, error}` |
| `get_xp_share_status(user_id)` | Retorna `{"active": bool, "expires_at": datetime \| None, "days_left": int}` — consultado por equipe.py e loja.py |
| `_extend_xp_share(cur, user_id)` | **Interno.** Estende `xp_share_expires_at` em +15 dias (GREATEST para não perder tempo restante); chamado por `do_checkin()` nos dias bônus |
| `_distribute_xp_share(user_id, main_pokemon_id, amount, source)` | **Interno.** Distribui 30% do XP para todos os Pokémon da equipe exceto o principal; usa `_distributing=True` para evitar recursão. Retorna `list[{name, xp, user_pokemon_id}]` para log de distribuição |
| `get_stone_targets(user_id, stone_slug)` | Pokémon do usuário elegíveis para evoluir com a pedra; inclui flag `in_team` |
| `evolve_with_stone(user_id, item_id, user_pokemon_id)` | Valida posse da pedra (categoria `stone`) e do Pokémon, executa evolução permanente, debita inventário, recalcula stats. Retorna `(bool, msg, evo_data)` |

### Batalhas PvP
| Função | Descrição |
|---|---|
| `get_battle_opponents(user_id)` | Lista outros usuários com slot 1 preenchido: `[{username, user_id, level, pokemon_name, sprite_url}]` |
| `get_daily_battle_count(user_id)` | Contagem de batalhas como desafiante hoje (máx `_MAX_BATTLES_PER_DAY = 3`) |
| `start_battle(challenger_id, opponent_id)` | Verifica limite diário, carrega Pokémon slot-1 de ambos e retorna estado inicial `{ch, op, turns, finished, result, winner_id, ...}` — **não persiste nada no banco** |
| `finalize_battle(state)` | Recebe o state de `start_battle` (com turns preenchidos), persiste batalha e turnos no banco, concede XP e moedas. Retorna dict com `turns`, `result`, `challenger`, `opponent`, `coins_earned` |
| `get_battle_history(user_id, limit=20)` | Últimas batalhas em que o usuário participou (desafiante ou oponente) |
| `get_battle_detail(battle_id)` | Todos os turnos de uma batalha específica |

**Constantes de batalha:**
- `_MAX_BATTLES_PER_DAY = 3`
- HP de batalha = `stat_hp + level * 2` (não afeta banco permanentemente)
- Ordem: maior `stat_speed` ataca primeiro; empate = aleatório
- Dano: `(atk / def) * power * random(0.85, 1.0) * (level / 20)`, mínimo 1
- Moves físicos usam `attack/defense`; especiais usam `sp_attack/sp_defense`; status = pulado
- Sem move equipado: usa "Investida" (power 40, físico)
- Máx 50 turnos — depois empate
- Vitória: +1 moeda, +30 XP; Derrota: +10 XP

### Loja e inventário
| Função | Descrição |
|---|---|
| `get_shop_items()` | Catálogo completo — cacheado (`@st.cache_data`) |
| `get_user_inventory(user_id)` | `{item_id: qty}` |
| `buy_item(user_id, item_id)` | Debita moedas (FOR UPDATE) + incrementa inventário; retorna `(bool, msg)`; bloqueia slug `loot-box` |
| `use_stat_item(user_id, item_id, user_pokemon_id)` | Debita inventário + aplica boost via `apply_stat_boost` |
| `use_nature_mint(user_id, item_id, user_pokemon_id, new_nature)` | Troca natureza do Pokémon; valida `new_nature` contra `_ALL_NATURES`; recalcula stats; retorna `(bool, msg)` |
| `open_loot_box(user_id, item_id)` | Consome 1 Loot Box do inventário; sorteia prêmio via `_roll_loot_box()`; aplica moedas/itens na transação; aplica XP pós-commit via `award_xp()`; retorna `(bool, msg, loot_dict)` |
| `use_xp_share_item(user_id, item_id)` | Ativa/estende XP Share via item da mochila (alternativa ao fluxo de compra) |

### Calendário e check-in
| Função | Descrição |
|---|---|
| `get_monthly_checkins(user_id, year, month)` | `{day: {streak, coins, bonus_item_id, spawned_species_id}}` |
| `get_checkin_streak(user_id)` | Streak atual de dias consecutivos |
| `do_checkin(user_id)` | Transação atômica: +1 moeda + streak + extensão de XP Share (+15 dias) nos dias 15/último + spawn (nível 5) com 25% de chance em streaks múltiplos de 3. Após commit, chama `award_xp(slot1_id, 10, "check-in")`. Retorna `{"success", "already_done", "streak", "coins_earned", "bonus_xp_share", "spawn_rolled", "spawned", "xp_result", "error"}` |

### Leaderboard
| Função | Descrição |
|---|---|
| `get_leaderboard_pokemon_count(limit=20)` | Ranking all-time por total de Pokémon capturados |
| `get_leaderboard_checkin_streak(year, month, limit=20)` | Ranking mensal por melhor streak de check-in |
| `get_leaderboard_workout_xp(year, month, limit=20)` | Ranking mensal por XP de treino acumulado |

Todas retornam `list[dict]` com chaves `user_id, username, value, lead_pokemon, lead_sprite, lead_level`. Em caso de erro retornam `[]`.

### Exercícios e treino
| Função | Descrição |
|---|---|
| `get_exercises(body_part=None)` | Lista completa de exercícios do catálogo; `body_part` filtra por parte do corpo (cacheado 3600s) |
| `get_muscle_groups()` | Lista de grupos musculares `[{id, name}]` |
| `get_distinct_body_parts()` | Lista de partes do corpo únicas extraídas de `exercises.body_parts` (cacheado 3600s) |
| `get_workout_sheets(user_id)` | Rotinas do usuário `[{id, name, day_count}]` |
| `create_workout_sheet(user_id, name)` | Cria nova rotina; retorna UUID |
| `delete_workout_sheet(sheet_id)` | Deleta rotina e todos os dias/exercícios em cascata via FK |
| `get_sheet_days(sheet_id)` | Dias de uma rotina `[{id, name, exercise_count}]` |
| `create_workout_day(sheet_id, name)` | Cria dia dentro de uma rotina; retorna UUID |
| `delete_workout_day(day_id)` | Deleta dia e todos os exercícios em cascata |
| `get_day_exercises_for_builder(day_id)` | Exercícios de um dia para exibição no builder/treino `[{wde_id, exercise_id, name_pt, prescribed_sets, prescribed_reps}]` |
| `add_exercise_to_day(day_id, exercise_id, sets, reps)` | Adiciona exercício prescrito ao dia; retorna UUID |
| `update_day_exercise(wde_id, sets, reps)` | Edita sets/reps de um exercício prescrito |
| `remove_exercise_from_day(wde_id)` | Remove exercício de um dia |
| `get_daily_xp_from_exercise(user_id)` | XP total ganho de treinos hoje (para progress bar de cap) |
| `get_workout_streak(user_id)` | Dias consecutivos com treino registrado |
| `get_workout_history(user_id, limit=10)` | Últimas sessões `[{date, day_name, exercise_count, xp_earned, spawned_species_id}]` |
| `do_exercise_event(user_id, exercises, day_id=None)` | Registra sessão de treino completa: persiste `workout_log` + `exercise_logs`, aplica XP (com efeito de habilidade passiva), detecta PRs, avança/choca ovos, rola spawn, verifica milestones de streak. Retorna `{xp_earned, capped, spawn_rolled, spawned, xp_result, milestone, milestone_xp, streak, prs, hatched_eggs, granted_eggs, error}` |

### Ovos
| Função | Descrição |
|---|---|
| `get_user_eggs(user_id)` | Retorna ovos pendentes (não chocados) do usuário, mais antigos primeiro |

### Admin
| Função | Descrição |
|---|---|
| `is_admin(user_id)` | Verifica coluna `is_admin` em `user_profiles`; retorna `bool` |
| `get_all_users(search="")` | Lista todos os usuários com filtro de busca opcional |
| `admin_update_user(target_id, username, coins)` | Edita username e coins |
| `admin_delete_user(acting_admin_id, target_id)` | Deleta conta; proibido auto-deletar |
| `set_admin_role(target_id, is_admin)` | Concede ou revoga papel admin |
| `log_admin_action(admin_id, action, details)` | Registra ação no log de auditoria |
| `get_system_logs(limit=50)` | Últimas entradas do log administrativo |
| `admin_gift_loot_box(admin_id, target_id, count=1)` | Concede `count` loot boxes; retorna `(bool, msg, list[dict])` |
| `admin_create_exercise(name, name_pt, ...)` | Cria exercício no catálogo |
| `get_global_stats()` | Métricas do sistema: total usuários, treinos, batalhas, Pokémon capturados |

---

## Fluxo de Autenticação e Sessão Persistente

```
Navegador abre o app
        │
        ▼
  app.py: cookie "lb_refresh_token" existe?
        ├── SIM → client.auth.refresh_session(token)
        │         └── OK → popula session_state + renova cookie (30 dias)
        │         └── FAIL → apaga cookie → vai para login
        └── NÃO → session_state.user == None → pages/login.py
                          │
                          ├── Login OK → salva cookie "lb_refresh_token"
                          └── Signup OK → idem, se session disponível
```

- **Cookie:** `lb_refresh_token` com validade de 30 dias; rotação automática (Supabase renova o refresh_token a cada uso)
- **Keys do CookieManager:** cada arquivo usa uma key única para evitar `StreamlitDuplicateElementKey`:
  - `app.py` → `key="lb_cookies"`
  - `login.py` → `key="lb_cookies_login"`
  - `equipe.py` → `key="lb_cookies_logout"`
- **Logout:** botão em `equipe.py` → deleta cookie + limpa session_state

---

## Imagens — Resolução em Desenvolvimento vs Produção

`get_image_as_base64(path)` tem três modos:

1. **URL HTTP/HTTPS explícita** → faz GET e retorna base64
2. **Arquivo local encontrado** → lê do disco (dev normal)
3. **Arquivo local não encontrado** → extrai o segmento após `assets/` e busca em:
   `https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/{rel}`

O mesmo fallback funciona para sprites, HQ, thumbnails e ícones de tipo/dano.

Em `pokedex.py`, `_resolve_asset(local_path)` é usada para `st.image()` que recebe diretamente caminho/URL:
```python
def _resolve_asset(local_path: str) -> str:
    if os.path.isfile(local_path):
        return local_path
    # extrai após assets/ e constrói URL do CDN
    ...
```

---

## Páginas do App

### Ordem na navegação (primeira = página inicial)
1. `pages/equipe.py` — Minha Equipe ⚔️
2. `pages/batalha.py` — Arena 🥊
3. `pages/conquistas.py` — Conquistas 🏅
4. `pages/leaderboard.py` — Ranking 🏆
5. `pages/pokedex.py` — Pokédex 📖
6. `pages/pokedex_pessoal.py` — Minha Pokédex 🗂️
7. `pages/loja.py` — Loja 🛒
8. `pages/calendario.py` — Calendário 📅
9. `pages/biblioteca.py` — Biblioteca 📚
10. `pages/rotinas.py` — Rotinas 📋
11. `pages/treino.py` — Treino 🏋️
12. `pages/admin.py` — Admin 🛠️ *(oculto para não-admins)*

### `pages/equipe.py`
- Grade 3×2 de slots com cards: sprite, nome, tipos, nível, XP bar, **6 barras de stats coloridas**
- Cores canônicas: HP=#FF5959, ATK=#F5AC78, DEF=#FAE078, SP.ATK=#9DB7F5, SP.DEF=#A7DB8D, SPD=#FA92B2; barra proporcional ao máximo 255
- **Badge de XP Share:** exibe status do XP Share no topo da página — se ativo, mostra dias restantes (`get_xp_share_status()`)
- Ações por slot: ⚔ Golpes (abre painel) / ↑ Promover para slot 1 / 🗑 Remover (vai para banco)
- **Banco de Pokémon:** seção abaixo da equipe com todos os `user_pokemon` fora de `user_team`; botão "→ Equipe" (desabilitado se equipe cheia 6/6)
- Painel de movimentos: 4 slots ativos (desquipar) + lista de disponíveis com botão equipar/trocar
- Modo substituição: quando 4 slots cheios, clicar em novo move entra em modo replace (borda amarela)
- Banner de evolução: se `st.session_state.team_evo_notice` estiver definido, exibe banner roxo com sprite e nome da evolução (limpo após exibição)
- Banner de Shedinja: se `st.session_state.team_shed_notice` estiver definido, exibe banner verde ("👻 Shedinja capturado!") com sprite e texto "A muda de Nincada ganhou vida" (limpo após exibição); set em `calendario.py` quando mecânica shed dispara no check-in
- **Banner de spawn do treino:** se `st.session_state.team_spawn_notice` estiver definido, exibe sprite e nome do Pokémon que apareceu durante a sessão de exercício (limpo após exibição); set em `treino.py` via `do_exercise_event()` com `source="exercise"`
- Log de XP Share: se `st.session_state.xp_share_log` estiver definido, exibe chips azuis com nome e XP recebido por cada Pokémon da equipe na última distribuição (limpo após exibição); set em `calendario.py` via `xp_result["xp_share_distributed"]` e em `treino.py` via `xp_result["xp_share_distributed"]`
- Logout: sidebar → botão "Sair" (deleta cookie + limpa session_state)

### `pages/pokedex.py`
- Sidebar selectbox com 1.025 Pokémon
- Header com gradiente dinâmico baseado nos tipos
- Layout: info + sprite HQ (via `st.image(_hq_path())`) | move cards com ícone de tipo, classe de dano, power, accuracy
- Base stats com barras visuais
- Cadeia evolutiva completa via CTE recursiva (thumbnails + setas)
- Botão "Capturar" na cadeia evolutiva

### `pages/pokedex_pessoal.py`
- Grade HTML de 1.025 cards com estado: capturado (sprite + borda colorida) vs não capturado (silhueta)
- Filtros: busca por nome/número, multiselect de tipo, radio de status
- Barra de progresso global + chips de progresso por geração
- **Atenção:** sem backslash em f-strings — usar variáveis intermediárias antes de interpolar dicts

### `pages/batalha.py`
- Header com título + contador diário colorido (verde/laranja/vermelho conforme uso)
- Selectbox de oponentes com seu Pokémon slot 1 + botão "⚔️ Batalhar" (desabilitado se limite atingido)
- Resultado: card de vitória/derrota/empate + cards dos dois lutadores com HP bar + log de turnos expansível
- Histórico: últimas batalhas como expanders com log de turnos dentro

### `pages/loja.py`
- Tab **Loja**: grade de itens por categoria (Pedras / Vitaminas / Outros) com preço e indicador de estoque
  - **XP Share tem fluxo especial de compra:** botão "▶ Ativar" quando inativo; botão "✚ +15 dias" quando ativo (mostrando dias restantes via `get_xp_share_status()`)
  - **Loot Box** não aparece na grade de compra (price=1, mas `buy_item()` bloqueia via slug `loot-box`)
- Tab **Mochila**:
  - *Vitaminas:* selectbox de Pokémon da equipe + botão "Usar" → `use_stat_item()`
  - *Pedras:* expander por item → selectbox de Pokémon elegíveis → preview sprite → botão "✨ Usar" → `evolve_with_stone()`; após evolução define `st.session_state.team_evo_notice`
  - *Nature Mint:* selectbox de Pokémon + selectbox de natureza destino → `use_nature_mint()`; exibe preview do modificador de nature antes de confirmar
  - *Loot Box:* botão "🎁 Abrir" → `open_loot_box()`; exibe card com prêmio sorteado e raridade; se for XP, chama `award_xp()` pós-commit
  - *Outros (XP Share):* exibe status de ativação com dias restantes

### `pages/calendario.py`
- Grade mensal HTML (7 colunas) com estados: normal / checado (verde) / bônus (dourado) / spawn (roxo)
- Navegação por mês (sem avançar além do mês atual)
- Streak stats: streak atual, check-ins do mês, moedas totais, dias para próximo spawn
- Resultado do check-in exibe cards encadeados: base (moeda + streak) → XP Share (se dia bônus) → spawn (se rolou) → **XP ganho** → **Level Up** (se subiu) → **Evolução** (se evoluiu)

### `pages/biblioteca.py`
- Grade 4 colunas de todos os exercícios do catálogo (`get_exercises()`)
- Card: GIF thumbnail via `gif_url`, `name_pt`, tags de `body_parts`, badge de tipo Pokémon colorido
- Filtros no topo: busca por nome, multiselect de grupo muscular (de `get_muscle_groups()`), body part (de `get_distinct_body_parts()`), equipamento
- Expander de detalhes: GIF em tamanho completo, músculos alvo completos, explicação da afinidade de tipo (ex.: "Exercícios de peito invocam Pokémon do tipo Lutador")
- Página somente leitura — sem escrita no banco

### `pages/rotinas.py`
- Árvore expansível: Rotina (`workout_sheets`) → Dia (`workout_days`) → Exercícios prescritos (`workout_day_exercises`)
- "Nova Rotina": input de nome → `create_workout_sheet()` → expande automaticamente
- "Adicionar Dia": input de nome dentro da rotina → `create_workout_day()`
- "Adicionar Exercício": selectbox com busca na biblioteca + number inputs de sets/reps → `add_exercise_to_day()`
- Edição inline de sets/reps → `update_day_exercise()`
- Deletar exercício/dia/rotina com confirmação (cascata via FK no banco) → funções `delete_*` e `remove_exercise_from_day()`
- Sets/reps aqui são **prescrição padrão** para o Import Default; não são valores de log real

### `pages/treino.py`
- Date picker (padrão = hoje) + seleção de Rotina e Dia (via `get_sheet_days()`)
- Botão "⬇ Importar Padrão": chama `get_day_exercises_for_builder(day_id)` e popula tabela editável
- Tabela de exercícios editável: cada linha tem nome, sets, reps, peso (kg); botão de remoção por linha; botão de adição de linha nova
- Sessão livre: quando sem rotina selecionada, exibe apenas a tabela vazia para preenchimento manual
- "✅ Registrar Treino": chama `do_exercise_event(user_id, exercises, day_id)`, exibe card de resultado (XP ganho, cap indicator, spawn se rolou, level-up se subiu, milestones de streak)
- Progress bar de cap diário: XP hoje / 300 — via `get_daily_xp_from_exercise()`; laranja > 200 XP, vermelho quando capped
- Streak de treino no topo (independente do streak de check-in), via `get_workout_streak()`
- Histórico: últimos 7 dias em tabela (`get_workout_history()`) com badge 🌟 se houve spawn
- Após resultado: define `st.session_state.team_evo_notice` (evolução), `st.session_state.team_shed_notice` (Shedinja), `st.session_state.team_spawn_notice` (spawn), `st.session_state.xp_share_log` se aplicável

### `pages/leaderboard.py`
- Header com título + navegação mensal (◀/▶) para meses anteriores
- 3 tabs: **XP de Treino** (mensal), **Streak de Check-in** (melhor streak do mês), **Coleção Pokémon** (all-time)
- Card de linha por usuário: posição (🥇/🥈/🥉/número), sprite do Pokémon slot 1, username, nível/nome do Pokémon líder, valor da métrica
- Badge "Você" verde-limão na linha do usuário logado (classe `is-me` com borda e fundo diferenciados)
- Sem dados → mensagem `lb-empty` estilizada

### `pages/login.py`
- Tabs "Entrar" / "Criar conta"
- Após login: `_save_session(session)` persiste `lb_refresh_token` em cookie 30 dias

### `pages/starter.py`
- Grade de 27 iniciais + 2 secretos (Cubone, Mimikyu) via easter egg (7 cliques em área vazia)
- Easter egg usa botão invisível `\u2800` + JS que escuta cliques no `window.parent.document`
- Ao confirmar: `create_user_profile()` → perfil + user_pokemon (stats copiados) + slot 1

### `pages/admin.py`
- Acesso restrito: exibe aviso de "Acesso negado" se `is_admin(user_id)` retornar `False`
- **Tab Visão Geral:** métricas do sistema via `get_global_stats()` (total usuários, treinos, batalhas, Pokémon capturados)
- **Tab Usuários:** campo de busca + tabela de resultados; editar username/coins inline; botão de deletar conta (com confirmação); toggle de papel admin
- **Tab Gift Loot Box:** selectbox de usuário alvo + número de loot boxes → `admin_gift_loot_box()`; exibe confirmação com lista de grants
- **Tab Exercícios:** formulário de criação com todos os campos (`name`, `name_pt`, `body_parts`, `target_muscles`, `equipments`, `gif_url`) → `admin_create_exercise()`
- **Tab Logs:** tabela das últimas ações admin via `get_system_logs()`; inclui timestamp, admin, ação, detalhes

---

## Sistema de XP e Evolução Automática

**Fórmula:** `level × 100` XP necessário para subir de nível (Lv.1→2 = 100 XP, Lv.50→51 = 5.000 XP).

**`award_xp(user_pokemon_id, amount, source, _distributing=False)`:**
1. `FOR UPDATE` no `user_pokemon` para consistência
2. Loop: enquanto `xp >= level * 100` → subtrai, incrementa nível, verifica evolução por nível
3. Para cada nível atingido: busca em `pokemon_evolutions` WHERE `trigger='level-up' AND min_level <= level`
4. **Bypass de triggers não-padrão** (`_BYPASS_LEVEL = 36`): evoluções com `trigger NOT IN ('level-up', 'use-item', 'shed')` — como troca, amizade, etc. — disparam automaticamente no nível 36 como alternativa ao requisito original
5. **Mecânica Shed:** se `trigger='shed'` (Nincada→Shedinja), verifica se a equipe tem espaço livre; se sim, captura um Shedinja diretamente para o próximo slot disponível; o dict de evolução retornado inclui `"shed": True`
6. Se evoluiu: atualiza `species_id` localmente para que o próximo nível use a nova espécie
7. Persiste `level`, `xp`, `species_id` de uma vez
8. Se houve evoluções: `_recalc_stats_on_evolution()` preserva boosts de vitaminas
9. Se XP Share ativo e `_distributing=False`: chama `_distribute_xp_share()` para repassar 30% do XP aos demais membros da equipe; resultado armazenado em `xp_share_distributed`
10. Retorna `{levels_gained, old_level, new_level, new_xp, evolutions, xp_share_distributed, error}`

> O parâmetro `_distributing=True` é interno — evita recursão infinita quando `_distribute_xp_share()` chama `award_xp()` para os outros Pokémon. Nesse caso `xp_share_distributed` é sempre `[]`.

**Integração com treinos via `do_exercise_event()`:** o módulo de exercícios chama `award_xp()` internamente. A entry point pública é:
```python
from utils.db import do_exercise_event
result = do_exercise_event(
    user_id,
    exercises=[{"exercise_id": int, "sets_data": [{"reps": int, "weight": float}], "notes": str | None}],
    day_id=None,   # UUID do workout_day prescrito; None = treino livre
)
# result: {xp_earned, capped, spawn_rolled, spawned, xp_result, error}
```

**`_recalc_stats_on_evolution(cur, user_pokemon_id, new_species_id)`:**
```
stat_* = new_base_* + SUM(delta) FROM user_pokemon_stat_boosts WHERE user_pokemon_id = X
```
Preserva todos os boosts permanentes de vitaminas na forma evoluída.

---

## Sistema de Habilidades Passivas (Release 3A)

### Arquivo: `utils/abilities.py`

Habilidades do Pokémon do **slot 1** têm efeito passivo durante eventos de treino (`do_exercise_event()`). Slugs não reconhecidos são no-op. A whitelist de habilidades suportadas é definida em `WORKOUT_ABILITIES`.

| Ability slug | Efeito |
|---|---|
| `blaze` | +15% XP em sessões com ≥200 XP bruto (via `apply_blaze()`) |
| `synchronize` | Aumenta distribuição do XP Share de 30% → 45% (via `apply_synchronize_multiplier()`) |
| `pickup` | Pequena chance de ganhar item aleatório após o treino |
| `pressure` | Aumenta chance de spawn do tipo mais frequente da sessão |
| `compound-eyes` | Rerola uma tentativa de spawn sem sucesso antes de desistir |

**Helpers públicos:**
- `get_ability_description(ability_slug)` → `str | None` — descrição para exibição na UI
- `is_supported(ability_slug)` → `bool` — True se o slug está na whitelist v1

**Funções internas em `db.py`:**
- `_get_slot1_ability(cur, user_id)` — retorna slug da habilidade do Pokémon do slot 1
- `_ranked_spawn_types(exercises)` — ordena tipos por frequência nos exercícios da sessão
- `_spawn_typed(cur, user_id, type_slug)` — spawn direcionado por tipo
- `_spawn_multi_typed(cur, user_id, types)` — spawn com fallback entre tipos

---

## Sistema de Ovos (Release 3A)

### Banco — `user_eggs`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | → user_profiles.id |
| species_id | INT FK | Espécie que vai chocar (determinada no recebimento) |
| rarity | TEXT | `"common"`, `"uncommon"` ou `"rare"` |
| workouts_to_hatch | INT | Treinos necessários para chocar |
| workouts_done | INT | Treinos concluídos desde o recebimento |
| received_at | TIMESTAMPTZ | |
| hatched_at | TIMESTAMPTZ | NULL enquanto não chocado |

### Milestones de concessão (`_EGG_MILESTONES`)

| Total de treinos | Raridade do ovo |
|---|---|
| 25 | uncommon |
| 50 | rare |
| 100 | rare |

### Treinos para chocar (`_EGG_WORKOUTS_TO_HATCH`)

| Raridade | Treinos para chocar |
|---|---|
| common | 5 |
| uncommon | 8 |
| rare | 12 |

### Funções em `db.py`

| Função | Descrição |
|---|---|
| `get_user_eggs(user_id)` | Retorna todos os ovos não chocados do usuário (`hatched_at IS NULL`) |
| `_grant_eggs_if_milestone(cur, user_id, workout_count)` | Concede 1 ovo se `workout_count` bater exato em milestone; fallback para rarity `common` se sem espécie elegível; retorna `list[dict]` |
| `_advance_and_hatch_eggs(cur, user_id)` | Incrementa `workouts_done` de todos os ovos pendentes; choca os que atingiram `workouts_to_hatch`; captura a espécie e adiciona ao banco/equipe; retorna `list[{species_id, name, sprite_url, type1, rarity}]` |
| `_pick_egg_species(cur, user_id, rarity)` | Escolhe espécie spawnable com `rarity_tier = rarity` que o usuário ainda não possui |

> Ambos `_grant_eggs_if_milestone` e `_advance_and_hatch_eggs` são chamados internamente por `do_exercise_event()` a cada sessão de treino concluída.

---

## Recordes Pessoais (Performance Records)

### Constantes

- `_PR_XP_BONUS = 50` — XP extra por PR detectado
- `_PR_MAX_PER_SESSION = 3` — máximo de bônus de PR por sessão

### Regras de detecção (`_detect_prs`)

Um PR é detectado por exercício quando:
- A maior carga da sessão **supera** o melhor histórico de carga, **ou**
- A carga é igual ao histórico e as repetições máximas nessa carga **superam** o melhor histórico.

### Funções em `db.py`

| Função | Descrição |
|---|---|
| `_get_exercise_bests(cur, user_id, exercise_ids)` | Retorna `{exercise_id: (best_weight, best_reps)}` com o melhor histórico de carga/reps por exercício |
| `_detect_prs(exercises, historical_bests, exercise_names)` | Compara sessão atual vs. histórico; retorna `list[{exercise_id, exercise_name, old_weight, new_weight, new_reps}]` (máx 1 PR por exercício) |

> PRs são calculados e o bônus de XP é aplicado dentro de `do_exercise_event()`.

---

## Painel Administrativo (`pages/admin.py`)

Acesso restrito a usuários com `is_admin(user_id) == True`. Implementado em Release 4.0.

### 5 Tabs

| Tab | Conteúdo |
|---|---|
| Visão Geral | Estatísticas globais via `get_global_stats()` |
| Usuários | Busca, edição de username/coins (`admin_update_user()`), exclusão (`admin_delete_user()`), concessão/revogação de admin (`set_admin_role()`) |
| Gift Loot Box | Envio de loot boxes a usuários via `admin_gift_loot_box()` |
| Exercícios | Criação de exercícios no catálogo via `admin_create_exercise()` |
| Logs | Histórico de ações administrativas via `get_system_logs()` |

### Funções em `db.py`

| Função | Descrição |
|---|---|
| `is_admin(user_id)` | Verifica se `user_profiles.is_admin = TRUE` |
| `get_all_users(search="")` | Lista todos os usuários com filtro opcional de busca |
| `admin_update_user(target_id, username, coins)` | Edita username e coins de um usuário |
| `admin_delete_user(acting_admin_id, target_id)` | Deleta conta (proibido auto-deletar) |
| `set_admin_role(target_id, is_admin)` | Concede ou revoga papel de admin |
| `log_admin_action(admin_id, action, details)` | Registra ação no log de auditoria |
| `get_system_logs(limit=50)` | Retorna últimas entradas do log administrativo |
| `admin_gift_loot_box(admin_id, target_id, count=1)` | Concede `count` loot boxes ao usuário alvo; retorna `(bool, msg, list[dict])` |
| `admin_create_exercise(name, name_pt, ...)` | Cria exercício no catálogo com todos os campos |
| `get_global_stats()` | Métricas do sistema: total de usuários, treinos, batalhas, etc. |

> **Nota:** `is_admin` requer coluna `is_admin BOOLEAN DEFAULT FALSE` em `user_profiles`. Adicionar via migration se necessário.

---

## Loja — Catálogo de Itens

| Categoria (`category`) | Itens | Efeito |
|---|---|---|
| `stone` | 10 pedras de evolução (fire, water, thunder, leaf, moon, sun, shiny, dusk, dawn, ice) | Evolução permanente de espécie via `evolve_with_stone()` |
| `stat_boost` | hp-up, protein, iron, calcium, zinc, carbos | Boost permanente de stat via `use_stat_item()` → `apply_stat_boost()`; cap de 5 usos por stat por Pokémon |
| `other` | xp-share | Ativa/estende XP Share por 15 dias — distribui 30% do XP recebido pelo slot 1 para os demais Pokémon da equipe |
| `other` | loot-box | **Não comprável na loja** (concedida via admin/milestone); aberta na Mochila via `open_loot_box()` — prêmio sorteado na tabela de raridade abaixo |
| `nature_mint` | nature-mint | Troca a natureza de um Pokémon via `use_nature_mint()`; consome 1 item do inventário; pode ser obtida via loot box (5%) |

### Tabela de Raridade — Loot Box (`_roll_loot_box`)

| Probabilidade | Tipo | Prêmio |
|---|---|---|
| 50% | XP (common) | +50 a +150 XP para o Pokémon do slot 1 |
| 30% | Moedas (common) | +50 a +150 moedas |
| 10% | Vitamina (rare) | 1× vitamina aleatória (hp-up / protein / iron / calcium / zinc / carbos) |
| 5% | Nature Mint (rare) | 1× nature-mint |
| 4% | Pedra de evolução (ultra-rare) | 1× pedra aleatória |
| 1% | XP Share (ultra-rare) | 1× xp-share |

---

## Calendário — Regras de Check-in

| Condição | Recompensa |
|---|---|
| Todo check-in | +1 moeda |
| Dia 15 do mês | Extensão do XP Share em +15 dias |
| Último dia do mês | Extensão do XP Share em +15 dias |
| Streak múltiplo de 3 | 25% de chance de spawn de Pokémon nível 5 aleatório não capturado |
| Todo check-in | +10 XP para o Pokémon do slot 1 (via `award_xp`) |

---

## Convenções de Código

- Nomes de arquivo de sprite: `XXXX.png` zero-padded 4 dígitos (`0001.png`, `0025.png`) — apenas para espécies normais (id ≤ 1025)
- `sprite_url` no banco: `src/Pokemon/assets/images/XXXX.png` para espécies normais; URL direta do CDN PokéAPI para formas regionais (id > 10000)
- Renderização de sprite regional: `_thumb()` retorna `None` para IDs > 10000 (sem arquivo local); fallback: `get_image_as_base64(member["sprite_url"])` que faz HTTP GET no CDN HybridShivam
- Imagens HQ: trocar `/images/` por `/imagesHQ/` no caminho; usar `_resolve_asset()` para garantir fallback CDN
- Queries SQL com parâmetros: sempre `%s` (psycopg2) — **nunca f-strings com valores do usuário**
- Cores de tipo: `utils/type_colors.py` → `get_type_color(slug)` retorna `{bg, light, dark, text}`
- **Sem backslash em f-strings** (`c[\"key\"]` é SyntaxError no parser do Streamlit Cloud) — extrair para variável antes: `bg = c["bg"]`
- `@st.cache_data` nos getters de catálogo (shop_items, all_pokemon) — não usar em queries de usuário
- Stat whitelist (`_VALID_STATS`) em `db.py` — obrigatório validar antes de interpolar nome de coluna

---

## Deploy — Streamlit Community Cloud

URL do app: configurada no Streamlit Cloud após o deploy de `shiruikhan/LimitBreak`.

1. Acessar [share.streamlit.io](https://share.streamlit.io)
2. New app → repo `shiruikhan/LimitBreak`, branch `master`, main file `app.py`
3. Advanced settings → Secrets → colar conteúdo do `secrets.toml`
4. Deploy → ~2 min para ficar online

Deploys automáticos a cada push no branch `master`.

---

## Scripts de Seed — Ordem de Execução

```bash
python scripts/seed_types.py          # 1. pokemon_types
python scripts/seed_pokedex.py        # 2. pokemon_moves + pokemon_species + species_moves
python scripts/seed_evolutions.py     # 3. pokemon_evolutions
python scripts/seed_stats.py          # 4. base_hp/attack/... em pokemon_species (~5 min, processa só NULL)
# seed_shop_items.py: executar após popular shop_items com SQL inicial
python scripts/seed_shop_items.py     # Atualiza name/description via PokéAPI (idempotente)
# update_sprites.py: opcional — substitui URLs PokéAPI por caminhos locais no banco

# ── Formas regionais (executar após os passos acima) ───────────────────────
python scripts/seed_regional_species.py  # pokemon_species + moves para as 42 formas regionais (~10 min)
```

`create_user_tables.sql`: executar uma única vez no SQL Editor do Supabase antes de usar o app.
`migrate_battles.sql`: executar para criar as tabelas `user_battles` e `user_battle_turns`.
`migrate_regional_forms.sql`: migração auxiliar de formas regionais — executar se necessário.
`migrate_v2.sql`: migrações v2 diversas — executar no Supabase quando necessário.
`migrate_drop_regional_catalog.sql`: executar para remover tabelas obsoletas `pokemon_regional_forms` e `user_pokemon_forms`.
`migrate_consolidate_profiles.sql`: executar para migrar FK de `workout_logs` para `user_profiles` e remover a tabela `profiles` legada.

Todos os scripts são **idempotentes** (upsert com `ON CONFLICT`).

---

## Estado Atual do Projeto (abril 2026)

### Implementado ✅
- Auth completo: login, cadastro, sessão persistente via cookie (30 dias, rotação automática)
- Onboarding: 27 iniciais (Gen 1–9) + easter egg (Cubone, Mimikyu)
- Pokédex nacional: sprites, tipos, moveset, cadeia evolutiva, base stats
- Pokédex pessoal: 1.025 cards com filtros, progresso por geração
- Equipe: 6 slots, moveset equipável (4 por Pokémon), modo substituição, stats visíveis
- Banco de Pokémon: Pokémon fora da equipe ficam no banco; seção na página de equipe com botão para trazer à equipe
- **Stats individuais com IV/EV/Nature:** fórmula padrão Pokémon; gerados aleatoriamente na captura; `seed_pokemon_instances.py` aplica retroativamente; `audit_team_stats.py` detecta divergências
- Sistema de XP e evolução automática: `award_xp()` com distribuição via XP Share
  - **Bypass de triggers não-padrão:** evoluções por troca, amizade, etc. disparam automaticamente no nível 36
  - **Mecânica Shed (Nincada):** ao evoluir para Ninjask, captura Shedinja automaticamente se houver slot livre; exibe banner verde em `equipe.py` e card verde em `calendario.py`
  - **`xp_share_distributed`** em `award_xp` return: lista `[{name, xp, user_pokemon_id}]` com o que cada Pokémon da equipe recebeu; exibido como chips azuis em `equipe.py`
- Evolução por pedra: `evolve_with_stone()` com recálculo de stats e preservação de boosts
- Cap de vitaminas: máximo 5 usos por stat por Pokémon (`_MAX_STAT_BOOSTS_PER_STAT = 5`)
- Loja: pedras de evolução (10), vitaminas (6), XP Share com botão de ativar/renovar; loot box (não-comprável, aberta na mochila); nature mint (troca de natureza); mochila funcional
- **Formas regionais:** 42 formas (16 Alola, 15 Galar, 10 Hisui + 1) como entidades padrão em `pokemon_species` (id > 10000); adquiridas pelas mesmas mecânicas de qualquer Pokémon (spawn, captura); sprites do CDN PokéAPI
- XP Share: distribui 30% do XP do slot 1 para os demais membros da equipe; ativado por check-in ou comprado na loja; badge de status em equipe.py e loja.py
- Calendário: check-in diário, streak, spawns nível 5 em streak ×3, extensão de XP Share nos dias 15/fim-de-mês
- Notificações de evolução: banner em equipe.py + cards em calendario.py
- Deploy em produção: Streamlit Cloud com CDN fallback para imagens
- Batalhas PvP offline: arena com limite de 3/dia, simulação por turnos, XP e moedas como recompensa
- **Conquistas:** 23 badges em 5 categorias; `check_and_award_achievements()` chamado após treino/check-in/batalha; banner de novos badges em `conquistas.py`
- **Leaderboard (`leaderboard.py`):** ranking mensal de XP de treino e streak de check-in; ranking all-time de coleção Pokémon; badge "Você" na linha do usuário logado
- **Phase 2 — Módulo de treinos completo:**
  - Biblioteca de exercícios (`biblioteca.py`): grade 4 colunas, GIF thumbnail, badge de tipo Pokémon, filtros por nome/grupo muscular/equipamento, expander de detalhes
  - Workout Builder (`rotinas.py`): árvore expansível Rotina → Dia → Exercícios, CRUD completo com confirmação de cascata, sets/reps editáveis inline
  - Routine Log (`treino.py`): date picker, Import Default, tabela editável, cap diário 300 XP, streak de treino, histórico 7 dias, milestones de streak (7/30 dias)
  - XP e spawn do treino fluem para `equipe.py` via `team_spawn_notice`, `team_evo_notice`, `team_shed_notice`, `xp_share_log`
  - `workout_logs` usa coluna `completed_at` (não `logged_at`) e tem coluna `duration_minutes`
- **Release 3A — Habilidades, Ovos e Loot Box:**
  - Habilidades passivas: 5 abilities do slot 1 com efeito em treino (blaze, synchronize, pickup, pressure, compound-eyes)
  - Sistema de ovos: concedidos em milestones de treino (25/50/100), chocam após N treinos, espécie determinada por raridade
  - Loot box: sorteio de XP/moedas/vitamina/pedra/mint/xp-share com probabilidades fixas; concedida via admin ou script
  - Nature Mint: troca de natureza de Pokémon via item consumível
  - Recordes Pessoais: detecção automática de PR por exercício com bônus de +50 XP (máx 3/sessão)
  - Spawn aprimorado: tipo-rankeado, multi-typed, shiny-roll por streak
- **Release 4.0 — Painel Admin:**
  - `pages/admin.py` com 5 tabs: Visão Geral, Usuários, Gift Loot Box, Exercícios, Logs
  - Funções admin em `db.py`: `is_admin()`, `get_all_users()`, `admin_update_user()`, `admin_delete_user()`, `set_admin_role()`, `log_admin_action()`, `get_system_logs()`, `admin_gift_loot_box()`, `admin_create_exercise()`, `get_global_stats()`

### A implementar

**Opcional**
- [ ] Formas de Paldea — popular com `seed_regional_species.py`
- [ ] Página de exibição de ovos pendentes para o usuário

---

## Sistema de Conquistas

### Arquivos
- **`utils/achievements.py`** — catálogo (`CATALOG`), `CATEGORY_META`, `badge_url(slug, unlocked)`
- **`pages/conquistas.py`** — página 🏅 Conquistas com badges shields.io
- **`scripts/migrate_achievements.sql`** — cria `user_achievements` (executar no Supabase)

### Banco — `user_achievements`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | → user_profiles.id ON DELETE CASCADE |
| achievement_slug | TEXT | Slug único da conquista |
| unlocked_at | TIMESTAMPTZ | Data/hora de desbloqueio |

> Constraint UNIQUE: `(user_id, achievement_slug)`

### Funções em `utils/db.py`
| Função | Retorno | Descrição |
|---|---|---|
| `get_user_achievements(user_id)` | `dict[slug, datetime]` | Conquistas desbloqueadas |
| `check_and_award_achievements(user_id)` | `list[str]` | Verifica condições, desbloqueia elegíveis, retorna novos slugs |

### Catálogo — 23 conquistas em 5 categorias
| Categoria | Slugs | Métrica verificada |
|---|---|---|
| `treino` | `first_workout`, `workouts_10/50/100`, `workout_streak_7/30` | `workout_count`, `workout_streak` |
| `colecao` | `first_capture`, `dex_10/50/100/200/500`, `dex_complete` | `pokemon_count` em `user_pokemon` |
| `checkin` | `checkin_streak_7/30/100/365` | `MAX(streak)` em `user_checkins` |
| `batalha` | `first_win`, `wins_10/50` | `COUNT` em `user_battles WHERE winner_id` |
| `especial` | `first_evolution`, `shiny_catch`, `regional_form`, `stone_evolution` | flags booleanas derivadas de joins |

### Gatilhos de verificação automática
`check_and_award_achievements(user_id)` é chamado após:
- `do_exercise_event` sem erro em `treino.py`
- `do_checkin` com sucesso em `calendario.py`
- `finalize_battle` em `batalha.py`

Novos slugs → `st.session_state.new_achievements_pending` → banner verde em `conquistas.py`.

### Badges shields.io
`https://img.shields.io/badge/{CATEGORIA}-{Nome}-{color}?style=for-the-badge`  
Cor: da categoria quando desbloqueada, `555555` quando bloqueada.  
Helper: `badge_url(slug, unlocked: bool)` em `utils/achievements.py`.
