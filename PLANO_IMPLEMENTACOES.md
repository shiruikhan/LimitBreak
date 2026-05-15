# LimitBreak — Snapshot de Implementação
> Atualizado em 2026-05-15 após auditoria e sincronização da documentação.

---

## Estado confirmado do código

### Arquitetura de banco

O split de `utils/db.py` está concluído e não deve mais aparecer como pendência.

| Módulo | Status | Conteúdo |
|---|---|---|
| `utils/db.py` | ✅ Facade | Reexporta a API pública para manter compatibilidade de imports |
| `utils/db_core.py` | ✅ Ativo | Conexão, helpers BRT, stats, sprites, utilitários base |
| `utils/db_catalog.py` | ✅ Ativo | Pokédex somente-leitura |
| `utils/db_user.py` | ✅ Ativo | Perfil, equipe, bench, moves, boosts |
| `utils/db_shop.py` | ✅ Ativo | Loja, inventário, loot box, XP Share, pedras, mint |
| `utils/db_combat.py` | ✅ Ativo | Arena PvP, dano, turnos, histórico |
| `utils/db_workout.py` | ✅ Ativo | Exercícios, treino, rotinas, ovos, analytics |
| `utils/db_progression.py` | ✅ Ativo | XP, check-in, descanso, conquistas, missões, rival, desafio |
| `utils/db_admin.py` | ✅ Ativo | Admin, leaderboard, logs |

### Infra já sincronizada

| Item | Status |
|---|---|
| `loguru` presente em `requirements.txt` e usado via `utils/logger.py` | ✅ |
| `utils/app_cache.py` centraliza caches de leitura e invalidação por domínio | ✅ |
| Bootstrap controlado de missões em `app.py` com `ensure_current_user_missions()` | ✅ |
| Navegação principal via `st.navigation(..., position="hidden")` + sidebar customizada | ✅ |
| Página standalone da mochila (`pages/mochila.py`) e página de ovos (`pages/ovos.py`) | ✅ |

---

## Itens em aberto

Estas continuam sendo as frentes técnicas úteis para próximas sessões:

| Item | Descrição | Prioridade |
|---|---|---|
| Testes focados | Cobrir `award_xp`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements` | Média |
| Retry de conexão | Adicionar backoff em `get_connection()` para reduzir falhas de cold start | Média |
| Cache de sprites regionais | Evitar fetch/reconstrução repetida de URLs para forms regionais | Baixa |
| Higiene de documentação | Manter `README.md`, `NEXT_STEPS.md` e `CLAUDE.md` sincronizados após mudanças estruturais | Baixa |

---

## Referência rápida

- **Stack:** Python + Streamlit + PostgreSQL (Supabase) + `psycopg2`
- **Auth:** Supabase Auth + cookie `lb_refresh_token` com rotação
- **Cache:** `utils/app_cache.py`
- **Logger:** `from utils.logger import logger`
- **Deploy:** Streamlit Community Cloud com deploy automático no branch `master`
- **Arquivos de verdade operacional:** `CLAUDE.md` para arquitetura detalhada, `NEXT_STEPS.md` para backlog de produto

---

## Nota de manutenção

Se uma feature já existe em código, não manter este arquivo como backlog daquela entrega. Use este documento como snapshot técnico do estado real do projeto e como ponto de retomada para a próxima sessão.
