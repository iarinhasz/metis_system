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

- **Três slots**, cada um com um `ModelSpec` (provedor, modelo, parâmetros). A configuração fica nos settings, e o Run guarda um snapshot.
  - Hoje há chave da OpenAI e do Google (D14): A = GPT, B = Gemini, C = outro modelo de uma das duas famílias, de tamanho ou geração diferente.
  - O slot C troca de provedor só por config (ex.: OpenRouter ou Ollama) quando houver chave de uma 3ª família.
- **Independência.** Cada avaliador faz os próprios passes, checagens e síntese. Só o mapa do documento é compartilhado, e ele é extraído em código, sem nenhuma opinião.
- **Por que famílias diferentes:** os erros ficam menos correlacionados. Três execuções do mesmo modelo tendem a errar igual, e aí nem o juiz nem a mediana pegam. Com duas famílias em três slots, a correlação é maior (risco R13): o A/B do M3 mede a concordância entre os slots da mesma família à parte.

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
- **Juiz cruzado, de modelo forte.** Para evitar viés de autopreferência, cada revisão é julgada por um modelo forte da **outra** família: o GPT é julgado pelo Gemini, e o Gemini pelo GPT. O slot C segue a regra da família dele (`ModelFactory.judge_for(spec)`, D14).
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

- **Forma (D17):** a rodada 1 é validada e julgada antes do loop. Se sobrar item pendente, cada iteração do loop é "revisar → validar → julgar", então a última revisão sempre passa pelo juiz.
- **Limite:** `Loop(max_iterations=2)` no Agno, dentro de um `Condition` que só entra no loop se houver pendência. O `end_condition` consulta o estado persistido (há itens pendentes?).
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

## Workflow (Agno 3)

```text
Parallel(evaluator_A, evaluator_B, evaluator_C)      # cada um: passes por seção → checagens → síntese
validate → judge                                     # rodada 1
Condition(há pendências,
    Loop(máx. 2, até não haver pendências,
         [revise → validate → judge]))               # a última revisão sempre passa pelo juiz
mark_unresolved
```

O esboço em código (E4 e E5), com a tabela do que cada passo lê, grava e pula num retry, está em [Agentes e workflows](agents.md#e4--avaliação-evaluationworkflowpy). Em resumo:
- **Passes por seção:** rodam dentro do `SectionPassStep`, num pool com limite de concorrência, porque o `Parallel` do Agno não tem limite.
- **Executors:** classes chamáveis, com as dependências no construtor.
- **Idempotência:** um passe ou uma síntese que já tem saída na rodada é pulado quando o estágio é retentado.
- **Agentes:** vêm da `AgentFactory`, criados por execução.
- **A consolidação é outro estágio** (E5), com o próprio workflow.

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

### Consolidação implementada (3.11)

O app `evaluation` inclui os contratos e a persistência de rodadas necessários da
etapa 3.2 e o workflow real do E5. O E4 permanece stub nesta branch: sem três
rodadas persistidas, julgadas e finalizadas, o E5 interrompe com `waiting_setup`.
Ele não transforma uma execução sem avaliações em relatório pronto.

`ReviewRound.store` exige posse do E4 e valida a escala do snapshot do método.
Após registrar os `JudgeVerdict`, `ReviewRound.finalize` verifica a cobertura de
vereditos, os ids e as pendências. Uma rodada finalizada não é alterada; revisões
seguintes criam outra rodada. O E5 usa a última rodada de cada slot, nunca uma
rodada antiga pronta quando existe uma mais nova ainda incompleta. Exige os três
slots, o mesmo modo e todas as sínteses dos critérios ativos.

A política inicial `median-v1` usa:

- Mediana das notas válidas; com duas notas, a média aritmética.
- Exclusão de critério `unresolved`, de voto sem veredito válido e de síntese
  apoiada em observação/checagem pendente. A exclusão se aplica ao voto daquele
  slot; os votos válidos dos outros avaliadores continuam disponíveis.
- Dispersão `max − min` quando há pelo menos dois votos válidos.
- Total como média ponderada pelas definições do método. Um critério sem votos
  fica com nota `null` e seu peso sai do denominador. Critério de peso zero não
  afeta o total; critério inativo nem participa da agregação.
- Concordância geral como média ponderada de `1 − dispersão/amplitude_da_escala`,
  apenas nos critérios com dois ou mais votos. É um indicador descritivo, não
  kappa nem uma estimativa de independência dos modelos. Sem pares, fica `null`.
- Faixas de desenvolvimento: `≥4 accept`, `≥3 minor`, `≥2 major`, abaixo de 2
  `reject`. Os limiares são provisórios, versionados no snapshot e aguardam
  calibração no A/B do M3. Não há arredondamento antes da escolha da faixa.

Sem nota válida em nenhum critério, total, concordância e recomendação ficam
`null`; o relatório exige revisão humana. Votos excluídos e pouca cobertura
também ficam sinalizados. A integridade aparece como `not_checked`, com risco
desconhecido, enquanto o E3 for pass-through.

O E5 congela os inputs, a política, o ModelSpec do meta-revisor e seu template
no primeiro processamento. Usa o `evaluation_config` do Run; para rodadas legadas
sem esse snapshot, captura o método registrado e identifica a origem como
`registry_at_consolidation`. Novos executores do E4 devem guardar esse config
antes das chamadas. Agregação, tentativas de narrativa e narrativa validada têm
checkpoints em `Run.consolidation`, protegidos pela posse da task.

O meta-revisor recebe somente a agregação e o catálogo validado. Os ids são
qualificados, como `a:observation:obs-1`, evitando colisões entre os slots.
Sua saída não aceita notas. Referência desconhecida ou schema inválido recebe
uma nova tentativa; se persistir, o ponto inteiro é removido e a ocorrência fica
no relatório. Uma falha de transporte usa o retry do Celery sem reiniciar o
orçamento de duas respostas nem repetir uma narrativa já guardada. Tokens e
custo passam pelo mesmo `DatabaseUsageSink` dos outros estágios.

O JSON inclui `criteria`, `sections`, `evidence`, `integrity`, `figures`, narrativa,
pendências e `versions`. O catálogo `evidence` permite resolver os ids citados.
Versões incluem Question em snapshot, taxonomia, modo, rodadas escolhidas,
ModelSpecs e todos os hashes de prompt registrados. Os Decimals são serializados
como strings para preservar precisão; as colunas auxiliares no banco usam seis
casas, sem alterar os valores do JSON. O relatório é único por Run e imutável.

O endpoint autenticado aceita:

```text
GET /api/runs/{id}/report
GET /api/runs/{id}/report?format=markdown
```

Retorna `409` antes de `done`, inclusive se o relatório foi salvo mas a task ainda
não concluiu a transição. Run inexistente ou interno (`rubric_check`, `ab_test`)
retorna `404`. JSON e Markdown usam `Cache-Control: private, no-store`; Markdown
é baixado como arquivo, com texto do manuscrito e do modelo escapado. O admin
expõe rodadas, vereditos e relatório apenas para leitura. A saída em PDF continua
fora do escopo desta etapa, que exige render Markdown.

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
