# Avaliadores, juiz e consolidação (E4 e E5)

## Visão geral

```text
por avaliador (A, B e C, independentes):
   1. passes por seção (em paralelo)    seção + mapa do documento ──▶ observações (sem nota)
   2. checagens entre seções            promessa × resultado, método × pergunta, figura × texto
   3. síntese por critério              observações + checagens ──▶ nota + justificativa
                  │
                  ▼
   ┌──── Loop (no máximo 2 rodadas de revisão) ───────────────────────┐
   │ validadores ──▶ juiz (com o artigo inteiro) ──▶ revisão só do    │
   │                                                 que foi invalidado│
   └──────────────────────────────────────────────────────────────────┘
                  │
                  ▼
   consolidação: mediana, concordância, meta-review ──▶ FinalReport
```

**Por que por seção.** Com o artigo inteiro e todos os critérios numa chamada, a atenção do modelo se dilui:
- ele lê melhor o começo e o fim que o meio, e daí vêm afirmações erradas como "o artigo não informa X";
- as justificativas ficam genéricas;
- a nota varia de uma execução para outra.

Cada passe por seção tem uma tarefa pequena e um checklist próprio. Mas parte da avaliação está entre as seções, e por isso existem três peças com visão mais ampla: as checagens entre seções, o mapa do documento em todo passe e o juiz com o artigo inteiro.

