# LimitBreak — Plano de Melhorias de Performance

> Atualizado: 07 de maio de 2026. Sync após implementação das Etapas 1 e 2.
>
> Documento de referência para implementação e manutenção futura das melhorias de performance do projeto. O foco é reduzir latência percebida, custo de rerender no Streamlit e carga desnecessária no banco Supabase/PostgreSQL.

---

## Objetivo

Este documento organiza as melhorias de performance identificadas no projeto em uma ordem prática de execução, com critérios de prioridade, impacto esperado, riscos e orientações para futuras features.

Ele deve ser usado para:
- priorizar otimizações com melhor custo-benefício;
- orientar refactors sem regressão funcional;
- evitar reintrodução de gargalos conhecidos;
- servir como checklist para novas páginas, queries e componentes.

---

## Contexto Atual

O projeto já possui uma base boa de otimização para a stack atual:
- uso de `@st.cache_data` em leituras recorrentes;
- uso de `@st.cache_resource` para cliente Supabase;
- uso pontual de `st.fragment` em áreas específicas;
- catálogos e consultas centrais já separados parcialmente em `utils/app_cache.py` e `utils/db.py`.

Os principais gargalos atuais estão concentrados em:
- queries com filtros pouco amigáveis para índice;
- consultas em cascata em páginas com árvore de dados;
- mistura de escrita com leitura em componentes compartilhados;
- crescimento de custo conforme aumenta o histórico de treino e uso do app.

Melhorias já concluídas nesta frente:
- invalidação de cache por domínio e por usuário em `utils/app_cache.py`;
- remoção do uso ativo de base64 para URLs remotas nas páginas principais;
- padronização de `sprite_img_tag()` para preferir `src` direto em assets HTTP/S;
- redução de conversões repetidas de ícones locais em telas como `Pokédex` e `Equipe`.

---

## Metas de Performance

### 1. Reduzir custo por rerun

**Objetivo:** fazer cada rerun do Streamlit tocar menos banco, menos disco e menos processamento Python.

**Indicadores práticos:**
- menos funções pesadas chamadas em sidebars e headers;
- menos imagens reconvertidas ou baixadas em loops;
- menos recomputação em páginas de uso frequente.

### 2. Reduzir carga no banco

**Objetivo:** diminuir round-trips e garantir que as queries mais comuns usem índices de forma eficiente.

**Indicadores práticos:**
- menos `SELECT` repetidos por tela;
- menos consultas derivadas em cascata;
- filtros por data compatíveis com índices;
- menor custo das telas `Treino`, `Calendário`, `Hub`, `Equipe` e `Pokédex`.

### 3. Melhorar escalabilidade do app

**Objetivo:** evitar que a experiência degrade de forma perceptível conforme crescem:
- número de usuários;
- volume de `workout_logs`;
- volume de `exercise_logs`;
- quantidade de assets carregados por página.

---

## Prioridades

| Prioridade | Frente | Impacto | Esforço | Status |
|---|---|---|---|---|
| P0 | Invalidação de cache por domínio e por usuário | Alto | Médio | Concluído |
| P0 | Rework de imagens e remoção de base64 em massa | Alto | Baixo a médio | Concluído |
| P0 | Índices e revisão de queries de treino | Alto | Médio | Em andamento |
| P1 | Redução de N+1 em rotinas e páginas estruturadas | Médio a alto | Médio | Concluído |
| P1 | Cache de catálogos quase estáticos | Médio | Baixo | Concluído |
| P1 | Separação entre leitura e escrita em missões/sidebar | Médio | Médio | Concluído |
| P2 | Remoção de compatibilidade de schema desnecessária | Baixo a médio | Médio | Concluído |
| P2 | Telemetria simples de performance | Médio | Baixo | Futuro |

---

## Plano de Implementação

### Etapa 1. Corrigir invalidação de cache

**Status:** concluída.

**Problema original:** `clear_user_cache()` limpava todos os caches compartilhados, inclusive dados de outros usuários e de outras áreas do sistema.

**Resultado entregue:** a invalidação agora acontece por domínio e por usuário, mantendo uma função agregadora apenas para fluxos realmente amplos do mesmo usuário.

**Implementado:**
- criação de helpers específicos como:
  - `clear_profile_cache(user_id)`;
  - `clear_team_cache(user_id)`;
  - `clear_inventory_cache(user_id)`;
  - `clear_missions_cache(user_id)`;
  - `clear_workout_cache(user_id)`;
  - `clear_checkin_cache(user_id, year, month)`;
  - `clear_battle_cache(user_id)`;
  - `clear_achievements_cache(user_id)`;
