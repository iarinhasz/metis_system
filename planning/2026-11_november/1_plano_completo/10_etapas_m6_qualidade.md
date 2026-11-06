# M6 — Qualidade

**Objetivo:** medir, calibrar e endurecer.
**Trilhas:** todas
**Referência:** [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#outras-avaliações), [Testes e verificação](12_testes_e_verificacao.md)

Caminhos relativos a `projects/correction/`.

---

## Etapa 6.1 — Evals offline

**O que fazer**
- Pacote `evals/` com os comandos:
  - `bench_reviews`: correlação (Spearman, QWK) com as notas por aspecto do PeerRead e acerto de accept/reject;
  - `bench_judge`: erros plantados nas saídas dos avaliadores (quote falso, `missing` de algo que está em outra seção, nota contradizendo as observações) → recall do juiz e taxa de rejeição indevida;
  - `bench_plagiarism` (da 4.10) e os benchmarks da 5.6, no mesmo formato.
- Relatório por versão de prompt e por `ModelSpec`, gravado em `evals/results/`.
- Fora do CI.

**Pronto quando:** cada comando roda e grava um relatório comparável com o anterior.

**Commit sugerido:** `feat: add offline evaluation commands`

---

## Etapa 6.2 — Custo no admin

**O que fazer**
- Agregações de `LLMCall` no admin: por run, por estágio, por papel, por modelo e por período.
- Alerta para run acima do orçamento.

**Teste** (`attempts/tests/test_cost_admin.py`): a soma por run bate com as chamadas.

**Commit sugerido:** `feat: show LLM cost aggregates in the admin`

---

## Etapa 6.3 — Endurecimento

**O que fazer**
- Limites de upload e de páginas (Q9, com o número medido no M1); timeouts dos parsers.
- Teste de carga leve: N submissões simultâneas com fakes, conferindo filas, workers e o reconciliador.
- Revisão de segurança: arquivos fora de URL pública, logs sem texto do manuscrito, `/docs` desligado sem DEBUG.

**Commit sugerido:** `chore: harden upload limits and timeouts`

---

## Etapa 6.4 — Retenção e docs

**O que fazer**
- Retenção de dados (Q7): por quanto tempo guardar PDFs, recortes e relatórios, e quem vê; comando de limpeza com dry-run.
- Revisão dos docs contra o código.
- Metas dos marcos anteriores revistas com os números.

**Pronto quando:** a política de retenção está decidida e aplicada, e os docs refletem o código.

**Commit sugerido:** `docs: review documentation against the code`

---

## Pronto do M6 (I6)

- A correlação com o PeerRead está medida e registrada.
- As metas dos marcos anteriores foram revisadas com os números.
- Os docs refletem o código.
