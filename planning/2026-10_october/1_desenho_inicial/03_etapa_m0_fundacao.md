# M0 — Fundação

**Situação:** não iniciado
**Objetivo:** esqueleto ponta a ponta. Um PDF submetido passa pelos 5 estágios (stubs) até `done`, com retries, gate humano e reconciliador funcionando
**Referência:** [Orquestração](../../../docs/orchestration.md), [Modelos de dados](../../../docs/data_models.md), [Infraestrutura](../../../docs/infrastructure.md)
**Fora daqui:** `LLMCall` e o primeiro agente (M1), Questions (M2), as saídas reais dos estágios, o serviço `grobid` (M1)

---

## Etapa 0.1 — Projeto, configuração e qualidade

**O que fazer**
- **Dependências:** projeto `uv` com Python 3.14.
  - Runtime: `django`, `django-ninja`, `celery[redis]`, `psycopg[binary]`, `pydantic`, `pydantic-settings`, `gunicorn`, `whitenoise`.
  - Extra `flower`.
  - Grupo `dev`: `pytest`, `pytest-django`, `ruff`, `mypy`, `django-stubs`, `celery-types`.
- **Projeto Django `metis/`:** `settings.py`, `urls.py`, `wsgi.py`, `manage.py`.
- **`metis/config.py`:** `MetisSettings` (pydantic-settings, prefixo `METIS_`). É o único leitor de variáveis de ambiente, e valida os tempos na subida (regras em [Orquestração](../../../docs/orchestration.md#tempos-e-validação-na-subida)).
- **ruff:** `banned-api` (TID251) proibindo `os.getenv`/`os.environ` fora do `config.py`; exceção só nos arquivos de bootstrap (`manage.py`, `wsgi.py`, `celery.py`).
- **mypy:** com django-stubs e o plugin do pydantic; funções sem tipo só nos testes.
- **pytest-django** e o CI no GitHub Actions, com um serviço Postgres (`pgvector/pgvector:pg18`).

**Por quê**
Configuração num lugar só e portões de qualidade antes que o código se acumule.

**Teste** (`metis/tests/test_config.py`)
- Cada regra de validação dos tempos recusa um valor contraditório.
- Hosts separados por vírgula viram uma lista limpa.

**Pronto quando:** `ruff check`, `ruff format --check`, `mypy` e `pytest` passam no CI.

**Commit sugerido:** `chore: bootstrap Django project with uv, ruff, mypy and pytest`

---

## Etapa 0.2 — Attempts, runs e máquina de estados

**O que fazer**
- **App `attempts`:**
  - base `TimeStampModel` (UUIDv7);
  - models `Article`, `Attempt`, `Run` e `RunEvent`, com os campos de [Modelos de dados](../../../docs/data_models.md#attempts).
- **`attempts/status.py`:**
  - os enums `RunStatus`, `Stage` e `HumanDecision`;
  - `StageSpec` e `STAGES`;
  - a tabela `TRANSITIONS`, explícita;
  - os conjuntos `CHECKPOINTS`, `RUNNING`, `FINAL`, `RECOVERABLE` e `STAGE_FAILURES`.
- **`attempts/managers.py`:**
  - `AttemptManagement`: travar o artigo, achar por sha256, criar a versão seguinte;
  - `RunManagement`: `create`, `claim_stage`, `complete_stage`, `fail_stage`, `record_retry`, `decide`, `recover`, `release_stale`, `mark_republished`, `supersede_other_attempts`;
  - todas as operações rodam com lock da linha, validam `TRANSITIONS` e gravam o `RunEvent` na mesma transação.
- **Admin:** somente leitura, para os quatro models.

**Por quê**
A máquina de estados é a espinha do sistema. Todo o resto depende dela, então ela vem primeiro e com a cobertura mais forte.

**Teste**
- `attempts/tests/test_status.py`:
  - todo status tem entrada na tabela;
  - os finais não têm saída;
  - cada estágio consegue começar (entrada → rodando) e terminar (rodando → concluído).
- `attempts/tests/test_run_management.py`:
  - o claim leva do checkpoint a "rodando";
  - uma segunda task não consegue o claim, mas a mesma task consegue retomar;
  - o complete exige ser o dono;
  - uma transição inválida levanta exceção;
  - uma versão nova torna os runs pendentes `superseded`;
  - decidir fora do gate dá conflito;
  - reprocessar volta ao checkpoint do estágio que falhou;
  - nenhum evento sai duplicado.

**Pronto quando:** os testes passam com o Postgres real.

**Commit sugerido:** `feat: add attempts, runs and the run state machine`

---

## Etapa 0.3 — API de submissão

**O que fazer**
- **`metis/authentication.py`:** `ServiceBearerAuth` (token comparado em bytes com `compare_digest`) e `DenyAllAuth`. A `NinjaAPI` bloqueia por padrão, e `/docs` só fica ligado em DEBUG.
- **`POST /api/attempts`:**
  - valida o cabeçalho `%PDF-` e o tamanho, e calcula o sha256 em blocos;
  - reenvio idêntico → 200 com os ids existentes; arquivo novo → 202 com a versão seguinte;
  - a versão nova torna os runs pendentes da anterior `superseded`;
  - cria o `Run(received)` e publica o E1 após o commit.
- **`GET /api/runs/{run_id}`** (status, estágio, eventos) e **`GET /health/`**.

**Teste** (`attempts/tests/test_api.py`)
- Sem token → 401; token não configurado → 401.
- Submissão nova → 202, run em `received` e callback registrado no `on_commit`.
- Mesmo arquivo → 200, com os mesmos ids.
- Arquivo novo do mesmo artigo → `attempt_number=2`, e o run anterior fica `superseded`.
- Arquivo que não é PDF → 400; arquivo grande demais → 400.
- O status lista os eventos em ordem.

**Pronto quando:** os testes passam, e a identificação do artigo foi decidida (questão aberta Q3).

**Commit sugerido:** `feat: add submission and run status API`

---

## Etapa 0.4 — Pipeline com estágios stub

**O que fazer**
- **Celery:** `metis/celery.py`; filas, rotas e beat em `settings.py`; uma task fina por estágio em `pipeline/tasks.py`.
- **`pipeline/stages.py`:**
  - `StageTask`, com o ciclo claim → `execute()` → complete → publicar o próximo;
  - `StageOutcome(payload, halt)`;
  - os 5 estágios, com `execute()` stub (o E3 devolve risco baixo).
- **`pipeline/errors.py`:** `TransientStageError`, `LLMUnavailable`, `InvalidSubmission`, `SetupRequired`.
- **Retries:** `get_exponential_backoff_interval` do Celery, com jitter completo, mais o evento `retry_scheduled`.
- **`pipeline/publishing.py`:** publica com `transaction.on_commit(..., robust=True)`.

**Teste** (`pipeline/tests/test_pipeline.py`, Celery em modo eager e transações reais)
- O caminho feliz chega a `done`, com a sequência de eventos esperada.
- Um erro passageiro (2 vezes) é retentado e chega a `done`.
- Retries esgotados terminam em `error_llm`.
- `InvalidSubmission` leva a `rejected_invalid_submission` e nada mais é publicado.
- Um erro inesperado termina em `error_unexpected`.
- Um estágio que perdeu a posse no meio (run `superseded`) não faz transição.

**Pronto quando:** os testes passam.

**Commit sugerido:** `feat: add stage pipeline with stub stages`

---

## Etapa 0.5 — Gate humano e reprocessamento

**O que fazer**
- O E3 stub pode devolver risco alto nos testes → o run vai para `waiting_human_review`.
- **`pipeline/services.py`:**
  - `decide`: *continuar* → `integrity_checked` + publica o E4; *encerrar* → `closed_by_reviewer`;
  - `recover`: `error_*` ou `waiting_setup` → checkpoint do estágio que falhou + publica.
- Ações no admin do `Run`: "Continuar avaliação", "Encerrar", "Reprocessar". Também `POST /api/runs/{id}/decision`.

**Teste**
- Risco alto → `waiting_human_review`.
- *Continuar* → `done`; *encerrar* → `closed_by_reviewer`.
- Decidir fora do gate → 409.
- Reprocessar um `error_llm` no E4 retoma a partir de `integrity_checked`, sem refazer E1–E3.

**Commit sugerido:** `feat: add human review gate and run recovery`

---

## Etapa 0.6 — Reconciliador

**O que fazer**
- `pipeline/reconciler.py` + a task do beat `pipeline.reconcile_runs`:
  - republica checkpoints parados, contando com `publish_count` e respeitando o limite;
  - libera estágios travados, contando com `stage_claims` e respeitando o limite.
- As duas ações passam pelo `RunManagement`.

**Teste** (`pipeline/tests/test_reconciler.py`)
- Checkpoint parado → evento `republished` e `publish_count=1`.
- Checkpoint recente → nada.
- Limite de republicação → `error_unexpected`.
- Estágio travado → volta ao checkpoint e é republicado.
- Limite de claims → `error_unexpected`.
- Estágio rodando dentro do prazo → nada.

**Commit sugerido:** `feat: add run reconciler`

---

## Etapa 0.7 — Docker e operação

**O que fazer**
- **Dockerfile:** `python:3.14-slim` + uv com versão fixa, usuário não-root, falha se um `.env` vazar para o build, healthcheck.
- **`docker-compose.yml`:** os serviços de [Infraestrutura](../../../docs/infrastructure.md), com `x-common-env` e portas configuráveis.
- `.env.example`, `.dockerignore`, `.gitignore`.
- README com "como rodar".

**Teste:** a verificação manual de [05](05_testes_e_verificacao.md#verificação-manual-do-m0).

**Commit sugerido:** `chore: add Docker setup`
