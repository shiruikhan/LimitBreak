# LimitBreak — Sugestões de Melhorias de Alto Impacto

Auditoria realizada em 29/04/2026. Foco: fortalecer o vínculo treino → progresso virtual e aumentar retenção.

---

## Prioridade 1 — Fortalecer o vínculo Real World → Pokémon

Estas são as que mais aprofundam a proposta central do produto.

### 1.1 Detecção de Personal Record (PR) com Bônus de XP

**O que é:** comparar o peso/reps de cada exercício com o histórico em `exercise_logs` e detectar quando o usuário supera seu próprio recorde. Conceder +50 XP bônus por PR detectado no `do_exercise_event()`.

**Por que alto impacto:** PR é o momento mais emocional do treino de musculação. Ligá-lo a uma explosão de XP cria um feedback loop imediato entre esforço físico e recompensa virtual — o núcleo do produto.

**Implementação:**
- Adicionar coluna `max_weight` + `max_reps` em `exercise_logs` ou calcular via query antes de persistir
- `do_exercise_event()` retorna lista `prs: [{exercise_name, new_weight}]`
- `treino.py` exibe card amarelo de PR com sprite do Pokémon do slot 1 "comemorando"
- Novo achievement: `"pr_first"` (primeiro PR), `"pr_10"` (10 PRs acumulados)

---

### 1.2 Afinidade de Tipo por Grupo Muscular nos Spawns

**O que é:** ao invés de spawnar qualquer Pokémon aleatório, o `do_exercise_event()` filtra espécies por tipo compatível com os músculos trabalhados no treino.

**Mapeamento sugerido:**
| Grupo muscular | Tipos Pokémon |
|---|---|
| Peito | Fighting, Normal |
| Costas | Water, Dragon |
| Pernas | Ground, Rock, Steel |
| Ombro / Trapézio | Flying, Psychic |
| Bíceps / Tríceps | Fire, Electric |
| Core / Abdômen | Ghost, Dark |
| Cardio | Flying, Electric |

**Por que alto impacto:** dá significado real à escolha do treino do dia. O usuário passa a escolher exercícios de perna porque quer spawnar Pokémon Ground. Cria sinergia entre catálogo de exercícios e Pokédex.

**Implementação:**
- Adicionar campo `pokemon_types: list[str]` em `exercises` (ou derivar de `body_parts` via mapping dict)
- `do_exercise_event()` agrega os tipos do treino e passa para o roll de spawn
- Spawn filtra `pokemon_species` WHERE `type1_slug IN (tipos_do_treino) OR type2_slug IN (tipos_do_treino)`

---

### 1.3 Sistema de Ovos (Egg Hatch)

**O que é:** ao atingir certos milestones de treino (número de séries, volume total, streak), o usuário recebe um Pokémon Egg. O ovo eclode após N sessões de treino registradas, revelando um Pokémon surpresa.

**Por que alto impacto:** mecânica de antecipação — o usuário volta a treinar para eclodir o ovo. Cria uma razão de retorno que vai além do check-in.

**Implementação:**
- Nova tabela `user_eggs`: `(id, user_id, species_id, workouts_to_hatch, workouts_done, received_at, hatched_at)`
- `species_id` gerado no momento da entrega mas revelado só na eclosão (mantido oculto na UI)
- `do_exercise_event()` incrementa `workouts_done` em todos os ovos pendentes do usuário
- Quando `workouts_done >= workouts_to_hatch`: ovo eclode, `capture_pokemon()` é chamado
- Distribuição: milestone de 25 sessões de treino = ovo Comum; 50 sessões = ovo Raro; 100 = Lendário (pseudo-lendário)
- `equipe.py` ou página nova exibe ovos pendentes com barra de progresso de eclosão

---

### 1.4 Habilidades Passivas dos Pokémon

**O que é:** cada Pokémon tem uma habilidade (baseada na PokéAPI) que concede bônus passivo durante treinos. O Pokémon do slot 1 aplica sua habilidade automaticamente.

**Exemplos de habilidades úteis:**
| Habilidade | Pokémon | Efeito no treino |
|---|---|---|
| Blaze | Charizard | +15% XP em treinos de alta intensidade (>200 XP bruto) |
| Hustle | Raticate | +20% XP, mas -10% moedas ganhas |
| Synchronize | Alakazam | Aumenta o XP ganho através do XP share |
| Speed Boost | Yanmega | Reduz cooldown de batalha de 3 para 4/dia |
| Pickup | Meowth | 10% de chance de item extra após treino |

**Por que alto impacto:** dá valor estratégico à composição da equipe e razão para trocar o Pokémon do slot 1 conforme o tipo de treino planejado.

**Implementação mínima:**
- Adicionar coluna `ability_slug` em `pokemon_species` (seed via PokéAPI)
- Dict de efeitos em `utils/abilities.py`
- `do_exercise_event()` lê ability do slot 1 e aplica multiplicadores antes de persistir XP

---

## Prioridade 2 — Loops de Retenção

### 2.1 Missões Diárias e Semanais

