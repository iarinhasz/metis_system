# Infraestrutura

## Serviços do docker-compose

| Serviço | Imagem e comando | Papel | Porta no host |
|---|---|---|---|
| `web` | Imagem do projeto: `migrate` + gunicorn (o `collectstatic` roda no build) | API, admin, healthcheck | `${METIS_WEB_PORT:-8100}` |
| `worker-extraction` | `celery worker -Q extraction`, concorrência 1–2 (começa em 1), limite de memória (`mem_limit: 2g`) | E1 | — |
| `worker-integrity` | `celery worker -Q integrity` | E3 | — |
| `worker-evaluation` | `celery worker -Q evaluation,default` | E2, E4, E5 e reconciliador | — |
| `beat` | `celery beat`, com o arquivo de agenda em `/tmp` | Agenda o reconciliador | — |
| `flower` | `celery flower` (imagem própria, com o extra `flower`) | Monitoramento das filas | `127.0.0.1:${METIS_FLOWER_PORT:-5556}` |
| `postgres` | `pgvector/pgvector:pg18` | Banco e vetores | `127.0.0.1:${METIS_POSTGRES_PUBLISHED_PORT:-5440}` |
| `redis` | `redis:7-alpine` | Broker do Celery | — (só na rede interna) |

- **Mesma imagem para `web` e workers**; só o `command` muda.
- **Configuração:** todos os serviços do projeto leem o `.env` (`env_file`). O bloco `x-common-env` (YAML anchor) troca só o que muda dentro da rede do compose: banco em `postgres:5432`, broker em `redis://redis:6379/0` e `METIS_MEDIA_ROOT=/data/media`.
- **Ordem de subida:** o `web` espera o Postgres e o Redis saudáveis e aplica as migrações antes do gunicorn. Workers, beat e flower esperam o `web` saudável, de modo que nunca rodam sobre um banco sem migração.
- **Volumes:**
  - `pgdata`, montado em `/var/lib/postgresql`: o Postgres 18 mudou o layout do `PGDATA` na imagem oficial;
  - `media`, montado em `/data/media`, com PDFs e recortes, compartilhado entre `web` e workers.
- **Portas:** as padrão evitam colisão com portas comuns em máquinas de desenvolvimento (8000, 5432/5433, 5555). Todas são configuráveis no `.env`.

## A imagem

- `python:3.14-slim` + `uv` com versão fixa; usuário não-root (`app`); venv em `/opt/venv`; `uv sync --frozen --no-dev`. O flower monta a mesma receita com o build arg `UV_SYNC_ARGS="--extra flower"`.
- O `.dockerignore` é uma lista de permissão: entram só `pyproject.toml`, `uv.lock`, `.python-version`, `manage.py` e `projects/` (sem `media/` e sem caches). O `.env`, o `.git`, o `dataset_project/` e os docs ficam de fora.
- O build falha se um `.env` escapar para o contexto de build.
- O `collectstatic` roda no build; o WhiteNoise serve os estáticos.
- `HEALTHCHECK` em `/health/` (testa o banco), pelo `127.0.0.1`, que precisa estar em `METIS_ALLOWED_HOSTS`. Workers, beat e flower desligam o healthcheck.
- Tamanho: ~625 MB, com o Agno e a SDK do Google (E1).
- Nenhum serviço de parse de PDF: o GROBID foi descartado em 11/11/2026 (imagem de 1,7 GB, 3,6 GB de RAM). Se o Docling entrar para as figuras (1.6), ele traz os modelos do torch e precisa ser medido antes.

## Configuração

Toda configuração passa por `metis/config.py` (pydantic-settings, prefixo `METIS_`), validado na subida. O `.env.example` lista todas as variáveis.