- manutenção de `clear_user_cache(user_id, ...)` apenas como agregadora por usuário;
- revisão dos principais call sites de mutation em `Treino`, `Calendário`, `Hub`, `Loja`, `Equipe`, `Batalha`, `Missões`, `Mochila`, `Login` e `Starter`.

**Arquivos principais:**
- `utils/app_cache.py`
- `pages/treino.py`
- `pages/calendario.py`
- `pages/hub.py`
- `pages/loja.py`
- `pages/equipe.py`
- `pages/batalha.py`
- `pages/missoes.py`

**Critério atendido:**
- mutações deixam de invalidar caches que não pertencem ao mesmo usuário ou domínio;
- a limpeza global não é mais o caminho padrão para ações de usuário.

### Etapa 2. Reestruturar pipeline de imagens

**Status:** concluída.

**Problema original:** parte das telas ainda convertia imagens para base64 repetidamente em loops, o que custava I/O, CPU e memória.

**Resultado entregue:** o app agora prefere `src` direto para URLs remotas e mantém `base64` apenas como fallback local no helper central.

**Implementado:**
- padronização de `sprite_img_tag()` para usar `src` direto em URLs HTTP/S;
- ajuste de `get_image_as_base64()` para deixar de converter URLs remotas em fluxos ativos;
- remoção do uso ativo de `base64` em páginas principais como:
  - `pages/hub.py`
  - `pages/leaderboard.py`
  - `utils/bag_ui.py`
- redução de conversões repetidas em loops com helpers cacheados e pré-mapas de ícones em:
  - `pages/pokedex.py`
  - `pages/equipe.py`
- limpeza de imports e atualização de código legado relacionado a `app_pokedex.py`.

**Critério atendido:**
- assets remotos deixam de ser rebaixados para base64 sem necessidade;
- páginas com muitos cards passam a usar predominantemente URLs ou conteúdo cacheado;
- `base64` permanece somente como fallback para assets locais.

### Etapa 3. Revisar queries de treino e adicionar índices

**Status:** concluída.

**Problema original:** várias queries usavam `AT TIME ZONE` ou `::date` diretamente sobre a coluna filtrada, o que tendia a dificultar o uso de índice.

**Resultado atual:** a camada Python foi refatorada para usar janelas temporais explícitas em BRT e comparações diretas em `WHERE`; a aplicação dos índices no banco ficou preparada por migration e depende apenas da execução no ambiente.

**Implementado no código:**
- criação de helpers de janela temporal em BRT para dia, intervalo inclusivo e mês;
- substituição dos filtros antigos por intervalos calculados e comparações diretas, como:
  - `completed_at >= start_ts`
  - `completed_at < end_ts`
- revisão e refactor de consultas de:
  - XP diário;
  - contagem diária de batalhas;
  - rival semanal;
  - desafio comunitário;
  - leaderboard mensal;
  - distribuição muscular e analytics recentes;
  - streak e leituras auxiliares de histórico de treino.

**Preparado para o banco:**
- migration criada em `scripts/migrate_performance_stage3_indexes.sql` com:
  - `workout_logs(user_id, completed_at)`
  - `workout_logs(completed_at)`
  - `exercise_logs(workout_log_id, exercise_id)`
  - `user_battles(challenger_id, battled_at)`
- a execução dessa migration ficou pendente do lado do banco.

**Observações:**
- `user_team(user_id, slot)` já é coberto pela PK existente;
- `weekly_challenge_participants(challenge_id, user_id)` já é coberto pela PK existente;
- índices adicionais para `pokemon_species_moves` e `pokemon_evolutions` permanecem como avaliação futura, caso o volume dessas tabelas cresça.

**Critério parcialmente atendido:**
- as queries de treino e batalha no código deixam de aplicar função na coluna indexada no `WHERE`;
- a migration já reflete o caminho principal de leitura do app;
- a etapa será considerada concluída após a execução dos índices no banco e validação prática de desempenho.

### Etapa 4. Reduzir N+1 e cascatas de leitura

**Status:** concluída.

**Problema original:** algumas telas montavam a árvore de dados com múltiplas queries sequenciais por item ou por nível hierárquico.

**Resultado entregue:** os fluxos ativos de rotinas deixaram de buscar rotina, dias e exercícios em cascata, passando a carregar a árvore completa em lote e montar a UI em memória.

**Implementado:**
- criação de `get_workout_builder_tree(user_id)` em `utils/db.py` para retornar:
  - rotina + dias + contagem de exercícios;
  - dia + exercícios prescritos em lote;
