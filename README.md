# 🏋️‍♂️ LimitBreak

Aplicativo web de acompanhamento de treinos de musculação com sistema de gamificação inspirado em Pokémon. O usuário progride no mundo real (treinos, frequência, carga) e isso reflete diretamente em sua jornada virtual — XP, evoluções, capturas e colecionismo.

---

## 🎮 O que já funciona

- **Autenticação completa** — login, cadastro e sessão persistente via Supabase Auth
- **Seleção de Pokémon inicial** — 27 iniciais (Gen 1–9) com um easter egg secreto desbloqueável
- **Pokédex interativo** — 1.025 Pokémon com sprites, tipos, base stats, moveset por nível e cadeia evolutiva completa
- **Gerenciamento de equipe** — até 6 Pokémon com moveset equipável (4 slots por Pokémon, respeitando nível)

---

## 🗺️ Próximas funcionalidades

| Funcionalidade | Status |
|---|---|
| XP por exercício realizado | ⏳ Aguarda módulo de treinos |
| Evolução automática por nível | 🔜 A implementar |
| Sistema de encontros e captura | 🔜 A implementar |
| Pokédex pessoal (capturados vs não capturados) | 🔜 A implementar |
| Calendário de presença com moedas | 🔜 A implementar |
| Loja virtual (XP Share, skins regionais) | 🔜 A implementar |

---

## ⚙️ Stack

- **Frontend/Backend:** Python + Streamlit
- **Banco de dados:** PostgreSQL (Supabase)
- **Autenticação:** Supabase Auth
- **Dados Pokémon:** PokéAPI

---

## 🚀 Como rodar localmente

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Criar .env com as credenciais PostgreSQL
# 3. Criar .streamlit/secrets.toml com as credenciais Supabase Auth
# 4. (Primeira vez) Executar scripts/create_user_tables.sql no Supabase
# 5. (Primeira vez) Rodar os scripts de seed

streamlit run app.py
```

Veja o `CLAUDE.md` para documentação técnica completa — schema do banco, ordem dos seeds, detalhes de arquitetura e convenções de código.

---

## 🔀 Divisão de responsabilidades

Este repositório é responsável exclusivamente pela **gamificação** (Pokédex, XP, capturas, equipe, loja).  
O módulo de treinos (exercícios, planos, biomecânica, GIFs) é desenvolvido separadamente — a integração ocorre via banco de dados.
