# M4 — Integridade, Fase 1

**Objetivo:** a similaridade em funil, as regras de risco e o gate humano com evidências.
**Trilha:** I (4.1, 4.3 e 4.5 começam na fase 1, logo depois do M0)
**Referência:** [Checagem de integridade](../../../docs/integrity_check.md), [Agentes e workflows](../../../docs/agents.md#e3--integridade-integrityworkflowpy)

Caminhos relativos a `projects/correction/`.

---

## Etapa 4.1 — Clientes do scholarly

**O que fazer**
- Pacote `scholarly/`: clientes de Crossref, OpenAlex, Semantic Scholar, arXiv e Unpaywall, com os limites de [Checagem de integridade](../../../docs/integrity_check.md#apis-externas).
- Rate limit por provedor com token bucket no Redis; cache por DOI; timeouts; erro passageiro (`TransientStageError`).
- Chaves e e-mails no `MetisSettings` (`crossref_mailto`, `openalex_api_key`, `semantic_scholar_api_key`, `unpaywall_email`).
- Testes com respostas HTTP reais gravadas (cassetes).

**Teste** (`scholarly/tests/`)
- Cada cliente parseia a resposta gravada; 429 → espera e tenta de novo; 5xx esgotado → `TransientStageError`.
- O token bucket não passa do limite com chamadas concorrentes.
- A mesma consulta por DOI não vai à rede duas vezes.

**Commit sugerido:** `feat: add scholarly API clients with rate limiting and cache`

---

## Etapa 4.2 — Resolução de referências

**O que fazer**
- `integrity/references.py`: cascata Crossref → OpenAlex por DOI → S2 `search/match`, a partir dos `references[]` do contrato.
- Critério de aceite: título com similaridade ≥ ~0,9, mesmo sobrenome do primeiro autor, diferença de ano ≤ 1.
- Resultado por referência (DOI, ids, abstract, link de acesso aberto), usado pelas duas fases.

**Teste** (`integrity/tests/test_references.py`, cassetes, fixtures)
- Referência com DOI resolve no Crossref; sem DOI, pela string crua; título parecido com ano distante não aceita.

**Commit sugerido:** `feat: resolve references through a scholarly cascade`

---

## Etapa 4.3 — Corpus e embeddings

**O que fazer**
- Extensão `pgvector` por migration; models `SourceDocument` e `SourceChunk` (`VectorField(1024)` + `HnswIndex` por cosseno).
- `integrity/embeddings.py`: BGE-M3 local no `worker-integrity` (o manuscrito não sai da infraestrutura); carga do modelo uma vez por processo.
- Comando `load_peerread` (dry-run por padrão): semeia o corpus com os artigos do PeerRead, em chunks com embeddings.
- Cada attempt processada entra no corpus interno.

**Teste** (`integrity/tests/test_corpus.py`)
- `load_peerread --execute` em 5 artigos cria documentos e chunks; rodar de novo não duplica.
- A busca por vizinhos devolve o chunk do mesmo texto em primeiro.

**Commit sugerido:** `feat: add similarity corpus with pgvector and BGE-M3`

---

## Etapa 4.4 — Fontes de candidatos

**O que fazer**
- Strategy `CandidateSource`: corpus interno, obras citadas (abstract + full text em acesso aberto, com o texto lido como no E1), S2 `/paper/search`, arXiv, OpenAlex (busca paga).
- Orçamento por run para as buscas pagas; o que ficar de fora vai para o `coverage`.

**Teste** (`integrity/tests/test_candidates.py`): orçamento estourado para a busca e registra; cada fonte devolve candidatos no mesmo formato.

**Commit sugerido:** `feat: collect similarity candidates within a budget`

---

## Etapa 4.5 — Léxico: MinHash e winnowing

**O que fazer**
- `integrity/lexical.py`: MinHash-LSH (`datasketch`) sobre shingles de palavras para os parágrafos candidatos; winnowing com hash estável (blake2b) para os trechos idênticos, com offsets.

**Teste** (`integrity/tests/test_lexical.py`)
- Trecho comum com pelo menos `w + k − 1` palavras é sempre achado, com offsets certos.
- Textos sem trecho comum não geram par.

**Commit sugerido:** `feat: detect lexical overlap with MinHash and winnowing`

---

## Etapa 4.6 — Semântico e PT↔EN

**O que fazer**
- `integrity/semantic.py`: k vizinhos por chunk no HNSW; alinhamento de frases nos dois sentidos para cópia traduzida (sequência de frases alinhadas na mesma ordem).
- Limiares configuráveis, calibrados com abstracts bilíngues do SciELO.

**Teste** (`integrity/tests/test_semantic.py`): um par PT/EN traduzido é detectado; dois textos do mesmo tema, mas diferentes, não passam do limiar.

**Commit sugerido:** `feat: detect paraphrase and translated copy with embeddings`

---

## Etapa 4.7 — Filtro por citação e adjudicador

**O que fazer**
- `integrity/citation_filter.py`: a fonte está citada no trecho (`citations[]` da extração, 1.10)? Entre aspas? Boilerplate? Mesmo trabalho (título e autores)?
- Agente `plagiarism_adjudicator()` nos top-N pares, via `bounded_map`, com o veredito de [Checagem de integridade](../../../docs/integrity_check.md#fase-1--similaridade-em-funil).

**Teste** (`integrity/tests/test_adjudication.py`, fakes)
- Trecho citado e entre aspas → `properly_cited` sem chamar o agente.
- Só os top-N vão ao agente.

**Commit sugerido:** `feat: filter cited passages and adjudicate similarity pairs`

---

## Etapa 4.8 — Regras, relatório e workflow do E3

**O que fazer**
- `integrity/rules.py`: regras de risco v1, com N, X e K configuráveis; `rules_version`.
- Models `IntegrityReport` e `IntegrityFinding`; `coverage` preenchido.
- Agente `integrity_narrator()`, que recebe o nível já decidido.
- `integrity/workflow.py`: o workflow do E3 com a Fase 0 e o ramo da Fase 1; o *pass-through* vira real. Risco alto → `StageOutcome(halt=True)`.

**Teste**
- `test_rules.py`: um caso por regra e por nível; limiares vêm da config.
- `test_workflow.py` (eager, fakes): fixture limpa → `integrity_checked`; fixture com trecho copiado de fonte não citada → `waiting_human_review`; instrução oculta → risco alto.

**Commit sugerido:** `feat: run integrity phase 1 with explicit risk rules`

---

## Etapa 4.9 — Gate no admin e endpoint

**O que fazer**
- Admin do run em `waiting_human_review`: achados com o trecho do artigo e o da fonte lado a lado, nota da decisão, ações "Continuar" e "Encerrar" (da 0.5).
- Grupo "revisores" com permissão só para o gate (Q8).
- `GET /api/runs/{id}/integrity`.

**Teste**
- Usuário fora do grupo não vê as ações; decisão vira `RunEvent` com a nota.
- `GET /integrity` antes do E3 → 409.

**Commit sugerido:** `feat: show integrity evidence in the review gate`

---

## Etapa 4.10 — Benchmark de plágio e calibração

**O que fazer**
- Comando `bench_plagiarism`: plágio sintético a partir do PeerRead (trechos literais, parafraseados por LLM, traduzidos para PT) → precisão e recall por tipo.
- Calibrar N, X, K e os limiares semânticos; registrar os números e a meta (Q11).

**Pronto quando:** precisão e recall registrados, e metas definidas.

**Commit sugerido:** `feat: benchmark plagiarism detection on synthetic data`

---

## Pronto do M4 (I4)

- Precisão e recall foram medidos no plágio sintético e atingem a meta (Q11).
- No E2E, um PDF com trecho copiado vai a `waiting_human_review`, e "continuar" leva a `done`.
- A verificação manual de [12](12_testes_e_verificacao.md#i4--integridade-fase-1) passa.
