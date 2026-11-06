# Modelos de dados

Campos principais previstos. Cada marco fecha os models do seu app (tipos, índices, restrições), e este documento é atualizado junto com o código.

## Visão geral

```text
Article 1──N Attempt 1──N Run ──┬── N RunEvent              (trilha de auditoria)
                                ├── N LLMCall               (custo por chamada)
                                ├── 1 IntegrityReport 1──N IntegrityFinding
                                ├── N ReviewRound 1──N JudgeVerdict
                                ├── 1 FinalReport
                                ├── → ExtractedDocument     (compartilhado entre runs: sha256 + versões dos parsers)
                                └── → Question (+ snapshot)

TaxonomyNode 1──N Question 1──N RubricField
SourceDocument 1──N SourceChunk                             (corpus da similaridade, com vetores)
```

Todos os models herdam de uma base com PK **UUIDv7** (ordenável no tempo), `created_at` e `updated_at`. O valor é gerado por `uuid.uuid7` (Python 3.14) e, como `db_default`, por `uuidv7()` (Postgres 18).

## `attempts`

**`Article`**

| Campo | Observação |
|---|---|
| `external_id` | Texto, único. A chave do artigo no sistema que submete (ver questão aberta Q3 no planejamento) |
| `title` | Preenchido pelo E1, a partir do cabeçalho do PDF |

**`Attempt`**: uma versão enviada do artigo.

| Campo | Observação |
|---|---|
| `article` | FK, `PROTECT` |
| `attempt_number` | Único por artigo; incrementa a cada versão |
| `file` | PDF no storage do Django, fora de qualquer URL pública |
| `original_filename`, `size_bytes` | Metadados do upload |
| `sha256` | Único por artigo: reenviar o mesmo arquivo devolve a attempt existente |
| `submitted_by` | O serviço autenticado que enviou |

**`Run`**: uma execução do pipeline.

| Campo | Observação |
|---|---|
| `attempt` | FK, `PROTECT` |
| `status` | `RunStatus`, indexado. Só muda via `RunManagement` |
| `stage` | Estágio atual, ou o último que rodou |
| `current_task_id` | Id da task Celery dona do estágio em andamento |
| `stage_started_at` | Início do estágio atual; o reconciliador usa para achar estágios travados |
| `stage_claims` | Quantas vezes o estágio atual começou (retries contam) |
| `publish_count` | Republicações do checkpoint atual |
| `version` | +1 a cada transição; compõe o `event_key` |
| `last_error` | Último erro. O histórico fica nos eventos |
| `extracted_document` (M1) | FK para a extração usada |
| `question` (M2) | FK para a Question resolvida |
| `profile` (M2) | Perfil do E2: área, confiança, tipo de artigo, idioma, papéis das seções e mapa do documento |
| `config_snapshot` (M2+) | `ModelSpec`s, versões de prompt, versão da taxonomia, snapshot da Question, modo de avaliação. Num rubric check, leva a Question rascunho |
| `purpose` (M2) | `evaluation` (padrão), `rubric_check` ou `ab_test`. Só `evaluation` aparece para quem submete e torna outros runs `superseded` (D18) |

**`RunEvent`**: append-only.

| Campo | Observação |
|---|---|
| `run` | FK |
| `event_type` | `transition`, `retry_scheduled` ou `republished` |
| `from_status`, `to_status`, `stage`, `task_id` | Contexto do evento |
| `actor` | `pipeline`, `reconciler`, um usuário do admin ou o serviço da API |
| `payload` | JSON: erro, decisão humana, nota, motivo da republicação |
| `event_key` | Único: `{run}:{version}` nas transições. Retry e reentrega não duplicam eventos |

**`LLMCall`** (M1): uma linha por chamada de modelo.

| Campo | Observação |
|---|---|
| `run`, `stage`, `role` | Papel: `profiler`, `figure_describer`, `evaluator_<slot>`, `judge`, `meta_reviewer`, `adjudicator`… |
| `provider`, `model`, `prompt_version` | A versão é o hash do prompt |
| `input_tokens`, `output_tokens`, `cached_tokens` | Vêm das métricas do Agno |
| `cost_usd`, `latency_ms` | Custo pela tabela de preços (um modelo sem preço gera alerta) |
| `success`, `error` | Resultado da chamada |

## `questions`

| Model | Campos principais |
|---|---|
| `TaxonomyNode` | `code`, `level` (domain, field, subfield, topic), `name`, `parent`, `taxonomy_version` |
| `Question` | `taxonomy_node` (vazio na genérica), `is_generic`, `name`, `method`, `validated`, `active`, `version` |
| `RubricField` | `question`, `key`, `label`, `rubric_text` (contexto do domínio, com quebras de linha), `order` |

