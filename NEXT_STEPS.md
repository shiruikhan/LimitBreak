# LimitBreak — Next Steps

> Atualizado: 03 de maio de 2026 após implementação do Release 6.
>
> Estado: **Release 6 completo.** Sistema de Felicidade/Amizade implementado.

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
| Loja: pedras (10), vitaminas (6), XP Share, Nature Mint, Loot Box | ✅ |
| Calendário: check-in, streak, spawn ×3, bônus dias 15/último | ✅ |
| Batalhas PvP (3/dia, turno a turno, XP + moedas) | ✅ |
| Conquistas: 23 badges em 5 categorias | ✅ |
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

---

## Próximas features (priorizadas)

### ~~Release 6 — Felicidade / Amizade~~ ✅ *Completo*

`happiness SMALLINT DEFAULT 70` em `user_pokemon`. Incrementos: +2/level-up, +1/treino, +1/check-in, +5/descanso. Penalidade: −5 por inatividade ≥7 dias. Happiness ≥ 180 → +5% XP; < 50 → −5% XP + badge "Desmotivado" na equipe. Evoluções por amizade (`min_happiness = 220`) desbloqueadas em `award_xp()` via coluna `pokemon_evolutions.min_happiness`. Botão "Registrar Descanso" em `calendario.py` com nota visual no grid. Migration: `scripts/migrate_happiness.sql`.

---

### ~~Release 7 — Insígnias de Ginásio~~ ✅ *Completo*

8 insígnias Kanto implementadas como categoria `"ginasio"` em `utils/achievements.py` (+ `GYM_BADGES` list). Badge rack visual em `pages/conquistas.py` (tab Ginásio). Contador "Insígnias: X/8" com mini badge rack colorido em `pages/hub.py`. Stat `evolved_count` adicionado a `_collect_achievement_stats` em `db.py`.

---

### Release 8 — Analytics de Treino *(estimativa: ~1 semana)*

**Por que agora:** usuários de musculação são orientados a dados. Gráficos de progressão são retentivos independente da gamificação.

**Design:**
- Gráfico de volume por exercício ao longo do tempo (sets × reps × kg)
- Melhor carga histórica por exercício (já calculado em `_get_exercise_bests()`)
- Distribuição semanal de grupos musculares (quais partes do corpo treinadas esta semana vs. última)
- Tudo derivado de `exercise_logs.sets_data` existente — sem mudança de schema

**UI:** nova tab "📊 Análise" em `treino.py` com `st.line_chart` e `st.bar_chart`.

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
| Desafio comunitário semanal | Requer job de reset semanal |
| Página de perfil público do treinador | Mais interessante após insígnias e felicidade existirem |
| Formas de Paldea | Opcional; baixo impacto até ter mais usuários |

---

## Resumo: Esforço × Impacto

| Feature | Esforço | Impacto | Status |
|---|---|---|---|
| Felicidade / amizade | Médio | Alto | ✅ Release 6 |
| Mecânica de descanso | Baixo | Médio | ✅ Release 6 (junto) |
| Insígnias de Ginásio | Médio | Alto | ✅ Release 7 |
| Analytics de treino | Médio | Alto | 🔴 Release 8 |
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
