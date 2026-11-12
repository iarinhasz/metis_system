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

## Etapa 1.6 — Figuras e tabelas pelo modelo (incorpora a 1.8)

**Decidido (12/11, Q16):** o próprio Gemini, como na 1.5, sem Docling (pesado: torch e modelos). O recorte da imagem fica para quando o admin ou o relatório precisarem mostrar a figura. Vem **depois da 1.10**.

**O que fazer**
- **Lista** (uma chamada, `prompts/scan_figures.md`): figuras e tabelas com o rótulo ("Figure 3", "Tabela 2"), o tipo (`figure` ou `table`), a página e a legenda literal. A legenda é conferida contra o texto do PDF (fidelidade, como nas seções); abaixo do limite, a chamada é refeita com uma dica.
- **Onde cada uma é citada** (código): as frases das seções que mencionam o rótulo nas várias grafias ("Fig. 3", "Figura 3", "Table 2"), com a seção e os offsets.
- **Descrição** (uma chamada por figura ou tabela, em paralelo, `prompts/describe_figure.md`): o PDF, o rótulo, a página, a legenda e as frases que a citam. A resposta (`FigureDescription`) traz a classe (gráfico de linhas, de barras, diagrama, foto…), a descrição, os dados legíveis, se a figura sustenta o que o texto afirma sobre ela (com o motivo) e os problemas (eixo sem unidade, legenda que não bate com o desenho). Para tabela, também o markdown.
- **Falhas:** uma figura que falha fica sem descrição, marcada, e o estágio segue; todas falhando com `ModelUnavailable` → retry do estágio.
- **No resultado:** `ExtractedArticle.figures[]` (id, rótulo, tipo, página, legenda, frases que citam, descrição ou nula), com valor padrão vazio para as extrações antigas continuarem válidas.
- **`DocumentConfig`:** `figures_prompt`, `describe_figure_prompt` e `describe_figures`.
- **Fora daqui:** o recorte (pypdfium2 + a caixa devolvida pelo Gemini + Pillow, leve, quando precisar), fórmulas em LaTeX (ficam no texto como o modelo copiou) e o custo em `LLMCall` (1.4).

**Teste**
- `extractor/tests/test_figures.py` (sessão falsa): lista conferida; legenda inventada refeita; frases que citam achadas pelo rótulo nas várias grafias; falha isolada não derruba o estágio; todas falhando sobem.
- `pytest -m llm`: o ICLR 633 (30 figuras, gráficos vetoriais).
- Conferência manual: as figuras de 2 artigos comparadas com o PDF.

**Pronto quando:** num artigo com gráfico vetorial, todas as figuras e tabelas são listadas com a legenda certa e descritas, e uma falha isolada deixa só aquela sem descrição.

**Commit sugerido:** `feat: describe figures and tables with Gemini`

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

**Incorporada à 1.6 (12/11).** A descrição vem na mesma etapa que a lista das figuras, pelo Gemini, sem esperar a 1.3 e a 1.4.

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

## Etapa 1.10 — Referências em campos e ligação das citações

**Decidido (12/11, Q17):** híbrido. O modelo separa a lista de referências em campos; o código acha as chamadas no texto das seções e liga cada uma à sua referência. Vem **antes da 1.6**: destrava a 4.2, a 4.4, a 4.7 e a 5.x da Integridade.

**O que fazer**
- **Referências em campos** (uma chamada a mais por artigo, só com texto, `prompts/parse_references.md`): o texto da seção de referências, já extraído na 1.5, vai ao modelo. A resposta (`ParsedReferences`) traz, para cada entrada, o texto cru (`raw`), a marca da lista quando houver (`[3]`, `3.`), autores, título, ano (com o sufixo, `2020a`), venue, DOI e arXiv.
  - Conferência como na 1.5: cada `raw` precisa estar no texto da seção (fidelidade), e a cobertura da seção pelas entradas mostra se faltou referência; abaixo do limite, a chamada é refeita com uma dica.
  - Ids `ref_1`, `ref_2`… na ordem da lista.
- **Chamadas no texto** (código, `citations.py`), sobre o texto de cada seção, menos a de referências:
  - estilo numérico: `[3]`, `[1, 4]`, `[2–5]` (o intervalo é expandido);
  - estilo autor-ano: "Silva (2020)", "(Silva, 2020; Souza et al., 2019a)", "Silva e Souza (2020)", "Silva et al. (2020)";
  - o estilo do artigo sai da própria lista (numerada ou não) e das chamadas que aparecem.
- **Ligação** (código): no numérico, pela marca ou pela posição na lista; no autor-ano, pelo sobrenome do primeiro autor (sem acento e sem caixa) e pelo ano com o sufixo. Sem candidato ou com mais de um, `reference_id` fica nulo, o que a 5.3 usa (citação sem entrada na lista).
- **No resultado:** `ExtractedArticle.references[]` (id, `raw` e campos) e `citations[]` (id da referência ou nulo, marca, frase, seção e offsets no texto da seção), com valor padrão vazio para as extrações antigas continuarem válidas. O prompt novo muda a versão do extractor e força uma extração nova para os próximos PDFs. O evento do E1 passa a trazer o número de referências e de citações sem ligação.
- **`DocumentConfig`:** `references_prompt`. A seção lida é a obrigatória `references`.
- **Medição** (comando `bench_citation_links` no app `extractor`; em dry-run lista o que rodaria e só chama o modelo com `--execute`): roda o E1 em 10–20 PDFs do PeerRead que têm `parsed_pdfs` (ICLR, ACL, CoNLL) e compara com os `referenceMentions` do science-parse. Para cada chamada do gabarito, a nossa aponta para a mesma referência (casadas pelo título)? Saem a precisão e o recall da ligação; o primeiro número vai para o planejamento e vira a meta. O gabarito também erra, então os desacordos são conferidos à mão numa amostra.

**Teste**
- `extractor/tests/test_citations.py`: cada forma de chamada (numérica com lista e intervalo; autor-ano com "et al.", dois autores, sufixo de ano e acento); estilo misturado; chamada sem referência; ambiguidade → nulo; offsets batem com a frase.
- `extractor/tests/test_references.py` (sessão falsa): entradas conferidas contra o texto; entrada inventada refeita ou descartada; ids na ordem.
- `pytest -m llm`: um artigo inventado com as duas formas de chamada.

**Pronto quando:** a ligação foi medida no PeerRead e o número está registrado, e a Integridade consegue ler `references[]` e `citations[]` de uma `Extraction`.

**Commit sugerido:** `feat: parse references and link citations`

---

## Pronto do M1 (I2)

- 3–5 PDFs reais divididos com cobertura e fidelidade dentro dos limites (dois do ICLR 2017 já calibrados em 11/11).
- Num artigo com gráfico vetorial, todas as figuras e tabelas são listadas e descritas (o recorte ficou para depois, 1.6); um texto oculto plantado é detectado (1.7).
- A ligação citação ↔ referência foi medida no PeerRead (1.10).
- Cada chamada de visão aparece em `LLMCall`, com custo.
- A verificação manual de [12](12_testes_e_verificacao.md#i2--extração-real) passa.
