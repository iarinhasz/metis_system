# Infraestrutura

Revisão de 13/11/2026 contra [compose](../docker-compose.yml),
[Dockerfile](../Dockerfile), [configuração](../projects/correction/metis/config.py)
e [CI](../.github/workflows/ci.yml). Os serviços existem; E3 e E4 ainda são stubs.
Veja [estado e metas](status_and_metrics.md) antes de interpretar um run como avaliação completa.

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
- Tamanho histórico do build do E1: ~625 MB; não medido novamente nesta revisão.
- Nenhum serviço de parse de PDF: GROBID descartado em 11/11/2026. Na 1.6 decidiu-se usar Gemini para figuras, sem Docling; recortes de imagem continuam adiados.

## Configuração

Toda configuração da aplicação passa por `metis/config.py` (pydantic-settings,
prefixo `METIS_`), validado na subida. O `.env.example` mostra as opções operacionais.
Os valores abaixo são os padrões do código, sem calibração de produção.

| Variável | Para quê | Marco |
|---|---|---|
| `METIS_SECRET_KEY`, `METIS_DEBUG`, `METIS_ALLOWED_HOSTS`, `METIS_CSRF_TRUSTED_ORIGINS` | Django | M0 |
| `METIS_POSTGRES_HOST`, `_PORT`, `_DB`, `_USER`, `_PASSWORD` | Banco | M0 |
| `METIS_REDIS_URL` | Broker | M0 |
| `METIS_API_TOKEN` | Token do sistema que submete; vazio deixa a API bloqueada | M0 |
| `METIS_MEDIA_ROOT`, `METIS_MAX_UPLOAD_MB` | Arquivos | M0 |
| `METIS_EVALUATION_METHOD`, `METIS_PROFILING_TAXONOMY_VERSION` | Método (`standard`) e versão da taxonomia; vazio seleciona a última carga antes de congelar no Run | M2 |
| `METIS_PROFILING_MAX_ATTEMPTS`, `METIS_PROFILING_CONFIDENCE_THRESHOLD` | 3 respostas por passo e limiar 0,7 para usar Question específica | M2 |
| `METIS_STAGE_MAX_RETRIES`, `METIS_STAGE_RETRY_BACKOFF_SECONDS`, `METIS_STAGE_RETRY_BACKOFF_MAX_SECONDS` | Retries | M0 |
| `METIS_STAGE_SOFT_TIME_LIMIT_SECONDS`, `METIS_STAGE_TIME_LIMIT_SECONDS`, `METIS_BROKER_VISIBILITY_TIMEOUT_SECONDS` | Limites de tempo | M0 |
| `METIS_RECONCILE_INTERVAL_SECONDS`, `METIS_REPUBLISH_AFTER_SECONDS`, `METIS_STALE_STAGE_AFTER_SECONDS`, `METIS_MAX_REPUBLISH`, `METIS_MAX_STAGE_CLAIMS` | Reconciliador | M0 |
| `METIS_WEB_PORT`, `METIS_FLOWER_PORT`, `METIS_POSTGRES_PUBLISHED_PORT` | Portas publicadas no host; lidas só pelo compose, não pelo `config.py` | M0 |
| `GEMINI_KEY` | Chave do Gemini, lida sem o prefixo `METIS_`. Usada pelo E1 | M1 |
| `METIS_LLM_TIMEOUT_SECONDS` | Timeout de cada chamada ao modelo; menor que o soft limit da task | M1 |
| `METIS_OPENAI_API_KEY`, `METIS_GOOGLE_API_KEY` | Chaves explícitas das fábricas; `GEMINI_KEY` continua aceita como alternativa para Google | M1/M3 |
| `METIS_AGNO_CONTRACT_OPENAI_MODEL`, `METIS_AGNO_CONTRACT_GOOGLE_MODEL` | Modelos dos contratos ao vivo da etapa 1.2; não definem os slots de produção | M1 |
| `METIS_<PAPEL>` (JSON) ou `METIS_<PAPEL>__MODEL_ID`, `__TIMEOUT_SECONDS`, `__PARAMS` | Nove `ModelSpec`s com padrões de desenvolvimento; substituição por papel, validada na subida (ver [Agentes e workflows](agents.md#implementação-da-etapa-13)) | M1–M3 |
| `METIS_LLM_MAX_CONCURRENCY` | Chamadas simultâneas por provedor, por worker (`ProviderLimiter`) | M1 |
| `METIS_OPENALEX_API_KEY` | Opcional para carga da taxonomia; `load_taxonomy --file` permite carga sem rede | M2 |
| `METIS_LLM_RUN_BUDGET_USD` | Alerta visual opcional por run; sem variável não há limite configurado. Não bloqueia chamadas | 6.2 |
| `AGNO_TELEMETRY=false` | Desliga a telemetria do Agno (lida pelo próprio Agno) | M1 |

Os valores iniciais e as regras de validação dos tempos estão em [Orquestração](orchestration.md#tempos-e-validação-na-subida).

## Integrações externas

| Serviço | Configuração atual | Situação |
|---|---|---|
| OpenAI e Google | Chaves explícitas das fábricas | Somente esses dois provedores são aceitos pelos contratos atuais; condições de conta e retenção exigem conferência antes do uso |
| OpenAlex | `METIS_OPENALEX_API_KEY`, opcional no loader | Cliente implementado para taxonomia; 1 requisição/s |
| Semantic Scholar, Crossref, arXiv e Unpaywall | Sem campos ativos em `MetisSettings` | Clientes e opções de M4/M5 ainda planejados; não basta definir variáveis no `.env` |

Limites comerciais externos não foram reconferidos nesta revisão. Preços
registrados no projeto são snapshots datados em [Agentes](agents.md#tarifas-iniciais).

## CI

- **GitHub Actions** com um serviço Postgres (`pgvector/pgvector:pg18`).
- **Passos:** `uv sync --locked --all-groups` → `ruff check` → `ruff format --check` → `makemigrations --check --dry-run` → `mypy` → `pytest` (uv 0.13.8, Python 3.14).
- **Celery em modo eager** nos testes, sem Redis no CI.
- **Sem provedores externos no CI:** contratos reais OpenAI/Google são marcados `llm` e excluídos do pytest padrão. Fakes e HTTP local exercitam os clientes; respostas com chaves válidas ainda não têm validação registrada. Benchmarks de desempenho também ficam fora do CI.

## Operação

```bash
cp .env.example .env                       # preencher os segredos
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose logs -f worker-evaluation
docker compose up -d postgres              # só o banco, para o pytest no host (127.0.0.1:5440)
# Admin: http://localhost:8100/admin/   Flower: http://127.0.0.1:5556
```

Depois das migrações, configure o E2 com `load_taxonomy --execute`,
`seed_questions --execute` e revisão/validação/ativação no admin, como em
[Questions iniciais](questions_and_profiling.md#questions-iniciais-e-benchmark-27).
Sem E4 real, chegar a `waiting_setup` no E5 é esperado; reprocessar não fabrica rodadas.

Não há limite de páginas, timeout separado do pypdf ou comando de retenção
implementados. Os limites de task não substituem esses itens pendentes de 6.3/6.4.
[Política e pendências](status_and_metrics.md#operação-limites-e-pendências-de-retenção).
