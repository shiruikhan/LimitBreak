# LimitBreak — Roadmap Aberto

> Atualizado: 06 de maio de 2026.
>
> Documento canônico de backlog. Mantém apenas itens ainda não implementados, consolidados a partir de `suggestions.md` e do antigo `NEXT_STEPS.md`.

---

## Prioridades de Produto

### 1. Animação de Evolução

**Objetivo:** tornar o momento de evolução mais memorável e recompensador visualmente.

**Escopo:**
- substituir o banner estático por uma sequência curta;
- mostrar sprite atual com efeito visual, transição e sprite evoluído;
- implementar com CSS em `st.markdown()` e containers temporários via `st.empty()`;
- manter zero dependências novas.

**Esforço:** baixo  
**Impacto:** médio

---

### 2. Indicador de Equilíbrio Muscular

**Objetivo:** expor lacunas recentes de treino e incentivar retorno por grupo muscular.

**Escopo:**
- agregar `body_parts` dos últimos 7 dias a partir de `exercise_logs JOIN exercises`;
- exibir badges ou cards por grupo muscular em `pages/treino.py` ou `pages/hub.py`;
- destacar grupos "frios" sem treino recente;
- opcionalmente sugerir tipos/spawns relacionados ao grupo selecionado.

**Esforço:** baixo  
**Impacto:** alto

---

### 3. Perfil Público do Treinador

**Objetivo:** dar identidade social ao usuário e transformar leaderboard em porta de entrada para descoberta.

**Escopo:**
- criar `pages/perfil.py`;
- exibir avatar, insígnias, top 3 Pokémon da equipe e stats resumidos;
- ligar o acesso a partir do leaderboard;
- manter implementação somente leitura, reutilizando dados já existentes.

**Esforço:** médio  
**Impacto:** médio

---

### 4. Compartilhamento de Rotinas

**Objetivo:** permitir que usuários publiquem e copiem rotinas, aumentando reutilização e senso de comunidade.

**Escopo:**
- adicionar `is_public` e `copies` em `workout_sheets`;
- listar rotinas públicas com autor e total de cópias;
- criar ação "Copiar para minha conta" reutilizando o fluxo já existente de criação de rotina;
- decidir regras mínimas de curadoria e ordenação da biblioteca.

**Esforço:** baixo  
**Impacto:** médio

---

## V2 Social

### 5. Sistema de Trocas de Pokémon

**Objetivo:** habilitar trocas entre usuários e abrir caminho para evoluções por troca sem depender do bypass de nível.

**Escopo:**
- criar tabela `trade_proposals`;
- suportar proposta, aceite, recusa e expiração;
- trocar Pokémon com segurança e validar evolução por troca após conclusão;
- limitar propostas simultâneas por usuário.

**Dependências:**
- fluxo assíncrono claro para propostas pendentes;
- idealmente alguma forma de notificação ou inbox.

**Esforço:** alto  
**Impacto:** alto

---

### 6. Sistema de Guildas

**Objetivo:** introduzir accountability social com progresso coletivo e recompensas de grupo.

**Escopo:**
- grupos pequenos de treinadores;
- XP coletivo semanal;
- metas e recompensas compartilhadas;
- gestão de entrada, saída e ownership do grupo.

**Risco principal:** complexidade de estado e moderação aumenta bastante para a base atual.

**Esforço:** alto  
**Impacto:** muito alto

---

## Conteúdo Opcional

### 7. Formas de Paldea

**Objetivo:** expandir cobertura de formas especiais sem mexer no loop principal.

**Escopo:**
- popular espécies e formas faltantes;
- revisar pipeline de seed para regionais;
- validar sprites e compatibilidade com a Pokédex.

**Observação:** item de baixo impacto imediato; manter atrás das entregas sociais.

**Esforço:** baixo a médio  
**Impacto:** baixo

---

## Dívida Técnica

| Item | Descrição | Urgência |
|---|---|---|
| `db.py` com ~4400 linhas | Split em submódulos (`pokemon`, `progression`, `combat`, `shop`, `workout`, `admin`) | Baixa |
| Sem testes automatizados | Cobrir `award_xp`, `_roll_loot_box`, `_detect_prs`, `check_and_award_achievements` | Baixa |
| Retry na conexão DB | Adicionar backoff em `get_connection()` para reduzir falha em cold start | Baixa |
| Cache de sprites regionais | Evitar HTTP GET repetido para forms regionais (`id > 10000`) | Baixa |

---

## Ordem Recomendada

1. Indicador de Equilíbrio Muscular
2. Animação de Evolução
3. Perfil Público do Treinador
4. Compartilhamento de Rotinas
5. Sistema de Trocas de Pokémon
6. Sistema de Guildas
7. Formas de Paldea

---

## Resumo

| Item | Esforço | Impacto | Status |
|---|---|---|---|
| Animação de evolução | Baixo | Médio | Aberto |
| Indicador de equilíbrio muscular | Baixo | Alto | Aberto |
| Perfil público do treinador | Médio | Médio | Aberto |
| Compartilhamento de rotinas | Baixo | Médio | Aberto |
| Sistema de trocas | Alto | Alto | V2 |
| Sistema de guildas | Alto | Muito alto | V2 |
| Formas de Paldea | Baixo a médio | Baixo | Backlog |
| Refactor de `db.py` | Alto | Médio | Dívida técnica |
| Testes automatizados | Médio | Alto | Dívida técnica |
| Retry de conexão DB | Baixo | Médio | Dívida técnica |
| Cache de sprites regionais | Baixo | Baixo | Dívida técnica |
