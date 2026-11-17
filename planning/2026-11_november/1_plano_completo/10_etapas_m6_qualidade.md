# M6 — Qualidade

**Objetivo:** medir, calibrar e endurecer.
**Trilhas:** todas
**Referência:** [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#outras-avaliações), [Testes e verificação](12_testes_e_verificacao.md)

Caminhos relativos a `projects/correction/`.

---

## Etapa 6.1 — Evals offline

**Situação (13/11/2026):** a base, da trilha de Agentes, está implementada. Faltam o `bench_reviews` e o `bench_judge` (Avaliação) e os benchmarks de integridade (4.10 e 5.6).

**O que fazer**
- Pacote `evals/` com os comandos:
  - `bench_reviews`: correlação (Spearman, QWK) com as notas por aspecto do PeerRead e acerto de accept/reject;
  - `bench_judge`: erros plantados nas saídas dos avaliadores (quote falso, `missing` de algo que está em outra seção, nota contradizendo as observações) → recall do juiz e taxa de rejeição indevida;
  - `bench_plagiarism` (da 4.10) e os benchmarks da 5.6, no mesmo formato.
- Relatório por versão de prompt e por `ModelSpec`, gravado em `evals/results/`.
- Fora do CI.

**Pronto quando:** cada comando roda e grava um relatório comparável com o anterior.

**Commit sugerido:** `feat: add offline evaluation commands`

**Base implementada (13/11/2026, `agentes/6.1-evals-base`):** contrato comum de
relatório com amostra, parâmetros, hashes de prompt, `ModelSpec`, código, métricas
e consumo; persistência sem sobrescrita em `evals/results/`; `bench_profiling`
integrado; comando `compare_evals` com verificação de compatibilidade e leitura
do baseline legado. Medições de desempenho continuam fora do CI.
Ver [operação e contrato](../../../docs/evals.md).

Os runners específicos `bench_reviews`, `bench_judge`, `bench_plagiarism` e os
benchmarks da Fase 2 permanecem como próximas integrações do plano completo.

**Verificação da base:** 654 testes passaram em Python 3.14 e PostgreSQL 18, com
5 contratos `llm` excluídos e o aviso de depreciação já existente do SDK Google.
Mypy aprovou 237 arquivos; Ruff e formatação passaram (239 arquivos); checks do
Django e `makemigrations --check --dry-run` sem problemas ou alterações pendentes.

Foi executado o comando real de regras locais nos 30 artigos, gerando um novo
relatório e sua comparação em `evals/results/`: 119/152 papéis corretos (78,29%),
zero chamadas de LLM e diferença zero em relação ao baseline da 2.7. O arquivo
histórico permaneceu intacto; os artefatos locais gerados estão fora do Git.

---

## Etapa 6.2 — Custo no admin

**Situação (13/11/2026):** implementada.

**O que fazer**
- Agregações de `LLMCall` no admin: por run, por estágio, por papel, por modelo e por período.
- Alerta para run acima do orçamento.

**Teste** (`attempts/tests/test_cost_admin.py`): a soma por run bate com as chamadas.

**Commit sugerido:** `feat: show LLM cost aggregates in the admin`

**Implementação (13/11/2026):** painel na lista de `LLMCall` e no detalhe do `Run`,
com somas históricas em `Decimal`, filtros por período e desdobramentos por run,
estágio, papel, provedor/modelo e dia. O orçamento de alerta por run é opcional
(`METIS_LLM_RUN_BUDGET_USD`); o alerta sempre usa o histórico completo do run,
mesmo com filtros ativos. Valores sem preço são identificados como totais parciais.
Ver [documentação de custo](../../../docs/agents.md#consulta-no-admin-62).

**Verificação:** 608 testes passaram, com 5 testes `llm` excluídos, em Python 3.14
e PostgreSQL 18; há somente o aviso de depreciação já existente do SDK Google.
Ruff passou (223 arquivos formatados), mypy passou (221 arquivos), `manage.py check`
não apontou problemas e `makemigrations --check --dry-run` não encontrou alterações.

---

## Etapa 6.3 — Endurecimento

**O que fazer**
- Limites de upload e de páginas (Q9, com o número medido no M1); timeouts dos parsers.
- Teste de carga leve: N submissões simultâneas com fakes, conferindo filas, workers e o reconciliador.
- Revisão de segurança: arquivos fora de URL pública, logs sem texto do manuscrito, `/docs` desligado sem DEBUG.

**Commit sugerido:** `chore: harden upload limits and timeouts`

---

## Etapa 6.4 — Retenção e docs

**Decidido (15/11):** a retenção (Q7) e o comando de limpeza saem do escopo do projeto. A revisão dos docs segue junto de cada etapa.

**Situação (13/11/2026):** a parte de docs da trilha de Agentes está feita. A retenção (Q7) e a revisão final dos docs continuam com a Plataforma.

**Recorte docs do módulo entregue em 13/11/2026:** revisão contra o código de
`32ff4e6`, identificação do fluxo alvo e da implementação atual, comandos/API,
configuração, limites, modelos e metas de M0–M6. Os [números e metas revistas](../../../docs/status_and_metrics.md)
preservam os ensaios históricos: citações 244/263 de recall e 244/264 de
precisão no protocolo filtrado; regras locais 119/152 e F1 micro 0,7885, sem LLM.
Os 654 testes da 6.1 são referência da entrega anterior, não nova execução de 6.4.

**Verificação do recorte:** 21 arquivos Markdown revisados, 181 links/âncoras
locais conferidos sem erros e `git diff --check` limpo. Baseline, totais por
área, padrões da configuração, rotas, stubs e sink da curadoria conferidos
diretamente contra os arquivos locais. Sem alteração de código, banco ou
chamada a provedor nesta revisão.

**A etapa completa permanece aberta:** Q7 ainda precisa de política de retenção,
permissões específicas e comando de limpeza com dry-run. Nada foi apagado nesta
revisão. Medição de LLM/PeerRead, A/B e benchmarks de integridade continuam
pendentes; este recorte não fecha o pronto do M6.

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