- refactor de `pages/rotinas.py` para consumir a árvore agregada em vez de chamar loaders por rotina e por dia;
- refactor de `pages/treino.py` para reutilizar a mesma árvore no seletor de rotina/dia e na importação de treino padrão;
- adição de cache para a árvore agregada em `utils/app_cache.py`, integrada à invalidação de treino.

**Arquivos principais:**
- `utils/db.py`
- `utils/app_cache.py`
- `pages/rotinas.py`
- `pages/treino.py`

**Critério atendido:**
- `Rotinas` deixa de crescer linearmente em número de queries conforme o número de dias/exercícios;
- `Treino` deixa de buscar dias e exercícios prescritos em cascata durante a seleção e importação de rotina.

### Etapa 5. Cachear catálogos quase estáticos

**Status:** concluída.

**Problema original:** alguns catálogos mudavam pouco, mas ainda eram buscados no banco sem cache compartilhado suficientemente longo.

**Resultado entregue:** os catálogos quase estáticos agora passam por cache compartilhado em `utils/app_cache.py`, com invalidação explícita quando o catálogo é alterado.

**Implementado:**
- criação de wrappers compartilhados para catálogos em `utils/app_cache.py`:
  - `get_cached_exercises()`;
  - `get_cached_distinct_body_parts()`;
  - `get_cached_shop_items()`;
- adoção dos catálogos cacheados em:
  - `pages/biblioteca.py`;
  - `pages/rotinas.py`;
  - `pages/treino.py`;
  - `pages/loja.py`;
  - `utils/bag_ui.py`;
  - `pages/admin.py`;
- criação de `clear_catalog_cache()` para invalidação explícita quando o catálogo de exercícios for alterado por admin.

**Critério atendido:**
- abrir `Biblioteca`, `Rotinas`, `Treino` e `Loja` não reconsulta catálogos estáticos em todo rerun;
- atualizações administrativas do catálogo invalidam o cache compartilhado de forma controlada.

### Etapa 6. Separar leitura de escrita em componentes compartilhados

**Status:** concluída.

**Problema original:** componentes de leitura, como o tracker de missões na sidebar, podiam provocar escrita no banco em seu caminho de carregamento.

**Resultado entregue:** a garantia das missões atuais saiu do caminho de leitura e passou para um bootstrap controlado do app, mantendo sidebar e página de missões como leitura pura durante o render.

**Implementado:**
- extração de `get_current_mission_periods()` e `ensure_current_user_missions(user_id)` em `utils/db.py`;
- remoção do `_ensure_missions()` de dentro de `get_user_missions()`, que passou a ser leitura pura;
- bootstrap de missões no fluxo principal de `app.py`, controlado por período diário/semanal em `session_state`;
- limpeza específica de cache com `clear_missions_cache(user_id)` após bootstrap;
- auditoria dos componentes compartilhados restantes sem novos casos de escrita oculta em render.

**Critério atendido:**
- abrir uma página não causa escrita oculta no banco apenas para renderizar sidebar;
- `render_quest_sidebar()` e `pages/missoes.py` dependem apenas de leitura cacheada no caminho de renderização.

### Etapa 7. Simplificar compatibilidade de schema quando a base estabilizar

**Status:** em andamento.

**Problema original:** o projeto mantém proteções úteis para drift de schema, mas elas adicionam custo e complexidade operacional.

**Objetivo:** reduzir consultas extras a `information_schema` quando não forem mais necessárias.

**Resultado entregue:** os fluxos críticos de `Rotinas`, `Treino` e da leitura principal de `user_pokemon` agora assumem o contrato atual do schema em pontos quentes, sem fallbacks dinâmicos remanescentes nesses caminhos.

**Implementado até agora:**
- remoção da checagem dinâmica de `exercises.metric_type` nos caminhos ativos de treino e analytics;
- adoção explícita de `workout_days.workout_sheet_id` e `workout_day_exercises.workout_day_id` como contrato atual do builder;
- remoção dos fallbacks antigos por nomes alternativos (`sheet_id` e `day_id`) nas leituras e mutations do builder;
- remoção do helper legado `_first_existing_column()` em `utils/db.py`;
- remoção das checagens dinâmicas das colunas genéticas (`iv_*`, `ev_*`, `nature`) em `user_pokemon`, agora tratadas como contrato do app;
- formalização do contrato de `workout_sheets.created_by` e `workout_sheets.updated_at` via `scripts/migrate_workout_sheet_metadata.sql`;
- remoção do último guard dinâmico de `workout_sheets` em `utils/db.py`.