**Dois modos de avaliação.** O fluxo por seção (`sectioned`) é a proposta. O artigo inteiro numa chamada por avaliador (`whole_document`) fica como linha de base. Os dois são estratégias do método, escolhidas por config, e o A/B do M3 decide qual vira padrão (ver [Como decidir o modo](#como-decidir-o-modo-ab-no-m3)).

## O que cada chamada recebe

| Chamada | Recebe |
|---|---|
| Passe por seção | Mapa do documento + texto da seção (com suas figuras e tabelas) + prompt e checklist do papel + os critérios desse papel, com o `rubric_text` de cada um |
| Checagem entre seções | Só as seções envolvidas (ex.: abstract e introdução × resultados e conclusão) + as descrições das figuras com `supports_claims` |
| Síntese | Observações e checagens do próprio avaliador + definição e escala dos critérios + `rubric_text` + resumo da integridade + obras relacionadas (para julgar novidade) |
| Juiz | O artigo inteiro + a revisão do avaliador (observações, checagens e síntese) |

- **Mapa do documento.** Montado em código no E2, sem LLM (ver [Perfil e Questions](questions_and_profiling.md#papéis-das-seções-e-mapa-do-documento)): abstract, seções com papel e primeira frase, legendas de figuras e tabelas.
  - Com ele, cada passe sabe o que existe fora da sua seção.
  - Na dúvida, o passe marca a observação como `possibly_elsewhere` em vez de afirmar que algo falta.
- **O artigo é dado, não instrução.** Todo trecho do artigo vai entre delimitadores, com a regra explícita de que nada dentro dele é comando. É a segunda defesa contra prompt injection; a primeira é o scan do E1.
- **Ordem do prompt.** O conteúdo do artigo vem antes da tarefa, como prefixo estável, para aproveitar o caching de prompt. Isso pesa sobretudo no juiz, que recebe o artigo inteiro em toda rodada.

## Papéis e critérios

Cada papel de seção avalia só os critérios que dependem dele. A tabela é a proposta inicial e fica no config do método (`EvaluationConfig`):

| Papel | Critérios no passe | Exemplos do checklist |
|---|---|---|
| Introdução | `originality`, `impact`, `clarity` | O problema está claro? As contribuições estão explícitas? |
| Trabalhos relacionados | `meaningful_comparison`, `originality` | Os trabalhos mais próximos aparecem? A diferença está dita? |
| Método | `soundness`, `replicability`, `clarity` | Hipóteses, parâmetros, dados, código: dá para reproduzir? |
| Resultados | `substance`, `soundness` | Baselines, estatística, variância, ablações |
| Discussão e limitações | `soundness`, `impact` | As limitações e as ameaças à validade são reconhecidas? |
| Conclusão | `clarity`, `impact` | As conclusões se apoiam nos resultados? |

- `clarity` é observada em todo passe e consolidada na síntese.
- Os papéis mudam com o `paper_type`: um artigo teórico tem definições, teoremas e provas; uma revisão tem protocolo de busca e seções temáticas.
- Seção muito longa é dividida por subseção, e cada parte vira um passe.

## Os avaliadores

- **Três slots**, cada um com um `ModelSpec` (provedor, modelo, parâmetros), de **famílias diferentes** (ex.: Gemini, GPT, Claude). A configuração fica nos settings, e o Run guarda um snapshot.
- **Independência.** Cada avaliador faz os próprios passes, checagens e síntese. Só o mapa do documento é compartilhado, e ele é extraído em código, sem nenhuma opinião.
- **Por que famílias diferentes:** os erros ficam menos correlacionados. Três execuções do mesmo modelo tendem a errar igual, e aí nem o juiz nem a mediana pegam.

**Saídas**

- **Observação** (passe por seção): `{id, section_id, role, kind, statement, evidence[{quote, section_id}], criteria[], severity, possibly_elsewhere, confidence}`.
  - `kind`: `strength`, `weakness`, `missing` ou `inconsistency`.
  - `severity`: `minor`, `major` ou `critical`.
  - Não tem nota: o passe descreve, não pontua.
- **Checagem entre seções:** `{id, kind, verdict, evidence[], criteria[], severity}`.
  - `kind`: `claims_vs_results`, `method_vs_question` ou `figure_vs_text`.
  - `verdict`: `consistent`, `inconsistent` ou `unclear`.
- **Síntese** (por critério): `{criterion_key, grade, justification, observation_ids[], check_ids[], confidence}`.
  - O `grade` está no conjunto permitido do critério.
  - A justificativa só pode se apoiar nas observações e checagens citadas.

No modo `whole_document`, o avaliador devolve direto a síntese, com `evidence[]` no lugar dos ids.

## Validadores determinísticos

Rodam antes do juiz, em cadeia (Chain of Responsibility), sem custo de LLM:

| Validador | Recusa quando |
|---|---|
| Schema | A saída não parseia no `output_schema` (o Agno devolve `str` no lugar do objeto) |
| Nota permitida | `grade` fora do conjunto do critério |
| Critérios completos | Falta um critério na síntese, ou aparece um desconhecido |
| Evidência existe | O `quote` não está na seção citada (match fuzzy, normalizando espaços e hifenização) |
| Referências internas | A síntese cita um id de observação ou de checagem que não existe |
| Justificativa | Vazia, ou só repete a pergunta |

- O item recusado aqui volta direto para a revisão, já com o motivo, sem passar pelo juiz. Pedir de novo sem dizer o que estava errado tende a repetir o erro.
- Toda observação `missing` vai para o juiz, que é quem pode conferir no artigo inteiro.

## O juiz

O juiz **verifica**; não dá nota nem reescreve a avaliação. É ele que tem a visão global, com o artigo inteiro.

- **Uma chamada por avaliador**, com a revisão inteira (observações, checagens e síntese), para pegar contradição entre as partes.
- **Modelo forte e fixo.** Para evitar viés de autopreferência, a revisão do avaliador da mesma família do juiz vai para um juiz alternativo (regra em `ModelFactory.judge_for(spec)`).
- **Dicas de divergência** calculadas em código: "B deu 2 em soundness; A e C deram 4". Divergência sozinha não invalida.
- **Checklist:**

  | Categoria | Pergunta |
  |---|---|
  | `ungrounded` | A evidência sustenta a observação ou a justificativa? |
  | `factual_error` | Afirma algo falso sobre o artigo? Um `missing` que está em outra seção cai aqui |
  | `contradiction` | A nota é coerente com as observações citadas? |
  | `rubric_mismatch` | A avaliação segue a rubrica e a escala? |
  | `off_topic` | A observação é do papel da seção? A síntese responde ao critério? |

- **Saída por item** (observação, checagem ou critério): `{item_key, verdict: valid | invalid, issues[{category, excerpt, reason}]}`.
- **Conferência do `excerpt`.** O código confere que ele é substring do item. Se não for, o juiz é chamado de novo com esse motivo. Se o problema persistir, o apontamento é descartado e registrado.

## Revisão parcial e réplica

O que roda de novo depende de onde está o problema:

| Item inválido | O que roda de novo |
|---|---|
| Observação | O passe daquela seção, só para aquela observação; depois, a síntese dos critérios que a citam |
| Checagem entre seções | Aquela checagem; depois, a síntese dos critérios afetados |
| Síntese de um critério | Só a síntese daquele critério |

- O pedido de revisão (`RevisionPromptBuilder`) leva o item anterior, o trecho apontado e o motivo.
- O avaliador responde `accept` (corrige) ou `rebut` (mantém e traz nova evidência do artigo). O juiz reavalia na rodada seguinte.
- **Por que existe a réplica.** LLMs tendem a ceder a qualquer crítica (bajulação). Sem a opção de defender a resposta, quem definiria a nota seria, na prática, o juiz.

## O loop

- **Limite:** `Loop(max_iterations=2)` no Agno. O `end_condition` consulta o estado persistido (há itens pendentes?).
- **Itens que esgotam as rodadas** viram `unresolved`:
  - uma observação `unresolved` sai das sínteses;
  - um critério `unresolved` sai da agregação;
  - os dois aparecem no relatório final, sinalizados para revisão humana.
- **Persistência:** `ReviewRound` (o estado da revisão do avaliador naquela rodada) + `JudgeVerdict` (um por item verificado). É a trilha de auditoria: guarda o trecho que tornou a avaliação inconsistente e o motivo dado pelo juiz.

## Exemplo de uma rodada (ilustrativo)

1. **Rodada 1.** No passe do método, o avaliador B registra a observação `obs-7`: `kind=missing`, "O artigo não informa o modelo de ruído usado nas simulações", afetando `soundness`. Na síntese, B dá 2 em `soundness`, citando `obs-7`.
2. Os validadores aprovam. Como `obs-7` é `missing`, vai para o juiz.
3. O juiz, com o artigo inteiro, invalida:

   ```json
   {"item_key": "obs-7", "verdict": "invalid",
    "issues": [{"category": "factual_error",
                "excerpt": "O artigo não informa o modelo de ruído usado nas simulações",
                "reason": "A seção 4.2 (Resultados) descreve um modelo de ruído despolarizante com taxa de 10⁻³."}]}
   ```
4. **Rodada 2.** Só o passe do método roda de novo, e só para `obs-7`, com o trecho e o motivo.
   - B responde `accept` e troca a observação por uma `weakness`: o modelo de ruído existe, mas não foi validado em hardware real.
   - Em seguida, só a síntese de `soundness` roda de novo, e a nota passa a 3.
5. O juiz valida, não sobra item pendente e o loop termina. Ficam gravadas as duas `ReviewRound` de B e os vereditos de cada rodada.

## Esboço do workflow (Agno 3)

```python
Workflow(name="evaluation", telemetry=False, steps=[
    Parallel(*[Steps(name=f"evaluator_{s.slot}", steps=[
                   Step(name=f"sections_{s.slot}", executor=SectionPassStep(s, ctx, deps), max_retries=0),
                   Step(name=f"cross_checks_{s.slot}", executor=CrossCheckStep(s, ctx, deps), max_retries=0),
                   Step(name=f"synthesis_{s.slot}", executor=SynthesisStep(s, ctx, deps), max_retries=0),
               ]) for s in ctx.evaluator_specs], name="evaluators"),
    Loop(name="judge_loop", max_iterations=settings.MAX_REVISION_ROUNDS, end_condition=no_pending_items(run),
         steps=[Step(name="judge", executor=JudgeStep(ctx, deps), max_retries=0),
                Step(name="revise", executor=RevisionStep(ctx, deps), max_retries=0)]),
    Step(name="consolidate", executor=ConsolidationStep(ctx, deps), max_retries=0),
])
```

- **Passes por seção:** rodam dentro do `SectionPassStep`, num pool com limite de concorrência, porque o `Parallel` do Agno não tem limite.
- **Executors:** classes chamáveis, com as dependências no construtor.
- **Idempotência:** um passe ou uma síntese que já tem saída na rodada é pulado quando o estágio é retentado.
- **Agentes:** vêm da `AgentFactory`, criados por execução.

## Consolidação (E5)

**Agregação em código, por critério:**
- **mediana** das notas válidas, robusta a um outlier (com 2 notas válidas, vira a média);
- **dispersão** (máxima − mínima) como indicador de concordância;
- **total ponderado** pelos pesos dos critérios;
- **faixa → recomendação:** `accept`, `minor`, `major` ou `reject`. A faixa também calibra o tom do resumo.

**Meta-revisor (agente).** Une as sínteses e as observações dos 3 avaliadores em pontos fortes, pontos fracos e sugestões acionáveis, citando os critérios e as evidências que usa. **Não altera notas.**

**`FinalReport`.** JSON estruturado, renderizado em Markdown/PDF. Nunca é uma string que outra parte do sistema precise parsear.

| Campo | Conteúdo |
|---|---|
| `recommendation` | `accept`, `minor`, `major` ou `reject` |
| `total_score`, `agreement` | Total ponderado e concordância geral |
| `criteria[]` | Por critério: nota consolidada, dispersão, justificativa, observações citadas, `unresolved` |
| `sections[]` | Por seção: as observações principais dos 3 avaliadores, agrupadas (modo `sectioned`). É o retorno mais direto para quem vai revisar o texto |
| `strengths`, `weaknesses`, `suggestions` | Saída do meta-revisor |
| `integrity` | Nível de risco, principais achados e `coverage` |
| `figures` | Problemas encontrados nas figuras (`issues`) |
| `versions` | Modelos, versões de prompt, modo de avaliação, versão da Question e da taxonomia |

## Custo

| | `whole_document` | `sectioned` (proposta) |
|---|---|---|
| Chamadas por avaliador, na rodada 1 | 1 | ≈ 10 (≈ 6 passes + 2–3 checagens + 1 síntese) |
| Tokens de entrada por avaliador | ≈ 1× o artigo | ≈ 1,3–2× o artigo (cada passe lê a sua seção + o mapa). Estimativa, a medir |
| Tempo | Uma chamada longa | Parecido: os passes rodam em paralelo |
| Cache de prompt | O artigo inteiro, reaproveitado | Menor nos passes; o juiz continua com o artigo inteiro como prefixo |

Nos dois modos:
- o juiz faz 3 chamadas por rodada;
- as revisões cobrem só o que foi invalidado;
- os validadores rodam antes do juiz;
- o `LLMCall` registra tokens e custo de cada chamada.

## Como decidir o modo (A/B no M3)

Os dois modos rodam no mesmo conjunto (PeerRead + artigos da equipe):

| Métrica | O que mostra |
|---|---|
| Variação da nota em 3 execuções do mesmo avaliador | Consistência |
| Concordância entre os 3 avaliadores | Estabilidade entre modelos |
| Taxa de itens invalidados pelo juiz (erro factual, falta de evidência) | Aterramento |
| Correlação com as notas humanas do PeerRead | Qualidade |
| Custo e tempo por artigo | Viabilidade |

- **O que o A/B isola.** Os dois modos compartilham a evidência obrigatória, os validadores, o juiz e a rubrica, então a comparação mede só o efeito de dividir o artigo.
- **A decisão** fica registrada no planejamento. O modo que perder continua disponível enquanto servir para comparação.

## Outras avaliações

- **Calibração com o PeerRead:** correlação (Spearman, QWK) entre as notas do Metis e as notas por aspecto dos reviews humanos, e acerto de accept/reject.
- **Erros plantados** nas saídas dos avaliadores (quote falso, `missing` de algo que está em outra seção, nota contradizendo as observações) medem o recall do juiz. Nas saídas corretas, mede-se a taxa de rejeição indevida.
- **Acompanhamento** por versão de prompt e por `ModelSpec`, em evals offline (fora do CI).
