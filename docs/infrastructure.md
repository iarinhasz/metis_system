# Infraestrutura

## Serviços do docker-compose

| Serviço | Imagem e comando | Papel | Porta no host |
|---|---|---|---|
| `web` | Imagem do projeto: `migrate` + `collectstatic` + gunicorn | API, admin, healthcheck | `${METIS_WEB_PORT:-8100}` |
| `worker-extraction` | `celery worker -Q extraction`, concorrência 1–2, limite de memória | E1 | — |
| `worker-integrity` | `celery worker -Q integrity` | E3 | — |
| `worker-evaluation` | `celery worker -Q evaluation,default` | E2, E4, E5 e reconciliador | — |
| `beat` | `celery beat` | Agenda o reconciliador | — |
| `flower` | `celery flower` (imagem com o extra `flower`) | Monitoramento das filas | `127.0.0.1:${METIS_FLOWER_PORT:-5556}` |
| `postgres` | `pgvector/pgvector:pg18` | Banco e vetores | `127.0.0.1:${METIS_POSTGRES_PUBLISHED_PORT:-5440}` |
| `redis` | `redis:7-alpine` | Broker do Celery | — (só na rede interna) |
| `grobid` (M1) | `grobid/grobid:0.9.1-crf` | Parse estrutural do PDF | — |

- **Mesma imagem para `web` e workers**; só o `command` muda.
- **Variáveis comuns** num único bloco `x-common-env` (YAML anchor), em vez de repetidas por serviço.
- **Volumes:**
  - `pgdata`, montado em `/var/lib/postgresql`: o Postgres 18 mudou o layout do `PGDATA` na imagem oficial;
  - `media`, com PDFs e recortes, compartilhado entre `web` e workers.
- **Portas:** as padrão evitam colisão com portas comuns em máquinas de desenvolvimento (8000, 5432/5433, 5555). Todas são configuráveis no `.env`.

## A imagem

- `python:3.14-slim` + `uv` com versão fixa; usuário não-root; venv em `/opt/venv`; `uv sync --frozen`.
- O build falha se um `.env` escapar para o contexto de build.
- `HEALTHCHECK` em `/health/` (testa o banco). Workers, beat e flower desligam o healthcheck.
- Pendências do M1:
  - os modelos do Docling vão para a imagem de extração ou são baixados na primeira execução?
  - Docling/torch têm wheels para Python 3.14? Se não, a imagem de extração usa 3.13.

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
| `METIS_GROBID_URL` | GROBID | M1 |
| `METIS_OPENAI_API_KEY`, `METIS_GOOGLE_API_KEY`, `METIS_ANTHROPIC_API_KEY` | Provedores de LLM, passados explicitamente pela `ModelFactory` | M1 |
| `ModelSpec` por papel (profiler, describer, avaliadores, juiz, meta-revisor) | Qual modelo cumpre cada papel | M1–M3 |
| `METIS_CROSSREF_MAILTO`, `METIS_OPENALEX_API_KEY`, `METIS_SEMANTIC_SCHOLAR_API_KEY`, `METIS_UNPAYWALL_EMAIL` | APIs acadêmicas | M4–M5 |
| Orçamento por run (tokens, buscas pagas) | Limite de custo | M3–M4 |
| `AGNO_TELEMETRY=false` | Desliga a telemetria do Agno (lida pelo próprio Agno) | M1 |

Os valores iniciais e as regras de validação dos tempos estão em [Orquestração](orchestration.md#tempos-e-validação-na-subida).

## Chaves e contas externas

| Serviço | Precisa de | Observação |
|---|---|---|
| Provedores de LLM (3 famílias) | Chave de API de cada um | Conferir a política de retenção de dados: os manuscritos são inéditos |
| OpenAlex | Chave (a grátis dá US$ 1/dia) | Consulta por DOI é grátis; busca é paga |
| Semantic Scholar | Chave | 1 req/s |
| Crossref | E-mail (`mailto`) | Pool *polite* |
| Unpaywall | E-mail real | Endereços de exemplo são recusados |

## CI

- **GitHub Actions** com um serviço Postgres (`pgvector/pgvector:pg18`).
- **Passos:** `uv sync --frozen` → `ruff check` → `ruff format --check` → `mypy` → `pytest`.
- **Celery em modo eager** nos testes, sem Redis no CI.
- **A partir do M1**, um serviço `grobid` para os testes de integração da extração.

## Operação (comandos previstos)

```bash
cp .env.example .env                       # preencher os segredos
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose logs -f worker-evaluation
# Admin: http://localhost:8100/admin/   Flower: http://127.0.0.1:5556
```
