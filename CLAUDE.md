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
streamlit>=1.45.0
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
url         = "https://SEU_PROJECT_ID.supabase.co"
anon_key    = "sua_anon_key_aqui"
service_key = "sua_service_role_key"   # necessário apenas para scripts de manutenção

[database]
host     = "aws-X-REGION.pooler.supabase.com"
port     = "6543"
name     = "postgres"
user     = "postgres.SEU_PROJECT_ID"
password = "sua_senha"

[app]
url = "http://localhost:8501"   # Opcional/reservado para futuras integrações; o fluxo atual não consome esta seção
```

### Produção — Streamlit Cloud
Em **App settings → Secrets**, colar o mesmo conteúdo do `secrets.toml`.  
Credenciais disponíveis em: Supabase → **Settings → API** (supabase) e **Settings → Database → Connection pooling** (database).

**Nota:** `_db_params()` em `db.py` tenta `st.secrets["database"]` primeiro; se não existir, cai para `os.getenv()`. Isso garante que ambos os ambientes funcionem sem mudança de código.

---

## Estrutura de Arquivos

```
/
├── app.py                       # Entry point — auth gate, restauração de sessão, shell da UI e navegação agrupada
├── app_pokedex.py               # LEGADO — Pokédex standalone, manter apenas como referência
├── requirements.txt
├── CLAUDE.md                    # Este arquivo
├── pages/
│   ├── login.py                 # Login / Cadastro + salva cookie de sessão
│   ├── starter.py               # Seleção de Pokémon inicial (27 + 2 easter egg)
│   ├── hub.py                   # Hub central com atalhos, snapshot do progresso e navegação rápida
│   ├── equipe.py                # Equipe ativa + banco de Pokémon
│   ├── batalha.py               # Arena PvP — desafiar outros usuários
│   ├── conquistas.py            # Sistema de conquistas — 34 conquistas em 6 categorias
│   ├── leaderboard.py           # Ranking — XP de treino / streak de check-in / coleção Pokémon
│   ├── pokedex.py               # Pokédex nacional completo
│   ├── pokedex_pessoal.py       # Pokédex pessoal — capturados vs não capturados
│   ├── loja.py                  # Loja de itens + tab Mochila inline (usa bag_ui.py)
│   ├── mochila.py               # Mochila standalone — wrapper de bag_ui.render_bag_view()
│   ├── calendario.py            # Check-in diário + calendário mensal
│   ├── missoes.py               # Missões diárias (3) e semanal (1) com coleta de recompensas
│   ├── biblioteca.py            # Biblioteca de exercícios — catálogo Pokédex-style (152 exercícios)
│   ├── rotinas.py               # Workout Builder — criar/editar fichas e dias de treino
│   ├── treino.py                # Routine Log — registro de sessão com Import Default
│   ├── ovos.py                  # Ovos em incubação — grade de ovos pendentes com progresso e spoiler toggle
│   └── admin.py                 # Painel administrativo — restrito a is_admin(); 5 tabs
├── utils/
│   ├── __init__.py
│   ├── type_colors.py           # Paleta de cores dos 18 tipos Pokémon
│   ├── achievements.py          # Catálogo de conquistas (CATALOG, CATEGORY_META, GYM_BADGES, badge_url)
│   ├── abilities.py             # Registro de habilidades passivas de treino (Release 3A)
│   ├── app_cache.py             # Camada de cache compartilhado para leituras repetidas de usuário
│   ├── bag_ui.py                # Componentes reutilizáveis da Mochila — render_bag_view(), render_bag_styles(), etc.
│   ├── missions.py              # Catálogo de missões diárias/semanais (DAILY_POOL, WEEKLY_POOL)
│   ├── quest_tracker.py         # Widget compacto de missões para a sidebar
│   ├── db.py                    # TODAS as queries psycopg2 — ver seção abaixo
│   └── supabase_client.py       # Supabase client (somente Auth) — cacheado com st.cache_resource
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
    ├── retroactive_badges.py                 # Distribui badges de ginásio retroativamente a usuários existentes
    ├── migrate_missions.sql                  # Cria user_missions (executar no Supabase)
    ├── migrate_drop_regional_catalog.sql     # Remove pokemon_regional_forms e user_pokemon_forms (executar no Supabase)
    ├── migrate_battles.sql                   # Cria user_battles e user_battle_turns (executar no Supabase)
    ├── migrate_regional_forms.sql            # Migração auxiliar de formas regionais (executar no Supabase)
    ├── migrate_v2.sql                        # Migrações v2 diversas (executar no Supabase)
    ├── migrate_consolidate_profiles.sql      # Retarget workout_logs FK → user_profiles; remove tabela profiles legada
    ├── migrate_achievements.sql              # Cria user_achievements (executar no Supabase)
    ├── migrate_happiness.sql                 # Adiciona happiness a user_pokemon, min_happiness a pokemon_evolutions, cria user_rest_days
    ├── migrate_spawn_tiers.sql               # Adiciona is_spawnable e rarity_tier a pokemon_species
    ├── migrate_priority1_eggs.sql            # Cria user_eggs (executar no Supabase — Release 3A)
    ├── migrate_priority1_abilities.sql       # Adiciona ability à pokemon_species (executar no Supabase — Release 3A)
    ├── migrate_nature_mint.sql               # Suporte a nature_mint em shop_items/user_inventory
    ├── migrate_rival.sql                     # Adiciona weekly_rival_id e rival_assigned_week a user_profiles
    ├── migrate_weekly_challenge.sql          # Cria weekly_challenges e weekly_challenge_participants
    ├── seed_streak_shield.sql                # Insere item streak-shield em shop_items (executar uma vez)
    ├── migrate_metric_type.sql               # Adiciona metric_type TEXT NOT NULL DEFAULT 'weight' à tabela exercises
    ├── seed_regional_forms.py                # Seed alternativo de formas regionais (deprecado — usar seed_regional_species.py)
    ├── seed_spawn_tiers.py                   # Refina is_spawnable/rarity_tier via PokéAPI (lendários/míticos)
    ├── seed_wmx_exercises.py                 # Cadastra exercícios do protocolo WMX (idempotente por name_pt)
    ├── upload_sprites_to_supabase.py         # Faz upload de sprites locais para Supabase Storage
    ├── update_sprites.py                     # Substitui URLs da PokéAPI por caminhos locais (espécies normais)
    ├── update_regional_sprites.py            # Substitui URLs de sprites para formas regionais via CDN HybridShivam
    ├── migrate_performance_stage3_indexes.sql # Índices da Etapa 3 de performance para workout_logs/exercise_logs/user_battles
    └── create_user_tables.sql                # DDL completo das tabelas de usuário — executar no Supabase
