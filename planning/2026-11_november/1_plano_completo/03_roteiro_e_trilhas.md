# Roteiro e trilhas

Sem datas: a ordem, as dependências e o critério de pronto. A equipe tem 3 ou mais pessoas, então o trabalho anda em 3 trilhas paralelas, que se juntam em pontos de integração.

## Marcos

```text
M0 Fundação ─▶ M1 Extração ─▶ M2 Perfil + Questions ─▶ M3 Avaliação ─┬─▶ M4 Integridade, Fase 1 ─┐
                                                                     └─▶ M5 Integridade, Fase 2 ─┴─▶ M6 Qualidade
```

A ordem dos marcos continua a do [roteiro de outubro](../../2026-10_october/1_desenho_inicial/02_roteiro.md): a avaliação vem antes da integridade, e o E3 é *pass-through* até o M4. O que muda é que **partes de marcos posteriores começam antes**, em outras trilhas, quando não dependem do pipeline:

- o contrato `ExtractedDocument` e as fixtures (D19) liberam M2 e M3 antes da extração real;
- os clientes do `scholarly/`, o corpus, os embeddings e o léxico do M4 são código isolado e podem começar logo depois do M0.

| Marco | Objetivo | Etapas | Pronto quando |
|---|---|---|---|
| M0 Fundação | Esqueleto ponta a ponta com estágios stub | [04](04_etapas_m0_restante.md) | CI verde; `docker compose up` + `POST /api/attempts` levam o run a `done`; gate, falhas e reconciliador com teste |
| M1 Extração | `ExtractedDocument` real + base do Agno | [05](05_etapas_m1_extracao.md) | 3–5 PDFs reais com snapshot estável; gráfico vetorial recortado; texto oculto plantado detectado; ligação citação ↔ referência medida; toda chamada de visão em `LLMCall` |
| M2 Perfil | Área, Question e papéis das seções | [06](06_etapas_m2_perfil.md) | Amostra rotulada classificada (meta da primeira medição); fallback testado; curadoria no admin; papéis batem com a amostra |
| M3 Avaliação | Relatório final real e decisão do modo | [07](07_etapas_m3_avaliacao.md) | `FinalReport` de um PDF real no E2E; testes com fakes do loop do juiz; A/B rodado e modo decidido; custo por artigo medido |
| M4 Integridade, Fase 1 | Similaridade, regras, gate | [08](08_etapas_m4_integridade_fase1.md) | Precisão e recall no plágio sintético atingem a meta (Q11); E2E: trecho copiado → `waiting_human_review` → continuar → `done` |
| M5 Integridade, Fase 2 | Citações e cruzamento | [09](09_etapas_m5_integridade_fase2.md) | Referências inventadas detectadas, com falso positivo medido; linha de base em SciCiteVal e Citation Integrity |
| M6 Qualidade | Medir, calibrar, endurecer | [10](10_etapas_m6_qualidade.md) | Correlação com o PeerRead registrada; metas revistas; docs refletem o código |

## Trilhas

> **Desde 07/11/2026, as trilhas viraram 4 módulos, um por integrante.** Plataforma e Extração é a antiga P. A antiga A foi dividida em Agentes, Perfil e Relatório e em Avaliação. Integridade é a antiga I. A divisão, a ordem das etapas, as dependências, as branches e o fluxo de PR estão em [divisão em módulos](../2_divisao_equipe/divisao_em_modulos.html) (abra no navegador). As tabelas abaixo ficam como histórico.

| Trilha | Foco | Apps e pacotes |
|---|---|---|
| **P** — plataforma e extração | Pipeline, operação, E1, E5 | `pipeline/`, `metis/`, `extraction/`, parte de `evaluation/` (E5) |
| **A** — agentes e avaliação | Base do Agno, E2, E4 | `agents/`, `questions/`, `evaluation/` (E4) |
| **I** — integridade | E3 inteiro | `scholarly/`, `integrity/` |

Quem fica em cada trilha é a questão aberta Q15.

### Fases