Os critérios não são model: ficam em código (`EvaluationConfig`), ver [Perfil e Questions](questions_and_profiling.md#critérios-em-código).

## `extraction`

| Model | Campos principais |
|---|---|
| `ExtractedDocument` | `sha256`, `parser_versions`, `content` (JSON com o contrato descrito em [Extração](extraction.md#o-extracteddocument)). Único por (sha256, versões) |
| `Figure` | `document`, `figure_id`, `page`, `bbox`, `kind`, `caption`, `image` (recorte), `image_sha256`, `description` (`FigureDescription`) |

## `integrity`

| Model | Campos principais |
|---|---|
| `IntegrityReport` | `run` (1:1), `risk_level`, `coverage`, `narrative`, `rules_version` |
| `IntegrityFinding` | `report`, `type`, `severity`, `excerpt` (texto, página, offsets), `source` (DOI/URL, título, trecho), `lexical_score`, `semantic_score`, `cited`, `verdict`, `rationale` |
| `SourceDocument` | `origin` (interno ou externo), `attempt` (se interno), `doi`, `arxiv_id`, `openalex_id`, `title`, `year`, `oa_url`, `license`, `fetched_at` |
| `SourceChunk` | `source`, `ordinal`, `text`, `lang`, `embedding` (`VectorField(1024)` + `HnswIndex` por cosseno) |

## `evaluation`

| Model | Campos principais |
|---|---|
| `ReviewRound` | `run`, `evaluator_slot`, `model_spec` (snapshot), `round_number`, `mode` (`sectioned` ou `whole_document`), `observations`, `cross_checks`, `criteria` (sínteses), `changed_items` e as respostas `accept`/`rebut` dos itens revisados. Guarda o estado completo da revisão naquela rodada. Único por (run, slot, rodada) |
| `JudgeVerdict` | `round`, `item_type` (observação, checagem ou critério), `item_key`, `verdict`, `issues` (categoria, trecho, motivo), `source` (`validator` ou `judge`), `judge_model` (vazio quando é validador). Único por (rodada, tipo, item) |
| `FinalReport` | `run` (1:1), `recommendation`, `total_score`, `agreement`, `content` (JSON completo, ver [Avaliadores e juiz](evaluators_and_judge.md#consolidação-e5)) |

## Estados do Run

| Status | Tipo | Significado |
|---|---|---|
| `received` | checkpoint | Run criado; aguarda o E1 |
| `extracting` | rodando | E1 em andamento |
| `extracted` | checkpoint | Extração pronta; aguarda o E2 |
| `profiling` | rodando | E2 em andamento |
| `profiled` | checkpoint | Question resolvida; aguarda o E3 |
| `checking_integrity` | rodando | E3 em andamento |
| `integrity_checked` | checkpoint | Integridade ok ou liberada por uma pessoa; aguarda o E4 |
| `waiting_human_review` | espera | Risco alto; aguarda a decisão no admin |
| `evaluating` | rodando | E4 em andamento |
| `evaluated` | checkpoint | Avaliações prontas; aguarda o E5 |
| `consolidating` | rodando | E5 em andamento |
| `done` | final | Relatório final pronto |
| `rejected_invalid_submission` | final | O PDF não é um artigo processável |
| `closed_by_reviewer` | final | Encerrado na revisão humana |
| `superseded` | final | Chegou uma versão mais nova do artigo |
| `waiting_setup` | recuperável | Falta configuração (nenhuma Question disponível) |
| `error_llm`, `error_external` | recuperável | Falha do provedor ou de serviço externo após os retries |
| `error_unexpected` | recuperável | Bug, ou o reconciliador desistiu após os limites |

```text
received ─▶ extracting ─▶ extracted ─▶ profiling ─▶ profiled ─▶ checking_integrity ─┬─▶ integrity_checked ─▶ evaluating ─▶ evaluated ─▶ consolidating ─▶ done
                                                                                    │          ▲
                                                                                    └─▶ waiting_human_review ─┬─ continuar ─┘
                                                                                                              └─ encerrar ─▶ closed_by_reviewer

estágio rodando ──▶ rejected_invalid_submission | waiting_setup | error_llm | error_external | error_unexpected
waiting_setup / error_* ──"Reprocessar"──▶ checkpoint do estágio que falhou
qualquer status não final ──▶ superseded (chegou versão nova do artigo)
```

### Transições permitidas

"Falhas" = `rejected_invalid_submission`, `waiting_setup`, `error_llm`, `error_external`, `error_unexpected`.

| De | Para |
|---|---|
| `received` | `extracting`, `superseded`, `error_unexpected` |
| `extracting` | `extracted`, `received` (reconciliador), falhas, `superseded` |
| `extracted` | `profiling`, `superseded`, `error_unexpected` |
| `profiling` | `profiled`, `extracted` (reconciliador), falhas, `superseded` |
| `profiled` | `checking_integrity`, `superseded`, `error_unexpected` |
| `checking_integrity` | `integrity_checked`, `waiting_human_review`, `profiled` (reconciliador), falhas, `superseded` |
| `integrity_checked` | `evaluating`, `superseded`, `error_unexpected` |
| `waiting_human_review` | `integrity_checked` (continuar), `closed_by_reviewer` (encerrar), `superseded` |
| `evaluating` | `evaluated`, `integrity_checked` (reconciliador), falhas, `superseded` |
| `evaluated` | `consolidating`, `superseded`, `error_unexpected` |
| `consolidating` | `done`, `evaluated` (reconciliador), falhas, `superseded` |
| `waiting_setup`, `error_*` | o checkpoint do estágio que falhou ("Reprocessar"), `superseded` |
| `done`, `rejected_invalid_submission`, `closed_by_reviewer`, `superseded` | nenhuma (finais) |

Um checkpoint vai para `error_unexpected` quando o reconciliador desiste depois de republicar N vezes.

## Regras

- O status só muda pelo `RunManagement`. Uma transição fora da tabela levanta exceção: é bug de código, não condição de corrida.
- As FKs de `Article`, `Attempt` e `Run` usam `PROTECT`, para não perder trilha de auditoria.
- `event_key` único: retry e reentrega não duplicam eventos.
- Os arquivos (PDFs, recortes) nunca são servidos por URL.