```

> `src/Pokemon/` é um **submódulo git** apontando para `HybridShivam/Pokemon`. Em produção (Streamlit Cloud) o submódulo não é clonado — o app usa `sprite_img_tag()` com `src` direto para URLs remotas e fallback para o CDN público quando o asset local não existe.

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
| is_spawnable | BOOL | `TRUE` por padrão; `FALSE` para lendários/míticos (refinado por `seed_spawn_tiers.py`) |
| rarity_tier | TEXT | `"common"` (base_xp < 100), `"uncommon"` (100–179), `"rare"` (≥ 180); usado em ovos e spawns |

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
| trigger_name | TEXT | "level-up", "use-item", "shed", etc. |
| item_name | TEXT | Slug do item quando trigger = "use-item" (ex: "fire-stone") |
| min_happiness | SMALLINT | Felicidade mínima para evoluções por amizade (normalmente 220); `NULL` para demais triggers |

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
| metric_type | TEXT | `'weight'` (padrão), `'distance'` ou `'time'` — define como a série é registrada e como o XP é calculado |

> **Valores de metric_type:** `weight` → `{reps, weight}`; `distance` → `{distance_m}`; `time` → `{duration_s}`. Adicionado via `migrate_metric_type.sql`.

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
| weekly_rival_id | UUID FK | FK → user_profiles.id — rival atribuído para a semana atual (nullable, ON DELETE SET NULL) |
| rival_assigned_week | DATE | Segunda-feira da semana em que o rival foi atribuído (nullable) |

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
| happiness | SMALLINT | Felicidade 0–255, default 70; afeta XP (≥180 → +5%, <50 → −5%) e evoluções por amizade |

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

#### `user_missions`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | → user_profiles.id ON DELETE CASCADE |
| mission_slug | TEXT | Slug do catálogo (`DAILY_POOL` / `WEEKLY_POOL` em `utils/missions.py`) |
| mission_type | TEXT | `'daily'` ou `'weekly'` |
| period_start | DATE | Para daily: a data do dia; para weekly: a segunda-feira da semana |
| target | INT | Meta de progresso |
| progress | INT | Progresso atual (incrementado por `update_mission_progress()`) |
| completed | BOOL | `TRUE` quando `progress >= target` |
| reward_claimed | BOOL | `TRUE` após `claim_mission_reward()` ser chamado |
| created_at | TIMESTAMPTZ | |

> Constraint UNIQUE: `(user_id, mission_slug, period_start)` — garante uma instância por missão por período.

#### `user_rest_days`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | UUID FK | → user_profiles.id ON DELETE CASCADE |
| rest_date | DATE | Data do descanso registrado |

> Constraint UNIQUE: `(user_id, rest_date)`. Não quebra streak de check-in. Concede +5 happiness ao Pokémon do slot 1.

#### `weekly_challenges`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| week_start | DATE UNIQUE | Segunda-feira da semana do desafio |
| goal_type | TEXT | `'total_xp'`, `'total_workouts'` ou `'total_sets'` |
| goal_value | INT | Meta da comunidade |
| current_value | INT | Progresso atual acumulado |
| reward_item_slug | TEXT | Slug do item de recompensa |
| reward_quantity | INT | Quantidade do item de recompensa |
| completed | BOOL | `TRUE` quando `current_value >= goal_value` |
| reward_distributed | BOOL | `TRUE` após recompensa enviada |

#### `weekly_challenge_participants`
| Coluna | Tipo | Descrição |
|---|---|---|
| challenge_id | INT FK | CASCADE DELETE |
| user_id | UUID FK | ON DELETE CASCADE |
| contributed | INT | Contribuição individual do usuário |
| reward_claimed | BOOL | `TRUE` após `claim_weekly_challenge_reward()` |

> PK: `(challenge_id, user_id)`.

---

## Funções de `utils/db.py`

### Conexão
| Função | Descrição |
|---|---|
| `_db_params()` | Lê credenciais: `st.secrets["database"]` primeiro, fallback para `.env` |
| `get_connection()` | Retorna conexão psycopg2 por sessão (`st.session_state._db_conn`); reconecta se fechada ou em estado de erro |
| `get_image_as_base64(path)` | Converte apenas assets locais para base64; URLs remotas nao passam mais por este helper |
| `sprite_img_tag(sprite_url, width=..., extra_style=...)` | Renderiza sprite com `src` direto para URLs HTTP/S; para caminhos locais tenta CDN HybridShivam antes do fallback em base64 |
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
| `get_team_stat_boost_counts(user_id)` | `{user_pokemon_id: {stat: count}}` — contagem de vitaminas aplicadas por stat para todos os membros da equipe; usada por `equipe.py` para exibir o indicador de cap |
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
| `award_xp(user_pokemon_id, amount, source, _distributing=False)` | **Ponto de integração com o módulo de treinos.** Aplica modificador de happiness ao XP bruto (≥180 → +5%; <50 → −5%). Concede XP, processa loop de level-up (fórmula: `level × 100`), acumula +2 happiness por level-up, detecta evoluções por nível (até 3 por chamada), inclui evoluções por amizade (`min_happiness` atendida), recalcula stats. Se XP Share ativo e `_distributing=False`, distribui 30% do XP para os demais Pokémon da equipe via `_distribute_xp_share()`. Retorna `{levels_gained, old_level, new_level, new_xp, evolutions, xp_share_distributed, error}` |
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
| `get_monthly_checkins(user_id, year, month)` | `{day: {streak, coins, bonus_item, spawned_species_id}}` |
| `get_checkin_streak(user_id)` | Streak atual de dias consecutivos |
| `do_checkin(user_id)` | Transação atômica: +1 moeda + streak + extensão de XP Share (+15 dias) nos dias 15/último + spawn (nível 5) com 25% de chance em streaks múltiplos de 3. Se houver gap de 2 dias e o usuário tiver `streak-shield`, consome 1 item e preserva o streak; nos dias 7 e 21 concede 1 `streak-shield`. Bumps happiness +1 no slot 1. Após commit, chama `award_xp(slot1_id, 10, "check-in")`. Retorna `{"success", "already_done", "streak", "coins_earned", "bonus_xp_share", "spawn_rolled", "spawned", "xp_result", "shield_used", "bonus_shield", "error"}` |
| `register_rest(user_id)` | Registra dia de descanso (INSERT em `user_rest_days`); bumps happiness +5 no slot 1; idempotente por UNIQUE. Retorna `{"success", "already_done", "happiness_gained", "error"}` |
| `get_monthly_rest_days(user_id, year, month)` | `set[int]` — dias do mês em que houve descanso registrado |

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
| `get_exercises(body_part=None)` | Lista completa de exercícios do catálogo; `body_part` filtra por parte do corpo. Para páginas, prefira o wrapper compartilhado em `app_cache.py` |
| `get_muscle_groups()` | Lista de grupos musculares `[{id, name}]` |
| `get_distinct_body_parts()` | Lista de partes do corpo únicas extraídas de `exercises.body_parts` (cacheado 3600s) |
| `get_workout_sheets(user_id)` | Rotinas do usuário `[{id, name, day_count}]` |
| `get_workout_builder_tree(user_id)` | Árvore agregada do builder: rotina + dias + contagem de exercícios + exercícios prescritos em lote |
| `create_workout_sheet(user_id, name)` | Cria nova rotina; retorna `(uuid, error)` |
| `update_workout_sheet(user_id, sheet_id, name)` | Renomeia rotina; retorna `(bool, error_msg \| None)` |
| `delete_workout_sheet(sheet_id)` | Deleta rotina e todos os dias/exercícios em cascata via FK |
| `get_sheet_days(sheet_id)` | Dias de uma rotina `[{id, name, exercise_count}]` |
| `create_workout_day(sheet_id, name)` | Cria dia dentro de uma rotina; retorna UUID |
| `delete_workout_day(day_id)` | Deleta dia e todos os exercícios em cascata |
| `get_day_exercises_for_builder(day_id)` | Exercícios de um dia para exibição no builder/treino `[{id, exercise_id, name, sets, reps, metric_type}]` |
| `add_exercise_to_day(day_id, exercise_id, sets, reps)` | Adiciona exercício prescrito ao dia; retorna UUID |
| `update_day_exercise(wde_id, sets, reps)` | Edita sets/reps de um exercício prescrito |
| `remove_exercise_from_day(wde_id)` | Remove exercício de um dia |
| `get_daily_xp_from_exercise(user_id)` | XP total ganho de treinos hoje (para progress bar de cap) |
| `get_last_exercise_values(user_id, exercise_ids)` | Último valor logado por exercício, usado para pré-preencher o Import Default. Retorna `{exercise_id: {reps, weight, distance_km, duration_min}}` — campos irrelevantes ao `metric_type` do exercício são `None` |
| `get_workout_streak(user_id)` | Dias consecutivos com treino registrado |
| `get_workout_history(user_id, limit=10)` | Últimas sessões `[{date, day_name, exercise_count, xp_earned, spawned_species_id}]` |
| `do_exercise_event(user_id, exercises, day_id=None)` | Registra sessão de treino completa: persiste `workout_log` + `exercise_logs`, aplica XP (com efeito de habilidade passiva), bumps happiness +1 no slot 1, aplica penalidade de inatividade (−5 happiness se ≥7 dias sem treino), detecta PRs, avança/choca ovos, rola spawn, verifica milestones de streak. Retorna `{xp_earned, capped, spawn_rolled, spawned, xp_result, milestone, milestone_xp, streak, prs, hatched_eggs, granted_eggs, error}` |

### Analytics de Treino
| Função | Descrição |
|---|---|
| `get_volume_history(user_id, exercise_id, days=90)` | Volume diário para um exercício num período, adaptado ao `metric_type`: weight=Σ(kg×reps), distance=Σkm, time=Σmin. Retorna `[{date, volume, max_val, total_sets, metric_type, unit}]` ordenado por data |
| `get_exercise_bests_all(user_id)` | Melhor métrica por exercício já logado. Retorna `[{exercise_id, name, metric_type, unit, best_primary, best_secondary}]`. Para weight: `best_primary`=kg, `best_secondary`=reps; para distance/time: `best_primary`=valor, `best_secondary`=`None` |
| `get_muscle_distribution(user_id)` | Sets por parte do corpo na semana atual vs. anterior (BRT). Retorna `{this_week: {body_part: sets}, last_week: {body_part: sets}, this_label, last_label}` |

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
| `get_system_logs(limit=200, action_filter="", user_filter="")` | Últimas entradas do log administrativo (filtrável por ação e usuário) |
| `admin_gift_loot_box(admin_id, target_id, count=1)` | Concede `count` loot boxes; retorna `(bool, msg, list[dict])` |
| `admin_create_exercise(name, name_pt, ...)` | Cria exercício no catálogo |
| `get_global_stats()` | Métricas do sistema: total usuários, treinos, batalhas, Pokémon capturados |

### Missões
| Função | Descrição |
|---|---|
| `get_user_missions(user_id)` | Retorna `{'daily': [...], 'weekly': [...]}` para o período atual; gera missões se ausentes via `_ensure_missions()` |
| `update_mission_progress(user_id, event_type, data=None)` | Incrementa progresso nas missões ativas que correspondem ao `event_type`; retorna lista de missões recém-concluídas. Chamado em `treino.py`, `batalha.py`, `calendario.py` após cada evento |
| `claim_mission_reward(user_id, mission_id)` | Consome a recompensa de uma missão completa; retorna `(bool, msg, reward_dict)`. Tipos de recompensa: `xp`, `coins`, `stone`, `vitamin`, `loot_box` |

### Rival Semanal e Desafio Comunitário
| Função | Descrição |
|---|---|
| `assign_weekly_rival(user_id)` | Atribui (ou mantém) o rival da semana; na virada de semana avalia se o usuário venceu o rival anterior (+10 moedas); retorna `{rival_username, rival_xp, my_xp, diff, rival_sprite, won_last_week, bonus_coins}` |
| `get_rival_status(user_id)` | Leitura leve do confronto atual — sem writes. Retorna `{rival_username, rival_xp, my_xp, diff, rival_sprite}` ou `{}` se sem rival |
| `get_current_challenge(user_id)` | Retorna estado do desafio comunitário desta semana, criando-o se necessário; inclui contribuição e status de coleta do usuário. Retorna `dict` ou `None` |
| `claim_weekly_challenge_reward(user_id)` | Coleta a recompensa do desafio comunitário quando `completed=True`; retorna `(bool, msg, reward_dict)` |
| `_ensure_weekly_challenge(cur)` | **Interno.** Garante que existe um desafio para a semana atual; retorna `challenge_id` |
| `_update_weekly_challenge(cur, user_id, xp_earned, sets_total)` | **Interno.** Atualiza progresso do desafio comunitário após treino |

**Tipos de meta (`goal_type`):** `"total_xp"`, `"total_workouts"`, `"total_sets"` — acumulados por todos os usuários participantes.

**`event_type` e dados esperados:**
- `"workout"` — `{sets_total, max_weight, xp_earned}` → atualiza `register_workout`, `weekly_workout_3`
- `"workout_sets"` — `{sets_total}` → atualiza `log_5_sets`
- `"workout_heavy"` — `{max_weight}` → atualiza `log_heavy_set`
- `"workout_xp"` — `{xp_earned}` → atualiza `weekly_xp_200`
- `"pr"` — `{count}` → atualiza `beat_pr`
- `"battle_win"` — `{}` → atualiza `win_battle`, `weekly_wins_3`
- `"checkin"` — `{}` → atualiza `daily_checkin`, `weekly_checkin_5`

**Geração de períodos:**
- Daily: 3 slugs sorteados de `DAILY_POOL` (6 opções) no primeiro acesso do dia
- Weekly: 1 slug sorteado de `WEEKLY_POOL` (4 opções) na segunda-feira de cada semana

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
                          ├── Email/senha OK → salva cookie "lb_refresh_token"
                          └── Signup OK → idem, se session disponível
```