**Critério atendido:**
- o código deixa de consultar metadados de schema nos caminhos ativos cobertos pela etapa;
- o contrato atual de `metric_type`, vínculos do builder, genética de `user_pokemon` e metadados de `workout_sheets` passa a estar documentado no repositório.

---

## Ganhos Esperados por Área

| Área | Ganho esperado |
|---|---|
| `Hub` | Menos custo em carregamento inicial e sidebar |
| `Calendário` | Menos recarga de dados derivados e resposta melhor em navegação mensal |
| `Treino` | Menor latência em analytics e importação de treino |
| `Equipe` | Menos custo com ícones, sprites e dados de time |
| `Pokédex` | Menor custo visual em grids grandes |
| `Rotinas` | Menos queries em cascata |
| Banco | Menor custo por leitura e melhor escalabilidade com histórico |

---

## Diretrizes para Uso Futuro

### Regras para novas queries

Sempre que criar nova query:
- evitar função sobre coluna filtrada no `WHERE`;
- preferir intervalos (`>=`, `<`) a casts para data;
- revisar se a query precisa de índice novo;
- pensar em volume futuro, não só no dataset atual.

### Regras para novos componentes visuais

Sempre que criar nova página ou card:
- evitar `get_image_as_base64()` dentro de loops grandes;
- preferir `st.image(url)` ou tag HTML com `src` remoto quando o asset já está publicado;
- se o asset for local e repetido, cachear a leitura;
- evitar sidebars que consultem múltiplas fontes de dados pesadas.

### Regras para novos caches

Ao adicionar cache:
- definir TTL coerente com a natureza do dado;
- separar cache global de catálogo e cache por usuário;
- documentar quem invalida o cache após mutation;
- evitar funções de limpeza total quando um escopo menor basta.

### Regras para novas mutations

Ao adicionar uma ação de escrita:
- invalidar só os domínios afetados;
- não limpar catálogos estáticos;
- não limpar dados de outros usuários;
- revisar se a mutation pode ser agrupada com outras para evitar reruns em excesso.

### Regras para novas sidebars e widgets compartilhados

Componentes compartilhados devem:
- fazer leitura barata;
- evitar `commit()` durante render;
- usar caches apropriados;
- não duplicar consultas já feitas pela página principal sem necessidade.

---

## Checklist de Revisão Antes de Merge

- a mudança adiciona nova query? verificar índice e padrão de filtro;
- a mudança adiciona nova imagem em loop? revisar estratégia de carregamento;
- a mudança usa cache? definir TTL, chave e invalidação;
- a mudança mexe com sidebar/header? medir custo porque impacta várias rotas;
- a mudança toca `utils/db.py`? revisar se cabe em extração futura por domínio;
- a mudança adiciona mutation? invalidar caches de forma específica;
- a mudança aumenta volume histórico? revisar implicação em `workout_logs` e `exercise_logs`.

---

## Ordem Recomendada de Execução

1. Invalidação de cache por domínio e por usuário — concluído
2. Rework do pipeline de imagens — concluído
3. Índices e revisão das queries de treino — em andamento
4. Redução de N+1 em rotinas
5. Cache de catálogos estáticos — concluído
6. Separação entre leitura e escrita em missões/sidebar — concluído
7. Simplificação de compatibilidade de schema — em andamento
8. Telemetria simples de performance

---

## Backlog de Apoio

### Telemetria simples

**Objetivo:** facilitar futuras análises sem depender apenas de inspeção manual de código.

**Sugestões:**
- medir tempo de funções críticas em ambiente local;
- registrar tempo de queries acima de um limiar;
- criar checklist manual de benchmark para páginas críticas;
- opcionalmente expor uma visão admin para contagem de reruns, tempo médio e queries mais pesadas.

### Refactor estrutural

**Objetivo:** reduzir acoplamento entre cache, banco e páginas.

**Sugestões:**
- continuar o plano de split de `utils/db.py`;
- aproximar cada domínio do seu cache correspondente;
- concentrar assets e helpers visuais em utilitários menores e previsíveis.

---

## Resumo Executivo

As maiores oportunidades de ganho no LimitBreak não exigem troca de stack. O melhor retorno vem de:
- invalidar menos cache;
- parar de reconverter imagens repetidamente;
- tornar queries de treino compatíveis com índice;
- reduzir consultas em cascata;
- separar leitura e escrita nos componentes compartilhados.

Se essas frentes forem executadas primeiro, o app deve ganhar:
- melhor tempo de resposta nas telas principais;
- menor carga no Supabase/Postgres;
- menor risco de degradação conforme o histórico de treinos crescer;
- base mais segura para evolução futura do produto.
