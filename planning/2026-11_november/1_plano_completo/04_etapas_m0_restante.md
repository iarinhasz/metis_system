# M0 — Fundação (restante)

**Situação:** etapas 0.1–0.7 implementadas, em `projects/correction/`; a verificação manual do I1 passou no `docker compose` em 11/11.
**Trilha:** P
**Referência:** [etapas originais do M0](../../2026-10_october/1_desenho_inicial/03_etapa_m0_fundacao.md), [Orquestração](../../../docs/orchestration.md)

As etapas 0.4–0.7 seguem o [plano de outubro](../../2026-10_october/1_desenho_inicial/03_etapa_m0_fundacao.md#etapa-04--pipeline-com-estágios-stub). Este arquivo lista o que muda com o monorepo e com as decisões novas. Caminhos relativos a `projects/correction/`.

---

## Pendências da etapa 0.3

**O que fazer**
- A reorganização (monorepo) e a API da 0.3 já estão no commit `548587f`.
- Rodar `ruff check`, `ruff format --check`, `mypy projects/correction` e `pytest` no CI, com o serviço `pgvector/pgvector:pg18`.
- Mensagem do `banned-api` no `pyproject.toml`: trocar "metis.config" por "projects.correction.metis.config". Feito na 0.4.
- Os testes da 0.3 que dependiam do `on_commit` (API) e do claim fora do checkpoint foram corrigidos na 0.4, ao rodarem pela primeira vez no Postgres.

**Pronto quando:** CI verde com os testes da 0.3 rodando no Postgres.

---

## Etapa 0.4 — Pipeline com estágios stub

Como no plano de outubro, com estes ajustes:
- **`pipeline/publishing.py`:** `publish_stage(run_id, stage)` substitui `attempts/publishing.py`. A fila e o nome da task vêm do `STAGES`. O `attempts/api.py` passa a importar daqui, pela borda (a API pode importar `pipeline`).
- **`pipeline/stages.py`:** o `StageTask.execute()` recebe um `StageContext(run_id, attempt_id, task_id, stage)`. Nos stubs, ele não usa o Agno. A partir da 1.9, cada estágio troca o stub por `build_<estágio>_workflow(ctx, deps).run(...)` (ver [docs/agents.md](../../../docs/agents.md#visão-geral)). O E1 trocou o stub já na 1.5, sem Workflow: chama `extract_attempt()`.
- **`pipeline/errors.py`:** as quatro exceções. O `LLMUnavailable` também é reexportado por `agents/errors.py` (1.3).
- **`metis/celery.py`:** app Celery, `acks_late`, `task_reject_on_worker_lost`, `prefetch_multiplier=1`, filas e rotas.

**Teste:** `pipeline/tests/test_pipeline.py`, como no plano de outubro.

**Commit sugerido:** `feat: add stage pipeline with stub stages`

---

## Etapa 0.5 — Gate humano e reprocessamento

Como no plano de outubro. O `POST /api/runs/{id}/decision` usa a `ServiceBearerAuth` existente.

**Commit sugerido:** `feat: add human review gate and run recovery`

---

## Etapa 0.6 — Reconciliador

Como no plano de outubro.

**Commit sugerido:** `feat: add run reconciler`

---

## Etapa 0.7 — Docker e operação

Como no plano de outubro, com estes ajustes:
- O `command` dos serviços usa `python manage.py` da raiz e `celery -A projects.correction.metis.celery`.
- O `.dockerignore` exclui `dataset_project/raw/` (o zip do PeerRead tem ~1,2 GB).

**Como ficou:** o `.dockerignore` é uma lista de permissão (só `pyproject.toml`, `uv.lock`, `.python-version`, `manage.py` e `projects/`, sem `media/`); o `collectstatic` roda no build; o flower tem imagem própria, com `UV_SYNC_ARGS="--extra flower"`; workers, beat e flower esperam o `web` ficar saudável, o que garante as migrações aplicadas.

**Commit sugerido:** `chore: add Docker setup`

---

## Pronto do M0 (I1)

- CI verde.
- `docker compose up` + `POST /api/attempts` levam o run a `done`.
- Os caminhos do gate, das falhas e do reconciliador têm teste.
- A verificação manual de [12](12_testes_e_verificacao.md#i1--m0) passa.
