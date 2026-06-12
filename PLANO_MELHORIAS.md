# LimitBreak — Plano de Melhorias (Layout + Performance)

> Gerado em 2026-06-11 a partir de auditoria completa: código local, documentação e banco Supabase via MCP.
>
> Backlog de produto (features novas) continua em `NEXT_STEPS.md`. Este documento cobre **qualidade**: layout/UX, performance, banco e robustez.

---

## Resultado da Auditoria (resumo)

### Banco (Supabase — projeto `nxtcetqtnmqpamhfpjdm`)
| Achado | Severidade | Ação proposta |
|---|---|---|
| Projeto estava **pausado** (free tier, INACTIVE) — restaurado em 2026-06-11 | Alta (disponibilidade) | Fase 1 — keep-alive ou upgrade |
| FK `user_profiles.weekly_rival_id` sem índice | Baixa | Fase 1 — migration de índices |
| FK `weekly_challenge_participants.user_id` sem índice | Baixa | Fase 1 — migration de índices |
| Leaked password protection desabilitado no Auth | Média | Fase 1 — toggle no dashboard |
| RLS sem policies em `user_rest_days`, `weekly_challenges`, `weekly_challenge_participants` | Info | Fase 4 — documentado; deny-all é seguro para REST (app usa psycopg2) |
| Tabela legada `user_pokemons` (0 rows) ainda existe | Baixa | Fase 1 — DROP via migration |
| Schema em sincronia com o código (metric_type, happiness, rival, stage3 indexes, player-choice) | ✅ OK | — |

### Código / Layout
| Achado | Severidade | Ação proposta |
|---|---|---|
| Design system (`utils/design_system.py`) adotado por apenas ~5 arquivos; 13+ páginas ainda injetam `<style>` próprio (196 blocos `unsafe_allow_html` em `pages/`) | Média | Fase 2 — migração progressiva |
| CSS duplicado re-injetado a cada rerun em cada página | Baixa-média | Fase 2 — consolidar no design system |
| `get_connection()` sem retry/backoff — falha em cold start do pooler (agravado pelo auto-pause do free tier) | Média | Fase 1 |
| Sem testes automatizados para funções críticas (`award_xp`, `_roll_loot_box`, `_detect_prs`, weekend bonus, `apply_evolution_choice`) | Média | Fase 3 |
| Arquivos muito grandes: `equipe.py` (~62 KB), `treino.py` (~54 KB), `db_workout.py` (~72 KB), `db_progression.py` (~63 KB) | Baixa | Fase 4 — extrair componentes |
| Animação de evolução é banner estático (backlog antigo) | Baixa | Fase 2 |

---

## Fase 1 — Banco e Disponibilidade (esforço: baixo · impacto: alto) ✅ CONCLUÍDA em 2026-06-11

> Status: 1.1, 1.2, 1.3 e 1.4(a) aplicados. 1.5 **descartado** — leaked password protection não está disponível no plano free do Supabase.
> Secrets `SUPABASE_URL` e `SUPABASE_ANON_KEY` cadastrados no GitHub e workflow de keep-alive validado com execução manual bem-sucedida em 2026-06-11.

### 1.1 Migration de índices de FK pendentes
Criar `scripts/migrate_performance_stage4_indexes.sql` (idempotente):

```sql
CREATE INDEX IF NOT EXISTS idx_user_profiles_weekly_rival_id
    ON user_profiles (weekly_rival_id)
    WHERE weekly_rival_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_wcp_user_id
    ON weekly_challenge_participants (user_id);
```

Aplicar via MCP (`apply_migration`) ou SQL Editor. Beneficia `assign_weekly_rival()` (joins por rival) e `claim_weekly_challenge_reward()` / leitura de contribuição por usuário.

### 1.2 Remover tabela legada `user_pokemons`
`scripts/migrate_drop_legacy_user_pokemons.sql`:

```sql
DROP TABLE IF EXISTS user_pokemons;
```

Pré-checagem: confirmar 0 rows (confirmado em 2026-06-11) e nenhuma referência no código (confirmado — apenas documentação). Atualizar a nota de tabela legada no `CLAUDE.md` após o drop.

### 1.3 Retry/backoff em `get_connection()` (`utils/db_core.py`)
Problema: o pooler do Supabase recusa conexões nos primeiros segundos após cold start/restore; hoje a primeira visita do dia pode estourar exceção na cara do usuário.

Implementação:
- envolver `_new_conn()` em loop de até 3 tentativas com backoff 0.5s → 1s → 2s;
- capturar apenas `psycopg2.OperationalError`;
- logar tentativas com `logger.warning()`;
- manter contrato atual (retorna conexão ou levanta a última exceção).

