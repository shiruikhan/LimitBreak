# LimitBreak — Next Steps

> Atualizado: 06 de maio de 2026.
>
> Estado: **Release 9 completo.** Próximo foco: V2 — camada social leve (`perfil`, compartilhamento de rotinas, trocas, guilds).

---

## O que está pronto (auditoria confirmada)

| Sistema | Status |
|---|---|
| Auth + sessão persistente (cookie 30d) | ✅ |
| Onboarding + starter (27 + 2 easter egg) | ✅ |
| Pokédex nacional 1025 + 42 formas regionais | ✅ |
| Pokédex pessoal com filtros e progresso por geração | ✅ |
| Equipe (6 slots, 4 moves, stats IV/EV/Nature) | ✅ |
| Banco de Pokémon | ✅ |
| Sistema de XP + evolução automática (level-up, pedra, shed) | ✅ |
| Bypass nível 36 para evoluções por troca/amizade | ✅ |
| XP Share (distribui 30% para o time) | ✅ |
| Cap de vitaminas (5 por stat por Pokémon) | ✅ |
| Loja: pedras (10), vitaminas (6), XP Share, Nature Mint, Streak Shield, Loot Box | ✅ |
| Calendário: check-in, streak, spawn ×3, bônus dias 15/último | ✅ |
| Batalhas PvP (3/dia, turno a turno, XP + moedas) | ✅ |
| Conquistas: 34 conquistas em 6 categorias | ✅ |
| Leaderboard: XP mensal, streak mensal, coleção all-time | ✅ |
| Missões diárias (3/dia) e semanal (1/semana) com recompensas | ✅ |
| Admin panel: 5 tabs (Visão Geral, Usuários, Gift, Exercícios, Logs) | ✅ |
| Habilidades passivas: blaze, synchronize, pickup, pressure, compound-eyes | ✅ |
| Sistema de ovos: concessão em milestones 25/50/100, choca em N treinos | ✅ |
| Recordes pessoais (PR): +50 XP por PR, máx 3/sessão | ✅ |
| Loot Box: tabela de raridade 50/30/10/5/4/1% | ✅ |
| Biblioteca de exercícios (152 exercícios) | ✅ |
| Workout Builder (Rotinas → Dias → Exercícios) | ✅ |
| Routine Log com cap 300 XP/dia e histórico 7 dias | ✅ |
| Shell visual unificado + hub central + cache compartilhado | ✅ |
| Página de Ovos pendentes com spoiler toggle e barras de progresso | ✅ |
| Widget de missões no hub com progresso individual por missão | ✅ |
| Indicador de cap de vitaminas na equipe (🔒 por stat) | ✅ |
| Toast global de conquistas em app.py | ✅ |
| Insígnias de Ginásio: 8 badges Kanto com badge rack visual | ✅ |
| Felicidade/Amizade: happiness 0–255 com XP modifier, evolução por amizade, descanso | ✅ |
| Analytics de Treino: volume histórico, distribuição muscular, melhores cargas | ✅ |

---

## Releases recentes auditados

### ~~Release 9 — Retenção e Retorno~~ ✅ *Completo*

Três features de retenção implementadas: Streak Shield, Rival Semanal, Desafio Comunitário.

---

#### ~~9.1 Streak Shield~~ ✅

**Objetivo:** proteger o streak de check-in por um dia perdido por mês, convertendo abandono em alívio.

**Schema:**
```sql
-- Adicionar item na loja (comprável + recompensável)
INSERT INTO shop_items (slug, name, description, icon, category, price)
VALUES ('streak-shield', 'Escudo de Streak', 'Protege seu streak por um dia perdido. Consumido automaticamente.', '🛡️', 'other', 100)
ON CONFLICT (slug) DO NOTHING;
```
Sem migration de tabela — usa `user_inventory` já existente.

