# Testes e verificação

Os princípios e as tabelas do M0 continuam os do [plano de outubro](../../2026-10_october/1_desenho_inicial/05_testes_e_verificacao.md). Este arquivo acrescenta os testes de M1–M6, os testes do Agno e a verificação manual por ponto de integração.

**Leitura desta matriz (13/11/2026):** nomes de testes e roteiros de integração
abaixo incluem itens **planejados**. Eles não são prova de execução. Na base
`32ff4e6`, a última validação registrada teve 654 testes passando, 5 `llm`
excluídos, mypy em 237 arquivos e Ruff em 239, sem migrações pendentes. Essa
validação pertence à 6.1; a revisão de docs 6.4 não reexecuta a suíte.
O E3 roda enxuto e o E4 está ligado (3.10), mas I3–I6 ainda não estão comprovados ponta a ponta.
Veja [resultados, limites e metas revistas](../../../docs/status_and_metrics.md).

## Princípios (resumo)

- **Banco real** (pytest-django com Postgres), sem mock nem patch.
- **LLM por fakes:** a `FakeAgentFactory` responde conforme o `output_schema` e tem roteiros de erro.
- **APIs externas** por respostas HTTP reais gravadas.
- **Celery em modo eager**; E2E com `docker compose`.
- **Threads:** teste que usa `Parallel` ou `bounded_map` com ORM roda com `transaction=True`.
- **Evals offline** (`evals/`) fora do CI.
- **Chamadas reais ao Agno** só em testes de contrato marcados, fora do CI.

## Testes comuns a todo workflow Agno

Cada workflow real deve atender aos contratos abaixo. E2 e E5 já têm testes de
retomada/posse com fakes; E1 usa sessão, sem Workflow. A lista não afirma que
workflows de E3/E4 ou todos estes nomes de teste já existam:

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

**Situação (15/11/2026, `dev` em `42a16ca`):** os passos 1, 4 e 5 passam. O ICLR 410 chega a `extracted` (19 seções, 42 referências, 13 figuras descritas), com as 37 chamadas do E1 em `LLMCall`, com tokens e custo (US$ 0,12), e o mesmo PDF enviado como outro artigo reaproveita a extração sem chamar o modelo. Um PDF sem abstract é rejeitado antes das chamadas por seção (coberto em `extractor/tests/test_service.py`). Ficam abertos o texto oculto (1.7) e o recorte das figuras (adiado na 1.6), e por isso o I2 ainda não fecha.

### I3 — Avaliação real

**Situação (16/11/2026):** em aberto. Com a 3.10, o ICLR 410 passa pelo E1, E2 e E3 (risco baixo) e termina no E4 em `error_llm`: as respostas dos modelos reais não passavam em algumas validações do E4. As correções (ver a 3.10) estão cobertas com modelos falsos; falta repetir o run real.

1. Enviar um PDF real com o E3 ainda *pass-through*.
2. Acompanhar até `done`: o run tem `profile`, `question`, 3 `ReviewRound` na rodada 1, os `JudgeVerdict` e o `FinalReport`.
3. `GET /api/runs/{id}/report` → 200, com `criteria[]`, `sections[]` e `versions`.
4. No `config_snapshot`, conferir os slots A (GPT), B (Gemini), C e os juízes cruzados.
5. Conferir o tempo do E4 contra o soft limit e o custo total do run.

### I4 — Integridade, Fase 1

**Situação (15/11/2026):** como o plágio saiu do escopo, o I4 passa a ser conferido com texto oculto: o ICLR 410 com instruções plantadas parou em `waiting_human_review`, o achado aparece no admin e em `GET /integrity`, e "continuar" pela API levou o run adiante, com a nota no `RunEvent`. Os passos abaixo, de plágio, ficam como desenho.

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

### Revisão documental 6.4

Conferir os links e âncoras locais de `README.md`/`docs/`, as fontes de código,
rotas e opções de comandos citadas, e se cada métrica informa data, amostra,
modo e limitações. As metas de desenvolvimento ficam em
[Estado e métricas](../../../docs/status_and_metrics.md#metas-revistas-por-marco).
Links comerciais e tarifas são snapshots históricos, sem nova validação externa.

## Portões no CI

`ruff check` + `ruff format --check`, `mypy projects/correction`, `pytest` (unitário e integração, com Postgres; os testes com o modelo de verdade, `-m llm`, ficam fora). Testes de contrato com provedores reais e evals ficam fora do CI.
