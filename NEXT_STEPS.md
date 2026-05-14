# LimitBreak — Roadmap Aberto

> Atualizado: 14 de maio de 2026.
>
> Documento canônico de backlog. Mantém apenas itens ainda não implementados e frentes futuras de produto.
>
> Melhorias técnicas de performance em andamento ficam documentadas separadamente em `PLANO_MELHORIAS_PERFORMANCE.md`.

---

## Prioridades de Produto

### 1. Animação de Evolução

**Objetivo:** tornar o momento de evolução mais memorável e recompensador visualmente.

**Escopo:**
- substituir o banner estático por uma sequência curta;
- mostrar sprite atual com efeito visual, transição e sprite evoluído;
- implementar com CSS em `st.markdown()` e containers temporários via `st.empty()`;
- manter zero dependências novas.

**Esforço:** baixo  
**Impacto:** médio

---

### 2. Perfil Público do Treinador

**Objetivo:** dar identidade social ao usuário e transformar leaderboard em porta de entrada para descoberta.

**Escopo:**
- criar `pages/perfil.py`;
- exibir avatar, insígnias, top 3 Pokémon da equipe e stats resumidos;
- ligar o acesso a partir do leaderboard;
- manter implementação somente leitura, reutilizando dados já existentes.

**Esforço:** médio  
**Impacto:** médio

---

### 3. Compartilhamento de Rotinas

**Objetivo:** permitir que usuários publiquem e copiem rotinas, aumentando reutilização e senso de comunidade.

**Escopo:**
- adicionar `is_public` e `copies` em `workout_sheets`;
- listar rotinas públicas com autor e total de cópias;
- criar ação "Copiar para minha conta" reutilizando o fluxo já existente de criação de rotina;
- decidir regras mínimas de curadoria e ordenação da biblioteca.

**Esforço:** baixo  
**Impacto:** médio

---

## V2 Social

### 4. Sistema de Trocas de Pokémon

**Objetivo:** habilitar trocas entre usuários e abrir caminho para evoluções por troca sem depender do bypass de nível.

**Escopo:**
- criar tabela `trade_proposals`;
- suportar proposta, aceite, recusa e expiração;
- trocar Pokémon com segurança e validar evolução por troca após conclusão;
- limitar propostas simultâneas por usuário.

**Dependências:**
- fluxo assíncrono claro para propostas pendentes;
- idealmente alguma forma de notificação ou inbox.

**Esforço:** alto  
**Impacto:** alto

---

### 5. Sistema de Guildas

**Objetivo:** introduzir accountability social com progresso coletivo e recompensas de grupo.

**Escopo:**
- grupos pequenos de treinadores;
- XP coletivo semanal;
- metas e recompensas compartilhadas;
- gestão de entrada, saída e ownership do grupo.

**Risco principal:** complexidade de estado e moderação aumenta bastante para a base atual.

**Esforço:** alto  
**Impacto:** muito alto

---

## Conteúdo Opcional

### 6. Formas de Paldea

**Objetivo:** expandir cobertura de formas especiais sem mexer no loop principal.

**Escopo:**
- popular espécies e formas faltantes;
- revisar pipeline de seed para regionais;
- validar sprites e compatibilidade com a Pokédex.

**Observação:** item de baixo impacto imediato; manter atrás das entregas sociais.

**Esforço:** baixo a médio  
**Impacto:** baixo

---

## Dívida Técnica