**Formas de obter o item:**
1. **Compra na loja** — 100 moedas, na grade de itens `other` (junto com XP Share). Sem limite de compra por mês; o limite é natural (1 uso por gap de 2 dias).
2. **Recompensa do calendário** — concedido automaticamente em dois dias fixos por mês:
   - **Dia 7** do mês: 1× streak-shield no inventário.
   - **Dia 21** do mês: 1× streak-shield no inventário.
   - Lógica em `do_checkin()`: após o check-in bem-sucedido, verificar se `today.day in (7, 21)` e conceder via upsert em `user_inventory`. Retornar `{"bonus_shield": True}` no resultado.
   - Exibir card dourado distinto dos dias 15/último (XP Share): "🛡️ +1 Escudo de Streak recebido!"

**Lógica de ativação em `do_checkin()` (`utils/db.py`):**
1. Buscar a data do último check-in do usuário.
2. Calcular `gap = hoje - last_checkin_date` (em dias).
3. Se `gap == 2` (um dia perdido ontem):
   a. Buscar `streak-shield` no inventário do usuário (`user_inventory JOIN shop_items WHERE slug = 'streak-shield' AND quantity > 0`).
   b. Se tiver: decrementar `quantity` em 1, manter `streak` atual (não zerar para 1), registrar check-in normalmente. Setar `shield_used = True`.
   c. Se não tiver: comportamento atual (streak zera para 1).
4. Se `gap > 2`: streak sempre zera, independente de shield.
5. Se `gap == 1`: comportamento normal (streak incrementa).
6. Após registrar o check-in: verificar `today.day in (7, 21)` → conceder 1× streak-shield se for o caso. Setar `bonus_shield = True`.

**Exibição:**
- Em `loja.py`, mostrar `streak-shield` na grade de itens `other`. Botão de compra padrão (sem fluxo especial — só incrementa inventário).
- Em `bag_ui.py`: mostrar quantidade + botão "Usar" desabilitado com tooltip "Consumido automaticamente no check-in".
- Em `calendario.py`, encadear dois cards possíveis no resultado do check-in:
  - Se `shield_used = True`: card azul "🛡️ Escudo de Streak ativado! Seu streak de N dias foi preservado."
  - Se `bonus_shield = True`: card dourado "🛡️ +1 Escudo de Streak recebido! (Dia 7/21 do mês)"
- No grid mensal: marcar os dias 7 e 21 com ícone de escudo pequeno (🛡️) nos dias futuros/passados para o usuário saber quando vêm as recompensas.

**Retorno atualizado de `do_checkin()`:**
```python
{"success", "already_done", "streak", "coins_earned", "bonus_xp_share",
 "spawn_rolled", "spawned", "xp_result", "shield_used", "bonus_shield", "error"}
```

**Checklist de implementação:**
- [x] SQL: inserir `streak-shield` em `shop_items` (executar no Supabase)
- [x] `db.py`: modificar `do_checkin()` — lógica de gap + ativação do shield
- [x] `db.py`: modificar `do_checkin()` — concessão nos dias 7 e 21 via upsert em `user_inventory`
- [x] `db.py`: garantir que `clear_user_cache()` é chamado se shield consumido ou concedido
- [x] `loja.py`: exibir item na grade `other` com botão de compra padrão
- [x] `bag_ui.py`: exibir quantidade na mochila, botão desabilitado com tooltip
- [x] `calendario.py`: card azul "shield ativado" + card dourado "shield recebido"
- [x] `calendario.py`: marcar dias 7 e 21 com ícone 🛡️ no grid mensal

---

#### 9.2 Rival Semanal

**Objetivo:** criar competição leve e personalizada que dá razão para treinar além do mínimo.

**Schema:**
```sql
-- Migration: scripts/migrate_rival.sql
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS weekly_rival_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS rival_assigned_week DATE;  -- segunda-feira da semana de atribuição
```

**Lógica de atribuição (`utils/db.py` — nova função `assign_weekly_rival`):**
1. Recebe `user_id`.
2. Verifica `rival_assigned_week` no perfil — se já é desta semana (segunda-feira atual), retorna sem fazer nada.
3. Busca ranking da semana atual via query inline (análoga a `get_leaderboard_workout_xp()` mas para a semana corrente):
   ```sql
   SELECT up.id, COALESCE(SUM(wl.xp_earned), 0) AS week_xp
   FROM user_profiles up
   LEFT JOIN workout_logs wl ON wl.user_id = up.id
     AND wl.completed_at >= date_trunc('week', NOW() AT TIME ZONE 'America/Sao_Paulo')
   WHERE up.id != %(user_id)s
   GROUP BY up.id
   ORDER BY ABS(COALESCE(SUM(wl.xp_earned), 0) - %(my_xp)s)
   LIMIT 1
   ```
