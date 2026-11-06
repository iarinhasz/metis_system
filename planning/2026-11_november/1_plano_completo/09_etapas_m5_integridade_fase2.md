# M5 — Integridade, Fase 2

**Objetivo:** verificar as citações (existência, retratação, consistência, alinhamento) e cruzar com a Fase 1.
**Trilhas:** I e P
**Referência:** [Checagem de integridade](../../../docs/integrity_check.md#fase-2--citações), [Agentes e workflows](../../../docs/agents.md#e3--integridade-integrityworkflowpy)

Caminhos relativos a `projects/correction/`.

---

## Etapa 5.1 — Existência das referências

**O que fazer**
- `integrity/existence.py`: a partir da resolução da 4.2, resultado por referência `ok | metadata_mismatch | not_found`; 404 de DOI no Crossref é alerta.
- Agente `reference_adjudicator()` só nos casos duvidosos; heurísticas de `halref` e `RefChecker` (MIT).

**Teste** (`integrity/tests/test_existence.py`, cassetes, fakes)
- Referência inventada com DOI de aparência real → `not_found`.
- Livro sem DOI encontrado por título → `ok`.
- Só os duvidosos chamam o agente.

**Commit sugerido:** `feat: verify that references exist`

---

## Etapa 5.2 — Retratação

**O que fazer**
- Crossref (`update-to`/`updated-by`, fonte Retraction Watch) + `is_retracted` do OpenAlex.

**Teste** (`integrity/tests/test_retraction.py`, cassetes): obra retratada vira achado; obra corrigida, mas não retratada, não.

**Commit sugerido:** `feat: flag retracted references`

---

## Etapa 5.3 — Consistência

**O que fazer**
- Referência nunca citada no texto, citação sem entrada na lista, taxa de autocitação.

**Teste** (`integrity/tests/test_consistency.py`, fixtures): cada caso numa fixture alterada.

**Commit sugerido:** `feat: check citation consistency`

---

## Etapa 5.4 — Alinhamento citação ↔ afirmação

**O que fazer**
- Amostra de K frases que citam; compara com o abstract da obra e só busca o full text em `INSUFFICIENT`.
- Agente `citation_alignment_judge()` (frases em PT contra fontes em EN incluídas), com os rótulos `SUPPORTS | PARTIAL | CONTRADICTS | UNRELATED | INSUFFICIENT`.

**Teste** (`integrity/tests/test_alignment.py`, fakes): só K frases vão ao agente; `INSUFFICIENT` dispara a busca do full text uma vez.

**Commit sugerido:** `feat: check citation alignment with claims`

---

## Etapa 5.5 — Cruzamento, regras v2 e Parallel das fases

**O que fazer**
- `integrity/cross_phases.py`: fonte similar fora das referências → citação faltante; similar, citada e entre aspas → desce de severidade; similar a trabalho retratado → registrado à parte.
- Regras de risco v2, com os achados da Fase 2.
- No workflow do E3, o ramo da Fase 2 entra no `Parallel` com a Fase 1.

**Teste**
- `test_cross_phases.py`: cada leitura da tabela de cruzamento.
- `test_workflow.py`: as duas fases rodam; uma falha passageira numa fase leva ao retry do estágio, e a fase que já gravou não roda de novo.

**Commit sugerido:** `feat: cross integrity phases and apply risk rules v2`

---

## Etapa 5.6 — Benchmarks da Fase 2

**O que fazer**
- Referências inventadas plantadas: recall e taxa de falso positivo.
- Linha de base em SciCiteVal e Citation Integrity para o alinhamento.

**Pronto quando:** os números estão registrados.

**Commit sugerido:** `feat: benchmark citation checks`

---

## Pronto do M5 (I5)

- Referências inventadas plantadas são detectadas, e a taxa de falso positivo foi medida.
- Há uma linha de base em SciCiteVal e Citation Integrity.
- A verificação manual de [12](12_testes_e_verificacao.md#i5--pipeline-completo) passa.