| Item | Descrição | Urgência |
|---|---|---|
| `db.py` com 4946 linhas | Split em andamento — `db_core` ✅ e `db_catalog` ✅ extraídos; faltam `db_user`, `db_shop`, `db_combat`, `db_workout`, `db_progression`, `db_admin` | Baixa |
| Sem testes automatizados | Cobrir `award_xp`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements` | Baixa |
| Retry na conexão DB | Adicionar backoff em `get_connection()` para reduzir falha em cold start | Baixa |
| Cache de sprites regionais | Evitar HTTP GET repetido para forms regionais (`id > 10000`) | Baixa |

---

## Ordem Recomendada

1. Animação de Evolução
2. Perfil Público do Treinador
3. Compartilhamento de Rotinas
4. Sistema de Trocas de Pokémon
5. Sistema de Guildas
6. Formas de Paldea

---

## Resumo

| Item | Esforço | Impacto | Status |
|---|---|---|---|
| Animação de evolução | Baixo | Médio | Aberto |
| Perfil público do treinador | Médio | Médio | Aberto |
| Compartilhamento de rotinas | Baixo | Médio | Aberto |
| Sistema de trocas | Alto | Alto | V2 |
| Sistema de guildas | Alto | Muito alto | V2 |
| Formas de Paldea | Baixo a médio | Baixo | Backlog |
| Refactor de `db.py` | Alto | Médio | Dívida técnica |
| Testes automatizados | Médio | Alto | Dívida técnica |
| Retry de conexão DB | Baixo | Médio | Dívida técnica |
| Cache de sprites regionais | Baixo | Baixo | Dívida técnica |

---

## Plano de Ação — Split de `db.py`

**Objetivo:** quebrar `utils/db.py` em módulos menores sem alterar comportamento visível da aplicação, preservando imports existentes durante a transição.

### ✅ Etapa 0. Preparação e mapeamento (concluída)

**Objetivo:** reduzir risco antes de mover código.

**Pontos a trabalhar:**
- inventariar todas as funções exportadas hoje por `utils.db` e identificar quais páginas/scripts dependem de cada uma;
- agrupar helpers internos por domínio e por dependência cruzada;
- mapear funções mais sensíveis a regressão: `award_xp`, `do_exercise_event`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements`, `start_battle`, `finalize_battle`;
- identificar helpers compartilhados que não pertencem a um domínio específico, como `get_connection()`, `_table_has_column()`, `_first_existing_column()`, `_today_brt()` e helpers de stats/base SQL;
- definir convenção de organização para os novos arquivos em `utils/db/` ou estrutura equivalente.

**Saída esperada:**
- lista de funções públicas por domínio;
- lista de helpers compartilhados;
- ordem de extração validada.

### ✅ Etapa 1. Criar camada base compartilhada (concluída — `db_core.py` 617 linhas)

**Objetivo:** separar infraestrutura comum antes de extrair regras de negócio.

**Pontos a trabalhar:**
- criar módulo base para conexão e utilidades transversais;
- mover `get_connection()`, `_db_params()`, `_new_conn()`, `_today_brt()` e helpers de compatibilidade de schema;
- centralizar constantes compartilhadas usadas em mais de um domínio;
- garantir que a nova base não importe módulos de negócio para evitar ciclos;
- manter `utils/db.py` reexportando esses símbolos para compatibilidade.

**Critério de conclusão:**
- nenhum import externo precisa mudar;
- páginas continuam importando de `utils.db` sem quebra.

### ⏳ Etapa 2. Extrair domínio `pokemon` (parcialmente concluída)

> `db_catalog.py` (114 linhas) extrai as queries de Pokédex somente-leitura. Falta extrair equipe/captura/moves/stat boosts → será feito em `db_user.py`.

**Objetivo:** isolar operações de Pokédex, time, captura, moves e stats.

**Pontos a trabalhar:**
- mover consultas de espécies, tipos, detalhes e cadeia evolutiva;
- mover criação/captura de Pokémon do usuário e gerenciamento de time/bench;
- mover helpers de genética, nature, IV/EV e sincronização de stats;
- mover leitura e escrita de moves equipados;
- manter atenção especial a funções usadas por outros domínios, como `_insert_user_pokemon()`, `_sync_user_pokemon_stats()` e `sprite_img_tag()`.

**Risco principal:**
- `progression`, `workout` e `combat` dependem de helpers internos de Pokémon.

### Etapa 3. Extrair domínio `shop`

**Objetivo:** separar inventário, loja, itens consumíveis e loot.

**Pontos a trabalhar:**
- mover catálogo da loja e leitura de inventário;
- mover helpers de adição de item e garantia de existência da loot box;
- mover compra e uso de itens (`vitamins`, `xp-share`, `nature-mint`, pedras evolutivas);
- mover `_roll_loot_box()` e `_grant_loot_box()`;
- revisar dependências com `progression` por causa de `award_xp()` e com `pokemon` por causa de evolução com pedra.

**Critério de conclusão:**
- página da loja e fluxos de inventário continuam funcionando sem alteração de import externo.

### Etapa 4. Extrair domínio `combat`

**Objetivo:** encapsular toda a lógica de batalha em um módulo isolado.

