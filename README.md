# Metis

Avaliador de artigos científicos. Quem submete envia o PDF de um artigo e recebe um relatório com nota por critério, justificativas, evidências e a checagem de integridade. Por trás disso, o Metis:

1. extrai o conteúdo, inclusive as figuras;
2. identifica a área do artigo;
3. checa a integridade (plágio, citações, manipulação);
4. faz três avaliações independentes, seção por seção, com modelos de linguagem de famílias diferentes;
5. valida essas avaliações com um juiz.

O sistema recomenda; não decide sozinho. Risco alto de plágio e pontos sem consenso vão para revisão humana.

> **Situação (12/11/2026):** M0 implementado (etapas 0.1–0.7), com os estágios ainda em stub e a [verificação manual do I1](planning/2026-11_november/1_plano_completo/12_testes_e_verificacao.md#i1--m0) passando no `docker compose`. Na fase 2 do [roteiro](planning/2026-11_november/1_plano_completo/03_roteiro_e_trilhas.md), o E1 já divide o artigo de verdade, com chamadas ao Gemini conferidas contra o PDF, separa as referências em campos e liga cada citação à sua referência ([Extração](docs/extraction.md)); os demais estágios seguem em stub. A equipe trabalha em 4 módulos, com uma branch por etapa e PR para a `dev`: [divisão em módulos](planning/2026-11_november/2_divisao_equipe/divisao_em_modulos.html) (abra no navegador).

## Como funciona

```text
PDF ─▶ E1 Extração ─▶ E2 Perfil ─▶ E3 Integridade ─┬─▶ E4 Avaliação ─▶ E5 Consolidação ─▶ relatório
       texto, refs,   área e       similaridade,   │   3 avaliadores    mediana,
       figuras        Question     citações        │   por seção, juiz  meta-review
       descritas                                   └─▶ risco alto: revisão humana
```

Cada estágio roda numa task Celery curta, com checkpoint no banco. Os agentes de cada estágio rodam com Agno. O passo a passo está em [Fluxo de uma avaliação](docs/evaluation_flow.md).

## Stack

Django 6 + Django Ninja · Celery + Redis · PostgreSQL 18 + pgvector · Agno 3 + Gemini · pypdf · Docker

## Documentação

- [docs/](docs/README.md): como o sistema funciona (arquitetura, fluxo, orquestração, cada estágio, modelos de dados, infraestrutura, convenções).
- [planning/](planning/2026-10_october/1_desenho_inicial/00_sumario.md): decisões, diagnóstico, roteiro M0–M6, riscos e testes.

## Dados

`dataset_project/` tem o loader do [PeerRead](https://github.com/allenai/PeerRead): artigos de computação com reviews e notas por aspecto. É usado para semear o corpus de similaridade e para calibrar as avaliações. Veja os limites em [01_diagnostico.md](planning/2026-10_october/1_desenho_inicial/01_diagnostico.md#o-peerread-dataset_project).

## Como rodar

Requer Docker com o Compose v2. O compose sobe a API, os workers Celery, o beat, o Flower, o Postgres e o Redis ([Infraestrutura](docs/infrastructure.md)).

```bash
cp .env.example .env            # preencha METIS_SECRET_KEY e METIS_API_TOKEN
docker compose up -d --build
curl http://localhost:8100/health/                         # {"status": "ok"}
docker compose exec web python manage.py createsuperuser   # admin em http://localhost:8100/admin/
```

Para enviar um artigo e acompanhar o run (o token é o `METIS_API_TOKEN` do `.env`):

```bash
curl -H "Authorization: Bearer $TOKEN" -F external_id=artigo-1 -F file=@artigo.pdf \
  http://localhost:8100/api/attempts                       # 202, com o run_id
curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/api/runs/<run_id>
```

O Flower fica em http://127.0.0.1:5556. Com `METIS_DEBUG=true`, a documentação da API fica em http://localhost:8100/docs.

## Desenvolvimento

Requer Python 3.14 e `uv`. Para preparar o ambiente e executar o servidor Django:

```bash
uv sync --group dev --group analysis
cp .env.example .env
uv run python manage.py check
```

Os testes usam o Postgres do compose, publicado em `127.0.0.1:5440`:

```bash
docker compose up -d postgres
uv run ruff check && uv run ruff format --check && uv run mypy projects/correction && uv run pytest
```

O grupo `analysis` fornece Jupyter e pandas para o notebook PeerRead. Para iniciar o notebook, use `uv run jupyter lab` e selecione o kernel do ambiente `.venv`.

O código Django fica em `projects/correction/` (`metis/` e apps de domínio); `dataset_project/` mantém os dados e a análise PeerRead separados.
