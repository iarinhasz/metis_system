# M1 — Extração e base do Agno

**Objetivo:** o `ExtractedDocument` real e a base do Agno (`agents/`, `LLMCall`) que todos os estágios seguintes usam.
**Trilhas:** A (1.1–1.4), P (1.5–1.10)
**Referência:** [Extração](../../../docs/extraction.md), [Agentes e workflows](../../../docs/agents.md)
**Fora daqui:** OCR de PDF escaneado (fica `rejected_invalid_submission`), Questions (M2)

Caminhos relativos a `projects/correction/`.

---

## Etapa 1.1 — Contrato do ExtractedDocument e fixtures do PeerRead

**Situação:** implementada em 16/11/2026. O contrato `ExtractedDocument` e o `render_for_llm()` são da trilha de Avaliação; a Plataforma gerou as 12 fixtures reais (ACL 2017) em `extractor/tests/fixtures/peerread/`, com a atribuição (CC BY 4.0), e o `test_peerread_fixture_files.py` carrega e renderiza cada uma.

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

**Implementação (15/11/2026, branch `avaliacao/1.1-1.11-extracted-document`):**
`extractor/contract.py` define modelos Pydantic congelados para o documento,
seções hierárquicas, referências, citações e figuras/tabelas; offsets e páginas
são opcionais quando a fonte não os fornece. `render_for_llm()` preserva a
hierarquia, inclui os elementos visuais nas posições conhecidas e devolve blocos
limitados por tamanho. `peerread_to_document()` converte `parsed_pdfs` sem LLM,
e `make_peerread_fixtures` é dry-run por padrão, gravando só com `--execute`.

**Ainda pendente para o pronto:** o checkout não contém os JSONs do PeerRead em
`dataset_project/raw`, então não foi possível gerar e validar 10–20 fixtures reais.
O contrato, a conversão sintética e o dry-run/execução do comando têm testes.

---

## Etapa 1.2 — Spike do Agno 3 em Python 3.14

