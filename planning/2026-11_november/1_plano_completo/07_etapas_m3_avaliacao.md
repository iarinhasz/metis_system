# M3 — Avaliação

**Objetivo:** o relatório final real (3 avaliadores, juiz, consolidação) e a decisão, com números, do modo de avaliação (D13). A integridade ainda é *pass-through*.
**Trilhas:** A (3.1–3.10, 3.12, 3.13), P (3.11)
**Referência:** [Avaliadores, juiz e consolidação](../../../docs/evaluators_and_judge.md), [Agentes e workflows](../../../docs/agents.md#e4--avaliação-evaluationworkflowpy)

Caminhos relativos a `projects/correction/`.

---

## Etapa 3.1 — Contexto e modelos dos avaliadores

**O que fazer**
- `evaluation/context.py`: `EvaluationContextBuilder`, que junta o `ExtractedDocument`, o perfil, a Question (snapshot), os critérios, o resumo da integridade e as obras relacionadas.
- Os slots A (GPT), B (Gemini) e C (segundo modelo de uma das duas) vêm dos `ModelSpec` da 1.3; o snapshot vai para o `config_snapshot` do Run (D14).
- Dicas de divergência calculadas em código, para o juiz.

**Teste** (`evaluation/tests/test_context.py`)
- O contexto de uma fixture tem as seções com papel, o mapa e os critérios de cada papel.
- O snapshot dos specs fica no Run.

**Commit sugerido:** `feat: build the evaluation context`

---

## Etapa 3.2 — Schemas e models das rodadas

**O que fazer**
- `agents/schemas/evaluation.py`: `Observation`, `SectionObservations`, `CrossCheckResult`, `CriterionSynthesis`, `CriteriaSynthesis`, `RevisionResponse`, `JudgeReport` (com `ItemVerdict` e `Issue`), com os campos de [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#os-avaliadores).
- Models `ReviewRound` (único por run, slot e rodada) e `JudgeVerdict` (único por rodada, tipo e item; com `source` = `validator` ou `judge`).

**Teste** (`evaluation/tests/test_models.py`)
- Unicidades; um `grade` fora do enum do critério não valida.

**Commit sugerido:** `feat: add evaluation schemas and review round models`

---

## Etapa 3.3 — Passes por seção

**O que fazer**
- Prompts `agents/prompts/sections/<papel>.md`, um por papel, com o checklist do papel.
- Agente `section_reviewer(slot, role)`.
- Executor `SectionPassStep(slot)`: `bounded_map` sobre as seções (seção longa → uma chamada por subseção); grava as observações na `ReviewRound(round=1)`; pula a seção que já tem observações.

**Teste** (`evaluation/tests/test_section_pass.py`, fakes)
- Cada seção com papel gera observações; `other` não gera passe.
- Rodar de novo não chama o agente.
- Uma observação `missing` incerta vem com `possibly_elsewhere`.

**Implementação nesta branch:** `SectionPassStep` executa os passes por seção
com concorrência limitada, usa o `ModelSpec` congelado no Run, valida e
checkpointa observações em `ReviewRound(round=1)`, e retoma sem repetir seções
já concluídas. Cada subseção extraída é uma unidade de avaliação; quando o texto
de uma unidade excede o limite, os trechos terminam preferencialmente no último
parágrafo que couber, com fallback para linha, palavra e limite exato. O executor
é testável isoladamente; sua conexão ao workflow E4 fica para a etapa 3.10.

**Commit sugerido:** `feat: run section passes for each evaluator`

---

## Etapa 3.4 — Checagens entre seções

**O que fazer**
- Decidir a lista inicial (questão aberta Q13; proposta: promessas × resultados, método × pergunta, figuras × texto).
- Agente `cross_checker(slot, kind)` e executor `CrossCheckStep(slot)`, com só as seções envolvidas na entrada.

**Teste** (`evaluation/tests/test_cross_checks.py`): cada tipo recebe só as seções certas; resultado gravado na rodada.

**Implementação nesta branch:** a lista inicial fica fixada nos três tipos acima,
com pares de papéis ajustados ao tipo de artigo. A checagem de figuras usa apenas
seções ligadas às figuras pela extração. Tipos sem evidência suficiente são
ignorados; os resultados válidos são checkpointados e não são chamados de novo
no retry. O executor pode ser testado isoladamente; a conexão ao workflow E4
continua para a etapa 3.10.

**Commit sugerido:** `feat: add cross-section checks`

---

## Etapa 3.5 — Síntese por critério

**O que fazer**
- Agente `synthesizer(slot)` e executor `SynthesisStep(slot)`: nota + justificativa por critério, citando só ids de observações e checagens que existem.

**Teste** (`evaluation/tests/test_synthesis.py`): todos os critérios ativos recebem síntese; um critério já sintetizado não é chamado de novo.

**Commit sugerido:** `feat: synthesize criterion grades from observations`

---

## Etapa 3.6 — Modo whole_document

**O que fazer**
- Agente `whole_document_reviewer(slot)` e executor `WholeDocumentStep(slot)`: o artigo inteiro numa chamada, com `evidence[]` no lugar dos ids.
- Strategy de modo: `evaluator_steps(slot, mode)` escolhe os passos na montagem do workflow.

**Teste** (`evaluation/tests/test_modes.py`): o modo do `config_snapshot` monta os passos certos; os dois modos geram sínteses no mesmo schema.

**Commit sugerido:** `feat: add whole-document evaluation mode`

**Implementação nesta branch:** `WholeDocumentStep` envia o documento inteiro
uma vez por avaliador, exige uma síntese por critério com evidência direta em
seções existentes e checkpointa a rodada no modo `whole_document`. O modo é
configurável por `METIS_EVALUATION_MODE`, congelado no snapshot do Run, e a
strategy escolhe entre os passos sectioned (3.3–3.5) e whole-document. A ligação
ao workflow E4 continua para 3.10.

---

## Etapa 3.7 — Validadores determinísticos

**O que fazer**
- `evaluation/validators.py`, em cadeia: schema, nota permitida, critérios completos, evidência existe (match fuzzy normalizando espaços e hifenização), referências internas, justificativa.
- Executor `ValidateStep`: grava `JudgeVerdict(source=validator)` para o que recusar.

**Teste** (`evaluation/tests/test_validators.py`): um caso por validador; quote com hifenização diferente passa; quote inventado é recusado.

**Commit sugerido:** `feat: add deterministic validators for evaluator output`

**Implementação nesta branch:** `ValidatorChain` valida o schema antes das
regras determinísticas de escala, critérios, evidências, referências e
justificativas; `ValidateStep` grava `JudgeVerdict(source=validator)` por item
recusado e retoma sem regravar vereditos. A evidência é conferida em ambos os
modos, com referências por ID em `sectioned` e trechos diretos em
`whole_document`. Critérios ativos ausentes impedem a etapa porque não há um
item persistido ao qual associar um veredito.

---

## Etapa 3.8 — Juiz

**O que fazer**
- Agente `judge(for_spec)`, com o modelo de `judge_for` (D14) e o artigo inteiro como prefixo.
- Executor `JudgeStep`: uma chamada por avaliador, só com os itens ainda sem veredito na rodada; todo `missing` vai para o juiz.
- Conferência do `excerpt` (substring do item): se falhar, chama de novo com o motivo; se persistir, descarta o apontamento e registra.

**Teste** (`evaluation/tests/test_judge.py`, fakes)
- O avaliador GPT é julgado pelo juiz Gemini, e vice-versa; o slot C segue a família dele.
- `excerpt` que não é substring → segunda chamada; persistiu → apontamento descartado.
- Itens já julgados na rodada não vão de novo.

**Commit sugerido:** `feat: add the judge with cross-family assignment`

**Implementação nesta branch:** `JudgeStep` envia ao juiz cruzado somente itens
sem veredito; itens recusados pelos validadores da 3.7 seguem diretamente para a
revisão. O juiz recebe o artigo inteiro, a revisão do slot e dicas calculadas de
divergência. O `excerpt` de cada apontamento é conferido como substring do item;
uma saída com trecho incorreto recebe uma chamada corretiva, e apontamentos ainda
inválidos são descartados. Vereditos e snapshot do modelo julgador são persistidos
por item com checkpoints de posse e retomada.

---

## Etapa 3.9 — Revisão, loop e unresolved

**O que fazer**
- `RevisionPromptBuilder`: item anterior + trecho + motivo.
- Agente `reviser(slot, level)` e executor `RevisionStep`: só os itens inválidos; a revisão de uma observação roda o passe daquela seção só para ela e, depois, a síntese dos critérios que a citam.
- `accept` e `rebut` gravados na `ReviewRound(round=n+1)`.
- `has_pending_items` e `no_pending_items` consultando o banco; `MarkUnresolvedStep`.

**Teste** (`evaluation/tests/test_revision_loop.py`, fakes, o workflow do E4 parcial)
- Rodada 1 limpa → o loop não roda.
- Inválido uma vez → uma revisão, julgada, e o loop termina.
- Inválido sempre → 2 revisões, ambas julgadas, e o item vira `unresolved`.
- `rebut` com nova evidência aceito pelo juiz → o item fica válido sem mudar.
- A revisão de uma observação não roda de novo as outras seções.

**Commit sugerido:** `feat: add partial revision loop with rebuttal`

**Implementação nesta branch:** `RevisionStep` abre rodadas imutáveis para itens
recusados por validador ou juiz. `accept` substitui o item com a mesma identidade;
`rebut` mantém a avaliação e acrescenta evidência conferida no artigo. Vereditos
válidos independentes são copiados sem nova chamada; a revisão de observação ou
checagem atualiza somente as sínteses dependentes. O limite `METIS_MAX_REVISION_ROUNDS`
tem padrão 2; `MarkUnresolvedStep` marca as recusas restantes, e a agregação exclui
critérios que dependam de observações unresolved. A integração ao Workflow E4 segue
para a etapa 3.10.

---

## Etapa 3.10 — Workflow do E4

**O que fazer**
- `evaluation/workflow.py`: o workflow do E4 de [docs/agents.md](../../../docs/agents.md#e4--avaliação-evaluationworkflowpy) (D17).
- O stub do E4 no `StageTask` vira o workflow real.
- Conferir o tempo do E4 de uma fixture contra o soft limit (25 min).

**Teste** (`evaluation/tests/test_workflow.py`, eager, fakes)
- Fixture → `evaluated`, com 3 `ReviewRound` na rodada 1.
- Retry do estágio no meio → nada que já foi gravado é chamado de novo.
- `LLMUnavailable` persistente → `error_llm`; "Reprocessar" retoma do `integrity_checked`.

**Commit sugerido:** `feat: run the evaluation stage as an Agno workflow`

**Implementação (16/11/2026):** `EvaluationStage` executa o workflow Agno do E4
com a estratégia do snapshot (`sectioned` ou `whole_document`), checkpoints
retomáveis, validação e juiz por rodada, loop de revisão limitado, marcação de
`unresolved` e finalização das rodadas mais recentes dos slots A/B/C. Reentregas
retomam os checkpoints, inclusive uma rodada de revisão parcialmente gravada. O
E5 continua no mesmo módulo sem compartilhar seu estado com E4.

**Verificação:** 113 testes de avaliação e pipeline passaram com PostgreSQL 18;
Ruff e formatação passaram (263 arquivos); mypy passou nos quatro módulos alterados.
Os testes medem o fluxo com agentes falsos e comparam sua duração ao soft limit de
25 minutos; não medem tempo de provedor real nem qualidade das avaliações.

---

## Etapa 3.11 — Consolidação e relatório final

**O que fazer**
- `evaluation/aggregation.py`: mediana das notas válidas (com 2, a média), dispersão, total ponderado, faixa → recomendação; itens `unresolved` fora da agregação.
- Agente `meta_reviewer()` e a validação de que ele só cita ids que existem.
- Model `FinalReport` (JSON) + render em Markdown; `GET /api/runs/{id}/report`.
- Workflow do E5; o stub vira real.

**Teste**
- `test_aggregation.py`: mediana com outlier; 2 notas válidas → média; critério `unresolved` fora.
- `test_final_report.py`: o relatório tem `criteria[]`, `sections[]`, `integrity` e `versions`; o meta-revisor não altera notas.
- `attempts/tests/test_api.py`: `GET /report` antes de `done` → 409; depois → 200.

**Commit sugerido:** `feat: consolidate evaluations into the final report`

**Implementação (13/11/2026):** E5 real em `evaluation/workflow.py`, agregação
determinística, narrativa com ids validados e uma retentativa, checkpoints com
posse e relatório único/imutável. Inclui os contratos e models necessários da
3.2 (`ReviewRound`, `JudgeVerdict`), pois ainda não existiam nesta branch.
E4 continua stub e, sem três últimas rodadas finalizadas, E5 usa `waiting_setup`.
O relatório explicita integridade não verificada e faixas ainda não calibradas.
Endpoint autenticado JSON/Markdown, `409` antes de `done`, `404` para Runs internos.
Persistência e constraints cobertas por testes em PostgreSQL 18; agentes usam fakes.

Validação: **594 testes passaram**, com 5 contratos ao vivo excluídos; mypy
aprovou 219 arquivos, Ruff/formatação aprovados (221 arquivos), checks do Django
sem problemas e `makemigrations --check --dry-run` sem alterações pendentes.
As migrations `attempts/0005_run_consolidation.py` e `evaluation/0001_initial.py`
foram aplicadas pelo pytest em banco PostgreSQL 18 novo. Para atualizar o banco
de desenvolvimento, executar `uv run python manage.py migrate`.

---

## Etapa 3.12 — Rubric check

**O que fazer**
- Ação no admin da Question: "Rodar rubric check" com N attempts de amostra → cria Runs com `purpose=rubric_check` e a Question rascunho no `config_snapshot` (D18).
- Esses runs reaproveitam a extração do cache, pulam o E3 e rodam E2 (com a Question do snapshot), E4 e E5.
- Tela de resultado: os `FinalReport` lado a lado.

**Teste** (`questions/tests/test_rubric_check.py`)
- O rubric check não muda a Question ativa nem outros runs.
- O run usa a Question rascunho, e não a resolvida pela árvore.

**Commit sugerido:** `feat: run rubric checks with draft questions`

**Implementação (13/11/2026):** ação e formulário no admin para amostras de 1–20
attempts com cache do E1, criação atômica e idempotente de lotes internos,
snapshot do rascunho e da configuração de avaliação, desvio auditado do E3 e
comparação dos relatórios lado a lado. A Question ativa e avaliações anteriores
permanecem intactas. O desvio também vale para a retomada pelo reconciliador.

**Dependência pendente nesta branch:** E4 ainda é um stub; os relatórios completos
dependem das rodadas julgadas da etapa 3.10. A tela mostra `waiting_setup` quando
elas faltam. A integração substitui apenas E4 por rodadas julgadas sintéticas e
executa E2/E5 reais, com fakes no limite dos provedores.
Ver [operação no admin](../../../docs/questions_and_profiling.md#rubric-check-no-admin-312).

**Verificação:** 633 testes passaram em Python 3.14 e PostgreSQL 18, com 5 contratos
`llm` excluídos e apenas o aviso de depreciação existente do SDK Google. Mypy
aprovou 225 arquivos; Ruff e formatação passaram (227 arquivos); checks do Django
sem problemas e `makemigrations --check --dry-run` sem mudanças pendentes.

---

## Etapa 3.13 — A/B do modo de avaliação e custo

**O que fazer**
- Comando `ab_evaluation_mode`: cria Runs `purpose=ab_test` nos dois modos para o mesmo conjunto (~10–20 artigos: PeerRead + artigos da equipe) e 3 execuções por avaliador.
- Métricas de [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#como-decidir-o-modo-ab-no-m3): variação da nota, concordância, taxa de invalidação pelo juiz, correlação com o PeerRead, custo e tempo.
- Com duas famílias, a concordância entre A e C (mesma família ou não) fica separada das outras (R13).
- Registrar a decisão (Q12) e o custo por artigo (Q2) no planejamento.

**Pronto quando:** o modo padrão está decidido e registrado.

**Commit sugerido:** `feat: compare evaluation modes with an A/B command`

---

## Pronto do M3 (I3 e parte do I5)

- Um PDF real gera o `FinalReport` no E2E.
- Os testes com fakes passam: inválido N vezes, quote inexistente, `missing` falso, réplica, limite de rodadas.
- O A/B rodou, e o modo padrão foi decidido e registrado.
- O custo por artigo foi medido nos dois modos.
- A verificação manual de [12](12_testes_e_verificacao.md#i3--avaliação-real) passa.