4. Atualiza `weekly_rival_id` e `rival_assigned_week` no perfil.
5. Retorna `{rival_id, rival_username, rival_xp, my_xp}`.

**Integração:**
- Chamar `assign_weekly_rival(user_id)` no início de `hub.py` (fora de fragment, com cache curto — 5 min via `st.cache_data(ttl=300)`).
- Também chamar após `do_exercise_event()` em `treino.py` (para garantir que rival existe antes de exibir comparativo).

**Banner em `hub.py`:**
- Posição: abaixo do snapshot de streak/moedas, acima dos cards de seção.
- Conteúdo: sprite do Pokémon slot 1 do rival (thumbnailed), username, diferença de XP semanal.
- Estados:
  - "⚔️ Você está **N XP à frente** de [rival]! Mantenha o ritmo." (verde)
  - "⚠️ [rival] está **N XP à sua frente**! Treine para superar." (laranja)
  - "🤝 Empate técnico com [rival] — próximo treino decide." (cinza)
- Se nenhum rival atribuído (sem outros usuários): ocultar o banner silenciosamente.

**Recompensa:**
- Verificar resultado do rival no momento do check-in de segunda-feira via `do_checkin()` (ou em `hub.py` como check passivo): se `my_week_xp > rival_week_xp`, conceder +10 moedas e exibir card de vitória.
- Implementação simples: checar na função `assign_weekly_rival()` — ao atribuir novo rival (segunda-feira), verificar semana anterior e conceder bônus se aplicável. Retornar `{"won_last_week": bool, "bonus_coins": int}`.

**Migration:** `scripts/migrate_rival.sql`

**Checklist de implementação:**
- [x] SQL: criar migration `scripts/migrate_rival.sql`
- [x] `db.py`: função `assign_weekly_rival(user_id)` com lógica de semana e bônus retroativo
- [x] `db.py`: função `get_rival_status(user_id)` → `{rival_username, rival_xp, my_xp, diff}` (para exibição no hub)
- [x] `hub.py`: banner de rival com os três estados (frente/atrás/empate)
- [x] `hub.py`: toast de "Você venceu a semana!" se `won_last_week = True`
- [x] `hub.py`: chama `assign_weekly_rival()` a cada render (cache 5 min)

---

#### 9.3 Desafio Comunitário Semanal

**Objetivo:** criar senso de comunidade sem exigir coordenação ativa — todos contribuem para um mesmo número.

**Schema:**
```sql
-- Migration: scripts/migrate_weekly_challenge.sql
CREATE TABLE IF NOT EXISTS weekly_challenges (
  id           SERIAL PRIMARY KEY,
  week_start   DATE NOT NULL UNIQUE,          -- segunda-feira da semana
  goal_type    TEXT NOT NULL,                 -- 'total_xp' | 'total_workouts' | 'total_sets'
  goal_value   INT NOT NULL,                  -- meta coletiva (ex: 50000)
  current_value INT NOT NULL DEFAULT 0,       -- acumulado pela comunidade
  reward_item_slug TEXT NOT NULL,             -- slug do item recompensa (ex: 'loot-box')
  reward_quantity  INT NOT NULL DEFAULT 1,
  completed    BOOL NOT NULL DEFAULT FALSE,
  reward_distributed BOOL NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS weekly_challenge_participants (
  challenge_id INT REFERENCES weekly_challenges(id) ON DELETE CASCADE,
  user_id      UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  contributed  INT NOT NULL DEFAULT 0,        -- contribuição individual
  reward_claimed BOOL NOT NULL DEFAULT FALSE,
  PRIMARY KEY (challenge_id, user_id)
);
```

**Geração de desafios:**
- Função `_ensure_weekly_challenge(cur)` (interna, chamada por `get_current_challenge()`):
  - Verifica se existe registro com `week_start = monday_current_week`.
  - Se não existe: sorteia `goal_type` e calcula `goal_value` baseado no número de usuários ativos (ex.: `active_users × 200` para XP, `active_users × 3` para treinos).
  - Insere o novo desafio.