### 1.4 Mitigar auto-pause do projeto (free tier)
O projeto Supabase pausa após ~7 dias sem tráfego — foi encontrado pausado nesta auditoria. Opções (escolher uma):
- **a)** GitHub Action agendada (cron diário) executando `SELECT 1` via REST (anon key) — custo zero;
- **b)** upgrade para plano pago (sem pause);
- **c)** aceitar o pause (app é pessoal) e documentar que o primeiro acesso pós-pausa falha — combinado com 1.3 o impacto cai.

Recomendação: **(a)** + 1.3.

### 1.5 Habilitar leaked password protection
Dashboard Supabase → Authentication → Settings → habilitar "Leaked password protection" (checagem HaveIBeenPwned). Sem mudança de código.

---

## Fase 2 — Layout / UX (esforço: médio · impacto: alto) ✅ CONCLUÍDA em 2026-06-11

> Status: 2.1 (lotes A, B e C), 2.2 e 2.3 entregues. 2.4 parcialmente — toasts já existiam nos fluxos principais; classe `lb-skeleton` disponível no design system para uso futuro.
> Entregas extras: fundo global com glow lime, fade-in de página, hover lift em cards/tiles, pulso animado no "VS" da arena, wiggle no ovo pronto para chocar, brilho nos ranks 🥇🥈🥉 do leaderboard.
> Validação: `py_compile` em todas as páginas/utils + boot headless do Streamlit com `/_stcore/health` = ok.

### 2.1 Migrar páginas restantes para o design system
Hoje só `app.py`, `login.py`, `loja.py`, `pokedex.py`, `starter.py` e `bag_ui.py` usam `inject_design_system`/`render_page_heading`. Migrar as demais em lotes, removendo CSS local redundante:

| Lote | Páginas | Observação |
|---|---|---|
| A (alto tráfego) | `hub.py`, `treino.py`, `equipe.py` | Maiores blocos de CSS local; maior ganho visual e de manutenção |
| B (gamificação) | `calendario.py`, `missoes.py`, `batalha.py`, `conquistas.py`, `ovos.py` | Padronizar cards com `lb-card`/`lb-panel` |
| C (restante) | `leaderboard.py`, `biblioteca.py`, `rotinas.py`, `pokedex_pessoal.py`, `admin.py`, `mochila.py` | |

Para cada página:
1. substituir título/subtítulo manual por `render_page_heading()`;
2. trocar cores hardcoded por CSS vars (`var(--color-lime)`, `var(--bg-card)`, …);
3. mover regras genuinamente reutilizáveis para `design_system.py`; deletar o resto;
4. manter classes específicas da página (ex.: grid do calendário) num bloco `<style>` mínimo local.

Critério de pronto: nenhuma página define fontes, paleta base ou estilo de botão próprios.

### 2.2 Animação de evolução (NEXT_STEPS §1)
- Sequência curta com CSS keyframes em `st.markdown()` + `st.empty()`: sprite atual pulsa/brilha → flash branco → sprite evoluído com glow lime;
- aplicar nos três pontos que exibem evolução: banner de `equipe.py`, card de `calendario.py`, resultado de `treino.py`;
- componente único `render_evolution_animation(from_sprite, to_sprite, to_name)` em `utils/design_system.py` (zero dependências novas).

### 2.3 Responsividade mobile (preparação para Android/WebView)
- Adicionar media queries ao design system (`@media (max-width: 640px)`): reduzir `lb-page-title`, empilhar grids de cards (equipe 3×2 → 1 coluna, ovos 4 → 2);
- testar as 5 páginas mais usadas em viewport 380px;
- baixo esforço agora que o CSS está centralizado (depende de 2.1).

### 2.4 Polimento de feedback visual
- Skeleton/placeholder (`st.spinner` ou shimmer CSS) nos blocos que fazem queries pesadas no primeiro render (hub snapshot, leaderboard, análise de treino);
- toast (`st.toast`) para ações rápidas (equipar golpe, comprar item) em vez de rerun com banner.

---

## Fase 3 — Testes e Robustez (esforço: médio · impacto: médio-alto)

### 3.1 Suíte mínima de testes (pytest)
Criar `tests/` com mocks de cursor/conexão (sem banco real):