**Situação (12/11/2026):** dependências e testes de contrato implementados. Python 3.14.5 e Agno 3.1.12 conferidos localmente com as SDKs OpenAI e Google. O [resultado do spike](../../../docs/agents.md#resultado-do-spike-12) registra as políticas de erro de `Step`/`Condition`, falhas de `Parallel`, schemas, métricas, retries e telemetria. A validação com respostas reais e chaves válidas permanece pendente; a equipe optou por seguir com os testes locais. Não marcar a etapa como totalmente concluída antes dessa validação.

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

**Situação (12/11/2026):** implementada. O catálogo tem padrões de desenvolvimento substituíveis por papel no ambiente, conforme decisão da equipe. Entraram `ModelSpec`, fábricas, runner com medição, prompts e exemplos gerados dos schemas, limiter compartilhado, fakes e a fronteira de imports. A sessão do E1 usa a fábrica preservando a `DocumentConfig` e zero retries; seus pools de seções e figuras usam `bounded_map`. Os contratos definitivos de M2–M5 continuam em suas etapas; o catálogo usa `PendingOutput` onde ainda não há schema real.

**Verificação:** **412 testes passaram**, com 5 casos `llm` excluídos, em Linux com Python 3.14.10 e PostgreSQL 18. Passaram também lock/sync com `--locked`, Ruff (137 arquivos), mypy (135 arquivos) e `manage.py check`. Os testes de concorrência verificam conexões reais fechadas inclusive quando uma tarefa falha. Detalhe e configuração em [docs/agents.md](../../../docs/agents.md#implementação-da-etapa-13). A validação com chaves válidas da 1.2 continua pendente; `LLMCall`, preços de produção e persistência de uso ficam na 1.4.

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

**Situação (12/11/2026):** implementada. `LLMCall` e a migração `attempts.0003_llmcall` registram uso por run e estágio; o admin é somente leitura. `pipeline.usage.DatabaseUsageSink` grava pelo Management de `queries/attempts/llm_call.py`. O E1 recebe o sink e o run real na sessão; respostas retomadas e extrações reaproveitadas não geram novas linhas. A tabela Standard cobre os modelos de desenvolvimento e o E1, com cache, raciocínio faturável, faixa de contexto longo e a mudança de preço do Gemini 3.8 em janeiro. Modelo sem tarifa mantém custo nulo e aviso no log. Fontes e limites em [docs/agents.md](../../../docs/agents.md#implementação-da-etapa-14).

**Verificação:** **437 testes passaram**, com 5 casos `llm` excluídos, em Linux com Python 3.14.10 e PostgreSQL 18. Passaram Ruff (143 arquivos), mypy (141 arquivos), `manage.py check`, aplicação da migração e `makemigrations --check --dry-run`. Sem mudanças de dependências. A validação com chaves válidas da 1.2 continua pendente; as agregações de custo por run e período permanecem na 6.2.

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

## Etapa 1.6 — Lista de figuras e tabelas

**Decidido (12/11, Q16):** o próprio Gemini, como na 1.5, sem Docling (pesado: torch e modelos). O recorte da imagem fica para quando o admin ou o relatório precisarem mostrar a figura. A descrição de cada figura é a 1.8, num commit à parte, na mesma branch.

**Situação:** implementada em 12/11/2026.

**Como ficou** (detalhe em [Extração](../../../docs/extraction.md)):
- **Lista** (`extractor/figures.py`, `prompts/scan_figures.md`): uma chamada com o PDF devolve rótulo, tipo (`figure` ou `table`), página e legenda literal de cada figura e tabela, sem algoritmos, quadros de código e equações. A legenda é conferida contra o texto do PDF (fidelidade); as linhas que começam como legenda no texto do PDF ("Figure 3:", "Table 2.") dizem se faltou alguma, e a falta volta como dica numa nova tentativa. Ids `fig_1`, `fig_2`… pela ordem das páginas.
- **Chamadas no texto** (`figure_mentions.py`, só código): "Fig. 3", "Figure 3a", "Figura 2", "Figures 2 and 3", "Figs. 2–4", "Table 1", "Tabela A.1", ligadas pelo tipo e pelo número do rótulo.
- **No resultado:** `ExtractedArticle.figures[]` e `figure_mentions[]`, com valor padrão vazio; o evento do E1 conta as figuras.
- **`DocumentConfig`:** `figures_prompt`.

**Teste:** `test_figures.py` (sessão falsa: lista conferida, legenda inventada e figura faltando refeitas, sem texto do PDF, ordem por página) e `test_figure_mentions.py` (cada forma de chamada, intervalos, rótulo fora da lista). Com o Gemini: no ICLR 410, 12 tabelas e 1 figura com as legendas idênticas às do PDF e as 17 chamadas ligadas; no ICLR 304, 2 figuras e 4 tabelas.

**Commit sugerido:** `feat: list figures and tables with their captions and mentions`

---

## Etapa 1.7 — Texto oculto

**Decidido (15/11):** feita pela Plataforma, para fechar a trilha (a Integridade ainda não tem código), com o pdfminer.six no lugar do pdfplumber: é o motor de leitura do pdfplumber, só Python, sem o Pillow e o pypdfium2. O resultado fica no `ExtractedArticle` (`hidden_text`); e no `ExtractedDocument` (`hidden_text_findings`, 1.11).

**Situação:** implementada em 15/11/2026.

**Como ficou** (detalhe em [Extração](../../../docs/extraction.md#passo-a-passo), passo 12):
- `extractor/hidden_text.py`: marca o trecho em branco (cinza, RGB ou CMYK), em fonte abaixo de 2 pt ou fora da página; trechos seguidos viram um; `instruction` quando parece instrução a um revisor de IA, em inglês ou português. Um trecho precisa de uma palavra com 3 letras ou mais.
- `ExtractedArticle.hidden_text[]` (`page`, `text`, `reasons`) e `hidden_text_checked`; `DocumentConfig.scan_hidden_text`; o evento do E1 conta `hidden_passages` e `hidden_instructions`.
- Fica de fora: texto atrás de imagem e o modo de renderização invisível (usado pelo OCR dos PDFs escaneados).

**Teste:** `test_hidden_text.py` (branco em cinza, RGB e CMYK; 1 pt; fora da página; instrução em inglês e em português; linhas seguidas; cinza legível, glifo solto e letras espaçadas de figura não contam; PDF ilegível → não verificado) e `test_service.py` (o artigo traz o achado; a busca desliga pela config). Nos 12 PDFs reais da calibração, nenhum achado; com instruções plantadas no ICLR 410, o achado sai com `color`, `size` e `instruction`.

**O que fazer**
- `extraction/hidden_text.py` com pdfplumber: cor ≈ fundo, fonte < ~2 pt, fora da página, sob imagens, e padrões de instrução dirigida a revisores IA.
- Saída: `hidden_text_findings[]` no contrato.

**Teste** (`extraction/tests/test_hidden_text.py`)
- PDF com texto branco plantado → achado com motivo "cor".
- PDF com "ignore previous instructions" em fonte 1 pt → achado com motivo "tamanho" e "padrão de instrução".
- PDF limpo → nenhum achado.

**Commit sugerido:** `feat: scan PDFs for hidden text`

---

## Etapa 1.8 — Descrição das figuras e tabelas

**Decidido (12/11):** pelo Gemini, sem esperar a 1.3 e a 1.4 (a mesma exceção da 1.5: o Agno direto no `extractor/`). Vem depois da 1.6, na mesma branch.

**Situação:** implementada em 12/11/2026.

**Como ficou** (detalhe em [Extração](../../../docs/extraction.md)):
- **Uma chamada por figura ou tabela, em paralelo** (`extractor/figure_descriptions.py`, `prompts/describe_figure.md`): o PDF, o rótulo, a página, a legenda e até 5 frases que a citam (da 1.6). A resposta traz a classe (gráfico de linhas, diagrama, tabela…), a descrição, os dados legíveis, se a figura sustenta o que o texto afirma sobre ela (com o motivo), os problemas (eixo sem unidade, legenda que não bate com o desenho) e, para tabela, o markdown.
- **Conferências, com nova tentativa e dica:** o modelo devolve o começo da legenda da figura que descreveu, e o código confere se é a pedida (no ICLR 304 a "Figure 1" saiu uma vez com o conteúdo da "Table 1"); tabela só com o cabeçalho é refeita (no ICLR 410, a Table 5).
- **Falhas:** figura que falha ou continua trocada fica sem descrição e o estágio segue; todas falhando com `ModelUnavailable` → retry do estágio. Tabela que continua sem as linhas fica com a descrição e sem o markdown.
- **No resultado:** `Figure.description` (`FigureDescription`, ou nula); o evento do E1 conta as descritas (`figures_described`).
- **`DocumentConfig`:** `describe_figure_prompt` (marcadores conferidos) e `describe_figures`.

**Teste:** `test_figure_descriptions.py` (sessão falsa: cada figura descrita com a legenda e as frases que a citam; falha isolada deixa só aquela sem descrição; todas falhando sobem; resposta inválida refeita; figura trocada refeita e, se continuar, sem descrição; legenda devolvida sem o rótulo aceita; tabela sem as linhas refeita e, se continuar, sem o markdown; `describe_figures=False` não chama). Com o Gemini: as 19 figuras e tabelas do ICLR 304 e do 410 descritas, cerca de 80 s por artigo, e todos os números das 16 tabelas presentes no texto do PDF. Ficou de fora: a tabela cortada no meio (a Table 11 do 410 veio com 67 números numa rodada e 181 na outra) e um julgamento brando (todas "sustentam", nenhum problema apontado).

**Commit sugerido:** `feat: describe figures and tables with Gemini`

---

## Etapa 1.9 — Retomada dos passos do E1

**Decidido (12/11):** o que o plano antigo pedia aqui já entrou na 1.5 (o cache por sha256 + versão do extractor, o gate de abstract e referências antes das chamadas caras, que cumpre a D21, e o E1 real no `StageTask`), e o Workflow do Agno foi descartado no E1. Sobra a retomada. O builder do `ExtractedDocument` e o texto oculto passam para a 1.11.

**Situação:** implementada em 12/11/2026.

**Como ficou** (detalhe em [Extração](../../../docs/extraction.md#retomada)):
- **O problema:** um retry do estágio refazia todas as chamadas (umas 37 no ICLR 410 e 48 no 304), cada uma com o PDF.
- **`ResumableSession`** (`extractor/resumable_session.py`): envolve a sessão do Agno, com a mesma interface. Cada resposta válida é guardada no banco assim que chega; no retry, as guardadas voltam sem chamar o modelo. O retry segue o mesmo caminho, porque cada prompt depende só das respostas anteriores. Chave: hash do prompt, do schema pedido e de `with_document`.
- **No banco** (decidido em 12/11, no lugar do storage): model `ExtractionStep` (`sha256`, `version`, `key`, `answer`), único pelos três primeiros, com o acesso em `queries/extractor/extraction_step.py`. As respostas guardadas são lidas uma vez, na thread principal; cada thread das chamadas em paralelo grava a sua e fecha a própria conexão.
- **Ciclo de vida:** os passos são apagados quando a `Extraction` é guardada e quando o estágio falha com `InvalidModelAnswer` (senão o retry repetiria a mesma falha). Os de um run que terminou em `error_llm` ficam, e reprocessar no gate retoma deles; a limpeza das sobras entra na retenção da 6.4.
- **Descrição das figuras** (decidido em 12/11): o modelo fora do ar numa figura agora sobe para o retry do estágio, como nos outros passos, em vez de deixar a figura sem descrição para sempre na `Extraction`. As descrições que já tinham dado certo voltam guardadas.

**Teste:** `test_resumable_session.py` (a resposta guardada volta sem chamar o modelo; tuplas e nulos voltam iguais; outro PDF ou outra versão chamam o modelo; prompt, schema e `with_document` dão chaves diferentes; `forget` só apaga aquele PDF e versão) e `test_attempt_extraction.py` (retry do estágio no meio → o mapa e as seções não são pedidos de novo, e os passos somem depois da extração guardada; `InvalidModelAnswer` apaga os passos).

**Commit sugerido:** `feat: resume extraction steps after a stage retry`

---

## Etapa 1.10 — Referências em campos e ligação das citações

**Decidido (12/11, Q17):** híbrido. O modelo separa a lista de referências em campos; o código acha as chamadas no texto das seções e liga cada uma à sua referência. Vem **antes da 1.6**: destrava a 4.2, a 4.4, a 4.7 e a 5.x da Integridade.

**Situação:** implementada em 12/11/2026. **Meta inicial, medida no PeerRead:** recall de 93% e precisão de 92% na ligação citação ↔ referência, sobre as chamadas válidas do gabarito (10 artigos; contra o gabarito bruto, 80% e 71%). Detalhe da medição e da conferência manual em [Extração](../../../docs/extraction.md#como-testar).

**Como ficou:** `extractor/references.py` (lista em campos, conferida e refeita com dica), `citations.py` (numérico e autor-ano, com desempate pelo segundo autor e pelo "et al."), `ExtractedArticle.references[]` e `citations[]`, o evento do E1 com as contagens, e o comando `bench_citation_links` (`citation_bench.py`), com `--papers` e `--rescore`. Uma resposta inválida numa seção passou a contar como tentativa falha dela, sem derrubar a extração (um dos 10 artigos tinha falhado por isso).

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

## Etapa 1.11 — `ExtractedDocument` a partir da extração

**Situação:** implementada em 16/11/2026. O adaptador `ExtractedArticle` → `ExtractedDocument` é da trilha de Avaliação; a Plataforma acrescentou ao contrato `hidden_text_findings[]` e `hidden_text_checked`, preenchidos a partir da 1.7. O texto oculto fica fora do `render_for_llm()`: vai para a integridade, nunca para os avaliadores (teste em `test_document_adapter.py`).

**Decidido (12/11):** sai da 1.9 e fica na trilha Plataforma e Extração. Espera o contrato da 1.1 (Avaliação) e o texto oculto da 1.7 (Integridade).

**O que fazer**
- Montar o `ExtractedDocument` da 1.1 a partir do `ExtractedArticle` guardado na `Extraction` (seções, referências, citações, figuras e descrições).
- Juntar os achados de texto oculto da 1.7.
- O E1 passa a entregar o `ExtractedDocument` aos estágios seguintes.

**Teste:** um `ExtractedArticle` de fixture vira um `ExtractedDocument` válido; com um achado de texto oculto, ele aparece no documento.

**Implementação (15/11/2026, branch `avaliacao/1.1-1.11-extracted-document`):**
`extractor/document_adapter.py` converte, sob demanda, o `ExtractedArticle` salvo
em `Extraction.content` para `ExtractedDocument`. E2 e E4 leem a propriedade
`Extraction.document`; a serialização persistida e o cache de E1 não mudam. A
conversão preserva seções de conteúdo, referências, citações e descrições de
figuras, colocando cada figura na primeira menção conhecida. Testes verificam
compatibilidade com campos opcionais ausentes e que a conversão não altera a
extração original.

**Pendente para concluir a 1.11:** integrar achados de texto oculto. A etapa 1.7
está sendo feita por outra pessoa e ainda não há no repositório um modelo/campo
de achado acordado para receber essa informação. Também falta exercitar o
adaptador com o fluxo de avaliação ponta a ponta e o banco de testes. Como
verificação de compatibilidade, 10 amostras serializadas reais de E1 foram
adaptadas e renderizadas localmente, sem alterar os arquivos de origem. Não foi
criado um schema provisório para evitar incompatibilidade entre as etapas.

**Commit sugerido:** `feat: build the ExtractedDocument from the extraction`

---

## Pronto do M1 (I2)

- 3–5 PDFs reais divididos com cobertura e fidelidade dentro dos limites (dois do ICLR 2017 já calibrados em 11/11).
- Num artigo com gráfico vetorial, todas as figuras e tabelas são listadas e descritas (o recorte ficou para depois, 1.6); um texto oculto plantado é detectado (1.7).
- A ligação citação ↔ referência foi medida no PeerRead (1.10): recall de 93% e precisão de 92% (12/11).
- Cada chamada de visão aparece em `LLMCall`, com custo.
- A verificação manual de [12](12_testes_e_verificacao.md#i2--extração-real) passa.
