# LimitBreak

LimitBreak é um aplicativo web pessoal para desenvolvedores que serve como guia e instrutor de treinos de academia. O foco inicial é demonstrar e ensinar treinos usando a API do Exercisedb, além de permitir perfis individuais com atividades e calendário de treinos.

## Objetivo

- Criar um app web de uso pessoal para desenvolvedores.
- Disponibilizar um guia de exercícios e planos de treino.
- Usar a API do Exercisedb para demonstrar exercícios reais.
- Permitir cada dev ter um perfil de treino com histórico e calendário.

## Funcionalidades iniciais

- Exploração de exercícios pela API do Exercisedb.
- Visualização de detalhes de exercícios.
- Perfil individual de treino para cada usuário.
- Agenda/calendário de treinos e histórico de atividades.
- Possível hospedagem via Git (Pages / hosting estático).

## Estrutura proposta

- `public/`: ativos públicos, imagens, favicon e arquivos estáticos.
- `src/`: código-fonte do aplicativo web.
- `docs/`: documentação do projeto, requisitos e roteiro.

## API externa

A aplicação usará a API do Exercisedb para buscar informações sobre exercícios. Exemplo de URL:

- `https://exercisedb.p.rapidapi.com/exercises`

> Documentação da API: https://github.com/exercisedb/exercisedb-api

## Próximos passos

1. Definir framework front-end (React, Vue, Svelte, etc.).
2. Criar tela inicial com catálogo de exercícios.
3. Implementar perfil de usuário e calendário de treinos.
4. Adicionar autenticação leve e persistência local.

## Licença

Este projeto é inicial e aberto para uso pessoal dos desenvolvedores.