**O que é:** 3 missões diárias + 1 missão semanal geradas automaticamente. Recompensas em moedas, XP e itens.

**Exemplos de missões:**
- Diária: "Complete 3 séries de qualquer exercício de peito" → +20 moedas
- Diária: "Registre um treino hoje" → +15 XP
- Diária: "Vença uma batalha PvP" → +1 Poké Ball (novo item)
- Semanal: "Faça check-in 5 dias esta semana" → +1 pedra aleatória

**Por que alto impacto:** missões são o mecanismo mais eficaz de retenção diária em jogos mobile. Dão uma razão para abrir o app mesmo quando o usuário não ia treinar.

**Implementação:**
- Nova tabela `daily_missions`: `(id, user_id, date, mission_slug, target, progress, completed, reward_claimed)`
- Catalog de missões em `utils/missions.py` com funções `check_progress(user_id, slug)` que consultam tabelas existentes
- Geração automática das 3 missões no primeiro acesso do dia (verificar se `date = today` e `COUNT < 3`)
- Nova página `pages/missoes.py` ou tab em `calendario.py`

---

### 2.2 Sistema de Insígnias de Ginásio (Gym Badges)

**O que é:** 8 insígnias desbloqueáveis por milestones progressivos, referenciais às regiões da franquia Pokémon.

**Mapa sugerido:**
| Insígnia | Região | Milestone |
|---|---|---|
| Pedra | Kanto | 10 sessões de treino |
| Cascata | Kanto | Streak de 7 dias de check-in |
| Trovão | Kanto | Vencer 5 batalhas PvP |
| Arco-íris | Kanto | Ter 25 Pokémon capturados |
| Alma | Kanto | 30 dias consecutivos de treino |
| Pântano | Kanto | Detectar 10 PRs |
| Vulcão | Kanto | Evoluir 10 Pokémon |
| Terra | Kanto | Completar 100 sessões de treino |

**Por que alto impacto:** cria uma estrutura de progressão de longo prazo reconhecível por qualquer fã da franquia. A narrativa "sua jornada como treinador" fica visualmente concreta.

**Implementação:**
- Extensão natural do sistema de achievements existente: subset de `CATALOG` com visual especial
- Badge visual: sprite da insígnia oficial (via CDN ou SVG) em vez de shields.io
- Exibir no perfil/equipe como "Insígnias conquistadas: 3/8"

---

### 2.3 Amizade / Felicidade dos Pokémon

**O que é:** cada Pokémon tem um nível de `happiness` (0–255) que sobe com treinos consistentes e baixa com inatividade prolongada. Happiness alto desbloqueia mecânicas especiais.

**Efeitos de happiness:**
- `>= 220`: Pokémon que evoluem por amizade (Eevee→Espeon/Umbreon, Chansey→Blissey, etc.) evoluem corretamente em vez do bypass de nível 36
- `>= 180`: +5% XP bonus em todos os treinos
- `< 50`: -5% XP (Pokémon desmotivado)

**Por que alto impacto:** resolve o debt técnico atual do `_BYPASS_LEVEL = 36` para evoluções por amizade de forma semanticamente correta, e adiciona uma dimensão emocional ao sistema.

**Implementação:**
- Adicionar coluna `happiness SMALLINT DEFAULT 70` em `user_pokemon`
- `award_xp()` incrementa happiness (+2 por level up, +1 por treino)
- `do_checkin()` incrementa happiness (+1 por check-in no dia)
- Job diário implícito: checar `last_active` e decrementar se inativo > 7 dias (via `do_checkin` ou `do_exercise_event`)
- Refatorar condição de evolução por amizade: `trigger='friendship' AND happiness >= 220`

---

## Prioridade 3 — Social e Competição

### 3.1 Sistema de Troca de Pokémon

**O que é:** usuários podem propor trocas entre si. Necessário para evoluções que exigem troca (Gengar, Machamp, Alakazam, Golem).

**Por que alto impacto:** cria interação social orgânica e resolve corretamente mais um caso do `_BYPASS_LEVEL = 36`.

**Implementação:**
- Nova tabela `trade_proposals`: `(id, proposer_id, target_id, offered_pokemon_id, requested_species_id, status, created_at)`
- `status`: `'pending' | 'accepted' | 'rejected' | 'cancelled'`
- Ao aceitar: verifica posse, executa swap de `species_id` em `user_pokemon`, checa evolução por troca
- Notificação via `st.session_state` ao carregar equipe.py
- Limite: 3 propostas abertas simultâneas por usuário

---

### 3.2 Sistema de Guildas

**O que é:** grupos de até 10 treinadores com XP coletivo semanal e recompensas de grupo.

**Estrutura básica:**
- Nova tabela `guilds`: `(id, name, leader_id, created_at)`
- Nova tabela `guild_members`: `(guild_id, user_id, joined_at)`
- XP de treino de cada membro conta para um total semanal da guilda
- Top guilda da semana no leaderboard → Pokémon raro para todos os membros

**Por que alto impacto:** accountability social é um dos principais drivers de retenção em apps de fitness. "Minha guilda vai perder se eu não treinar hoje" é motivação real.

