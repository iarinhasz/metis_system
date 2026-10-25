# Roteiro: marcos M0–M6

```text
M0 Fundação ─▶ M1 Extração ─▶ M2 Perfil + Questions ─▶ M3 Avaliação ─┬─▶ M4 Integridade, Fase 1 ─┐
                                                                     └─▶ M5 Integridade, Fase 2 ─┴─▶ M6 Qualidade
```

**Por que esta ordem**
- O valor central, a avaliação, vem antes da integridade. Até o M4, o E3 é *pass-through*: devolve risco baixo e um relatório vazio, com `coverage` = "não checado".
- M4 e M5 podem andar em paralelo, com pessoas diferentes. Os dois dependem do M1 (referências extraídas) e do M3 (pipeline completo).
- A resolução das referências (passo 1 da Fase 2) é usada pelas duas fases, por isso entra no começo do M4.

Cada marco ganha a própria pasta de planejamento quando começar (`planning/<ano-mês>/<n>_<tema>/`), no mesmo formato desta.

---

## M0 — Fundação

**Objetivo:** o esqueleto ponta a ponta. Um PDF submetido passa pelos 5 estágios (ainda stubs) até `done`, com retries, gate humano e reconciliador funcionando.

**Entregas:** projeto Django + config, qualidade (ruff, mypy, pytest, CI), máquina de estados, API de submissão, pipeline com estágios stub, gate e reprocessamento, reconciliador, Docker. As etapas estão em [03](03_etapa_m0_fundacao.md).

**Pronto quando**
- O CI passa.
- `docker compose up` + `POST /api/attempts` levam o run a `done`.
- Os caminhos do gate (continuar, encerrar), das falhas e do reconciliador têm teste.

---

## M1 — Extração

**Objetivo:** o `ExtractedDocument` real.

**Entregas**
- Serviço `grobid` no compose e cliente com os parâmetros de [Extração](../../../docs/extraction.md). As seções saem com hierarquia (seção e subseção), para o E4 conseguir dividir seções longas.
- Docling: figuras, tabelas, fórmulas; junção GROBID ↔ Docling por bbox; recorte das figuras.
- Base de agentes em `agents/`, montada junto com o primeiro agente (descrição de figuras):
  - `ModelFactory` e `AgentFactory`;
  - schemas de saída;
  - prompts com render e hash;
  - `LLMCall` + tabela de preços.
- Scan de texto oculto.
- `ExtractedDocumentBuilder`, os models `ExtractedDocument` e `Figure`, e o cache por sha256 + versões.
- Gate de qualidade; o E1 real dentro do `StageTask`.

**Pronto quando**
- 3–5 PDFs reais geram um `ExtractedDocument` estável (snapshot).
- Um gráfico vetorial é detectado e recortado inteiro.
- Um texto oculto plantado é detectado.
- A ligação citação ↔ referência é medida contra o PeerRead (a meta sai da primeira medição).
- Cada chamada de visão aparece em `LLMCall`, com custo.

**Riscos**
- Wheels do Docling/torch para Python 3.14.
- Tempo de extração em CPU.

---

## M2 — Perfil e Questions

**Objetivo:** cada artigo ganha uma área e uma Question resolvida, com o contexto do domínio.

**Entregas**
- App `questions`: `TaxonomyNode`, `Question`, `RubricField`.
- Comando `load_taxonomy` (dry-run por padrão, grava com `--execute`).
- Critérios em código: o núcleo + as regras por `paper_type`.
- `ArticleProfiler` em 2 passos e resolver com fallback.
- Papéis das seções (regra por título + LLM nos ambíguos) e o mapa do documento, montado em código.
- Curadoria no admin: rascunho por LLM, edição, rubric check isolado, validação, versão.
- A Question genérica + 2–3 áreas (questão aberta Q4).
- O Run passa a guardar a Question e o snapshot dela.

**Pronto quando**
- Uma amostra rotulada (ex.: 10 artigos por área) é classificada no field certo; a meta é definida na primeira medição.
- O fallback está coberto por testes.
- A curadoria funciona ponta a ponta no admin.
- Os papéis das seções batem com uma amostra rotulada à mão.

**Riscos:** tempo de curadoria; artigos interdisciplinares.

---

## M3 — Avaliação