- **Cookie:** `lb_refresh_token` com validade de 30 dias; rotação automática (Supabase renova o refresh_token a cada uso)
- **Keys do CookieManager:** cada arquivo usa uma key única para evitar `StreamlitDuplicateElementKey`:
  - `app.py` → `key="lb_cookies"` (shell principal + logout do sidebar)
  - `login.py` → `key="lb_cookies_login"` (login e signup)
  - `equipe.py` → `key="lb_cookies_logout"` (botão "Sair" na página de equipe)
- **Logout:** botão "↩ Sair" no sidebar shell em `app.py` (presente em todas as páginas); botão "Sair" também em `equipe.py` — ambos deletam cookie + limpam session_state

---

## Imagens — Resolução em Desenvolvimento vs Produção

`get_image_as_base64(path)` agora é restrito a assets locais:

1. **Arquivo local encontrado** → lê do disco e retorna base64
2. **URL HTTP/HTTPS explícita** → retorna `None`
3. **Arquivo local não encontrado** → retorna `None`

Para renderização normal de sprites e ícones, o padrão atual é `sprite_img_tag()`:

1. **URL HTTP/HTTPS explícita** → usa `src` direto
2. **Arquivo local encontrado** → usa base64 como fallback local
3. **Arquivo local não encontrado com segmento `assets/`** → monta URL no CDN HybridShivam e usa `src` direto

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

