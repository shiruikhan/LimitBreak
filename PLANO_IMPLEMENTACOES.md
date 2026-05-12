# LimitBreak — Plano de Implementações Pendentes
> Atualizado em 2026-05-12 — retomar aqui na próxima sessão.

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

---

## 🏗️ Pendentes — Alto Impacto

### 1. Quebrar `utils/db.py` em módulos temáticos
**Contexto:** o arquivo tem ~5.500 linhas. Dificulta navegação, testes e manutenção.

**Divisão sugerida:**
- `utils/db_core.py` — `get_connection()`, `_today_brt()`, constantes, helpers BRT
- `utils/db_catalog.py` — pokédex, exercícios, loja, tipos (somente leitura)
- `utils/db_user.py` — perfil, equipe, banco, movimentos, stats, IVs/EVs
- `utils/db_gameplay.py` — XP, batalhas, check-in, missões, conquistas, ovos
- `utils/db_workout.py` — rotinas, treinos, analytics, PRs
- `utils/db_admin.py` — funções admin, logs do sistema
- `utils/db.py` — mantém apenas `from utils.db_* import *` para não quebrar nada

**Atenção:** todos os `pages/` e `utils/` importam `from utils.db import ...`. A re-exportação central evita quebrar qualquer import existente.

**Como executar:**
1. Criar cada módulo novo
2. Mover as funções grupo a grupo
3. Adicionar re-exports em `utils/db.py`
4. Testar que os imports continuam funcionando

---

## 📋 Ordem de execução sugerida

1. **Tarefa 1** (quebrar db.py) — maior esforço mas maior ganho de manutenibilidade. Começar por `db_core.py` + `db_catalog.py`, que têm zero dependências circulares.

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
