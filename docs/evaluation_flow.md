# Fluxo de uma avaliação

Este documento segue um artigo da submissão ao relatório final. A mecânica de cada passo (claims, retries, recuperação) está em [Orquestração](orchestration.md), e os diagramas com as entidades e as ligações entre elas em [Grafo do fluxo](flow_graph.md).

**Revisão de 13/11/2026:** E1, E2 e E5 implementados; E3 e E4 são stubs.
O diagrama é o fluxo alvo. Na base atual, sem rodadas julgadas de E4, E5 para
em `waiting_setup`. [Estado, testes e metas](status_and_metrics.md).

## Visão em uma página

```text
POST /api/attempts ──▶ valida PDF ──▶ mesma versão já enviada? ──sim──▶ 200 com a attempt existente
                                            │ não
                                            ▼
                         Attempt nova (versão N+1) + Run(received)
                         runs pendentes das versões anteriores → superseded
                                            │ após o commit
                                            ▼
E1 extração ──▶ E2 perfil ──▶ E3 integridade ──┬── risco baixo/médio ──▶ E4 avaliação ──▶ E5 consolidação ──▶ done
                                               │
                                               └── risco alto ──▶ waiting_human_review
                                                                     ├─ continuar ──▶ E4 …
                                                                     └─ encerrar  ──▶ closed_by_reviewer
```

## 0. Submissão

1. O sistema que submete chama `POST /api/attempts` como multipart com `file` e `external_id`, autenticado por token de serviço.
2. A API valida cabeçalho `%PDF-` e tamanho máximo (50 MiB por padrão). Limite de páginas e timeout separado do parser ainda estão pendentes na 6.3.
3. A API calcula o sha256 do arquivo.
   - **Mesmo artigo e mesmo sha256** → responde **200** com a attempt e o run existentes. Isso torna o reenvio idempotente: um cliente que perdeu a resposta pode repetir a chamada sem criar duplicata.
   - **Arquivo novo para o artigo** → cria a attempt seguinte (`attempt_number` + 1) e um `Run` em `received`, e responde **202**. Os runs de avaliação ainda pendentes das versões anteriores viram `superseded`; runs internos são preservados.
