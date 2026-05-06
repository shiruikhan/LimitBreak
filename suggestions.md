# LimitBreak — Sugestões de Melhorias

> Auditoria atualizada em 06/05/2026.
> Itens marcados ✅ já estão implementados e documentados no `CLAUDE.md`. O foco aberto agora está na camada social V2.

---

## Já Implementado ✅

| Sugestão | Release |
|---|---|
| PR Detection + bônus XP (+50 XP, máx 3/sessão) | Release 3A |
| Type affinity nos spawns (ranked + multi-typed) | Release 3A |
| Sistema de Ovos (milestones 25/50/100, choca em N treinos) | Release 3A |
| Habilidades passivas (blaze, synchronize, pickup, pressure, compound-eyes) | Release 3A |
| Missões diárias (3) e semanal (1) com recompensas | Priority B |
| Página de Ovos com progresso e spoiler toggle | Release 5A |
| Widget de missões no hub | Release 5B |
| Indicador de cap de vitaminas na equipe | Release 5C |
| Toast global de conquistas | Release 5D |
| Felicidade / Amizade (happiness 0–255, modificador XP, evoluções por amizade) | Release 6 |
| Mecânica de Descanso (botão em calendario.py, +5 happiness, user_rest_days) | Release 6 |
| Insígnias de Ginásio (8 insígnias Kanto, badge rack, contador no hub) | Release 7 |
| Analytics de Treino (tab Análise em treino.py: volume, distribuição, bests) | Release 8 |

---

## ~~Prioridade 1 — Vínculo Emocional com o Pokémon~~ ✅ *Releases 6–8 completos*

### ~~1.1 Felicidade / Amizade~~ ✅ *(Release 6)*

**O que é:** coluna `happiness SMALLINT DEFAULT 70` em `user_pokemon`. Sobe com treinos, check-ins e descanso; cai com inatividade prolongada. Desbloqueia evoluções por amizade (Eevee→Espeon/Umbreon, Chansey→Blissey, Golbat→Crobat) sem depender do bypass `_BYPASS_LEVEL = 36`.

**Efeitos:**
- ≥ 220 → evoluções por amizade desbloqueadas (trigger `'friendship'`)
- ≥ 180 → +5% XP em `award_xp()`
- < 50 → −5% XP + badge "desmotivado" na equipe

**Por que alto impacto:** remove dívida técnica de forma semântica e cria uma dimensão emocional concreta — o usuário vê que o Pokémon "responde" à consistência.

**Migration:** `ALTER TABLE user_pokemon ADD COLUMN happiness SMALLINT DEFAULT 70;`

---

### ~~1.2 Mecânica de Descanso~~ ✅ *(Release 6, junto com 1.1)*

**O que é:** botão "Registrar Descanso" em `calendario.py`. Concede +5 happiness ao slot 1, não quebra streak de check-in e exibe nota visual no grid do calendário.

**Por que importante:** remove a culpa de não treinar. Usuário que quebra streak abandona; usuário que registra descanso permanece ativo no app.

---

### 1.3 Animação de Evolução

**O que é:** ao evoluir, substituir o banner estático por sequência: sprite atual com efeito `@keyframes brightness` → spinner → sprite evoluído.

**Implementação:** CSS puro em `st.markdown()` + `st.empty()` para sequência de frames. Zero dependências novas.

**Esforço:** ~2h. Impacto visual alto no momento mais memorável do sistema de XP.

---

## ~~Prioridade 2 — Progressão de Longo Prazo~~ ✅ *Releases 7–8 completos*

### ~~2.1 Insígnias de Ginásio~~ ✅ *(Release 7)*

**O que é:** 8 insígnias Kanto desbloqueáveis por milestones progressivos. Extensão natural de `utils/achievements.py` com visual distinto.

| Insígnia | Marco |
|---|---|
| Pedra | 10 sessões de treino |
| Cascata | Streak de 7 dias de check-in |
| Trovão | 5 vitórias em batalha |
| Arco-íris | 25 Pokémon capturados |
| Alma | Streak de 30 dias de treino |
| Pântano | 10 PRs detectados |
| Vulcão | 10 Pokémon evoluídos |
| Terra | 100 sessões de treino |

**Exibição:** contador "Insígnias: 3/8" no hub e em `equipe.py`. Sprite oficial da insígnia via CDN ou SVG inline.

---

### ~~2.2 Analytics de Treino~~ ✅ *(Release 8)*

**O que é:** nova tab "📊 Análise" em `treino.py` com gráficos derivados de `exercise_logs.sets_data` — sem mudança de schema.

**Métricas:**
- Volume por sessão ao longo do tempo (sets × reps × kg)
- Melhor carga histórica por exercício (já existe em `_get_exercise_bests()`)
- Distribuição de grupos musculares desta semana vs. semana passada

**Por que agora:** usuários de musculação retêm por dados. A infraestrutura já existe — é só expor.

---

### 2.3 Indicador de Equilíbrio Muscular

**O que é:** grade de ícones coloridos em `treino.py` ou hub mostrando grupos musculares treinados nos últimos 7 dias. Grupos frios (não treinados há >5 dias) em cinza com destaque visual.

**Sinergia:** ao clicar num grupo frio, sugerir o Pokémon que spawna com aquele tipo. Ex.: "Costas há 6 dias → treine hoje para spawnar Water/Dragon".

**Implementação:** aggregar `body_parts` de `exercise_logs JOIN exercises` por semana. Exibir como `st.columns` com badges coloridos.