- Tipos de desafio (rotação ou sorteio):
  - `total_xp`: "A comunidade precisa acumular N XP esta semana."
  - `total_workouts`: "A comunidade precisa completar N sessões de treino."
  - `total_sets`: "A comunidade precisa completar N séries no total."

**Atualização do progresso (`utils/db.py`):**
- Em `do_exercise_event()`, após persistir o `workout_log`, chamar `_update_weekly_challenge(cur, user_id, xp_earned, sets_total)`:
  1. Buscar desafio da semana atual.
  2. Incrementar `current_value` com a contribuição relevante (XP, 1 workout, ou total de sets).
  3. Upsert em `weekly_challenge_participants` com `contributed += delta`.
  4. Se `current_value >= goal_value` e `completed = FALSE`: marcar `completed = TRUE`.
- Usar `UPDATE weekly_challenges SET current_value = current_value + %s WHERE week_start = %s` para evitar race condition (incremento atômico).

**Distribuição de recompensas:**
- Função `claim_weekly_challenge_reward(user_id)` em `db.py`:
  1. Verifica se desafio está `completed = TRUE` e `reward_distributed = FALSE` ou se participante ainda não coletou (`reward_claimed = FALSE`).
  2. Verifica se `contributed > 0` (participou da semana).
  3. Concede item via `user_inventory` (mesma lógica de `open_loot_box` ou `buy_item`).
  4. Marca `reward_claimed = TRUE` para o participante.
  5. Se todos coletaram (ou a qualquer momento via botão): marcar `reward_distributed = TRUE`.

**Exibição em `hub.py`:**
- Banner de largura total abaixo do rival (ou acima, dependendo do espaço):
  - Título: "🌍 Desafio da Semana: [descrição]"
  - Barra de progresso: `st.progress(current_value / goal_value)` com texto "X / Y XP acumulados"
  - Badge de participantes ativos na semana.
  - Estados:
    - Em andamento: barra azul com progresso.
    - Completo + não coletado: barra verde + botão "🎁 Coletar Recompensa" → chama `claim_weekly_challenge_reward()`.
    - Completo + coletado: barra verde com "✅ Recompensa coletada."
    - Não participou + completo: barra verde + aviso "Você não contribuiu esta semana."

**Funções públicas em `db.py`:**
| Função | Descrição |
|---|---|
| `get_current_challenge(user_id)` | Retorna `{challenge_id, description, goal_value, current_value, completed, user_contributed, reward_claimed, reward_item_slug}` ou `None` |
| `claim_weekly_challenge_reward(user_id)` | Concede recompensa; retorna `(bool, msg, reward_dict)` |

**Migration:** `scripts/migrate_weekly_challenge.sql`

**Checklist de implementação:**
- [x] SQL: criar migration `scripts/migrate_weekly_challenge.sql` com as duas tabelas
- [x] `db.py`: `_ensure_weekly_challenge(cur)` — geração automática do desafio da semana
- [x] `db.py`: `_update_weekly_challenge(cur, user_id, xp, sets)` — atualização atômica do progresso
- [x] `db.py`: integrar `_update_weekly_challenge()` em `do_exercise_event()`
- [x] `db.py`: `get_current_challenge(user_id)` — leitura do estado do desafio
- [x] `db.py`: `claim_weekly_challenge_reward(user_id)` — distribuição de recompensa
- [x] `hub.py`: banner do desafio com barra de progresso e botão de coleta
- [x] `hub.py`: chamar `clear_user_cache()` após coleta de recompensa

---

**Ordem de implementação recomendada:**
1. **9.1 Streak Shield** — menor esforço, maior impacto imediato na retenção. Sem nova tabela.
2. **9.2 Rival Semanal** — uma migration simples, banner no hub, grande motivação competitiva.
3. **9.3 Desafio Comunitário** — mais trabalhoso (duas tabelas, lógica de distribuição), mas completa a camada social.

---

### ~~Release 6 — Felicidade / Amizade~~ ✅ *Completo*