**Objetivo:** o relatório final real, com 3 avaliadores, juiz e consolidação, e a decisão, com números, de como o avaliador lê o artigo (D13). A integridade ainda é *pass-through*.

**Entregas**
- `EvaluationContextBuilder`.
- `ModelSpec`s dos 3 avaliadores e do juiz, com `judge_for`.
- Modo `sectioned`:
  - um prompt por papel de seção;
  - passes por seção, num pool com limite;
  - checagens entre seções;
  - síntese por critério.
- Modo `whole_document`: uma chamada por avaliador, como linha de base do A/B.
- Validadores determinísticos.
- Passos do workflow: `JudgeStep`, `RevisionStep` + `RevisionPromptBuilder` (`accept`/`rebut`, com revisão no nível da seção ou do critério), e o `Loop` com limite.
- Models `ReviewRound` e `JudgeVerdict`, com itens por observação, checagem e critério.
- `ConsolidationStep`: agregação + meta-revisor.
- `FinalReport` (por critério e por seção) + `GET /api/runs/{id}/report`.
- Comando do A/B: roda os dois modos no mesmo conjunto e compara as métricas de [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#como-decidir-o-modo-ab-no-m3).

**Pronto quando**
- Um PDF real gera o `FinalReport` no E2E.
- Os testes com fakes passam: inválido N vezes, quote inexistente, `missing` falso, réplica, limite de rodadas.
- O A/B rodou em ~10–20 artigos (PeerRead + artigos da equipe), e o modo padrão foi decidido e registrado.
- O custo por artigo foi medido nos dois modos; isso alimenta a questão aberta Q2.

**Riscos:** custo (R1); viés dos modelos (R11); complexidade do modo por seção (R12).

---

## M4 — Integridade, Fase 1

**Objetivo:** a similaridade em funil, as regras de risco e o gate humano.

**Entregas**
- **Resolução de referências em cascata** (Crossref → OpenAlex por DOI → S2 `search/match`), com rate limit e cache em `scholarly/`.
- **Corpus:**
  - `SourceDocument` e `SourceChunk`, com a extensão pgvector e índice HNSW;
  - comando `load_peerread`, que semeia o corpus.
- **Funil:**
  - fontes de candidatos (Strategy), com orçamento de buscas;
  - MinHash + winnowing;
  - BGE-M3 local + alinhamento PT↔EN;
  - filtro por citação;
  - LLM nos top-N pares.
- **Decisão e revisão:**
  - regras de risco v1 e `IntegrityReport`;
  - gate no admin, com as evidências lado a lado;
  - `GET /api/runs/{id}/integrity`.

**Pronto quando**
- Precisão e recall foram medidos no plágio sintético do PeerRead e atingem a meta (questão aberta Q11).
- No E2E, um PDF com trecho copiado vai a `waiting_human_review`, a decisão "continuar" leva a `done`.

**Riscos:** cobertura (R2); falso positivo (R3); mudanças nas APIs (R7).

---

## M5 — Integridade, Fase 2

**Objetivo:** a verificação das citações e o cruzamento com a Fase 1.

**Entregas**
- Existência em cascata, com critérios de aceite e LLM nos casos duvidosos.
- Retratação; consistência (referência não citada, citação sem referência, autocitação).
- Alinhamento citação ↔ afirmação, pelo abstract primeiro.
- Cruzamento das fases (citação faltante).
- Regras de risco v2.

**Pronto quando**
- Referências inventadas plantadas são detectadas, e a taxa de falso positivo foi medida.
- Há uma linha de base em SciCiteVal e Citation Integrity.

**Riscos:** falso positivo em referências sem DOI (livros, teses, relatórios); limites das APIs.

---

## M6 — Qualidade

**Objetivo:** medir, calibrar e endurecer.

**Entregas**
- Comandos de eval (`bench_reviews`, `bench_plagiarism`, `bench_judge`), com relatório por versão de prompt e por `ModelSpec`.
- Visão de custo no admin (agregações de `LLMCall`).
- Endurecimento: limites de upload e de páginas, timeouts, teste de carga leve.
- Revisão dos docs.

**Pronto quando**
- A correlação com o PeerRead está medida e registrada.
- As metas dos marcos anteriores foram revisadas com os números.
- Os docs refletem o código.