### Navegação atual

O app usa `st.navigation(..., position="hidden")` e renderiza uma sidebar customizada em `app.py`.

**Grupos da sidebar (conforme `_build_app_pages()` em `app.py`):**
1. `Hub` → Hub 🏠
2. `Treinador` → Minha Equipe ⚔️, Ovos 🥚, Conquistas 🏅, Missões 🎯
3. `Batalha` → Arena 🥊, Ranking 🏆
4. `Treinos` → Calendário 📅, Treino 🏋️, Rotinas 📋, Biblioteca 📚
5. `Pokédex` → Pokédex 📖, Minha Pokédex 🗂️
6. `Loja` → Loja 🛒, Mochila 🎒
7. `Admin` *(somente se `is_admin(user_id)` for true)* → Admin ⚙️

**Página inicial autenticada:**
- `pages/hub.py` — Hub 🏠

### `pages/hub.py`
- Hero principal com branding do app e atalhos rápidos
- Snapshot com moedas, tamanho da equipe, streak e batalhas restantes no dia
- **Contador de Insígnias de Ginásio:** mini badge rack colorido mostrando "Insígnias: X/8" com os 8 ícones das insígnias Kanto (earned vs. locked), via `GYM_BADGES` de `utils/achievements.py`
- Cards por seção para navegar sem depender da sidebar padrão
- Usa `st.fragment` para isolar blocos de snapshot e navegação rápida

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
- Tab **Mochila**: renderizado por `utils/bag_ui.render_bag_view()` — mesma lógica da página `mochila.py` standalone

