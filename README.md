# Metis

Avaliador de artigos científicos. Quem submete envia o PDF de um artigo e recebe um relatório com nota por critério, justificativas, evidências e a checagem de integridade. Por trás disso, o Metis:

1. extrai o conteúdo, inclusive as figuras;
2. identifica a área do artigo;
3. checa a integridade (plágio, citações, manipulação);
4. faz três avaliações independentes, seção por seção, com modelos de linguagem de famílias diferentes;
5. valida essas avaliações com um juiz.

O sistema recomenda; não decide sozinho. Risco alto de plágio e pontos sem consenso vão para revisão humana.

> **Situação (03/11/2026):** Etapa 0.1 do M0 em andamento: ambiente `uv`, base Django e configuração centralizada. O restante do M0 está planejado em [M0 — Fundação](planning/2026-10_october/1_desenho_inicial/03_etapa_m0_fundacao.md).

## Como funciona

```text
PDF ─▶ E1 Extração ─▶ E2 Perfil ─▶ E3 Integridade ─┬─▶ E4 Avaliação ─▶ E5 Consolidação ─▶ relatório
       texto, refs,   área e       similaridade,   │   3 avaliadores    mediana,
       figuras        Question     citações        │   por seção, juiz  meta-review
       descritas                                   └─▶ risco alto: revisão humana
```

Cada estágio roda numa task Celery curta, com checkpoint no banco. Os agentes de cada estágio rodam com Agno. O passo a passo está em [Fluxo de uma avaliação](docs/evaluation_flow.md).

## Stack

Django 6 + Django Ninja · Celery + Redis · PostgreSQL 18 + pgvector · Agno 3 · GROBID + Docling · Docker

## Documentação

- [docs/](docs/README.md): como o sistema funciona (arquitetura, fluxo, orquestração, cada estágio, modelos de dados, infraestrutura, convenções).
- [planning/](planning/2026-10_october/1_desenho_inicial/00_sumario.md): decisões, diagnóstico, roteiro M0–M6, riscos e testes.

## Dados

`dataset_project/` tem o loader do [PeerRead](https://github.com/allenai/PeerRead): artigos de computação com reviews e notas por aspecto. É usado para semear o corpus de similaridade e para calibrar as avaliações. Veja os limites em [01_diagnostico.md](planning/2026-10_october/1_desenho_inicial/01_diagnostico.md#o-peerread-dataset_project).

## Desenvolvimento

Requer Python 3.14 e `uv`. Para preparar o ambiente e executar o servidor Django:

```bash
uv sync --group dev --group analysis
cp .env.example .env
uv run python manage.py check
```

O grupo `analysis` fornece Jupyter e pandas para o notebook PeerRead. Para iniciar o notebook, use `uv run jupyter lab` e selecione o kernel do ambiente `.venv`.
