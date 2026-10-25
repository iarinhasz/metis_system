# Testes e verificação

## Princípios

- **Banco real:** os testes usam o Postgres (pytest-django), sem mock nem patch.
- **Fakes por injeção:** LLMs entram pelos fakes da `AgentFactory`; APIs externas, por respostas HTTP reais gravadas.
- **Determinístico primeiro:** máquina de estados, regras, validadores e agregação são código puro e têm a cobertura mais forte.
- **Celery em modo eager** nos testes. O E2E roda com `docker compose`.
- **Evals offline** (`evals/`) não bloqueiam o CI; são acompanhados por versão de prompt e por `ModelSpec`.

## M0, por arquivo

### `metis/tests/test_config.py`

| Teste | Espera |
|---|---|
| `test_rejects_soft_limit_not_below_hard_limit` | `ValidationError` |
| `test_rejects_backoff_not_below_visibility_timeout` | `ValidationError` |
| `test_rejects_stale_threshold_not_above_hard_limit` | `ValidationError` |
| `test_rejects_claims_not_above_retries` | `ValidationError` |
| `test_splits_comma_separated_hosts` | Lista limpa, sem itens vazios |

### `attempts/tests/test_status.py`

| Teste | Espera |
|---|---|
| `test_every_status_has_an_entry` | `TRANSITIONS` cobre todos os `RunStatus` |
| `test_final_statuses_have_no_exits` | `done`, `rejected_invalid_submission`, `closed_by_reviewer` e `superseded` sem saída |
| `test_each_stage_can_start_and_finish` | Entrada → rodando → concluído permitido nos 5 estágios |
| `test_running_status_can_return_to_its_checkpoint` | Rodando → entrada permitido (reconciliador) |
| `test_recoverable_statuses_reach_every_checkpoint` | `waiting_setup` e `error_*` → qualquer checkpoint |

### `attempts/tests/test_run_management.py`

| Teste | Espera |
|---|---|
| `test_claim_moves_checkpoint_to_running` | Status, `stage`, `current_task_id` e evento com `version=2` |
| `test_second_task_cannot_claim` | `None`; status inalterado |
| `test_same_task_can_reclaim` | Retoma; `stage_claims` + 1 |
| `test_complete_requires_ownership` | Outra task → `None`; status inalterado |
| `test_invalid_transition_raises` | `InvalidTransition` |
| `test_new_attempt_supersedes_pending_runs` | Pendentes → `superseded`; finais intocados |
| `test_decide_outside_gate_conflicts` | `RunConflict` |
| `test_recover_returns_to_failed_stage_checkpoint` | `error_llm` no E4 → `integrity_checked` |
| `test_events_are_not_duplicated` | `event_key` único em retry e reentrega |

### `attempts/tests/test_api.py`

| Teste | Espera |
|---|---|
| `test_requires_token` | 401 |
| `test_blocks_when_token_not_configured` | 401 |
| `test_new_attempt_returns_202_and_publishes_after_commit` | Run em `received`; callback registrado no `on_commit` |
| `test_same_file_returns_200_with_existing_ids` | Mesmos ids; nenhuma attempt nova |
| `test_new_file_creates_next_version` | `attempt_number=2`; o run anterior fica `superseded` |
| `test_rejects_non_pdf` | 400 |
| `test_rejects_oversized_file` | 400 |
| `test_run_status_lists_events_in_order` | Eventos em ordem de versão |

### `pipeline/tests/test_pipeline.py` (eager, transações reais)

| Teste | Espera |
|---|---|
| `test_happy_path_reaches_done` | `received` → … → `done`, com um evento por transição |
| `test_transient_error_is_retried` | 2 eventos `retry_scheduled`; termina em `done` |
| `test_exhausted_retries_end_in_error_llm` | `error_llm`, com `last_error` preenchido |
| `test_invalid_submission_stops_the_pipeline` | `rejected_invalid_submission`; nada publicado |
| `test_unexpected_error_ends_in_error_unexpected` | `error_unexpected` |
| `test_high_risk_waits_for_human` | `waiting_human_review`; o E4 não é publicado |
| `test_continue_decision_finishes_run` | `done` |
| `test_close_decision_closes_run` | `closed_by_reviewer` |
| `test_recover_resumes_from_failed_stage` | Só o estágio que falhou em diante roda de novo |
| `test_stage_that_lost_ownership_has_no_effect` | Run `superseded` no meio → nenhuma transição do estágio |

### `pipeline/tests/test_reconciler.py`

| Teste | Espera |
|---|---|
| `test_republishes_stale_checkpoint` | Evento `republished`; `publish_count=1` |
| `test_ignores_recent_checkpoint` | Nada |
| `test_gives_up_after_max_republish` | `error_unexpected` |
| `test_releases_stale_stage` | Volta ao checkpoint e é republicado |
| `test_gives_up_after_max_claims` | `error_unexpected` |
| `test_leaves_fresh_running_stage_alone` | Nada |

## Verificação manual do M0

1. `cp .env.example .env`, preencher os segredos e rodar `docker compose up -d --build`.
2. `curl http://localhost:8100/health/` → `{"status": "ok"}`.
3. `docker compose exec web python manage.py createsuperuser` e abrir `/admin/`.
4. Enviar um PDF com o token → 202. Consultar `GET /api/runs/{id}` até `done` (segundos, com os stubs).
5. Reenviar o mesmo arquivo → 200, com os mesmos ids.
6. Enviar outro PDF do mesmo artigo → `attempt_number=2`.
7. Parar o `worker-evaluation` no meio de um run: o run fica no checkpoint. Ao subir de novo, ele continua. Se a publicação se perder, o reconciliador republica depois de 15 min.
8. O Flower (`http://127.0.0.1:5556`) mostra as filas e os workers.

## M1–M6 (estratégia)

| Marco | O que testar | Como |
|---|---|---|
| M1 | `ExtractedDocument`, figuras vetoriais, ligação citação ↔ referência, texto oculto | Fixtures reais com snapshot; `referenceMentions` do PeerRead; PDFs com elementos plantados; serviço `grobid` no CI |
| M2 | Classificação, fallback, curadoria, versões, papéis das seções, mapa do documento | Fakes do profiler; amostra rotulada por área e por papel de seção; fluxo no admin |
| M3 | Passes por seção, checagens entre seções, síntese, validadores, juiz, revisão no nível da seção ou do critério, réplica, limite de rodadas, agregação, relatório; A/B dos modos | Fakes por papel de seção; erros plantados (quote falso, `missing` falso, nota contradizendo as observações); revisão que roda de novo só a seção afetada; E2E com PDF real; A/B com as métricas de [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#como-decidir-o-modo-ab-no-m3) |
| M4 | Funil, PT↔EN, filtro por citação, regras, gate | Plágio sintético do PeerRead; abstracts bilíngues do SciELO; E2E com trecho copiado |
| M5 | Existência, retratação, alinhamento, citação faltante | Referências plantadas; SciCiteVal; Citation Integrity; respostas HTTP gravadas |
| M6 | Calibração das notas | Spearman/QWK contra o PeerRead; accept/reject; acompanhamento por versão de prompt |

## Portões no CI

`ruff check` + `ruff format --check`, `mypy`, `pytest` (unitário e integração). As evals offline ficam fora do CI.