### `pages/mochila.py`
- Página standalone da Mochila acessível via sidebar (grupo Loja)
- Thin wrapper: chama `ensure_bag_session_state()`, `render_bag_styles()`, `render_bag_header(show_shop_button=True)`, `render_bag_view(user_id)` de `utils/bag_ui.py`
- Header mostra título "MOCHILA", subtítulo, saldo de moedas e botão "🛒 Ir para Loja"
- Conteúdo: Vitaminas, Nature Mint, Pedras, Loot Boxes, Outros (XP Share) — mesmas seções da tab Mochila em `loja.py`

### `pages/calendario.py`
- Grade mensal HTML (7 colunas) com estados: normal / checado (verde) / bônus (dourado) / spawn (roxo) / **descanso (rosa/vermelho claro)**
- Navegação por mês (sem avançar além do mês atual)
- Streak stats: streak atual, check-ins do mês, moedas totais, dias para próximo spawn
- **Botão "😴 Registrar Descanso":** chama `register_rest(user_id)`; concede +5 happiness ao slot 1; idempotente (desabilitado se já registrado hoje); dias de descanso aparecem no grid com cor própria
- Resultado do check-in exibe cards encadeados: base (moeda + streak) → XP Share (se dia bônus) → spawn (se rolou) → **XP ganho** → **Level Up** (se subiu) → **Evolução** (se evoluiu)

### `pages/biblioteca.py`
- Grade 4 colunas de todos os exercícios do catálogo (`get_exercises()`)
- Card: GIF thumbnail via `gif_url`, `name_pt`, tags de `body_parts`, badge de tipo Pokémon colorido
- Filtros no topo: busca por nome, multiselect de grupo muscular (de `get_muscle_groups()`), body part (de `get_distinct_body_parts()`), equipamento
- Badge de métrica por exercício: 🏋️ Carga / 📏 Distância / ⏱️ Tempo, além do badge de tipo Pokémon existente
- Expander de detalhes: GIF em tamanho completo, músculos alvo completos, explicação da afinidade de tipo (ex.: "Exercícios de peito invocam Pokémon do tipo Lutador")
- Página somente leitura — sem escrita no banco

### `pages/rotinas.py`
- Árvore expansível: Rotina (`workout_sheets`) → Dia (`workout_days`) → Exercícios prescritos (`workout_day_exercises`)
- "Nova Rotina": input de nome → `create_workout_sheet()` → expande automaticamente
- **Edição de nome de rotina:** botão "✏ Editar rotina" abre form inline → `update_workout_sheet()`
- "Adicionar Dia": input de nome dentro da rotina → `create_workout_day()`
- "Adicionar Exercício": selectbox com busca na biblioteca + number inputs de sets/reps (ou km/min dependendo do `metric_type`) → `add_exercise_to_day()`
- Edição inline de sets/reps → `update_day_exercise()`
- Deletar exercício/dia/rotina com confirmação (cascata via FK no banco) → funções `delete_*` e `remove_exercise_from_day()`
- Sets/reps aqui são **prescrição padrão** para o Import Default; não são valores de log real

### `pages/treino.py`
Duas tabs: **🏋️ Treino** e **📊 Análise**.

**Tab Treino:**
- Date picker (padrão = hoje) + seleção de Rotina e Dia usando a árvore agregada cacheada de `get_workout_builder_tree()`
- Botão "⬇ Importar Padrão": reutiliza os exercícios já carregados da árvore agregada + `get_last_exercise_values()` e popula tabela editável com os últimos valores registrados como hint (↩ hint abaixo do nome)
- Tabela de exercícios editável: cada linha tem nome, sets, e uma coluna de medida que varia por `metric_type` (Reps para weight, Distância km para distance, Duração min para time), mais Peso (kg) apenas para weight; botão de remoção por linha; botão de adição de linha nova
- Sessão livre: quando sem rotina selecionada, exibe apenas a tabela vazia para preenchimento manual
- "✅ Registrar Treino": chama `do_exercise_event(user_id, exercises, day_id)`, exibe card de resultado (XP ganho, cap indicator, spawn se rolou, level-up se subiu, milestones de streak)
- Progress bar de cap diário: XP hoje / 300 — via `get_daily_xp_from_exercise()`; laranja > 200 XP, vermelho quando capped
- Streak de treino no topo (independente do streak de check-in), via `get_workout_streak()`
- Histórico: últimos 7 dias em tabela (`get_workout_history()`) com badge 🌟 se houve spawn
- Após resultado: define `st.session_state.team_evo_notice` (evolução), `st.session_state.team_shed_notice` (Shedinja), `st.session_state.team_spawn_notice` (spawn), `st.session_state.xp_share_log` se aplicável

**Tab Análise:**
- **Volume por exercício** (`get_volume_history()`): selectbox de exercício + radio de período (30/60/90/180 dias); `st.line_chart` de volume diário; métricas de pico (max volume, max carga)
- **Distribuição de grupos musculares** (`get_muscle_distribution()`): `st.bar_chart` da semana atual vs. anterior por body part
- **Melhores cargas** (`get_exercise_bests_all()`): lista HTML com best weight + max reps por exercício logado

### `pages/leaderboard.py`
- Header com título + navegação mensal (◀/▶) para meses anteriores
- 3 tabs: **XP de Treino** (mensal), **Streak de Check-in** (melhor streak do mês), **Coleção Pokémon** (all-time)
- Card de linha por usuário: posição (🥇/🥈/🥉/número), sprite do Pokémon slot 1, username, nível/nome do Pokémon líder, valor da métrica
- Badge "Você" verde-limão na linha do usuário logado (classe `is-me` com borda e fundo diferenciados)
- Sem dados → mensagem `lb-empty` estilizada