| Alvo | Casos |
|---|---|
| `award_xp` | level-up simples, múltiplos níveis, modificador de happiness, evolução por nível, `evolution_choice` (player-choice não auto-evolui), XP Share 30%/45% (synchronize) |
| `_calc_exercise_xp` | weight/distance/time; bônus de fim de semana ×2 e cap 600 |
| `_detect_prs` | carga maior, carga igual + reps maior, sem PR, cap de 3/sessão |
| `_roll_loot_box` | distribuição de probabilidade (seed fixa), todos os tipos de prêmio |
| `apply_evolution_choice` | alvo válido normal, alvo válido regional, alvo inválido |
| `is_weekend_bonus` | sexta/sábado/domingo True; segunda False (mock de `_today_brt`) |

Adicionar `pytest>=8` como dependência de dev (não em `requirements.txt` de produção).

### 3.2 Smoke test de imports
Teste que importa `utils.db` e todas as páginas via `importlib` para pegar `SyntaxError`/import quebrado antes do deploy (o parser do Streamlit Cloud é mais restrito).

---

## Fase 4 — Performance de Aplicação (esforço: médio · impacto: médio)

### 4.1 Cache de sprites regionais (backlog antigo)
`sprite_img_tag()` reconstrói URL/base64 a cada render. Adicionar `functools.lru_cache` (ou `st.cache_data` com TTL longo) sobre a resolução de caminho→URL para `id > 10000` e assets locais já convertidos a base64.

### 4.2 Reduzir re-render de páginas pesadas
- `equipe.py` e `treino.py` concentram HTML grande: aplicar `st.fragment` nos blocos isolados (painel de golpes, tabela de exercícios, histórico) como já feito em `hub.py`/`calendario.py`;
- medir com `time.perf_counter` + `logger.debug` antes/depois (somente em dev).

### 4.3 Extração de componentes dos arquivos grandes
- `equipe.py` (~1.300 linhas): extrair painel de golpes e cards de slot para `utils/team_ui.py`;
- `treino.py`: extrair tab Análise para `utils/analytics_ui.py` ou página própria;
- sem mudança de comportamento — apenas manutenção. Fazer **depois** de 2.1 para não migrar CSS duas vezes.

### 4.4 Documentar postura de RLS
As 3 tabelas com RLS sem policy estão em deny-all para REST — seguro, mas implícito. Adicionar nota no `CLAUDE.md` (feito em 2026-06-11) e, se um dia o app passar a usar PostgREST/anon key para dados, criar policies explícitas por `user_id`.

---

## Ordem de Execução Recomendada

| # | Item | Fase | Esforço | Impacto |
|---|---|---|---|---|
| 1 | ✅ Índices de FK + drop `user_pokemons` (aplicados via MCP em 2026-06-11) | 1.1/1.2 | 30 min | Médio |
| 2 | ✅ Retry em `_new_conn()` (`db_core.py`) | 1.3 | 1 h | Alto |
| 3 | ✅ Keep-alive (`.github/workflows/supabase-keepalive.yml` — falta cadastrar secrets no GitHub) | 1.4 | 30 min | Alto |
| 4 | ❌ Leaked password protection — indisponível no plano free | 1.5 | — | — |
| 5 | ✅ Design system — lote A (hub, treino, equipe) | 2.1 | 1–2 dias | Alto |
| 6 | ✅ Design system — lotes B e C (todas as demais páginas) | 2.1 | 2–3 dias | Médio |
| 7 | ✅ Animação de evolução compartilhada (`render_evolution_animation`) | 2.2 | 0,5 dia | Médio |
| 8 | Testes pytest mínimos | 3.1/3.2 | 1–2 dias | Alto (regressão) |
| 9 | Cache de sprites + fragments | 4.1/4.2 | 1 dia | Médio |
| 10 | ✅ Responsividade mobile (media queries ≤640px no design system) | 2.3 | 1 dia | Médio (cresce com Android) |
| 11 | Extração de componentes | 4.3 | 1–2 dias | Baixo (manutenção) |

**Quick wins desta semana:** itens 1–4 (meio dia total, eliminam os achados do advisor e o risco de cold start).

---

## Critérios de Conclusão

- [x] Advisors do Supabase sem lints de FK não indexada (verificado em 2026-06-11)
- [x] `user_pokemons` removida e nota do CLAUDE.md atualizada
- [x] Primeira conexão pós-pausa não estoura exceção para o usuário (retry 0.5s/1s/2s em `_new_conn()`)
- [x] Nenhuma página define paleta/fonte/botão fora do design system (migração concluída em 2026-06-11)
- [ ] `pytest` verde cobrindo XP, PRs, loot box, weekend bonus e evolution choice
- [ ] Documentação (`CLAUDE.md`, `PLANO_IMPLEMENTACOES.md`, `NEXT_STEPS.md`) refletindo o estado real após cada fase
