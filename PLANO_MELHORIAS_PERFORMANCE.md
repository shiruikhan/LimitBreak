# LimitBreak — Plano de Melhorias de Performance

> Atualizado: 07 de maio de 2026.
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
- invalidação excessiva de cache;
- custo alto de imagem e conversão para base64;
- queries com filtros pouco amigáveis para índice;
- consultas em cascata em páginas com árvore de dados;
- mistura de escrita com leitura em componentes compartilhados;
- crescimento de custo conforme aumenta o histórico de treino e uso do app.

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
| P0 | Invalidação de cache por domínio e por usuário | Alto | Médio | Aberto |
| P0 | Rework de imagens e remoção de base64 em massa | Alto | Baixo a médio | Aberto |
| P0 | Índices e revisão de queries de treino | Alto | Médio | Aberto |
| P1 | Redução de N+1 em rotinas e páginas estruturadas | Médio a alto | Médio | Aberto |
| P1 | Cache de catálogos quase estáticos | Médio | Baixo | Aberto |
| P1 | Separação entre leitura e escrita em missões/sidebar | Médio | Médio | Aberto |
| P2 | Remoção de compatibilidade de schema desnecessária | Baixo a médio | Médio | Futuro |
| P2 | Telemetria simples de performance | Médio | Baixo | Futuro |

---

## Plano de Implementação

### Etapa 1. Corrigir invalidação de cache

**Problema atual:** `clear_user_cache()` limpa todos os caches compartilhados, inclusive dados de outros usuários e de outras áreas do sistema.

**Objetivo:** invalidar apenas o que realmente mudou.

**Ações:**
- substituir a limpeza global por helpers específicos, como:
  - `clear_profile_cache(user_id)`;
  - `clear_team_cache(user_id)`;
  - `clear_inventory_cache(user_id)`;
  - `clear_missions_cache(user_id)`;
  - `clear_workout_cache(user_id)`;
  - `clear_checkin_cache(user_id)`;
- manter uma função agregadora apenas para fluxos realmente amplos;
- revisar páginas e mutations que hoje chamam `clear_user_cache()`.

**Arquivos principais:**
- `utils/app_cache.py`
- `pages/treino.py`
- `pages/calendario.py`
- `pages/hub.py`
- `pages/loja.py`
- `pages/equipe.py`
- `pages/batalha.py`
- `pages/missoes.py`

**Critério de conclusão:**
- mutações deixam de invalidar caches que não pertencem ao mesmo usuário ou domínio;
- abrir o app com mais de um usuário não dispara recarga global desnecessária.

### Etapa 2. Reestruturar pipeline de imagens

**Problema atual:** parte das telas ainda converte imagens para base64 repetidamente em loops, o que custa I/O, CPU e memória.

**Objetivo:** preferir URL direta e cachear apenas o que realmente precisa de leitura local.

**Ações:**
- usar `src` direto para imagens HTTP sempre que possível;
- aplicar `@st.cache_data` em `get_image_as_base64()` para assets locais pequenos e estáveis;
- evitar chamar `get_image_as_base64()` repetidamente dentro de loops de cards;
- pré-montar mapas de ícones por tipo/dano quando usados em massa;
- revisar telas de maior custo visual:
  - `pages/pokedex.py`
  - `pages/pokedex_pessoal.py`
  - `pages/equipe.py`
  - `utils/bag_ui.py`

**Critério de conclusão:**
- assets remotos deixam de ser rebaixados para base64 sem necessidade;
- páginas com muitos cards passam a usar predominantemente URLs ou conteúdo cacheado.

### Etapa 3. Revisar queries de treino e adicionar índices

**Problema atual:** várias queries usam `AT TIME ZONE` ou `::date` diretamente sobre a coluna filtrada, o que tende a dificultar o uso de índice.

**Objetivo:** tornar as consultas compatíveis com índices e preparar o banco para crescimento de histórico.

**Ações no código:**
- substituir filtros do tipo:
  - `completed_at::date >= ...`
  - `completed_at AT TIME ZONE ...`
- por intervalos calculados e comparações diretas, por exemplo:
  - `completed_at >= start_ts`
  - `completed_at < end_ts`
