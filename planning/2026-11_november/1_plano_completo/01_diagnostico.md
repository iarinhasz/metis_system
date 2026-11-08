# Diagnóstico: onde o projeto está

## O código hoje

Tudo em `projects/correction/`, com `manage.py` na raiz repassando para `projects/correction/manage.py`.

| Peça | Arquivo | Estado |
|---|---|---|
| Configuração | `metis/config.py` (`MetisSettings`) | Pronto: prefixo `METIS_`, validação dos tempos na subida, hosts por vírgula |
| Projeto Django | `metis/settings.py`, `urls.py`, `wsgi.py` | Pronto; `MEDIA_ROOT` configurado |
| API | `metis/api.py`, `metis/authentication.py` | Pronto: `NinjaAPI` fechada por padrão (`DenyAllAuth`), `/docs` só em DEBUG, `ServiceBearerAuth` com `compare_digest` |
| Models | `attempts/models.py` | `Article`, `Attempt`, `Run`, `RunEvent`, base UUIDv7 |
| Máquina de estados | `attempts/status.py` | `RunStatus`, `Stage`, `HumanDecision`, `STAGES`, `TRANSITIONS` e os conjuntos |
| Operações do run | `attempts/queries/` (antes `managers.py`) | `ArticleManagement`, `AttemptManagement`, `RunManagement` e `RunEventManagement`: todo acesso ao banco, com lock, validação de transição e evento na mesma transação |
| Submissão e status | `attempts/api.py` | `POST /api/attempts` (multipart, `external_id` obrigatório, 202/200), `GET /api/runs/{id}`, health |
| Publicação | `attempts/publishing.py` | `publish_extraction(run_id)` via `send_task` na fila `extraction` |
| Testes | `metis/tests/`, `attempts/tests/` | Config, status, run management e API |
| Qualidade | `pyproject.toml`, `.github/workflows/ci.yml` | ruff, mypy strict e pytest apontando para `projects/correction` |

**Pendente no M0:**
- rodar os testes com Postgres no CI (a reorganização e a 0.3 já estão no commit `548587f`);
- etapas 0.4–0.7: pipeline, gate, reconciliador e Docker.

## O que se reaproveita

| Existente | Usado por |
|---|---|
| `RunManagement` (`claim_stage`, `complete_stage`, `fail_stage`, `record_retry`, `decide`, `recover`, `release_stale`, `mark_republished`) | `StageTask` (0.4), serviços do gate (0.5), reconciliador (0.6). Nenhuma transição nova precisa ser escrita fora dele |
| `STAGES` e `StageSpec` | Roteamento das tasks por fila e o mapa estágio → próximo estágio |
| `publish_extraction` | Vira o caso geral `publish_stage(run_id, stage)` em `pipeline/publishing.py` (0.4); o import em `attempts/api.py` passa a apontar para lá |
| `MetisSettings` | Ganha os `ModelSpec` por papel, as chaves dos provedores, `METIS_LLM_MAX_CONCURRENCY` e `METIS_GROBID_URL` (M1) |
| `ServiceBearerAuth` | `POST /api/runs/{id}/decision` (0.5), `GET /report` (M3), `GET /integrity` (M4) |
| PeerRead em `dataset_project/` | Fixtures do `ExtractedDocument` (1.1), gabarito de citações (1.10), corpus (4.3), plágio sintético (4.10), calibração (6.1) |

## Lacunas encontradas no desenho

| # | Lacuna | Onde estava | Como este plano resolve |
|---|---|---|---|
| L1 | O loop do juiz era `[judge, revise]`: a revisão da última iteração nunca seria julgada | Esboço do workflow em `evaluators_and_judge.md` | D17: rodada 1 fora do loop + `Condition` + `Loop([revise, validate, judge])` |
| L2 | A regra "só `agents/` instancia o Agno" impediria montar os workflows nos apps, ou faria `agents/` depender dos apps | `architecture.md` | D16: `Agent` e modelos só em `agents/`; `Workflow` e passos no app; teste de fronteira |
| L3 | `Parallel` e pools rodam em threads, e cada thread abre a própria conexão com o Postgres | Não tratado | D20: `bounded_map` fecha a conexão por thread; `ProviderLimiter`; testes com `transaction=True` |
| L4 | O rubric check (M2) depende do E4 real (M3) | Roteiro | O rubric check passa para o M3 (etapa 3.12) |
| L5 | Rubric check e A/B não tinham onde rodar sem tocar a Question ativa | `questions_and_profiling.md` | D18: Runs com `purpose` e `config_snapshot` |
| L6 | O `LLMCall` fica em `attempts/`, mas quem mede a chamada é o `agents/`, que não pode importar apps | `data_models.md` × regras de dependência | `UsageSink` injetado na `AgentFactory`; o sink do pipeline grava o `LLMCall` |
| L7 | O gate de qualidade do E1 rodava depois da descrição das figuras | `extraction.md` | D21: o gate vem antes |
| L8 | M2 e M3 ficariam parados esperando o M1 inteiro | Roteiro | D19: contrato + fixtures do PeerRead primeiro |
| L9 | A D3 pede 3 famílias, mas há chave de 2 | Q1 | D14: 2 famílias + slot C plugável + juiz cruzado |
| L10 | Os validadores e o juiz gravam vereditos, mas o `JudgeVerdict` não dizia quem invalidou | `data_models.md` | Campo `source` (`validator` ou `judge`) no `JudgeVerdict` |

## O que confirmar no Agno 3

A pesquisa de 25/10 ([diagnóstico de outubro](../../2026-10_october/1_desenho_inicial/01_diagnostico.md#pesquisa-de-ferramentas-25102026)) é a base. O spike da etapa 1.2 confere, contra o pacote instalado:

| Item | O que conferir |
|---|---|
| Instalação | `agno>=3.1,<4` instala e importa em Python 3.14 (com `openai` e `google-genai`) |
| `Step` | Assinatura do executor (`StepInput` → `StepOutput`), `max_retries=0`, exceção dentro do executor interrompe o workflow e sobe para quem chamou |
| `Parallel` | Como os outputs dos ramos aparecem para o passo seguinte; exceção num ramo cancela os outros ou não |
| `Loop` | Assinatura do `end_condition`; quando ele é avaliado (depois de cada iteração); comportamento com `max_iterations` |
| `Condition` | Assinatura do `evaluator`; passos dentro dele podem ter `Loop` |
| `output_schema` | Funciona no OpenAI e no Gemini com pydantic aninhado e `Literal`; o que vem em `content` quando o parse falha |
| Métricas | Nomes dos campos de tokens (entrada, saída, cache) e de duração na resposta |
| Erros | Quais exceções o Agno levanta em 429, 5xx e timeout, depois dos `retries` do modelo |
| `run_id` e telemetria | Passar o id da task Celery como `run_id`; `telemetry=False` e `AGNO_TELEMETRY=false` desligam o envio |

O resultado vai para [docs/agents.md](../../../docs/agents.md), e qualquer diferença de API ajusta os esboços antes das etapas que dependem deles.