4. A task do E1 é publicada **só depois do commit**. Se o broker falhar nesse instante, o reconciliador republica (ver [Orquestração](orchestration.md#reconciliador)).

## 1. E1 — Extração

Entrada: o PDF. Saída: a `Extraction`, o artigo dividido em seções que os estágios seguintes leem.
- Uma chamada ao modelo (Gemini) mapeia os títulos das seções; sem abstract ou sem referências → `rejected_invalid_submission`.
- Uma chamada por seção, em paralelo, copia o texto de cada uma. O código confere a resposta contra o texto do PDF e refaz a seção que veio incompleta ou com texto de outra.
- Uma chamada separa as referências em campos, e o código liga cada citação no texto à sua referência.
- Uma chamada lista as figuras e tabelas, conferidas pela legenda; outra por figura, em paralelo, descreve cada uma (o que mostra, os dados legíveis, se sustenta o que o texto diz dela e, para tabela, o markdown).
- Um run novo do mesmo PDF reaproveita a extração guardada, e um retry do estágio retoma das respostas já guardadas.
- Em aberto: texto oculto (1.7, Integridade) e o `ExtractedDocument` montado a partir da extração (1.11).

Detalhe: [Extração](extraction.md).

## 2. E2 — Perfil e Question

- Um agente classifica o artigo numa taxonomia fechada (área, tipo de artigo, idioma).
- O profiler escolhe field e depois topic/subfield em dois passos. O sistema sobe pela árvore até achar uma Question validada e ativa do método. A genérica exige carga, revisão e ativação no admin; sem taxonomia ou candidata disponível, o run vai para `waiting_setup`.
- O caminho percorrido e a versão da Question ficam gravados no Run, para a avaliação ser reproduzível.
- Cada seção ganha um papel (introdução, método, resultados…), e o sistema monta, em código, o mapa do documento: abstract, seções e legendas.

Detalhe: [Perfil e Questions](questions_and_profiling.md).

## 3. E3 — Integridade e gate

**Planejado para M4/M5.** Hoje `IntegrityStage` apenas retorna `risk=low` e
segue, sem criar relatório ou achados. O gate está implementado na máquina de
estados e testado com cenários sintéticos; não há detecção real que o acione.

Três frentes:
- **Fase 1, similaridade:** compara o texto com o corpus interno e com fontes externas.
- **Fase 2, citações:** verifica se cada referência existe, se foi retratada e se sustenta o que o texto afirma.
- **Fase 0:** traz para o relatório o texto oculto encontrado no E1.

Regras explícitas definem o nível de risco:
- **Baixo ou médio:** o run segue. O resumo do relatório entra no contexto dos avaliadores.
- **Alto:** o run para em `waiting_human_review`. Uma pessoa vê as evidências no admin e escolhe *continuar* (o run vai para o E4) ou *encerrar* (`closed_by_reviewer`).

Detalhe: [Checagem de integridade](integrity_check.md).

## 4. E4 — Avaliação

**Executors isolados implementados em 3.3–3.6; integração planejada para 3.10.**
Existem contratos e models de rodadas/vereditos, mas a task atual ainda não
chama avaliadores nem juiz. O fluxo pretendido é:

1. Três slots (A = GPT, B = Gemini, C = outro modelo de uma das duas famílias) analisam o artigo **seção por seção**. Cada passe recebe o texto da seção, o prompt do papel dela e o mapa do documento, e devolve observações com trechos literais como evidência, sem nota.
2. Checagens entre seções conferem o que cruza partes do artigo: promessas × resultados, método × pergunta, figuras × texto.
3. A síntese transforma observações e checagens em nota e justificativa por critério.
4. Validadores em código conferem schema, notas permitidas, critérios completos e se cada trecho citado existe.
5. O juiz, com o artigo inteiro, verifica observações, checagens e sínteses. Ele devolve o trecho inconsistente e o motivo.
6. Só o que foi invalidado volta: o passe daquela seção ou a síntese daquele critério. O avaliador corrige ou mantém com nova evidência. São no máximo 2 rodadas de revisão; o que continuar inválido vira `unresolved`.

O modo por seção é a proposta. O A/B do M3 compara com o artigo inteiro numa chamada antes de fixar o padrão.

Detalhe: [Avaliadores, juiz e consolidação](evaluators_and_judge.md).

## 5. E5 — Consolidação

**Implementado na 3.11.** Consome a última rodada julgada e finalizada de cada
slot A/B/C. Ausência ou incompletude gera `waiting_setup` antes da meta-revisão.

- Por critério: mediana das notas válidas, dispersão e total ponderado → recomendação. A concordância é um índice descritivo, sem calibração; faixas de desenvolvimento em 4/3/2. [Política exata](evaluators_and_judge.md#consolidação-implementada-311).
- Um meta-revisor junta as justificativas em pontos fortes, fracos e sugestões, sem mexer em nota.
- O `FinalReport` estruturado fica disponível pela API e no admin. O run termina em `done`.

## Status que quem integra precisa tratar

| Status | Significa | O que fazer |
|---|---|---|
| `received` … `consolidating` | Em andamento | Consultar de novo mais tarde |
| `waiting_human_review` | Risco alto de integridade; aguardando uma pessoa | Aguardar a decisão no admin |
| `done` | Relatório final pronto | Buscar o relatório |
| `rejected_invalid_submission` | O PDF não é um artigo processável | Corrigir e reenviar (vira uma nova attempt) |
| `closed_by_reviewer` | Encerrado na revisão humana | Ver a nota da decisão |
| `superseded` | Chegou uma versão mais nova do artigo | Acompanhar o run da versão nova |
| `waiting_setup` | Falta chave/configuração, taxonomia, Question ou rodadas completas para E5 | Resolver a pendência do evento e reprocessar; repetir sem E4 real não cria avaliações |
| `error_llm`, `error_external`, `error_unexpected` | Falha após as tentativas automáticas | A equipe reprocessa pelo admin |

## Versões, reavaliação e reprocessamento

| Situação | O que acontece |
|---|---|
| O autor corrige o artigo e reenvia | Nova **attempt** (versão N+1) com um run novo; os runs pendentes da versão anterior viram `superseded` |
| Reavaliar a mesma versão com outra configuração (outro modelo, Question nova) | Novo **run** na mesma attempt. A extração é reaproveitada pelo cache (sha256 + hash da config e prompts do extractor) |
| Um estágio falhou (`error_*`, `waiting_setup`) | **Reprocessar** no admin: o run volta ao checkpoint do estágio que falhou e só esse estágio em diante roda de novo |

## Endpoints

| Método | Caminho | Autenticação | O que faz | Situação |
|---|---|---|---|---|
| POST | `/api/attempts` | token de serviço | Multipart: `file` (PDF) + `external_id`. **202** versão nova, **200** reenvio idêntico | Implementado |
| GET | `/api/runs/{run_id}` | token de serviço | Status, estágio atual e eventos | Implementado |
| POST | `/api/runs/{run_id}/decision` | token de serviço | JSON: `decision` (`continue` ou `close`), `note` opcional. **200** com o run, **409** fora do gate | Implementado |
| GET | `/api/runs/{run_id}/report` | token de serviço | JSON ou `?format=markdown`, somente em `done`; **409** enquanto indisponível | Implementado |
| GET | `/api/runs/{run_id}/integrity` | token de serviço | Relatório de integridade | Planejado, rota ausente |
| GET | `/health/` | — | Healthcheck do container web (testa o banco) | Implementado |
| — | `/admin/` | usuário Django | Curadoria, rubric check, custo, gate e auditoria | Implementado |

Rotas de run retornam **404** para id inexistente ou interno
(`purpose=rubric_check`/`ab_test`). JSON/Markdown do relatório têm
`Cache-Control: private, no-store`. Contratos em
[`attempts/api/routes.py`](../projects/correction/attempts/api/routes.py).

`/docs` e `/openapi.json` só ficam ligados com `DEBUG`, porque listam todas as rotas sem autenticação.
