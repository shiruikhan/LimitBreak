# LimitBreak

Aplicativo web em Streamlit para acompanhamento de treinos com gamificação inspirada em Pokemon. O progresso do mundo real alimenta XP, evolucoes, capturas, check-ins, colecao, missoes e batalhas.

---

## Estado atual

### Fluxo principal

- Autenticacao completa com Supabase Auth, cookies de sessao e restauracao automatica por refresh token
- Onboarding com escolha de Pokemon inicial e easter egg secreto
- Hub central (`pages/hub.py`) para acesso rapido a equipe, treino, calendario, arena, Pokédex e loja
- Sidebar organizada por grupos com navegacao customizada e menos ruido visual

### Sistemas live

- Equipe com 6 slots, moves equipaveis, XP Share, evolucoes e banco de Pokemon
- Pokédex nacional e Pokédex pessoal com filtros e progresso de captura
- Calendario de check-in com streak, moedas, bonus de XP Share e chance de spawn
- Loja e mochila com pedras, vitaminas, XP Share, Loot Box e Nature Mint
- Arena PvP assíncrona com limite diario, log de turnos, XP e moedas
- Modulo de treino com rotinas, biblioteca de exercicios, registro de sessoes, PRs, ovos e habilidades passivas
- Missoes diarias e semanais
- Conquistas e leaderboard
- Painel admin para operacoes do sistema

### Performance e UX

- Cache compartilhado em `utils/app_cache.py` com `@st.cache_data` para leituras repetidas por usuario
- Cliente Supabase cacheado com `@st.cache_resource`
- Uso de `st.fragment` em areas isoladas como hub e calendario para reduzir reruns completos

---

## Stack

- Frontend/Backend: Python + Streamlit
- Banco de dados: PostgreSQL no Supabase
- Autenticacao: Supabase Auth
- Acesso SQL: `psycopg2`
- Persistencia de sessao: `extra-streamlit-components`
- Dados Pokemon: PokéAPI + assets locais/CDN

---

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Configuracao necessaria

1. Criar `.streamlit/secrets.toml` com as secoes `[supabase]` e `[database]`
2. Opcionalmente criar `.env` como fallback para a conexao PostgreSQL
3. Executar `scripts/create_user_tables.sql` no Supabase
4. Rodar os seeds principais:

```bash
python scripts/seed_types.py
python scripts/seed_pokedex.py
python scripts/seed_evolutions.py
python scripts/seed_stats.py
python scripts/seed_shop_items.py
python scripts/seed_regional_species.py
```

---

## Documentacao

- `CLAUDE.md`: arquitetura, schema, funcoes importantes, navegacao atual e convencoes
- `NEXT_STEPS.md`: roadmap atualizado e prioridades de produto

---

## Escopo do repositorio

Este repositorio cobre o app completo de gamificacao e treino em Streamlit:

- autenticacao
- navegação e shell da aplicacao
- equipe, Pokédex, loja, calendario, batalha
- biblioteca, rotinas e registro de treino
- missoes, conquistas, leaderboard e admin
