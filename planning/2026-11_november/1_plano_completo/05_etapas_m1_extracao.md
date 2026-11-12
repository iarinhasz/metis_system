# M1 — Extração e base do Agno

**Objetivo:** o `ExtractedDocument` real e a base do Agno (`agents/`, `LLMCall`) que todos os estágios seguintes usam.
**Trilhas:** A (1.1–1.4), P (1.5–1.10)
**Referência:** [Extração](../../../docs/extraction.md), [Agentes e workflows](../../../docs/agents.md)
**Fora daqui:** OCR de PDF escaneado (fica `rejected_invalid_submission`), Questions (M2)

Caminhos relativos a `projects/correction/`.

---

## Etapa 1.1 — Contrato do ExtractedDocument e fixtures do PeerRead

**O que fazer**
- **`extraction/contract.py`:** o `ExtractedDocument` em pydantic congelado, com os campos de [Extração](../../../docs/extraction.md#o-extracteddocument) e um `contract_version`.
  - Seções com hierarquia (`level`, `parent_id`), offsets e páginas.
  - `references[]` com a string crua e os campos parseados; `citation_mentions[]` com a frase e a seção.
- **`render_for_llm()`:** o artigo inteiro ou uma seção, com `[FIGURA n: …]` e `[TABELA n: …]` na posição de cada elemento, e a divisão de seções longas por subseção.
- **Comando `make_peerread_fixtures`** (dry-run por padrão): lê os JSONs `parsed_pdfs` do zip em `dataset_project/raw/` e grava 10–20 artigos como `ExtractedDocument` em `extraction/tests/fixtures/`.
  - As figuras vêm sem recorte e sem descrição: o PeerRead não tem imagens.

**Por quê**
O contrato é o que E2–E5 leem. Com ele e as fixtures, as trilhas A e I começam sem esperar o GROBID e o Docling (D19).

**Teste** (`extraction/tests/test_contract.py`)
- Um documento sem abstract ou sem seções não valida.
- `render_for_llm()` põe as figuras e tabelas na posição certa e divide uma seção longa por subseção.
- As fixtures geradas validam no contrato atual.

**Pronto quando:** as fixtures validam, e as trilhas A e I conseguem carregá-las num teste.

**Commit sugerido:** `feat: add ExtractedDocument contract and PeerRead fixtures`

---

## Etapa 1.2 — Spike do Agno 3 em Python 3.14

**O que fazer**
- Adicionar `agno>=3.1,<4`, `openai` e `google-genai` ao `pyproject.toml` e conferir a instalação em Python 3.14.
- Escrever `agents/tests/test_agno_contract.py`, marcado para rodar fora do CI (precisa de chave), conferindo cada item de [O que confirmar no Agno 3](01_diagnostico.md#o-que-confirmar-no-agno-3):
  - um `Workflow` com `Parallel`, `Condition` e `Loop` sobre executors falsos, para assinaturas, ordem e exceções;
  - um `Agent` com `output_schema` aninhado (com `Literal`) no OpenAI e no Gemini, para o parse e as métricas;
  - uma chamada com chave inválida e outra com timeout curto, para as exceções.
- Registrar o resultado em [docs/agents.md](../../../docs/agents.md) e ajustar os esboços que mudarem.

**Por quê**
O Agno 3 é recente (R8), e o Python 3.14 não está confirmado (R15). Tudo que vem depois assume essas assinaturas.

**Pronto quando:** cada item da tabela está confirmado ou corrigido nos docs. Se o Agno não rodar em 3.14, a decisão (fixar a versão ou usar uma imagem 3.13 nos workers) fica registrada antes da 1.3.

**Commit sugerido:** `chore: add agno and verify its workflow API`

---

## Etapa 1.3 — Pacote `agents/`

**O que fazer**
- `specs.py`, `models.py`, `factory.py`, `runner.py`, `prompts/`, `schemas/`, `usage.py`, `pricing.py`, `limits.py`, `errors.py` e `fakes.py`, como em [docs/agents.md](../../../docs/agents.md#o-pacote-agents).
- **Configuração** em `MetisSettings`:
  - um `ModelSpec` por papel (`evaluator_a`, `evaluator_b`, `evaluator_c`, `judge_openai`, `judge_google`, `meta_reviewer`, `vision`, `fast`, `adjudicator`);
  - `openai_api_key` e `google_api_key`;
  - `llm_max_concurrency`.
- **`judge_for(spec)`:** devolve o juiz da outra família (D14).
- **Prompts:** `render()` com `<<nome>>`, erro se sobrar marcador, versão por hash e exemplo JSON gerado do schema.
- **`metis/concurrency.py`:** `bounded_map(fn, items, max_workers)`, que fecha a conexão do Django ao fim de cada tarefa (D20).
- **`agents/tests/test_import_boundaries.py`** (D16).

**Por quê**
Um ponto único para modelos, chaves, retries, custo e fakes. Sem ele, cada estágio reinventaria a chamada.

**Teste**
- `test_specs.py`: spec inválido não sobe; papel sem spec → erro de configuração na subida.
- `test_models.py`: `judge_for` sempre devolve a outra família, inclusive para o slot C.
- `test_prompts.py`: marcador sobrando → erro; exemplo JSON bate com o schema; o hash muda quando o texto muda.
- `test_runner.py`: com um modelo falso, `content` em `str` → `AgentResult(valid=False)`; a exceção do provedor → `LLMUnavailable`; o `UsageSink` recebe uma chamada por execução.
- `test_limits.py`: com N threads, o limiter nunca passa do limite.
- `metis/tests/test_concurrency.py` (`transaction=True`): o `bounded_map` não deixa conexão aberta.
- `test_import_boundaries.py`.

**Pronto quando:** os testes passam, e a `FakeAgentFactory` cobre todos os papéis do catálogo (os que ainda não têm schema real devolvem um schema mínimo).

**Commit sugerido:** `feat: add agents package with model and agent factories`

---

## Etapa 1.4 — LLMCall, preços e registro de uso

**O que fazer**
- Model `LLMCall` em `attempts/`, com os campos de [Modelos de dados](../../../docs/data_models.md#attempts); admin somente leitura.
- `pipeline/usage.py`: o `UsageSink` real, que grava o `LLMCall` ligado ao run e ao estágio.
- `agents/pricing.py`: tabela inicial com os modelos configurados; um modelo sem preço → custo vazio + alerta no log.

**Teste** (`pipeline/tests/test_usage.py`)
- Uma chamada pelo runner com modelo falso gera um `LLMCall` com tokens, custo e versão do prompt.
- Modelo sem preço → `cost_usd` vazio e alerta.

**Pronto quando:** os testes passam.

**Commit sugerido:** `feat: record LLM calls with token usage and cost`

---

## Etapa 1.5 — Divisão do artigo pelo modelo

**Situação:** implementada em 11/11/2026, no lugar do GROBID.

**Por que mudou:** o GROBID chegou a ser implementado e foi descartado: a imagem tem 1,7 GB e ele ocupa 3,6 GB de RAM para uma divisão que o modelo faz. Decisão de 11/11: a estrutura vem de chamadas ao modelo (Gemini 2.5 Flash, pelo Agno), com uma config tipada por tipo de documento, e o texto é conferido contra o PDF.

**O que foi feito** (detalhe em [Extração](../../../docs/extraction.md)):
- `extractor/config.py`: a `DocumentConfig` (estratégia, modelo, prompts, seções procuradas pelo nome, notas de rodapé, paralelismo e limites da conferência); `configs.py`: a `ARTICLE_CONFIG`.
- Chamada 1: o mapa das seções, só com títulos em linha própria (três rodadas seguidas deram o mesmo mapa) → dict das seções → gate de abstract e referências.
- Chamada 2, uma por seção, em paralelo, conferida contra o texto do PDF lido pelo pypdf (cobertura e fidelidade) e refeita com uma dica quando reprovada.
- `GEMINI_KEY` no `.env`, lida pelo `metis/config.py`; `METIS_LLM_TIMEOUT_SECONDS`.
- Adiantado da 1.9: o model `Extraction` (cache por sha256 + versão do extractor), `Run.extraction` e o E1 real no `StageTask`.

**Teste:** `extractor/tests/` (sessão falsa, servidor HTTP local no lugar do Google, PDFs gerados no teste, banco real); `pytest -m llm` com o Gemini de verdade; calibração em dois artigos do ICLR 2017 (PeerRead); E2E no compose, com o ICLR 410 chegando a `done` em cerca de 45 s.

**Commit sugerido:** `feat: split articles into sections with Gemini via Agno`

---

## Etapa 1.6 — Docling, junção e Figure

**Em aberto (11/11):** sem o GROBID, a junção por bbox não se aplica, e o Docling é pesado (modelos do torch). Antes de começar, decidir se as figuras vêm do Docling (medindo imagem e memória) ou de uma chamada de visão do modelo sobre as páginas do PDF.

**O que fazer** (plano original)
- `extraction/docling.py`: com as opções de [Extração](../../../docs/extraction.md#ferramentas); figuras com bbox, classe e recorte; tabelas em markdown; fórmulas em LaTeX.
- Junção GROBID ↔ Docling por página + sobreposição de bbox (`to_top_left_origin()` no Docling).
- Model `Figure` (recorte no storage, `image_sha256`).
- Imagem e worker de extração: decidir se os modelos do Docling vão na imagem ou são baixados na primeira execução; conferir as wheels de Docling/torch em Python 3.14 (R15).

**Teste** (`extraction/tests/test_docling.py`)
- Um PDF com gráfico vetorial → figura detectada e recortada inteira.
- A figura 3 do texto liga ao recorte certo e aos parágrafos que a citam.

**Commit sugerido:** `feat: detect and crop figures with Docling`

---

## Etapa 1.7 — Texto oculto

**O que fazer**
- `extraction/hidden_text.py` com pdfplumber: cor ≈ fundo, fonte < ~2 pt, fora da página, sob imagens, e padrões de instrução dirigida a revisores IA.
- Saída: `hidden_text_findings[]` no contrato.

**Teste** (`extraction/tests/test_hidden_text.py`)
- PDF com texto branco plantado → achado com motivo "cor".
- PDF com "ignore previous instructions" em fonte 1 pt → achado com motivo "tamanho" e "padrão de instrução".
- PDF limpo → nenhum achado.

**Commit sugerido:** `feat: scan PDFs for hidden text`

---

## Etapa 1.8 — Descrição das figuras

**O que fazer**
- Agente `figure_describer(kind)`, papel `vision`, `output_schema` `FigureDescription`; um prompt por grupo de classes (gráfico, diagrama, foto, tabela em imagem).
- Executor `DescribeFiguresStep`: `bounded_map` sobre as figuras, cache pelo hash da imagem, e uma figura sem descrição marcada no documento quando a chamada falha.

**Teste** (`extraction/tests/test_describe_figures.py`, `FakeAgentFactory`)
- Cada figura recebe uma descrição; uma falha isolada deixa só aquela sem descrição.
- Todas falhando com `LLMUnavailable` → o erro sobe.
- Mesmo hash de imagem → nenhuma chamada nova.
- Cada chamada gera um `LLMCall`.

**Commit sugerido:** `feat: describe figures with a vision agent`

---

## Etapa 1.9 — Builder, cache, gate e workflow do E1

**O que fazer**
- `ExtractedDocumentBuilder`: junta GROBID, Docling e texto oculto; valida no `build()`.
- Model `ExtractedDocument` (único por sha256 + versões dos parsers) e `Run.extracted_document`.
- `extraction/workflow.py`: o workflow do E1 de [docs/agents.md](../../../docs/agents.md#e1--extração-extractionworkflowpy), com o gate de qualidade antes das figuras (D21).
- O cache é checado em código antes do workflow.
- O stub do E1 no `StageTask` vira o workflow real.

**Teste** (`extraction/tests/test_workflow.py`, eager, fakes)
- PDF real → `extracted`, com o `ExtractedDocument` ligado ao run.
- PDF sem abstract → `rejected_invalid_submission`, sem nenhuma chamada de visão.
- Segundo run da mesma attempt → reaproveita a extração, sem chamar GROBID nem agente.
- Retry do estágio no meio → os passos já persistidos não rodam de novo.

**Como ficou (11/11):** o cache (`Extraction` por sha256 + versão do extractor), o gate de abstract e referências e o E1 real no `StageTask` entraram na 1.5, sem Workflow do Agno. Falta montar o `ExtractedDocument` da 1.1 a partir do `ExtractedArticle` e juntar as figuras (1.6 e 1.8) e o texto oculto (1.7).

**Commit sugerido:** `feat: run real extraction stage as an Agno workflow`

---

## Etapa 1.10 — Medição da ligação citação ↔ referência

**Em aberto (11/11):** sem o GROBID, ninguém liga as chamadas no texto às referências. Antes de medir, decidir como ligar: código sobre o texto das seções (`[3]`, "(Silva, 2020)") ou uma chamada ao modelo. A medição contra os `referenceMentions` do PeerRead continua valendo. As etapas 4.4 e 4.7 da Integridade dependem disso.

**O que fazer**
- Comando `bench_citation_links` em `evals/`: roda o GROBID em PDFs do PeerRead e compara com os `referenceMentions` (precisão e recall da ligação).
- Registrar o primeiro número no planejamento; ele vira a meta.

**Pronto quando:** o número está registrado.

**Commit sugerido:** `feat: measure citation linking against PeerRead`

---

## Pronto do M1 (I2)

- 3–5 PDFs reais divididos com cobertura e fidelidade dentro dos limites (dois do ICLR 2017 já calibrados em 11/11).
- Um gráfico vetorial é detectado e recortado inteiro; um texto oculto plantado é detectado.
- A ligação citação ↔ referência foi medida (depende da decisão da 1.10).
- Cada chamada de visão aparece em `LLMCall`, com custo.
- A verificação manual de [12](12_testes_e_verificacao.md#i2--extração-real) passa.
