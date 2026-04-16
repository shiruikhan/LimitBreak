# Integração com a API Exercisedb

O LimitBreak usará a API Exercisedb para buscar dados de exercícios e mostrar informações úteis aos usuários.

## Base da API

- Endpoint principal: `https://exercisedb.p.rapidapi.com/exercises`

## Dados esperados

A API retorna exercícios com campos como:

- `id`
- `name`
- `bodyPart`
- `target`
- `equipment`
- `gifUrl`
- `instructions`

## Uso no app

1. Buscar lista de exercícios.
2. Filtrar por grupo muscular, equipamento ou tipo de treino.
3. Exibir detalhes do exercício selecionado.
4. Usar GIF ou imagens para demonstrar o movimento.

## Considerações

- Verificar se a API exige chaves ou quotas.
- Considerar cache local para a navegação e melhor performance.
- Criar componentes de interface reutilizáveis para cards e fichas de exercício.