- revisar consultas de:
  - streak;
  - XP diário;
  - histórico;
  - analytics;
  - rival semanal;
  - desafio comunitário.

**Ações no banco:**
- adicionar índices explícitos para:
  - `workout_logs(user_id, completed_at)`
  - `exercise_logs(workout_log_id, exercise_id)`
  - `user_team(user_id, slot)`
  - `weekly_challenge_participants(challenge_id, user_id)` se necessário manter leitura frequente fora da PK
  - `pokemon_species_moves(species_id, learn_method, level_learned_at)` se a tabela crescer
  - `pokemon_evolutions(from_species_id)` e `pokemon_evolutions(to_species_id)` se ainda não existirem

**Critério de conclusão:**
- queries de treino deixam de aplicar função na coluna indexada no `WHERE`;
- migrations passam a refletir o caminho principal de leitura do app.

### Etapa 4. Reduzir N+1 e cascatas de leitura

**Problema atual:** algumas telas montam a árvore de dados com múltiplas queries sequenciais por item ou por nível hierárquico.

**Objetivo:** carregar dados em lote e montar a estrutura em memória.

**Alvos principais:**
- `pages/rotinas.py`
- fluxos que buscam rotinas, dias e exercícios separadamente;
- eventuais telas de admin e listagens agregadas.

**Ações:**
- criar consultas agregadas que retornem:
  - rotina + dias + contagem de exercícios;
  - dia + exercícios prescritos em lote;
- usar estrutura intermediária em Python para montar a UI;
- evitar round-trip por expander ou por bloco visual.

**Critério de conclusão:**
- a página de rotinas deixa de crescer linearmente em número de queries conforme o número de dias/exercícios.

### Etapa 5. Cachear catálogos quase estáticos

**Problema atual:** alguns catálogos mudam pouco, mas ainda são buscados no banco sem cache compartilhado suficientemente longo.

**Objetivo:** reduzir consultas repetidas em telas de leitura.

**Ações:**
- aplicar cache em:
  - `get_exercises()`;
  - listas auxiliares ligadas à biblioteca;
  - outros catálogos com baixa mutabilidade;
- revisar TTL por domínio:
  - catálogos: TTL alto;
  - estado do usuário: TTL curto;
  - métricas derivadas: TTL médio.

**Critério de conclusão:**
- abrir `Biblioteca`, `Rotinas`, `Treino` e `Loja` não reconsulta catálogos estáticos em todo rerun.

### Etapa 6. Separar leitura de escrita em componentes compartilhados

**Problema atual:** componentes de leitura, como o tracker de missões na sidebar, podem provocar escrita no banco em seu caminho de carregamento.

**Objetivo:** tornar render previsível e barato.

**Ações:**
- mover geração automática de missões para ponto controlado do fluxo:
  - login;
  - primeiro acesso diário;
  - primeiro acesso semanal;
  - ou função explícita de bootstrap;
- fazer `render_quest_sidebar()` depender só de leitura;
- revisar outras funções de leitura com `commit()` embutido.

**Critério de conclusão:**
- abrir uma página não causa escrita oculta no banco apenas para renderizar sidebar.

### Etapa 7. Simplificar compatibilidade de schema quando a base estabilizar

**Problema atual:** o projeto mantém proteções úteis para drift de schema, mas elas adicionam custo e complexidade operacional.

**Objetivo:** reduzir consultas extras a `information_schema` quando não forem mais necessárias.

**Ações:**
- mapear quais checagens de coluna ainda são necessárias em produção;
- substituir compatibilidade dinâmica por contrato explícito de migration quando possível;
- remover fallback legado de trechos já consolidados.

**Critério de conclusão:**
- o código deixa de consultar metadados de schema em rotas críticas sem necessidade real.

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

1. Invalidação de cache por domínio e por usuário
2. Rework do pipeline de imagens
3. Índices e revisão das queries de treino
4. Redução de N+1 em rotinas
5. Cache de catálogos estáticos
6. Separação entre leitura e escrita em missões/sidebar
7. Simplificação de compatibilidade de schema
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