---

## ~~Prioridade 3 — Retenção e Retorno~~ ✅ *Release 9 completo*

### ~~3.1 Streak Shield (Item de Proteção)~~ ✅

**O que é:** item da loja (`streak-shield`, categoria `other`) que protege o streak quando o usuário perde exatamente um dia de check-in e volta no dia seguinte (`gap == 2`). Consumido automaticamente.

**Status implementado:** compra na loja, concessão extra nos dias 7 e 21, consumo automático em `do_checkin()`, feedback visual no calendário/mochila e retorno com `shield_used` + `bonus_shield`.

**Por que impacto:** streak é o principal driver de retorno. Perder streak por um dia é motivo de abandono. Shield transforma a perda num momento de alívio — e cria demanda pela loja.

---

### ~~3.2 Rival Semanal~~ ✅

**O que é:** toda semana, o sistema designa automaticamente um rival com XP semanal próximo. Se o usuário vencer a semana anterior, recebe +10 moedas.

**Status implementado:** `assign_weekly_rival(user_id)` + `get_rival_status(user_id)` em `db.py`, migration dedicada em `scripts/migrate_rival.sql`, banner no `hub.py` com sprite/diferença semanal e toast de vitória na virada da semana.

---

### ~~3.3 Desafio Comunitário Semanal~~ ✅

**O que é:** desafio semanal compartilhado por toda a comunidade, com metas de XP, treinos ou séries. Quem contribui pode coletar a recompensa quando a meta é concluída.

**Status implementado:** `weekly_challenges` + `weekly_challenge_participants`, criação lazy via `_ensure_weekly_challenge()`, progresso atualizado dentro de `do_exercise_event()`, banner no `hub.py` e coleta via `claim_weekly_challenge_reward(user_id)`. A recompensa atual é um ovo.

**Por que funciona sem guildas:** cria senso de comunidade sem exigir coordenação ativa.

---

## Prioridade 4 — Social

### 4.1 Página de Perfil Público do Treinador

**O que é:** página pública `/perfil/{username}` (ou modal acessível via leaderboard) com: avatar emoji, insígnias conquistadas, top 3 Pokémon da equipe, stats resumidos (treinos, capturados, batalhas, streak recorde).

**Implementação:** nova `pages/perfil.py`. Dados já existem nas tabelas — é uma query de leitura. Link via leaderboard (username clicável).

**Por que agora:** mais impactante após insígnias e felicidade existirem. Identidade de treinador → investimento emocional.

---

### 4.2 Compartilhamento de Rotinas

**O que é:** botão "Tornar pública" em `rotinas.py`. Rotinas públicas ficam numa biblioteca compartilhada que qualquer usuário pode copiar com um clique.

**Implementação:**
- `ALTER TABLE workout_sheets ADD COLUMN is_public BOOL DEFAULT FALSE, copies INT DEFAULT 0;`
- Query `get_public_sheets()` listando rotinas públicas com autor e número de cópias
- Botão "Copiar para minha conta" chama `create_workout_sheet()` + `create_workout_day()` + `add_exercise_to_day()` em loop

---

### 4.3 Sistema de Trocas de Pokémon *(V2)*

**O que é:** proposta de troca entre usuários. Necessário para evoluções por troca (Gengar, Machamp, Alakazam, Golem) sem usar o bypass de nível 36.

**Implementação:**
- Nova tabela `trade_proposals`: `(id, proposer_id, target_id, offered_pokemon_id, requested_species_id, status, created_at)`
- Ao aceitar: swap de `species_id` em `user_pokemon`, checa evolução por troca
- Limite: 3 propostas abertas simultâneas por usuário

**Deferred:** requer infra de notificação assíncrona. Implementar após sistema de perfil público.

---

### 4.4 Sistema de Guildas *(V2)*

**O que é:** grupos de até 10 treinadores com XP coletivo semanal e recompensas de grupo.

**Por que alto impacto:** accountability social é um dos principais drivers de retenção em apps de fitness. "Minha guilda vai perder se eu não treinar" é motivação real e consistente.

**Deferred:** gerenciamento de estado de grupo é complexo; melhora com base maior de usuários.

---

## Resumo por Esforço vs. Impacto

| Sugestão | Esforço | Impacto | Status |
|---|---|---|---|
| Felicidade / amizade | Médio | Alto | ✅ Release 6 |
| Mecânica de descanso | Baixo | Médio | ✅ Release 6 (junto) |
| Animação de evolução | Baixo | Médio | 🟡 Quick win |
| Insígnias de Ginásio | Médio | Alto | ✅ Release 7 |
| Analytics de treino | Médio | Alto | ✅ Release 8 |
| Indicador de equilíbrio muscular | Baixo | Alto | 🟡 Quick win |
| Streak Shield | Baixo | Alto | ✅ Release 9.1 |
| Rival semanal | Baixo | Alto | ✅ Release 9.2 |
| Desafio comunitário | Médio | Alto | ✅ Release 9.3 |
| Perfil público do treinador | Médio | Médio | 🟠 Pós-insígnias |
| Compartilhamento de rotinas | Baixo | Médio | 🟡 Quick win |
| Sistema de Trocas | Alto | Alto | 🔵 V2 |
| Guildas | Alto | Muito Alto | 🔵 V2 |

---

*Princípio: cada treino real deve gerar uma consequência virtual significativa e memorável.*