### `pages/login.py`
- Tabs "Entrar" / "Criar conta"
- Após login email/senha: `_save_session(session)` persiste `lb_refresh_token` em cookie 30 dias
- Signup via `client.auth.sign_up(...)`; se `res.session` existir, persiste o cookie e segue direto para o starter

### `pages/starter.py`
- Grade de 27 iniciais + 2 secretos (Cubone, Mimikyu) via easter egg (7 cliques em área vazia)
- Easter egg usa botão invisível `\u2800` + JS que escuta cliques no `window.parent.document`
- Ao confirmar: `create_user_profile()` → perfil + user_pokemon (stats copiados) + slot 1

### `pages/missoes.py`
- Header "Missões" com subtítulo "Progressão diária"
- Seção **Missões Diárias** (3 cards): cada card mostra ícone + label + barra de progresso (progress/target) + badge de recompensa + botão "Coletar recompensa" (quando `completed=True` e `reward_claimed=False`)
- Seção **Missão Semanal** (1 card): período exibido como "Semana de DD/MM a DD/MM" em `st.caption`
- Ao coletar: chama `claim_mission_reward(user_id, mission_id)`; exibe card de resultado com `_show_claim_result()` (mensagem varia por tipo: xp/coins/stone/vitamin/loot_box)
- Nota de rodapé: "Missões diárias renovam à meia-noite (BRT). Semanal renova toda segunda-feira."
- Estado de missão `completed` exibe badge verde "✅ Completa"; `reward_claimed` exibe badge cinza "✓ Coletada" e opacidade reduzida

### `pages/ovos.py`
- Grade de ovos em incubação via `get_user_eggs(user_id)` — mostra apenas ovos com `hatched_at IS NULL`
- Cards 4 por linha: emoji de raridade (⚪/🔵/🟣), barra de progresso colorida por raridade, contador "N/M treinos", data de recebimento
- Alertas contextuais: "⚡ Falta N treino(s)!" quando `remaining <= 2`; "🔥 Pronto para chocar!" quando `done >= total`
- **Spoiler toggle:** checkbox "Revelar espécie" por ovo — só exibe sprite + nome quando o usuário opta; usa `sprite_img_tag()`
- Estado vazio: card explicativo com milestones (25/50/100 treinos) e botão "🏋️ Ir para Treino"
- Rodapé: atalhos para `treino.py` e `equipe.py`

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
1. `FOR UPDATE` no `user_pokemon` para consistência; lê `happiness`
2. Aplica modificador de felicidade ao XP bruto: happiness ≥ 180 → ×1.05; < 50 → ×0.95
3. Loop: enquanto `xp >= level * 100` → subtrai, incrementa nível, acumula `happiness_delta += 2` por level-up
4. Para cada nível atingido: busca em `pokemon_evolutions` WHERE `trigger='level-up' AND min_level <= level`
5. **Evoluções por amizade:** `trigger='level-up' AND min_happiness IS NOT NULL` — verificadas quando `happiness + happiness_delta >= min_happiness`
6. **Bypass de triggers não-padrão** (`_BYPASS_LEVEL = 36`): evoluções com `trigger NOT IN ('level-up', 'use-item', 'shed')` sem `min_happiness` disparam automaticamente no nível 36
7. **Mecânica Shed:** se `trigger='shed'` (Nincada→Shedinja), verifica se a equipe tem espaço livre; se sim, captura um Shedinja diretamente para o próximo slot disponível; o dict de evolução retornado inclui `"shed": True`
8. Se evoluiu: atualiza `species_id` localmente para que o próximo nível use a nova espécie
9. Persiste `level`, `xp`, `species_id` e `happiness` de uma vez
10. Se houve evoluções: `_recalc_stats_on_evolution()` preserva boosts de vitaminas
11. Se XP Share ativo e `_distributing=False`: chama `_distribute_xp_share()` para repassar 30% do XP aos demais membros da equipe; resultado armazenado em `xp_share_distributed`
12. Retorna `{levels_gained, old_level, new_level, new_xp, evolutions, xp_share_distributed, error}`

> O parâmetro `_distributing=True` é interno — evita recursão infinita quando `_distribute_xp_share()` chama `award_xp()` para os outros Pokémon. Nesse caso `xp_share_distributed` é sempre `[]`.

**Integração com treinos via `do_exercise_event()`:** o módulo de exercícios chama `award_xp()` internamente. A entry point pública é:
```python
from utils.db import do_exercise_event
result = do_exercise_event(
    user_id,
    exercises=[{
        "exercise_id": int,
        # sets_data varia por metric_type:
        #   weight:   [{"reps": int, "weight": float}]
        #   distance: [{"distance_m": float}]
        #   time:     [{"duration_s": int}]
        "sets_data": [...],
        "notes": str | None,
    }],
    day_id=None,   # UUID do workout_day prescrito; None = treino livre
)
# result: {xp_earned, capped, spawn_rolled, spawned, xp_result, milestone, milestone_xp, streak, prs, eggs_hatched, eggs_granted, ability_effects, error}
```

