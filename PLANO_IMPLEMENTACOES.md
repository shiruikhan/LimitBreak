# LimitBreak — Plano de Implementações Pendentes
> Atualizado em 2026-05-14 — retomar aqui na próxima sessão.

---

## ✅ Já feito (não refazer)

| Item | Arquivo |
|---|---|
| XSS: `html.escape()` no username do sidebar | `app.py` |
| `_BYPASS_LEVEL = 36` movido para nível de módulo | `utils/db.py` |
| TTL 3600s em `get_all_pokemon`, `get_all_pokemon_with_types`, `get_shop_items` | `utils/db.py` |
| Cursor padronizado em `get_battle_opponents` e `get_daily_battle_count` | `utils/db.py` |
| Janela de 400 dias em `_unique_workout_days_brt()` | `utils/db.py` |
| Rollback na conexão capturada em `create_workout_day` e `add_exercise_to_day` | `utils/db.py` |
| `_collect_achievement_stats()` consolidada em 1 query com 6 CTEs | `utils/db.py` |
| `migrate_performance_stage3_indexes.sql` aplicado via Supabase MCP | Supabase prod |
| CLAUDE.md atualizado com funções ausentes e backlog de dívida técnica | `CLAUDE.md` |
| `_exercise_metric_sql()` removida; CASE WHEN inlinado nas 3 funções de analytics | `utils/db.py` |
| Cursors de `start_battle`, `finalize_battle`, `get_battle_history`, `get_battle_detail` padronizados | `utils/db.py` |
| Logging real (loguru) em `do_checkin`, `award_xp`, `finalize_battle`, `do_exercise_event` | `utils/db.py`, `utils/logger.py`, `requirements.txt` |
| `import json` e `from utils.abilities import apply_blaze` movidos para nível de módulo | `utils/db.py` |
| `do_exercise_event()` refatorada: 3 blocos pós-commit eliminados; SAVEPOINTs nos spawns e efeitos secundários; `except: pass` substituídos por `logger.warning()` | `utils/db.py` |
| `utils/db_core.py` criado (617 linhas) — conexão, BRT helpers, stats/IV/EV/Nature, sprite helpers, `_insert_user_pokemon`, `_LOOT_VITAMINS` | `utils/db_core.py` |
| `utils/db_catalog.py` criado (114 linhas) — queries de Pokédex somente-leitura (5 funções) | `utils/db_catalog.py` |
| `utils/db.py` re-exporta `db_core` e `db_catalog`; compatibilidade total de imports preservada | `utils/db.py` |

---

## 🏗️ Pendentes — Split de `utils/db.py`

**Contexto:** `db.py` tem 4.946 linhas. `db_core` e `db_catalog` já foram extraídos.
Faltam 6 módulos temáticos. A facade `db.py` re-exporta tudo — nenhum import externo precisa mudar.

### Estado atual do split

| Módulo | Status | Conteúdo |
|---|---|---|
| `utils/db_core.py` | ✅ Feito | Conexão, BRT, stats, sprites, `_insert_user_pokemon` |
| `utils/db_catalog.py` | ✅ Feito | Pokédex somente-leitura (5 funções) |
| `utils/db_user.py` | ⏳ Pendente | Perfil, equipe, bench, moves, stat boosts |
| `utils/db_shop.py` | ⏳ Pendente | Loja, inventário, loot box, pedras, nature mint |
| `utils/db_combat.py` | ⏳ Pendente | Batalhas PvP (9 funções) |
| `utils/db_workout.py` | ⏳ Pendente | Exercícios, treino, spawn, PRs, ovos, analytics, rotinas |
| `utils/db_progression.py` | ⏳ Pendente | `award_xp`, XP Share, check-in, descanso, conquistas, missões, rival, desafio |
| `utils/db_admin.py` | ⏳ Pendente | Admin, logs, leaderboard |

**Ordem de extração:** `db_user` → `db_shop` → `db_combat` → `db_workout` → `db_progression` → `db_admin`

---

## 📋 Ordem de execução sugerida

1. **Continuar split de db.py** — extrair os 6 módulos restantes na ordem acima.

---

## 🔑 Contexto técnico rápido

- **Stack:** Python + Streamlit + PostgreSQL (Supabase) + psycopg2 direto
- **Banco:** projeto `nxtcetqtnmqpamhfpjdm` no Supabase (sa-east-1)
- **Arquivo crítico:** `utils/db.py` — todas as queries passam por aqui
- **Cache layer:** `utils/app_cache.py` — wrappers `@st.cache_data` sobre db.py
- **Logger:** `utils/logger.py` — importar com `from utils.logger import logger`
- **Auth:** Supabase Auth + cookie `lb_refresh_token` (30 dias)
- **Deploy:** Streamlit Community Cloud — push no branch `master` faz deploy automático
- **Índices em produção:** 4 índices de performance ativos (`idx_workout_logs_*`, `idx_exercise_logs_*`, `idx_user_battles_*`)