---

### 3.3 Desafio Semanal Comunitário

**O que é:** todo domingo, um desafio é gerado para todos os usuários (ex.: "Total de 50.000 XP de treino esta semana"). Se a meta coletiva for atingida, todos ganham uma recompensa.

**Por que alto impacto:** cria senso de comunidade sem exigir coordenação ativa. Muito mais simples de implementar que guildas, com impacto social similar.

**Implementação:**
- Nova tabela `weekly_challenges`: `(id, week_start, goal_type, goal_value, current_value, reward_item_id, completed)`
- Trigger em `do_exercise_event()` incrementa `current_value`
- Banner na home (equipe.py) com progresso da semana

---

## Prioridade 4 — Inteligência de Treino

### 4.1 Analytics de Volume e Progressão

**O que é:** gráficos em `treino.py` mostrando progressão de peso/volume por exercício ao longo do tempo.

**Métricas úteis:**
- Volume total por sessão (séries × reps × kg)
- Peso máximo por exercício (histórico)
- Distribuição de grupos musculares treinados no mês (radar chart)

**Por que alto impacto:** usuários de musculação são orientados a dados. Ver a progressão real é retentivo em si, independente da gamificação.

**Implementação:** queries em `exercise_logs` com `GROUP BY exercise_id, DATE_TRUNC('week', logged_at)`. Usar `st.line_chart` ou `st.bar_chart` nativos do Streamlit.

---

### 4.2 Indicador de Equilíbrio Muscular

**O que é:** radar ou barra mostrando quais grupos musculares foram treinados esta semana vs. semana passada. Destaque para grupos negligenciados.

**Por que alto impacto:** ferramenta prática de planejamento. Se o usuário ver que não treina costas há 2 semanas, vai programar — e o app sugere qual Pokémon Water pode spawnar.

**Implementação:** aggregar `body_parts` dos exercícios logados por semana. Exibir como grade de ícones coloridos por frequência.

---

### 4.3 Modo Repouso (Rest Day)

**O que é:** botão em `treino.py` ou `calendario.py` para registrar explicitamente um dia de descanso. Concede +5 happiness ao Pokémon do slot 1 e mantém streak de check-in sem spawnar.

**Por que alto impacto:** remove a culpa de não treinar e educa sobre periodização. Usuário que tira day off planejado não abandona o app — usuário que quebra streak abandona.

---

## Prioridade 5 — Polish e UX

### 5.1 Compartilhamento de Rotinas

**O que é:** botão "Tornar pública" em `rotinas.py`. Rotinas públicas ficam numa biblioteca compartilhada que qualquer usuário pode copiar para sua conta.

**Implementação:** adicionar coluna `is_public BOOL DEFAULT FALSE` em `workout_sheets`. Query para listar rotinas públicas com número de cópias.

---

### 5.2 Animação de Evolução

**O que é:** ao evoluir, em vez de apenas um banner estático, exibir uma sequência: sprite do Pokémon atual com efeito de brilho → spinner → sprite do Pokémon evoluído com fanfarra.

**Implementação:** CSS `@keyframes` + `st.empty()` para sequência de frames. Pode ser feito inteiramente em HTML/CSS sem JS.

---

### 5.3 Card de Perfil do Treinador

**O que é:** página de perfil público com: foto de perfil (emoji selecionável), insígnias conquistadas, top 3 Pokémon, stats resumidos (treinos, capturados, batalhas). Acessível via link ou via leaderboard.

**Por que alto impacto:** faz o usuário se identificar com o personagem. Identidade de treinador → maior investimento emocional.

---

## Resumo por Esforço vs. Impacto

| Sugestão | Esforço | Impacto | Prioridade |
|---|---|---|---|
| PR Detection + bônus XP | Baixo | Alto | 🔴 Crítico |
| Type affinity nos spawns | Baixo | Alto | 🔴 Crítico |
| Animação de evolução | Baixo | Médio | 🟡 Rápido win |
| Rest Day mechanic | Baixo | Médio | 🟡 Rápido win |
| Happiness / amizade | Médio | Alto | 🔴 Crítico |
| Gym Badges | Médio | Alto | 🟠 Importante |
| Missões diárias | Médio | Muito alto | 🔴 Crítico |
| Indicador muscular | Médio | Alto | 🟠 Importante |
| Analytics de volume | Médio | Alto | 🟠 Importante |
| Sistema de Ovos | Alto | Muito alto | 🟠 Importante |
| Habilidades passivas | Alto | Alto | 🟠 Importante |
| Desafio comunitário | Alto | Alto | 🟠 Importante |
| Compartilhamento de rotinas | Baixo | Médio | 🟡 Rápido win |
| Card de perfil | Médio | Médio | 🟡 Pós-core |
| Sistema de Troca | Alto | Alto | 🔵 V2 |
| Guildas | Alto | Muito alto | 🔵 V2 |

---

*Sugestões priorizadas com base na visão do produto: cada treino real deve gerar uma consequência virtual significativa e memorável.*