| Fase | Trilha P | Trilha A | Trilha I | Fecha |
|---|---|---|---|---|
| 1 | CI da 0.3 com Postgres; 0.4 pipeline; 0.5 gate; 0.6 reconciliador; 0.7 Docker | 1.1 contrato + fixtures; 1.2 spike do Agno; 1.3 `agents/` | 4.1 clientes do `scholarly/`; 4.3 corpus + BGE-M3 + `load_peerread`; 4.5 MinHash + winnowing | **I1** |
| 2 | 1.4 `LLMCall` (com a A); 1.5 divisão do artigo pelo modelo (feita); 1.10 referências e citações; 1.6 figuras e tabelas (com a 1.8); 1.7 texto oculto; 1.9 retomada do E1; 1.11 `ExtractedDocument` (espera a 1.1 e a 1.7) | 2.1–2.7 (M2 inteiro, sobre as fixtures) | 4.2 resolução de referências; 4.6 semântico + PT↔EN | **I2** (M1) |
| 3 | 3.11 E5 + `FinalReport` + `GET /report` | 3.1–3.10 (E4) | 4.4 candidatos; 4.7 filtro + adjudicador; 4.8 regras + relatório + workflow; 4.9 gate no admin; 4.10 benchmark | **I3** (M2 + M3 sem A/B), **I4** (M4) |
| 4 | 5.1–5.3 (com a I) | 3.12 rubric check; 3.13 A/B | 5.4 alinhamento; 5.5 cruzamento + regras v2; 5.6 benchmarks | **I5** (M3 completo, M5) |
| 5 | 6.2 custo no admin; 6.3 endurecimento | 6.1 evals de avaliação e juiz | 6.1 evals de integridade | **I6** (M6) |
| — | 6.4 retenção e docs (todos) | | | |

### Dependências entre trilhas

| Etapa | Espera por | Por quê |
|---|---|---|
| 1.4 `LLMCall` | 0.4 (pipeline) e 1.3 (`agents/`) | O sink grava por run e estágio |
| 1.6 figuras e tabelas | 1.10 | Mesma sessão e conferência do extractor; a ordem foi decidida em 12/11 |
| 2.3 profiler | 1.1 (fixtures) e 1.3 | Lê título e abstract do contrato |
| 2.5 workflow do E2 | 0.4 | Roda dentro do `StageTask` |
| 3.3 passes por seção | 2.4 (papéis) e 2.2 (critérios) | O prompt depende do papel |
| 3.11 E5 | 3.2 (schemas e models do E4) | Agrega as rodadas |
| 3.12 rubric check | 2.6 (curadoria) e 3.10 (E4) | Roda o E4 com a Question rascunho |
| 4.2 referências | 1.10 (`references[]` em campos) e 4.1 | Resolve a lista extraída |
| 4.7 filtro por citação | 1.10 (ligação citação ↔ referência) | Precisa saber se o trecho cita a fonte |
| 4.8 workflow do E3 | 0.5 (gate) | Risco alto pausa o run |
| 5.5 `Parallel` das fases | 4.8 | Acrescenta o ramo da fase 2 |

### Pontos de integração

Cada ponto é um E2E com `docker compose`, feito com as três trilhas juntas, e só fecha quando o roteiro de [12](12_testes_e_verificacao.md#verificação-manual-por-ponto-de-integração) passa.

| Ponto | O que roda de verdade | O que ainda é stub |
|---|---|---|
| I1 | API, pipeline, gate, reconciliador, Docker | E1–E5 |
| I2 | E1 real (divisão do artigo; figuras em aberto), `LLMCall` | E2–E5 |
| I3 | E1, E2, E4, E5 reais | E3 (*pass-through*) |
| I4 | E3 com a Fase 1 | Fase 2 |
| I5 | Pipeline completo; A/B decidido | — |
| I6 | Pipeline completo, medido e calibrado | — |

## Como cada etapa entra

- **Um commit por etapa**, em Conventional Commits em inglês; o "Commit sugerido" de cada etapa é o ponto de partida.
- **Docs junto com o código:** a etapa atualiza os docs que descrevem o que ela mudou, e o código passa a ser a fonte de verdade.
- **Etapa pronta** = testes da etapa passando no CI + o "Pronto quando" da etapa.
- **Mudança de contrato** (`ExtractedDocument`, schemas de saída, `StageContext`) avisa as outras trilhas no mesmo PR.