**Fórmula de XP por `metric_type` (`_calc_exercise_xp`):**
- `weight`: `CEIL(reps / 2) + FLOOR(weight_kg / 20)` por set
- `distance`: `FLOOR(distance_m / 100)` por intervalo — 1 XP / 100 m (5 km = 50 XP)
- `time`: `FLOOR(duration_s / 30)` por set — 1 XP / 30 s (10 min = 20 XP)

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
| `other` | streak-shield 🛡️ | **100 moedas.** Protege o streak de check-in por um dia perdido; consumido automaticamente dentro de `do_checkin()` quando detecta gap de 1 dia e o usuário tem o item no inventário |
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
- `sprite_url` no banco: `src/Pokemon/assets/images/XXXX.png` para espécies normais; URL direta do CDN HybridShivam para formas regionais (id > 10000)
- Renderização de sprite regional: o padrão atual é `sprite_img_tag(member["sprite_url"])`, usando `src` direto para CDN/URLs remotas
- Imagens HQ: trocar `/images/` por `/imagesHQ/` no caminho; usar `_resolve_asset()` para garantir fallback CDN
- Queries SQL com parâmetros: sempre `%s` (psycopg2) — **nunca f-strings com valores do usuário**
- Cores de tipo: `utils/type_colors.py` → `get_type_color(slug)` retorna `{bg, light, dark, text}`
- **Sem backslash em f-strings** (`c[\"key\"]` é SyntaxError no parser do Streamlit Cloud) — extrair para variável antes: `bg = c["bg"]`
- Leituras repetidas por usuário agora podem passar por `utils/app_cache.py`, que centraliza `@st.cache_data` para perfil, equipe, inventário, missões, check-ins, batalhas, árvore agregada de treino, catálogos quase estáticos e flags de admin
- `utils/supabase_client.py` usa `@st.cache_resource` para reutilizar o client do Supabase
- Prefira helpers específicos como `clear_profile_cache()`, `clear_workout_cache()` e `clear_inventory_cache()`; `clear_user_cache()` fica reservado para fluxos amplos do mesmo usuário
- Para catálogos quase estáticos, prefira `get_cached_exercises()`, `get_cached_distinct_body_parts()` e `get_cached_shop_items()`; ao alterar o catálogo por admin, use `clear_catalog_cache()`
- Missões atuais devem ser garantidas por `ensure_current_user_missions(user_id)` em ponto controlado do fluxo; `get_user_missions()` e `render_quest_sidebar()` devem permanecer leitura pura
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

`create_user_tables.sql`: executar uma única vez no SQL Editor do Supabase antes de usar o app. Ele cobre a base, mas não todas as adições recentes.
`migrate_battles.sql`: executar para criar as tabelas `user_battles` e `user_battle_turns`.
`migrate_regional_forms.sql`: migração auxiliar de formas regionais — executar se necessário.
`migrate_v2.sql`: migrações v2 diversas — executar no Supabase quando necessário.
`migrate_drop_regional_catalog.sql`: executar para remover tabelas obsoletas `pokemon_regional_forms` e `user_pokemon_forms`.
`migrate_consolidate_profiles.sql`: executar para migrar FK de `workout_logs` para `user_profiles` e remover a tabela `profiles` legada.
`migrate_priority1_eggs.sql`: cria `user_eggs` (Release 3A).
`migrate_priority1_abilities.sql`: adiciona coluna `ability` a `pokemon_species` (Release 3A).
`migrate_nature_mint.sql`: suporte a nature_mint em `shop_items`.
`migrate_rival.sql`: adiciona `weekly_rival_id` e `rival_assigned_week` a `user_profiles`.
`migrate_weekly_challenge.sql`: cria tabelas `weekly_challenges` e `weekly_challenge_participants`.
`seed_streak_shield.sql`: insere item `streak-shield` em `shop_items` (executar uma vez).
`migrate_metric_type.sql`: adiciona coluna `metric_type` à tabela `exercises` (executar uma vez; idempotente via `ADD COLUMN IF NOT EXISTS`).

Para um ambiente novo alinhado ao app atual, aplique pelo menos as migrations/seed acima relacionadas a releases posteriores: `migrate_happiness.sql`, `migrate_rival.sql`, `migrate_weekly_challenge.sql`, `migrate_metric_type.sql` e `seed_streak_shield.sql`.

Todos os scripts são **idempotentes** (upsert com `ON CONFLICT`).

---

## Estado Atual do Projeto (maio 2026)

### Implementado ✅
- Auth completo: login, cadastro e sessão persistente via cookie (30 dias, rotação automática)
- Shell de navegação customizado: sidebar agrupada + hub central (`pages/hub.py`) com snapshot e atalhos
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
- Loja: pedras de evolução (10), vitaminas (6), XP Share com botão de ativar/renovar; **Streak Shield** (🛡️ 100 moedas, protege streak por 1 dia perdido); loot box (não-comprável, aberta na mochila); nature mint (troca de natureza); mochila funcional
- **Formas regionais:** 42 formas (16 Alola, 15 Galar, 10 Hisui + 1) como entidades padrão em `pokemon_species` (id > 10000); adquiridas pelas mesmas mecânicas de qualquer Pokémon (spawn, captura); sprites via CDN HybridShivam
- XP Share: distribui 30% do XP do slot 1 para os demais membros da equipe; ativado por check-in ou comprado na loja; badge de status em equipe.py e loja.py
- Calendário: check-in diário, streak, spawns nível 5 em streak ×3, extensão de XP Share nos dias 15/fim-de-mês
- Notificações de evolução: banner em equipe.py + cards em calendario.py
- Deploy em produção: Streamlit Cloud com CDN fallback para imagens
- Batalhas PvP offline: arena com limite de 3/dia, simulação por turnos, XP e moedas como recompensa
- **Conquistas:** 34 conquistas em 6 categorias; `check_and_award_achievements()` chamado após treino/check-in/batalha; banner de novos badges em `conquistas.py`
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
- **Priority B — Missões Diárias e Semanais:**
  - `utils/missions.py`: catálogo com 6 missões diárias + 4 missões semanais
  - `user_missions` table: progresso por período (daily=data, weekly=segunda-feira da semana)
  - `get_user_missions()`, `update_mission_progress()`, `claim_mission_reward()` em `db.py`
  - `pages/missoes.py`: página com 3 cards diários + 1 card semanal; botão de coleta de recompensa
  - Hooks em `treino.py` (workout + pr), `batalha.py` (battle_win), `calendario.py` (checkin)
  - Recompensas: xp, coins, pedra aleatória, vitamina aleatória, loot box
  - Migration: `scripts/migrate_missions.sql`
- **Refactor UI/UX + Performance (abril 2026):**
  - `app.py` com shell visual unificado e navegação escondida do Streamlit
  - `pages/hub.py` como landing page autenticada
  - `utils/app_cache.py` com cache de leituras de usuário
  - `st.fragment` aplicado em áreas isoladas como hub e calendário