**Pontos a trabalhar:**
- mover cálculo de dano, efetividade de tipo e seleção de golpes;
- mover busca de oponentes, contagem diária, abertura/finalização de batalha e histórico;
- revisar dependências com `pokemon` para leitura de equipe, moves e stats;
- revisar dependências com `progression` para concessão de XP pós-batalha;
- validar se há helpers utilitários que devem permanecer em módulo base em vez de `combat`.

### Etapa 5. Extrair domínio `workout`

**Objetivo:** separar treino, streak, spawn, PRs, ovos, builder de rotinas e analytics.

**Pontos a trabalhar:**
- mover catálogo de exercícios, grupos musculares e filtros;
- mover histórico de treino, streak, XP diário, volume e melhores marcas;
- mover `do_exercise_event()` com seus subfluxos de spawn, milestone, egg system, abilities e PR bonus;
- mover `_detect_prs()` e helpers correlatos;
- mover CRUD de `workout_sheets`, `workout_days` e `workout_day_exercises`;
- mover analytics de distribuição muscular, volume e histórico recente.

**Risco principal:**
- este é o maior bloco acoplado do arquivo e depende de `progression`, `pokemon`, `shop` e abilities.

### Etapa 6. Extrair domínio `progression`

**Objetivo:** concentrar evolução de progresso do jogador e do Pokémon.

**Pontos a trabalhar:**
- mover `award_xp()` e toda a lógica de level-up, evolução e happiness;
- mover XP Share, check-in, descanso e eventuais bônus de progressão;
- mover achievements e recompensa associada;
- mover missões diárias/semanais se a decisão for manter progressão centralizada;
- revisar fronteira entre `progression` e `workout` para evitar duplicação de regras de XP.

**Atenção especial:**
- `award_xp()` é ponto crítico e deve manter assinatura e payload de retorno idênticos.

### Etapa 7. Extrair domínio `admin`

**Objetivo:** remover do arquivo central as rotinas de administração e observabilidade.

**Pontos a trabalhar:**
- mover permissões/admin role, listagem e atualização de usuários;
- mover exclusão de usuário e logs administrativos;
- mover criação de exercício por admin;
- mover métricas globais e consultas de system logs;
- revisar dependências com `workout` para `get_exercises()` e com `shop` para `admin_gift_loot_box()`.

### Etapa 8. Manter `utils.db` como facade temporária

**Objetivo:** evitar quebra nos imports existentes durante a migração.

**Pontos a trabalhar:**
- transformar `utils/db.py` em arquivo de reexportação das funções públicas;
- manter nomes e assinaturas atuais intactos;
- reexportar apenas API pública, evitando vazar helpers novos desnecessários;
- documentar no topo do arquivo que ele existe por compatibilidade transitória;
- só remover a facade após migrar todos os imports do projeto.

**Critério de conclusão:**
- páginas como `pages/treino.py`, `pages/admin.py`, `pages/loja.py`, `pages/batalha.py` e `utils/app_cache.py` continuam operando sem mudança obrigatória imediata.

### Etapa 9. Ajustar imports internos e quebrar ciclos

**Objetivo:** estabilizar a nova arquitetura.

**Pontos a trabalhar:**
- revisar imports circulares entre `pokemon`, `progression`, `shop`, `workout` e `combat`;
- mover helpers compartilhados para módulo base quando surgirem dependências bidirecionais;
- evitar imports locais ad hoc, exceto quando realmente necessários para quebrar ciclo;
- padronizar uso de tipos, constantes e utilidades comuns.

### Etapa 10. Validar regressões e fechar a operação

**Objetivo:** concluir o refactor com segurança.

**Pontos a trabalhar:**
- executar checklist manual dos fluxos principais: starter, captura, equipe, loja, treino, XP, evolução, batalha, admin, missões e conquistas;
- adicionar ou atualizar testes focados para `award_xp`, `_roll_loot_box`, `_detect_prs` e `check_and_award_achievements`;
- rodar diagnóstico/lint nos arquivos tocados;
- revisar se `utils/db.py` deixou de concentrar regra de negócio e passou a ser apenas compatibilidade;
- documentar quais módulos novos existem, o que cada um expõe e quais helpers continuam privados.

**Definição de pronto:**
- `db.py` deixa de ser o centro de implementação;
- cada domínio fica em arquivo próprio com responsabilidade clara;
- imports externos continuam estáveis ou são migrados de forma controlada;
- funções críticas mantêm comportamento e contrato de retorno;
- há cobertura mínima para os pontos de maior risco.