`happiness SMALLINT DEFAULT 70` em `user_pokemon`. Incrementos: +2/level-up, +1/treino, +1/check-in, +5/descanso. Penalidade: −5 por inatividade ≥7 dias. Happiness ≥ 180 → +5% XP; < 50 → −5% XP + badge "Desmotivado" na equipe. Evoluções por amizade (`min_happiness = 220`) desbloqueadas em `award_xp()` via coluna `pokemon_evolutions.min_happiness`. Botão "Registrar Descanso" em `calendario.py` com nota visual no grid. Migration: `scripts/migrate_happiness.sql`.

---

### ~~Release 7 — Insígnias de Ginásio~~ ✅ *Completo*

8 insígnias Kanto implementadas como categoria `"ginasio"` em `utils/achievements.py` (+ `GYM_BADGES` list). Badge rack visual em `pages/conquistas.py` (tab Ginásio). Contador "Insígnias: X/8" com mini badge rack colorido em `pages/hub.py`. Stat `evolved_count` adicionado a `_collect_achievement_stats` em `db.py`.

---

### ~~Release 8 — Analytics de Treino~~ ✅ *Completo*

Tab "📊 Análise" em `treino.py`. Três seções:
- **Volume por exercício** ao longo do tempo (`st.line_chart`), com seletor de período (30/60/90/180 dias) e métricas de pico.
- **Distribuição de grupos musculares** (semana atual vs. anterior, `st.bar_chart`).
- **Melhores cargas** por exercício (best weight + max reps, lista HTML).
Tudo derivado de `exercise_logs.sets_data` — sem mudança de schema. Novas funções: `get_volume_history()`, `get_exercise_bests_all()`, `get_muscle_distribution()` em `utils/db.py`.

---

## Dívida Técnica

| Item | Descrição | Urgência |
|---|---|---|
| `db.py` com ~4400 linhas | Split em submódulos (pokemon, progression, combat, shop, workout, admin) | Baixa |
| Sem testes automatizados | `award_xp`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements` sem cobertura | Baixa |
| Retry na conexão DB | `get_connection()` reconecta mas não tem backoff — pode falhar no cold start do Streamlit Cloud | Baixa |
| Cache de sprites regionais | HTTP GET a cada request para forms regionais (id > 10000) | Baixa |

---

## Deferred (V2 / Camada Social)

Valiosos, mas dependem do loop core estar mais profundo antes.

| Feature | Motivo do adiamento |
|---|---|
| Sistema de trocas de Pokémon | Requer estado de proposta assíncrona + infra de notificação |
| Sistema de guilds | Gerenciamento de estado de grupo; melhora com base maior de usuários |
| Página de perfil público do treinador | Mais interessante após insígnias e felicidade existirem |
| Compartilhamento de rotinas | Depende de modelagem pública/cópias em `workout_sheets` |
| Formas de Paldea | Opcional; baixo impacto até ter mais usuários |

---

## Resumo: Esforço × Impacto

| Feature | Esforço | Impacto | Status |
|---|---|---|---|
| Felicidade / amizade | Médio | Alto | ✅ Release 6 |
| Mecânica de descanso | Baixo | Médio | ✅ Release 6 (junto) |
| Insígnias de Ginásio | Médio | Alto | ✅ Release 7 |
| Analytics de treino | Médio | Alto | ✅ Release 8 |
| Streak Shield | Baixo | Alto | ✅ Release 9.1 |
| Rival Semanal | Baixo | Alto | ✅ Release 9.2 |
| Desafio Comunitário | Médio | Alto | ✅ Release 9.3 |
| Trocas de Pokémon | Alto | Alto | 🔵 V2 |
| Guilds | Alto | Muito Alto | 🔵 V2 |

---

## Checklist de Deploy

Antes de cada push em produção:

- [ ] Executar migrações SQL pendentes no Supabase (SQL Editor)
- [ ] Atualizar Secrets no Streamlit Cloud se novas variáveis foram adicionadas
- [ ] Verificar que seeds idempotentes foram executados (novos itens/espécies)
- [ ] Testar fluxo de auth (login, refresh, logout) em produção
- [ ] Verificar CDN fallback para sprites (testar sem submódulo local)
- [ ] Confirmar que `clear_user_cache()` é chamado após todas as novas mutações
