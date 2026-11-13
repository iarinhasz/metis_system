# Metis

Avaliador de artigos científicos em construção. O fluxo alvo recebe um PDF e
produz um relatório com notas por critério, justificativas, evidências e checagem
de integridade:

1. extrai o conteúdo, inclusive as figuras;
2. identifica a área do artigo;
3. checa a integridade (plágio, citações, manipulação);
4. faz três avaliações independentes, seção por seção, em três slots de duas famílias (GPT e Gemini);
5. valida essas avaliações com um juiz.

O sistema recomenda; não decide sozinho. Risco alto de plágio e pontos sem consenso vão para revisão humana.

> **Situação (13/11/2026):** plataforma, E1 (extração), E2 (perfil/Question),
> curadoria, rubric check, E5 (consolidação), custo no admin e base de evals
> implementados. **E3 e E4 ainda são stubs**: sem rodadas julgadas de A/B/C,
> E5 retorna `waiting_setup`. O pipeline ainda não produz uma avaliação completa
> de um PDF real. Veja [estado do módulo, evidências e metas](docs/status_and_metrics.md)
> e a [divisão em módulos](planning/2026-11_november/2_divisao_equipe/divisao_em_modulos.html).

## Fluxo alvo

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
- [planning/](planning/2026-11_november/1_plano_completo/00_sumario.md): plano completo M0–M6, decisões, riscos e testes. O desenho de outubro é o histórico.

## Dados

`dataset_project/` tem o loader do PeerRead: artigos de computação com reviews e
notas por aspecto. Já serviu à medição de citações do E1; corpus de similaridade
e calibração das notas permanecem planejados. A amostra de profiling contém 30
artigos PLOS ONE com rótulos provisórios. [Resultados e limites](docs/status_and_metrics.md#medições-disponíveis).

## Como rodar

Requer Docker com o Compose v2. O compose sobe a API, os workers Celery, o beat, o Flower, o Postgres e o Redis ([Infraestrutura](docs/infrastructure.md)).

```bash
cp .env.example .env            # preencha METIS_SECRET_KEY e METIS_API_TOKEN
docker compose up -d --build
curl http://localhost:8100/health/                         # {"status": "ok"}
docker compose exec web python manage.py createsuperuser   # admin em http://localhost:8100/admin/
```

Preencha também a chave do Google para E1 e a do provedor do papel `fast` para
E2. Antes do perfil, carregue a taxonomia e semeie os rascunhos; os comandos
começam em dry-run e gravam com `--execute`:

```bash
docker compose exec web python manage.py load_taxonomy --execute
docker compose exec web python manage.py seed_questions --execute
```

Revise, valide e ative a Question genérica no admin. Sem taxonomia/Question,
o run fica em `waiting_setup`. [Configuração e curadoria](docs/questions_and_profiling.md#questions-iniciais-e-benchmark-27).

Para enviar um artigo e acompanhar o run (o token é o `METIS_API_TOKEN` do `.env`):

```bash
curl -H "Authorization: Bearer $TOKEN" -F external_id=artigo-1 -F file=@artigo.pdf \
  http://localhost:8100/api/attempts                       # 202, com o run_id
curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/api/runs/<run_id>
```

`GET /api/runs/<run_id>/report` retorna JSON (ou `?format=markdown`) somente
quando o run está `done`; antes disso retorna `409`. E4 ainda precisa ser
implementado para gerar as avaliações que alimentam esse relatório.

O Flower fica em http://127.0.0.1:5556. Com `METIS_DEBUG=true`, a documentação da API fica em http://localhost:8100/docs.

## Desenvolvimento

Requer Python 3.14 e `uv`. Para preparar e conferir o ambiente Django:

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
