# Testes e verificação

Os princípios e as tabelas do M0 continuam os do [plano de outubro](../../2026-10_october/1_desenho_inicial/05_testes_e_verificacao.md). Este arquivo acrescenta os testes de M1–M6, os testes do Agno e a verificação manual por ponto de integração.

## Princípios (resumo)

- **Banco real** (pytest-django com Postgres), sem mock nem patch.
- **LLM por fakes:** a `FakeAgentFactory` responde conforme o `output_schema` e tem roteiros de erro.
- **APIs externas** por respostas HTTP reais gravadas.
- **Celery em modo eager**; E2E com `docker compose`.
- **Threads:** teste que usa `Parallel` ou `bounded_map` com ORM roda com `transaction=True`.
- **Evals offline** (`evals/`) fora do CI.
- **Chamadas reais ao Agno** só em testes de contrato marcados, fora do CI.

## Testes comuns a todo workflow Agno

Cada workflow (E1–E5) tem estes testes, além dos específicos:

| Teste | Espera |
|---|---|
| `test_workflow_reaches_checkpoint` | O estágio termina no checkpoint seguinte, com as saídas gravadas |
| `test_rerun_does_not_call_agents` | Rodar o mesmo workflow de novo não chama nenhum agente da fake |
| `test_llm_unavailable_bubbles_up` | `LLMUnavailable` persistente → retry do estágio → `error_llm` |
| `test_invalid_output_is_retried_with_reason` | Saída inválida → nova chamada com o motivo no prompt |
| `test_every_call_is_recorded` | Um `LLMCall` por chamada |
| `test_no_db_connections_leak` | Nenhuma conexão sobra aberta depois do workflow |

## Por marco

| Marco | Arquivos de teste | Destaques |
|---|---|---|
| M1 | `extraction/tests/test_contract.py`, `extractor/tests/` (config, mapa, conferência, nova tentativa, sessão, E1 por attempt; na 1.10 `test_references.py` e `test_citations.py`; na 1.6 `test_figures.py`), `test_hidden_text.py`, `test_workflow.py`; `agents/tests/test_specs.py`, `test_models.py`, `test_prompts.py`, `test_runner.py`, `test_limits.py`, `test_import_boundaries.py`; `metis/tests/test_concurrency.py`; `pipeline/tests/test_usage.py` | Snapshot de 3–5 PDFs; gráfico vetorial; texto oculto plantado; gate antes das figuras; cache por sha256; `judge_for` cruzado |
| M2 | `questions/tests/test_load_taxonomy.py`, `test_criteria.py`, `test_profiler.py`, `test_resolver.py`, `test_section_roles.py`, `test_document_map.py`, `test_workflow.py`, `test_curation.py` | Enum dinâmico do segundo passo; cada degrau do fallback; `waiting_setup` → reprocessar; rascunho fora da resolução |
| M3 | `evaluation/tests/test_context.py`, `test_models.py`, `test_section_pass.py`, `test_cross_checks.py`, `test_synthesis.py`, `test_modes.py`, `test_validators.py`, `test_judge.py`, `test_revision_loop.py`, `test_workflow.py`, `test_aggregation.py`, `test_final_report.py`; `questions/tests/test_rubric_check.py` | Rodada 1 limpa não entra no loop; inválido sempre → 2 revisões julgadas → `unresolved`; `rebut` aceito; revisão parcial; rubric check não toca a Question ativa |
| M4 | `scholarly/tests/`; `integrity/tests/test_references.py`, `test_corpus.py`, `test_candidates.py`, `test_lexical.py`, `test_semantic.py`, `test_adjudication.py`, `test_rules.py`, `test_workflow.py` | Token bucket; winnowing com offsets; PT↔EN; trecho citado não vai ao agente; risco alto → gate |
| M5 | `integrity/tests/test_existence.py`, `test_retraction.py`, `test_consistency.py`, `test_alignment.py`, `test_cross_phases.py`, `test_workflow.py` | Referência inventada com DOI falso; `INSUFFICIENT` → full text uma vez; retry com uma fase já gravada |
| M6 | `attempts/tests/test_cost_admin.py`; comandos de `evals/` | Soma do custo por run; relatórios comparáveis entre versões |

## Verificação manual por ponto de integração

### I1 — M0

A [verificação manual do M0](../../2026-10_october/1_desenho_inicial/05_testes_e_verificacao.md#verificação-manual-do-m0) de outubro: submissão → `done`, reenvio → 200, versão nova → `attempt_number=2`, worker parado no meio → retomada, Flower.

### I2 — Extração real

1. Subir o compose com a `GEMINI_KEY` no `.env`.
2. Enviar 3 PDFs reais: um com gráfico vetorial, um com texto oculto plantado, um sem abstract.
3. O primeiro chega a `extracted` com a figura recortada inteira e descrita; o segundo tem o achado de texto oculto; o terceiro vai a `rejected_invalid_submission` sem nenhum `LLMCall` de visão.
4. No admin, os `LLMCall` têm tokens e custo.
5. Reenviar o primeiro como novo run da mesma attempt: a extração é reaproveitada, sem chamada ao modelo (`reused: true` no evento do E1).

### I3 — Avaliação real

1. Enviar um PDF real com o E3 ainda *pass-through*.
2. Acompanhar até `done`: o run tem `profile`, `question`, 3 `ReviewRound` na rodada 1, os `JudgeVerdict` e o `FinalReport`.
3. `GET /api/runs/{id}/report` → 200, com `criteria[]`, `sections[]` e `versions`.
4. No `config_snapshot`, conferir os slots A (GPT), B (Gemini), C e os juízes cruzados.
5. Conferir o tempo do E4 contra o soft limit e o custo total do run.

### I4 — Integridade, Fase 1

1. Enviar um PDF com um parágrafo copiado de um artigo do corpus, sem citar.
2. O run para em `waiting_human_review`; no admin, o achado mostra os dois trechos lado a lado.
3. "Continuar" → o run vai a `done`, e a decisão aparece no `RunEvent`, com a nota.
4. Enviar o mesmo PDF com a citação e o trecho entre aspas → `properly_cited` e o run segue sem parar.

### I5 — Pipeline completo

1. Enviar um PDF com uma referência inventada (DOI de aparência real) e outra a um trabalho retratado.
2. O `IntegrityReport` tem os dois achados e o `coverage` preenchido.
3. O relatório final traz o resumo da integridade e o modo de avaliação decidido no A/B.

### I6 — Qualidade

1. Rodar `bench_reviews`, `bench_judge`, `bench_plagiarism` e os benchmarks da Fase 2.
2. Comparar com os números anteriores; as metas revistas estão registradas no planejamento.

## Portões no CI

`ruff check` + `ruff format --check`, `mypy projects/correction`, `pytest` (unitário e integração, com Postgres; os testes com o modelo de verdade, `-m llm`, ficam fora). Testes de contrato com provedores reais e evals ficam fora do CI.