- **Mochila standalone + Ovos:**
  - `utils/bag_ui.py`: componentes reutilizáveis da mochila extraídos de `loja.py`
  - `pages/mochila.py`: página independente da mochila acessível direto pela sidebar (grupo Loja)
  - `pages/ovos.py`: página de ovos em incubação com grade de cards, barra de progresso e spoiler toggle de espécie
- **Release 6 — Felicidade / Amizade:**
  - Coluna `happiness SMALLINT DEFAULT 70` em `user_pokemon`; range 0–255
  - Incrementos: +2/level-up, +1/treino (`do_exercise_event`), +1/check-in, +5/descanso; penalidade −5 por inatividade ≥7 dias
  - Efeito em `award_xp()`: happiness ≥ 180 → +5% XP; < 50 → −5% XP
  - Evoluções por amizade via `min_happiness` em `pokemon_evolutions` (threshold 220)
  - `register_rest(user_id)` + `get_monthly_rest_days()` + tabela `user_rest_days`
  - Botão "😴 Registrar Descanso" em `calendario.py` com estado no grid mensal
  - Migration: `scripts/migrate_happiness.sql`
- **Release 7 — Insígnias de Ginásio:**
  - 8 insígnias Kanto como categoria `"ginasio"` em `utils/achievements.py`
  - `GYM_BADGES` list exportada com slug, name, icon, badge_color
  - Tab "Ginásio" em `pages/conquistas.py` com badge rack visual
  - Contador "Insígnias: X/8" com mini badge rack colorido em `pages/hub.py`
  - `evolved_count` adicionado a `_collect_achievement_stats` em `db.py`
- **Release 8 — Analytics de Treino:**
  - Tab "📊 Análise" em `treino.py` com três seções
  - `get_volume_history()`, `get_exercise_bests_all()`, `get_muscle_distribution()` em `utils/db.py`
  - Dados derivados de `exercise_logs.sets_data` — sem mudança de schema
- **Tipos de métrica em exercícios (`metric_type`):**
  - Coluna `metric_type TEXT NOT NULL DEFAULT 'weight'` em `exercises` via `migrate_metric_type.sql`
  - Suporte a `weight` (reps+carga), `distance` (distância em km) e `time` (duração em min) no log de treino, import default e analytics
  - `get_last_exercise_values()` pré-preenche Import Default com último valor por exercício
  - `get_volume_history()` e `get_exercise_bests_all()` adaptam cálculo e labels ao metric_type
  - `biblioteca.py` exibe badge de métrica por card de exercício
  - `rotinas.py` agora permite editar o nome de rotinas via `update_workout_sheet()`
- **Spawn Tiers:**
  - Colunas `is_spawnable` e `rarity_tier` em `pokemon_species`
  - `migrate_spawn_tiers.sql` + `seed_spawn_tiers.py` (refina lendários/míticos via PokéAPI)
- **Streak Shield:**
  - Item `streak-shield` na loja (100 moedas, categoria `other`)
  - Consumido automaticamente em `do_checkin()` quando detecta 1 dia de gap — preserva o streak
  - `scripts/seed_streak_shield.sql` para inserir o item no banco
- **Rival Semanal + Desafio Comunitário:**
  - `assign_weekly_rival()`: atribui rival por proximidade de XP semanal; avalia resultado da semana anterior (+10 moedas ao vencedor)
  - `weekly_challenges` + `weekly_challenge_participants`: desafio coletivo semanal com meta de XP/treinos/séries; recompensa em item ao completar
  - Colunas `weekly_rival_id` e `rival_assigned_week` adicionadas a `user_profiles`
  - Migrations: `scripts/migrate_rival.sql` e `scripts/migrate_weekly_challenge.sql`
- **GIF upload via Supabase Storage:** admin pode fazer upload de GIF ao criar exercício em `admin.py` — armazenado no Supabase Storage e URL salva em `exercises.gif_url`

### A implementar

**Opcional**
- [ ] Formas de Paldea — popular com `seed_regional_species.py`

---

## Sistema de Conquistas

### Arquivos
- **`utils/achievements.py`** — catálogo (`CATALOG`), `CATEGORY_META`, `GYM_BADGES`, `badge_url(slug, unlocked)`
- **`pages/conquistas.py`** — página 🏅 Conquistas com duas tabs: **Conquistas** (badges shields.io por categoria) e **Ginásio** (badge rack visual das 8 insígnias Kanto)
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

### Catálogo — 34 conquistas em 6 categorias
| Categoria | Slugs | Métrica verificada |
|---|---|---|
| `treino` | `first_workout`, `workouts_10/50/100`, `workout_streak_7/30`, `pr_first`, `pr_10` | `workout_count`, `workout_streak`, `pr_count` |
| `colecao` | `first_capture`, `dex_10/50/100/200/500`, `dex_complete` | `pokemon_count` em `user_pokemon` |
| `checkin` | `checkin_streak_7/30/100/365` | `MAX(streak)` em `user_checkins` |
| `batalha` | `first_win`, `wins_10/50` | `COUNT` em `user_battles WHERE winner_id` |
| `especial` | `first_evolution`, `shiny_catch`, `regional_form`, `stone_evolution` | flags booleanas derivadas de joins |
| `ginasio` | `badge_pedra`, `badge_cascata`, `badge_trovao`, `badge_arco_iris`, `badge_alma`, `badge_pantano`, `badge_vulcao`, `badge_terra` | milestones progressivos (treinos, streak, batalhas, capturas, evolucões, PRs) |

**`GYM_BADGES`** — lista de 8 dicts `{slug, name, icon, badge_color, category}` exportada de `utils/achievements.py`; usada em `hub.py` (contador "Insígnias: X/8") e `conquistas.py` (tab Ginásio com badge rack visual).

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
