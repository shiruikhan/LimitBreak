# LimitBreak — Next Steps

> Atualizado: 30 de abril de 2026 após auditoria completa do repositório.
>
> Estado: **Release 4.0 + Priority B completos.** Todos os sistemas core estão implementados e estáveis.

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

---

## Lacunas encontradas na auditoria

### Funcionalidades listadas em "A implementar" no CLAUDE.md

| Item | Esforço estimado | Prioridade |
|---|---|---|
| **Página de Ovos pendentes** | ~3h | Alta — único item incompleto do spec |
| **Formas de Paldea** | ~8h | Baixa — opcional no CLAUDE.md |

### Melhorias de UX identificadas na auditoria

| Item | Descrição | Esforço |
|---|---|---|
| Widget de missões no hub | Missões visíveis só na sidebar; hub não mostra progresso diário | ~2h |
| Indicador visual de cap de vitaminas | Usuário só descobre o limite ao tentar usar o item | ~1h |
| Banner de conquistas fora de conquistas.py | `new_achievements_pending` só aparece em conquistas.py | ~1h |

### Dívida técnica

| Item | Descrição | Urgência |
|---|---|---|
| `db.py` com 4370 linhas | Split em submódulos (pokemon, progression, combat, shop, workout, admin) | Baixa |
| Sem testes automatizados | `award_xp`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements` sem cobertura | Baixa |
| Retry na conexão DB | `get_connection()` reconecta mas não tem backoff — pode falhar no cold start do Streamlit Cloud | Baixa |
| Cache de sprites regionais | HTTP GET a cada request para forms regionais (id > 10000) | Baixa |

---

## Próximas features (priorizadas)

### ~~Release 5 — Qualidade de Vida~~ ✅ ENTREGUE (30/04/2026)

**5A · Página de Ovos** ✅
- `pages/ovos.py`: grade de cards com raridade, barra de progresso, spoiler toggle de espécie
- `get_user_eggs` atualizado para incluir `species_id/name/sprite_url` via JOIN
- Registrada na sidebar (grupo "Treinador") e no hub SECTION_CARDS
- `db.py`: nova função `get_team_stat_boost_counts` em uma query

**5B · Widget de Missões no Hub** ✅
- `hub.py`: painel de missões diárias expandido com progresso individual por missão
- Barras de progresso coloridas: azul (em andamento), verde (completa), cinza (coletada)
- Importa `get_mission()` do catálogo para ícone e label de recompensa

**5C · Indicador de Cap de Vitaminas na Equipe** ✅
- `equipe.py`: importa `_MAX_STAT_BOOSTS_PER_STAT` e `get_cached_team_stat_boost_counts`
- `_stat_bars()` aceita `boost_counts` opcional; exibe 🔒 dourado quando stat está no limite
- `app_cache.py`: `get_cached_team_stat_boost_counts` (TTL 30s) + limpeza em `clear_user_cache()`

**5D · Toast de Conquistas Global** ✅
- `app.py`: toast `st.toast()` disparado uma única vez por conjunto de conquistas desbloqueadas
- Chave de controle derivada dos slugs evita repetição em rerenders

---

### Release 6 — Felicidade / Amizade *(estimativa: ~1 semana)*

**Por que agora:** remove o hack `_BYPASS_LEVEL = 36` de forma semântica e adiciona dimensão emocional ao vínculo com o Pokémon. Restaura a precisão de evolução para Gengar, Alakazam, Chansey e galho Eevee.

**Design:**
- `ALTER TABLE user_pokemon ADD COLUMN happiness SMALLINT DEFAULT 70;`
- Incrementos: +2 por level-up, +1 por treino, +1 por check-in, +5 por descanso registrado
- Decremento: −5 se inativo por 7 dias (verificação lazy no próximo evento)
- Happiness ≥ 220 → desbloqueio de evoluções por amizade (substituindo bypass do nível 36 para esses casos)
- Happiness ≥ 180 → +5% XP em `award_xp()`
- Happiness < 50 → −5% XP + indicador "desmotivado" na equipe

**Mechânica de Descanso (baixo esforço, incluso aqui):**
- Botão "Registrar Descanso" em `calendario.py`
- +5 happiness no slot 1, não quebra streak de check-in
- Nota visual no grid do calendário

---

### Release 7 — Insígnias de Ginásio *(estimativa: ~1 semana)*

**Por que agora:** cria espinha de progressão de longo prazo reconhecível. Extensão do catálogo de conquistas existente — baixa complexidade incremental.

**8 insígnias temáticas (Kanto):**

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

**Implementação:** subconjunto de `CATALOG` em `utils/achievements.py` com visual distinto (sprite de insígnia). Exibir contador "Insígnias: 3/8" em `equipe.py` ou hub.

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
| Página de Ovos | Baixo | Alto | 🔴 Release 5 |
| Widget de missões no hub | Baixo | Médio | 🔴 Release 5 |
| Indicador cap vitaminas | Baixo | Baixo | 🟡 Release 5 |
| Banner conquistas global | Baixo | Médio | 🟡 Release 5 |
| Felicidade / amizade | Médio | Alto | 🔴 Release 6 |
| Mecânica de descanso | Baixo | Médio | 🔴 Release 6 (junto) |
| Insígnias de Ginásio | Médio | Alto | 🔴 Release 7 |
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
