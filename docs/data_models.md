# Modelos de dados

Revisão de 13/11/2026. `attempts`, `questions`, `extractor` e `evaluation`
têm models e migrations. A seção `integrity` e suas entidades no diagrama são
**planejadas**, ainda sem app instalado. Os campos são um resumo; models e
migrations são a fonte de tipos, índices e restrições. [Estado do módulo](status_and_metrics.md).

## Visão geral

```text
Article 1──N Attempt 1──N Run ──┬── N RunEvent              (trilha de auditoria)
                                ├── N LLMCall               (custo por chamada)
                                ├── 1 IntegrityReport 1──N IntegrityFinding
                                ├── N ReviewRound 1──N JudgeVerdict
                                ├── 1 FinalReport
                                ├── → Extraction            (compartilhada entre runs: sha256 + versão do extractor)
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
| `title` | Campo opcional; o E1 atual guarda o título em `Extraction.content.title`, sem atualizar `Article.title` |

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
| `stage_claims` | Quantas vezes o estágio atual começou (retries contam); zera no "Reprocessar" |
| `publish_count` | Republicações do checkpoint atual; zera no claim e no "Reprocessar" |
| `version` | +1 a cada transição; compõe o `event_key` |
| `last_error` | Último erro. O histórico fica nos eventos |
| `extraction` | A `Extraction` que o E1 ligou ao run; os estágios seguintes leem daqui |
| `question` | FK com `PROTECT` para a Question resolvida; no rubric check aponta ao rascunho desde a criação |
| `profile` | JSON do E2: `field_choice`, `classification` (área, confianças, tipo e idioma), `resolution`, `section_roles`, `document_map` e `complete` |
| `config_snapshot` | Specs sem credenciais, templates e hashes dos prompts usados, versão da taxonomia, política do profiler, método e snapshot da Question. Num rubric check, recebe a Question rascunho e `rubric_check` com id do lote, revisão do rascunho e versão da extração |
| `purpose` | `evaluation` (padrão), `rubric_check` ou `ab_test`, indexado e com constraint no banco. Runs internos não aparecem nas rotas públicas nem participam da substituição de avaliações (D18) |

Implementado na etapa 2.5, com a migration `0004` de `attempts`. Os JSONs começam
vazios e aceitam checkpoints parciais; `complete=True` só é gravado depois do mapa.
Cada gravação confere status `profiling` e a posse pelo id da task. O reprocessamento
preserva os checkpoints e o snapshot, inclusive a Question já resolvida.

**`RunEvent`**: append-only.

| Campo | Observação |
|---|---|
| `run` | FK |
| `event_type` | `transition`, `retry_scheduled` ou `republished` |
| `from_status`, `to_status`, `stage`, `task_id` | Contexto do evento |
| `actor` | `pipeline`, `reconciler`, um usuário do admin ou o serviço da API |
| `payload` | JSON: erro, decisão humana, nota, motivo da republicação |
| `event_key` | Único: `{run}:{version}` nas transições. Retry e reentrega não duplicam eventos |

**`LLMCall`** (M1, etapa 1.4): uma linha por execução do runner, inclusive falhas e respostas inválidas. O admin permite somente leitura.

| Campo | Observação |
|---|---|
| `run`, `stage`, `role` | Run e estágio; papel do catálogo (`fast`, `vision`, `evaluator_a`, `judge_google`…) |
| `agent` | Agente executado (`profiler_field`, `figure_describer`, `document_extractor`…) |
| `provider`, `model`, `prompt_version` | A versão é o hash do prompt |
| `input_tokens`, `output_tokens`, `cached_tokens` | Vêm das métricas do Agno |
| `cache_write_tokens`, `reasoning_tokens` | Contagens adicionais; a saída inclui raciocínio uma única vez |
| `cost_usd`, `latency_ms` | Custo pela tabela de preços (um modelo sem preço gera alerta) |
| `success`, `error` | Resultado da chamada |

`cost_usd` usa `Decimal` com 12 casas e aceita nulo quando não há tarifa cadastrada. Os registros guardam o custo calculado na chamada: atualizar a tabela não altera o histórico. O sink não grava prompt, resposta, credenciais nem PDF. O acesso ao banco fica em `queries/attempts/llm_call.py`.

Na etapa 6.2, o admin passou a agregar esses registros por run, estágio, papel,
provedor/modelo e dia, respeitando busca e filtros. Custos nulos deixam o total parcial,
com contagem explícita; falhas e novas tentativas também são somadas. O alerta usa o
histórico completo de cada run e o limite opcional `METIS_LLM_RUN_BUDGET_USD`, sem alterar
os registros ou o estado do run. Detalhes em [Custo](agents.md#consulta-no-admin-62).

## `questions`

Implementado na etapa 2.1. Os três models herdam UUIDv7 e timestamps da base comum.

| Model | Campos principais |
|---|---|
| `TaxonomyNode` | `code`, `level` (domain, field, subfield, topic), `name`, `parent`, `taxonomy_version` |
| `Question` | `taxonomy_node` (vazio na genérica), `is_generic`, `name`, `method`, `validated`, `active`, `version` |
| `RubricField` | `question`, `key`, `label`, `rubric_text` (contexto do domínio, com quebras de linha), `order` |

Os critérios não são model: ficam em código (`EvaluationConfig`), ver [Perfil e Questions](questions_and_profiling.md#critérios-em-código).

- `TaxonomyNode.code` guarda a URL canônica do OpenAlex, com unicidade por
  `(code, taxonomy_version)`. A versão é o SHA-256 da árvore normalizada. O pai usa
  `PROTECT`; domains não têm pai e cada outro nível aponta para o nível imediatamente
  anterior da mesma versão. A carga valida todos os caminhos antes de gravar.
- Uma carga de conteúdo diferente cria outra versão inteira, preservando os UUIDs e nomes
  da anterior. Repetir conteúdo idêntico não altera os registros existentes.
- `Question.taxonomy_node` usa `PROTECT` e só fica vazio quando `is_generic=True`.
  A curadoria cria rascunhos com `validated=False`, `active=False` e `version=1`. Há no máximo uma
  Question validada e ativa por nó e método, e uma genérica validada e ativa por método.
  A resolução da etapa 2.3 devolve um snapshot imutável com id, versão e textos das
  rubricas. A curadoria da etapa 2.6 incrementa a versão ao validar; edições retiram
  aprovação e ativação. Ações de ativar/desativar preservam a versão dos textos.
- `RubricField` é único por `(question, key)`, ordenado por `order` e UUID. O texto
  mantém suas quebras de linha. A exclusão da Question remove seus campos (`CASCADE`).

O admin edita `RubricField` em linha na Question. Os Managements de curadoria
travam a Question antes de alterar textos, aprovar ou ativar. A leitura de
candidatas e suas rubricas usa a mesma disciplina, produzindo um snapshot
consistente para o Run. A edição usa também a revisão temporal da página para
recusar sobrescritas de outro curador. A etapa 2.6 usa os campos existentes e não
requer migration nova.

## `extractor`

| Model | Campos principais |
|---|---|
| `Extraction` | `sha256`, `version` (hash da config e dos prompts do extractor), `content` (o `ExtractedArticle` em JSON, descrito em [Extração](extraction.md#o-resultado)). Único por (sha256, versão) |
| `ExtractionStep` | `sha256`, `version`, `key` (hash do prompt, do schema e de `with_document`), `answer` (a resposta do modelo em JSON). Único por (sha256, versão, chave). Guarda as respostas enquanto a extração não termina, para o retry do estágio retomar delas; apagado quando a `Extraction` é guardada ([Extração](extraction.md#retomada)) |

As figuras e as descrições ficam dentro do `content` da `Extraction` (1.6 e 1.8); o recorte da imagem foi adiado.

## `integrity`

**Planejado para M4/M5.** Não existem models/migrations dessas entidades na base
atual. E3 não grava relatório; `FinalReport.integrity` é um resumo JSON com
`not_checked`, sem FK para uma tabela de integridade.

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

Os três models de `evaluation` estão implementados como dependência da consolidação
3.11. `ReviewRound` também guarda `unresolved` e `ready`: só a última rodada
finalizada de cada slot chega ao E5. `JudgeVerdict` registra ids e origem, exigindo
snapshot do modelo quando a origem é `judge`. Ambos exigem posse do E4 para escrita.
As unicidades e os enums das colunas de slot, modo, veredito e origem têm
constraints no PostgreSQL. Os conteúdos JSON passam pelos schemas e pela
escala do método antes da gravação.

`Run.consolidation` guarda inputs e checkpoints do E5. `FinalReport` usa FK 1:1 com
`PROTECT`, `content` JSON e `markdown`. As colunas auxiliares permitem nota,
concordância e recomendação nulas quando não há votos válidos; isso não produz
nota zero nem rejeição automática. A gravação trava o Run e confere a task dona
do E5. Um retry reaproveita o relatório existente; ele não é editável no admin.

As migrations são `attempts/0005_run_consolidation.py` e `evaluation/0001_initial.py`.

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
| `waiting_setup` | recuperável | Falta chave/configuração, taxonomia, Question ou rodadas completas para E5 |
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