| Variável | Para quê | Marco |
|---|---|---|
| `METIS_SECRET_KEY`, `METIS_DEBUG`, `METIS_ALLOWED_HOSTS`, `METIS_CSRF_TRUSTED_ORIGINS` | Django | M0 |
| `METIS_POSTGRES_HOST`, `_PORT`, `_DB`, `_USER`, `_PASSWORD` | Banco | M0 |
| `METIS_REDIS_URL` | Broker | M0 |
| `METIS_API_TOKEN` | Token do sistema que submete; vazio deixa a API bloqueada | M0 |
| `METIS_MEDIA_ROOT`, `METIS_MAX_UPLOAD_MB` | Arquivos | M0 |
| `METIS_STAGE_MAX_RETRIES`, `METIS_STAGE_RETRY_BACKOFF_SECONDS`, `METIS_STAGE_RETRY_BACKOFF_MAX_SECONDS` | Retries | M0 |
| `METIS_STAGE_SOFT_TIME_LIMIT_SECONDS`, `METIS_STAGE_TIME_LIMIT_SECONDS`, `METIS_BROKER_VISIBILITY_TIMEOUT_SECONDS` | Limites de tempo | M0 |
| `METIS_RECONCILE_INTERVAL_SECONDS`, `METIS_REPUBLISH_AFTER_SECONDS`, `METIS_STALE_STAGE_AFTER_SECONDS`, `METIS_MAX_REPUBLISH`, `METIS_MAX_STAGE_CLAIMS` | Reconciliador | M0 |
| `METIS_WEB_PORT`, `METIS_FLOWER_PORT`, `METIS_POSTGRES_PUBLISHED_PORT` | Portas publicadas no host; lidas só pelo compose, não pelo `config.py` | M0 |
| `GEMINI_KEY` | Chave do Gemini, lida sem o prefixo `METIS_`. Usada pelo E1 | M1 |
| `METIS_LLM_TIMEOUT_SECONDS` | Timeout de cada chamada ao modelo; menor que o soft limit da task | M1 |
| `METIS_OPENAI_API_KEY` | Provedor OpenAI, quando os slots com GPT entrarem. Um 3º provedor (para o slot C) entra com a própria chave | M3 |
| `ModelSpec` por papel (`evaluator_a`, `evaluator_b`, `evaluator_c`, `judge_openai`, `judge_google`, `meta_reviewer`, `vision`, `fast`, `adjudicator`) | Qual modelo cumpre cada papel (ver [Agentes e workflows](agents.md#modelos-e-papéis)) | M1–M3 |
| `METIS_LLM_MAX_CONCURRENCY` | Chamadas simultâneas por provedor, por worker (`ProviderLimiter`) | M1 |
| `METIS_CROSSREF_MAILTO`, `METIS_OPENALEX_API_KEY`, `METIS_SEMANTIC_SCHOLAR_API_KEY`, `METIS_UNPAYWALL_EMAIL` | APIs acadêmicas | M4–M5 |
| Orçamento por run (tokens, buscas pagas) | Limite de custo | M3–M4 |
| `AGNO_TELEMETRY=false` | Desliga a telemetria do Agno (lida pelo próprio Agno) | M1 |

Os valores iniciais e as regras de validação dos tempos estão em [Orquestração](orchestration.md#tempos-e-validação-na-subida).

## Chaves e contas externas

| Serviço | Precisa de | Observação |
|---|---|---|
| Provedores de LLM (hoje OpenAI e Google; um 3º opcional para o slot C) | Chave de API de cada um | Conferir a política de retenção de dados: os manuscritos são inéditos |
| OpenAlex | Chave (a grátis dá US$ 1/dia) | Consulta por DOI é grátis; busca é paga |
| Semantic Scholar | Chave | 1 req/s |
| Crossref | E-mail (`mailto`) | Pool *polite* |
| Unpaywall | E-mail real | Endereços de exemplo são recusados |

## CI

- **GitHub Actions** com um serviço Postgres (`pgvector/pgvector:pg18`).
- **Passos:** `uv sync --frozen` → `ruff check` → `ruff format --check` → `mypy` → `pytest`.
- **Celery em modo eager** nos testes, sem Redis no CI.
- **Sem chamadas ao modelo no CI:** os testes que falam com o Gemini de verdade são marcados com `llm` e ficam fora do `pytest` padrão (`pytest -m llm`, à mão, com a `GEMINI_KEY` do `.env`).

## Operação

```bash
cp .env.example .env                       # preencher os segredos
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose logs -f worker-evaluation
docker compose up -d postgres              # só o banco, para o pytest no host (127.0.0.1:5440)
# Admin: http://localhost:8100/admin/   Flower: http://127.0.0.1:5556
```
