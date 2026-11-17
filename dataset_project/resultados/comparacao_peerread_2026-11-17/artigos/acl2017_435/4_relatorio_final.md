# Neural Disambiguation of Causal Lexical Markers based on Context

Run: `01a1e77d-b1b9-75a5-b69b-44a040d42563`

Recomendação: **minor**
Nota ponderada: **3.12** · Concordância: **0.88**

Revisão humana sinalizada: sim

## Critérios

### Originalidade

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 2): O texto afirma contribuir com uma arquitetura/modelo para disambiguation de causalidade, mas a novidade em relação ao estado da arte não é sustentada com comparação direta verificável com métodos anteriores no trecho fornecido\. As passagens descrevem propostas e argumentos gerais \(“we contribute…”, “therefore, we propose…”, “in contrast…”\), porém não explicam com evidência como a arquitetura/representação difere especificamente dos trabalhos citados, nem fornecem um contraste demonstrável do que é novo\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Solidez

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `unresolved`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Substância

Nota: 3.50 · Dispersão: 1.00 · Votos válidos: 2

- B (rodada 3, nota 4): O artigo apresenta substância considerável, com um design experimental sólido que inclui a definição clara do estado da arte, a justificativa para as linhas de base e a abordagem do desequilíbrio de classes através de um dataset reduzido e balanceado\. Há estudos de ablação detalhados que comparam diferentes escolhas arquitetônicas, otimizadores e estratégias\. As alegações de melhoria são fortalecidas pelo uso de testes estatísticos apropriados, como o teste de McNemar, e a discussão sobre as tendências de desempenho da rede demonstra robustez\. A interpretação das métricas de Precision e Recall é perspicaz\. Contudo, falta uma análise estatística mais profunda dos resultados, como a variância das métricas de desempenho, o que é uma lacuna notável na seção de experimentos e resultados\.
- C (rodada 3, nota 3): O artigo apresenta resultados empíricos com métricas \(Precision/Recall/F1 e Accuracy\), ganho numérico em relação ao baseline e testes estatísticos \(McNemar\) além de ajustes para desbalanceamento\. Porém, existem lacunas de substância evidencial no trecho: algumas afirmações dependem de tabelas/figuras citadas sem os números/observações no texto fornecido, e certas interpretações sobre comportamento/causas \(ex\.: relação entre desempenho e suposições do modelo\) aparecem mais como inferências do que como análises totalmente suportadas pelos detalhes apresentados aqui\.
- Voto excluído de A: `unresolved`

### Clareza

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `unresolved`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Comparação

Nota: 3.00 · Dispersão: 0.00 · Votos válidos: 2

- A (rodada 3, nota 3): A revisão cobre trabalhos relevantes e identifica diferenças metodológicas, incluindo a comparação entre CNN e LSTM; os experimentos também incluem um baseline majoritário e o sistema de Hidey e McKeown\. Contudo, as comparações com trabalhos próximos são predominantemente qualitativas, não padronizam corpus, tarefa e métricas, e não abrangem suficientemente outras arquiteturas neurais e modelos de classificação causal\.
- C (rodada 3, nota 3): Há comparação com trabalhos relevantes e alternativas, com menção a limitações \(ambiguidade linguística/projeção de causality; engenharia de features e cobertura restrita; justificativa de mudar a codificação para desambiguar via contexto\)\. Também existe comparação explícita entre CNN com conhecimento de fundo e a alternativa LSTM, conectando limitações percebidas às decisões de arquitetura\. Entretanto, parte das comparações não fica totalmente equivalente/detalhada: em trabalhos próximos, a diferença do que a proposta neural muda concretamente \(representação/uso de contexto/desambiguação\) não é totalmente esclarecida; na comparação CNN vs LSTM, as hipóteses incompatíveis e a transposição da evidência de capacidade/desempenho para o cenário específico do método não são totalmente demonstradas; além disso, há indicação de falta de discussão de outras alternativas além de CNN/LSTM no trecho fornecido\.
- Voto excluído de B: `evidence_not_validated`

### Impacto

Nota: 4.00 · Dispersão: indisponível · Votos válidos: 1

- B (rodada 3, nota 4): O artigo articula claramente o impacto potencial de sua contribuição, abordando a necessidade de desambiguação de causalidade em cenários com &\#x27;Alternative Lexicalizations&\#x27; e sem construções fixas\. Os resultados empíricos apresentados validam as alegações dos autores sobre a eficácia do sistema proposto, demonstrando que ele supera o estado da arte e lida com cenários desafiadores, o que indica uma relevância demonstrada para a área\. Além disso, a seção de conclusões apresenta um plano de trabalho futuro bem definido, focado na criação de novos recursos para a tarefa, o que aborda uma lacuna reconhecida no campo e aponta para um impacto futuro significativo e não especulativo\.
- Voto excluído de A: `unresolved`
- Voto excluído de C: `evidence_not_validated`

### Reprodutibilidade

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `unresolved`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

## Pontos fortes

- O desenho experimental é substancial: inclui baselines claros, estudos de ablação sobre arquitetura, otimizadores e padding, tratamento do desbalanceamento de classes e teste de McNemar para apoiar as comparações de desempenho\. [b:observation:sec\_10:results:1:obs\_1\_baselines, b:observation:sec\_10:results:1:obs\_2\_ablations, b:observation:sec\_10:results:1:obs\_3\_statistics, b:observation:sec\_10:results:1:obs\_7\_data\_balancing]
- A contribuição é apresentada como relevante para a desambiguação de causalidade em contextos ambíguos, e a conclusão articula resultados, cenários desafiadores e uma agenda futura voltada à criação de novos recursos para a tarefa\. [b:observation:sec\_2:introduction:1:impact\_claim\_1, b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_01, b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_02]
- A revisão de literatura cobre abordagens relevantes e explicita uma diferença metodológica entre CNN e LSTM, relacionando a escolha da arquitetura à necessidade de representar contexto e informação sequencial\. [a:observation:sec\_3:related\_work:1:sec\_3\_obs\_1, a:observation:sec\_7:related\_work:1:sec\_7\_obs\_1, a:observation:sec\_7:related\_work:1:sec\_7\_obs\_2, c:observation:sec\_3:related\_work:1:obs\_2]

## Pontos fracos

- A novidade da arquitetura e da codificação neural de contexto não é delimitada por um contraste verificável com os trabalhos citados; permanece pouco claro se a originalidade está na arquitetura, na representação, na tarefa, no corpus ou na combinação desses elementos\. [c:observation:sec\_2:introduction:1:obs\_3, c:observation:sec\_3:related\_work:1:obs\_4, a:observation:sec\_3:related\_work:1:sec\_3\_obs\_5]
- As comparações com trabalhos próximos são predominantemente qualitativas e não estabelecem condições equivalentes de corpus, tarefa, tipo de relação e métricas; além disso, a discussão não abrange suficientemente outras arquiteturas e modelos de classificação causal\. [a:observation:sec\_3:related\_work:1:sec\_3\_obs\_3, a:observation:sec\_7:related\_work:1:sec\_7\_obs\_4, c:observation:sec\_7:related\_work:1:obs\_2, c:observation:sec\_7:related\_work:1:obs\_3, c:observation:sec\_7:related\_work:1:obs\_4]
- A análise dos resultados não reporta variância das métricas e algumas interpretações dependem de tabelas, figuras ou inferências causais sem os valores quantitativos correspondentes explicitados no texto\. [b:observation:sec\_8:results:1:obs\_8\_2, c:observation:sec\_10:results:1:sec\_10\_obs\_5, c:observation:sec\_10:results:1:sec\_10\_obs\_8]

## Sugestões

- Delimitar explicitamente a novidade em uma comparação estruturada com cada trabalho mais próximo, especificando diferenças de arquitetura, representação do contexto, uso dos dois eventos, tarefa e corpus\. [c:observation:sec\_2:introduction:1:obs\_3, c:observation:sec\_3:related\_work:1:obs\_3, c:observation:sec\_3:related\_work:1:obs\_4, a:observation:sec\_3:related\_work:1:sec\_3\_obs\_5]
- Ampliar a avaliação comparativa com alternativas neurais adicionais e, quando possível, padronizar corpus, definição da tarefa, métricas e condições experimentais para tornar as conclusões sobre superioridade mais verificáveis\. [a:observation:sec\_3:related\_work:1:sec\_3\_obs\_3, a:observation:sec\_7:related\_work:1:sec\_7\_obs\_4, c:observation:sec\_7:related\_work:1:obs\_2, c:observation:sec\_7:related\_work:1:obs\_3, c:observation:sec\_7:related\_work:1:obs\_4]
- Complementar os resultados com variância ou intervalos de confiança obtidos em repetições, explicitar os valores das tabelas e figuras relevantes e distinguir claramente hipóteses interpretativas de conclusões diretamente demonstradas pelos experimentos\. [b:observation:sec\_8:results:1:obs\_8\_2, c:observation:sec\_10:results:1:sec\_10\_obs\_5, c:observation:sec\_10:results:1:sec\_10\_obs\_8]

## Seções

### 1 Introduction

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1 [unresolved]: A introdução explicita um problema relevante: a cobertura limitada de expressões causais por recursos e abordagens baseados em listas lexicais ou construções sintáticas fixas\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2 [unresolved]: A contribuição principal é declarada de forma direta: propor uma arquitetura de rede neural para desambiguar a causalidade e avaliá\-la no corpus de Hidey e McKeown \(2016\)\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3 [unresolved]: A originalidade da arquitetura não é suficientemente diferenciada em relação ao estado da arte na introdução: o texto afirma a contribuição, mas não informa quais componentes, mecanismo ou hipótese arquitetural são novos em comparação com Hidey e McKeown \(2016\) e outros trabalhos anteriores\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_4: O impacto é apresentado de modo plausível, mas ainda pouco sustentado: a introdução relaciona o método à necessidade de ampliar a cobertura de expressões causais, porém não explicita o alcance prático ou científico esperado além da tarefa e do corpus avaliados\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5 [unresolved]: Há uma inconsistência terminológica que reduz a clareza da formulação do objetivo: a introdução alterna entre “causal meaning disambiguation”, “causality disambiguation” e formulações de “classify causality”/“classification method” sem explicar se esses termos designam a mesma tarefa ou tarefas distintas\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6: A alegação empírica final é excessivamente vaga para sustentar a contribuição: não são apresentados na introdução os resultados quantitativos, a configuração comparada ou a magnitude da melhoria sobre o estado da arte\.
- b:observation:sec\_2:introduction:1:problem\_clarity\_1 [unresolved]: O problema de pesquisa é explicitamente articulado e sustentado através da identificação das limitações das abordagens linguísticas e computacionais existentes para capturar a totalidade da expressão causal, especialmente em cenários com &\#x27;Alternative Lexicalizations&\#x27; e a ausência de construções lexicais ou sintáticas fixas para a causalidade\.
- b:observation:sec\_2:introduction:1:contribution\_originality\_1 [unresolved]: As contribuições do artigo são claramente apresentadas como uma nova arquitetura de rede neural para a desambiguação da causalidade, baseada na hipótese de que redes neurais podem codificar o significado de eventos para descobrir relações causais subjacentes\. Isso se diferencia das limitações das abordagens anteriores discutidas\.
- b:observation:sec\_2:introduction:1:impact\_claim\_1: O impacto potencial da contribuição é afirmado de forma explícita, indicando que os resultados empíricos validarão a afirmação dos autores sobre a eficácia da abordagem proposta para a desambiguação da causalidade, endereçando uma necessidade clara na área\.
- c:observation:sec\_2:introduction:1:obs\_1: O problema é contextualizado com base em lacunas/limitações da modelagem linguística e da cobertura de recursos para relações causais \(especialmente AltLex versus PDTB\)\.
- c:observation:sec\_2:introduction:1:obs\_2: A motivação do método é explicitada como hipótese sobre o papel da codificação do sentido na desambiguação causal\.
- c:observation:sec\_2:introduction:1:obs\_3: A alegação de novidade/contribuição em relação ao estado da arte não é sustentada no texto do trecho fornecido \(não há comparação direta com métodos anteriores nem descrição do que diferencia a arquitetura proposta\)\.
- c:observation:sec\_2:introduction:1:obs\_4: O impacto é declarado de forma genérica \(“outperform” no resumo do documento\), mas no corpo do trecho fornecido a evidência quantitativa de superioridade não aparece\.
- c:observation:sec\_2:introduction:1:obs\_5: Há alguma inconsistência/ambiguidade na caracterização do que “causality” representa: primeiro é tratada como relação de discurso \(PDTB\) e depois como tarefa de “causality disambiguation” entre dois eventos; a ponte entre essas unidades não é formulada explicitamente no trecho\.

### 2 Related Work

- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_1: A seção cobre uma sequência relevante de trabalhos, desde sistemas baseados em regras e construções sintáticas específicas até abordagens que incorporam informação contextual, distribuição lexical e relações temporais\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_2: A diferença central da proposta é explicitada de forma relativamente clara: em vez de limitar a representação a padrões sintáticos ou recursos semânticos, o trabalho propõe codificar o contexto para desambiguar o significado causal\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_3: A comparação com os trabalhos mais próximos é majoritariamente qualitativa e não informa, para cada abordagem, condições diretamente comparáveis como corpus, definição da tarefa, tipo de relação causal e métricas; isso dificulta estabelecer precisamente em que sentido a proposta supera ou amplia cada alternativa\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_4: A síntese final generaliza excessivamente o estado da arte ao afirmar que os trabalhos anteriores definem a causalidade por construções sintáticas específicas ou verbos causativos, embora a própria revisão também descreva abordagens que usam coocorrência entre predicados e argumentos, semântica distribucional e relações temporais\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_5: A alegação de novidade da codificação neural do contexto é plausível, mas não é delimitada contra alternativas neurais ou abordagens de representação contextual mais recentes; a seção não estabelece claramente se a originalidade está na arquitetura, na tarefa, no corpus ou na combinação desses elementos\.
- b:observation:sec\_3:related\_work:1:obs1 [unresolved]: The related work section provides a comprehensive overview of previous approaches to causality classification, starting from early rule\-based systems to more recent contextual and knowledge\-base approaches\.
- b:observation:sec\_3:related\_work:1:obs2: The section effectively highlights the limitations and drawbacks of previous works, such as ambiguity, restricted flexibility, reliance on specific features, and complex engineering, which clearly motivates the necessity for a new approach\.
- b:observation:sec\_3:related\_work:1:obs3: The unique contribution of the current proposal, which is the neural encoding of context to disambiguate causal meaning, is clearly differentiated from prior works that relied on syntactic patterns or semantic resources\.
- c:observation:sec\_3:related\_work:1:obs\_1: A seção compara múltiplas abordagens anteriores para classificação de relações causais e explicita limitações recorrentes \(ex\.: ambiguidade linguística e projeção de causality\)\.
- c:observation:sec\_3:related\_work:1:obs\_2: A comparação com métodos que usam engenharia de características e/ou recursos linguísticos \(WordNet, features léxicas/sintáticas/semânticas\) está explícita, preparando a justificativa para a proposta neural baseada em contexto\.
- c:observation:sec\_3:related\_work:1:obs\_3: A diferença da proposta em relação a trabalhos próximos \(Do et al\. 2011; Riaz e Girju 2013/2014\) não fica totalmente clara: o texto indica que eles “ainda dependem de features léxicas e sintáticas”, mas não detalha o que exatamente a proposta neural muda em termos de representação, uso de contexto e desambiguação \(além da motivação geral\)\.
- c:observation:sec\_3:related\_work:1:obs\_4: A alegação de originalidade \(“we propose\.\.\.”\) é apresentada sem explicitar evidência no texto de que a novidade é distinta do estado da arte nos itens citados; o texto lista ideias gerais, mas não amarra “novidade” a um contraste verificável \(por exemplo, em como o modelo difere arquiteturalmente ou de representação vs\. métodos citados\)\.
- c:observation:sec\_3:related\_work:1:obs\_5: O texto identifica limitações associadas a cobertura/recorte de construções sintáticas e a dependência de padrões linguísticos, alinhando com o racional de desambiguação por representação de contexto\.

### 3 Causality classification

- a:observation:sec\_4:method:1:sec\_4\_obs\_1 [unresolved]: A seção organiza claramente a apresentação metodológica ao indicar, em sequência, a definição da tarefa, os dados e o sistema proposto\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2 [unresolved]: A introdução da seção não explicita as hipóteses operacionais, o protocolo de avaliação nem a relação entre a definição da tarefa, os dados e o sistema; esses elementos precisam estar descritos nas subseções para permitir avaliar a solidez e reproduzir o método\.
- b:observation:sec\_4:method:1:replicability\_sec4\_missing\_details [unresolved]: Details regarding the data used in experiments and the proposed system, which are crucial for replicating the method, are explicitly deferred to subsequent subsections \(3\.2 and 3\.3\) and are not present in this introductory section\.
- b:observation:sec\_4:method:1:soundness\_sec4\_missing\_elements: A seção introduz claramente os tópicos a serem abordados nas subseções seguintes \(3\.1, 3\.2 e 3\.3\), fornecendo uma excelente estrutura organizacional para o capítulo do método\.
- b:observation:sec\_4:method:1:clarity\_sec4\_organizational\_strength: The introductory sentence clearly outlines the structure and content of the subsequent subsections \(3\.1, 3\.2, 3\.3\), providing a clear roadmap for the method section\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_1 [unresolved]: A seção começa com uma frase de orientação \(“The next sections expose\.\.\.”\), mas não apresenta \(ainda\) definição operacional do método, hipóteses ou como a “proposed system” será implementada\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_2 [unresolved]: Há quebra de linha/hifenização no texto \(“Sec\-tion 3\.2”\), o que pode afetar a clareza/legibilidade local, embora não mude o sentido científico do conteúdo\.

### 3\.1 Definition


### 3\.2 Data

- a:observation:sec\_6:method:1:sec\_6\_obs\_1: A seção justifica adequadamente a necessidade de anotar simultaneamente os eventos, o marcador lexical e o sentido da relação, distinguindo marcadores causais inequívocos de expressões dependentes do contexto\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_2: A comparação entre os três corpora explicita diferenças relevantes para a escolha dos dados, incluindo disponibilidade, tamanho, anotação de relações explícitas e cobertura de expressões alternativas\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_3 [unresolved]: A descrição não fornece, neste trecho, detalhes suficientes para reproduzir a construção e a preparação do conjunto de dados: faltam os valores da Tabela 3, a definição operacional dos conjuntos de treino e teste, os critérios exatos de alinhamento entre Wikipedia e Simple Wikipedia, o procedimento de bootstrap, o tratamento de duplicatas e a composição final das instâncias\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_4 [unresolved]: As estatísticas de distribuição são discutidas sem apresentar os denominadores nem os valores completos no texto, o que dificulta avaliar o desequilíbrio entre classes, a prevalência de marcadores ambíguos e a comparabilidade entre as versões do corpus\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_5 [unresolved]: A inferência de que diferenças na distribuição entre treino e teste representam maior dificuldade para o sistema não é demonstrada apenas pela descrição do corpus; seria necessário definir a métrica de diferença e relacioná\-la a resultados ou análises controladas\.
- b:observation:sec\_6:method:1:sec\_6\_obs\_1 [unresolved]: The description of the AltLex corpus construction method, specifically the alignment and bootstrapping processes, lacks sufficient detail regarding specific algorithms, parameters, or heuristics used, requiring reference to an external publication for full replicability\.
- b:observation:sec\_6:method:1:sec\_6\_obs\_2 [unresolved]: The paper transparently identifies a potential challenge with the &\#x27;bootstrapping&\#x27; version of the AltLex corpus, noting that its class distribution differs between training and test sets, implying a higher difficulty for the classification system\.
- b:observation:sec\_6:method:1:sec\_6\_obs\_3: The article provides clear justifications for selecting or rejecting corpora based on crucial factors like availability, size, and annotation schema, thereby establishing a sound basis for data choice\.
- b:observation:sec\_6:method:1:sec\_6\_obs\_4: The AltLex corpus, which is the primary dataset used for experiments, is explicitly stated to be &\#x27;freely released&\#x27;, significantly aiding the replicability of the work\.
- b:observation:sec\_6:method:1:sec\_6\_obs\_5: Key characteristics of the AltLex corpus, such as its size and the class distribution of lexical markers, are clearly referenced in tables \(Table 3 and Table 4\), providing essential information for understanding the dataset and reproducing experiments\.
- c:observation:sec\_6:method:1:obs\_6\_1: O texto fundamenta a necessidade de dados anotados especificando a ambiguidade do marcador causal e a dependência do contexto, justificando a exigência de corpus com eventos, marcador lexical e significado da relação\.
- c:observation:sec\_6:method:1:obs\_6\_2: Ao comparar corpora existentes, o texto indica limitações \(acesso e tamanho\) mas não quantifica o tamanho nem explicita critérios objetivos para dizer que “não é grande o suficiente” para métodos neurais, o que reduz a replicabilidade/justificativa operacional\.
- c:observation:sec\_6:method:1:obs\_6\_3 [unresolved]: Há problemas de redação/gramática \(quebras de palavras e fragmentações\) que podem prejudicar a clareza, sem afetar diretamente a metodologia, mas tornando o texto menos verificável localmente\.
- c:observation:sec\_6:method:1:obs\_6\_4 [unresolved]: A descrição do processo de construção do AltLex \(alinhamento e bootstrap\) é dada em alto nível; faltam detalhes operacionais suficientes \(ex\.: critérios/limiares de alinhamento, regras para rotular causal vs não\-causal\) para reproduzir o método de construção do corpus\.
- c:observation:sec\_6:method:1:obs\_6\_5: A seção afirma resultados de análise \(dificuldade por desvio de distribuição e que a Seção 4\.3 mostra desempenho\), mas não fornece nesta seção os números/contextos necessários; isso torna a evidência dependente de outras seções/tabelas\.

### 3\.3 Disambiguation of the Causal Meaning

- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_1: O trabalho mais próximo é identificado explicitamente: Kruengkrai et al\. \(2017\) são apresentados como referência para a identificação do significado causal, e a comparação considera uma diferença metodológica relevante entre CNN e LSTM\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_2: A diferença proposta em relação ao trabalho baseado em CNN é relativamente clara: o artigo substitui a CNN por LSTM para representar a informação sequencial e considera que isso pode capturar melhor o significado causal, inclusive quando a causalidade não possui uma estrutura sintática fixa\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_3: A justificativa de originalidade é limitada, pois a contribuição é formulada principalmente como a substituição de CNN por LSTM; o trecho não esclarece se a arquitetura com dois eventos, nem as variantes conectada e não conectada, diferem de arquiteturas LSTM já existentes para tarefas semelhantes\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_4: Falta uma comparação mais ampla com alternativas próximas: além de Kruengkrai et al\. e do uso geral de LSTM citado por Melamud et al\., o trecho não posiciona a arquitetura proposta frente a outros modelos de classificação causal ou a outras arquiteturas neurais de codificação conjunta de dois eventos\.
- b:observation:sec\_7:related\_work:1:obs1\_sec7\_meaningful\_comparison: O artigo compara seu trabalho com uma abordagem existente que utiliza CNNs para a identificação de significado causal, destacando as limitações do método anterior e as vantagens da proposta de LSTM\.
- b:observation:sec\_7:related\_work:1:obs2\_sec7\_originality: A proposta introduz o uso de LSTM RNNs para a classificação de causalidade, explicitamente diferenciando\-a das abordagens baseadas em CNN e justificando essa escolha pela maior capacidade de codificação de significado do LSTM para a tarefa\.
- b:observation:sec\_7:related\_work:1:obs3\_sec7\_clarity: A diferença da proposta em relação aos trabalhos anteriores é claramente explicada, detalhando as desvantagens das CNNs para a tarefa de causalidade e apresentando os motivos para a adoção de LSTMs, bem como as características iniciais da arquitetura proposta\.
- c:observation:sec\_7:related\_work:1:obs\_1: A seção compara de forma explícita um trabalho anterior \(CNN com conhecimento de fundo\) com a alternativa proposta \(LSTM\), conectando as limitações percebidas de cada abordagem à justificativa da mudança de arquitetura\.
- c:observation:sec\_7:related\_work:1:obs\_2: A comparação com a CNN de Kruengkrai et al\. é feita principalmente por alegações gerais \(estrutura sintática da causação e escolha de kernel size\), sem detalhar quais hipóteses/condições da CNN são incompatíveis com o seu problema, o que deixa a comparação menos equivalente\.
- c:observation:sec\_7:related\_work:1:obs\_3: A justificativa de por que LSTM é superior apoia\-se em uma afirmação de capacidade \(“higher capacity”\) e em evidência citada de desempenho de LSTM vs média de embeddings, mas não fica claro como essa evidência \(Melamud et al\., 2016\) se traduz especificamente para a tarefa de classificação de causalidade e para o cenário do seu método \(dois eventos \+ marcador lexical \+ comparação entre duas entradas\)\.
- c:observation:sec\_7:related\_work:1:obs\_4: Não há discussão \(neste trecho\) de alternativas além de CNN e LSTM \(por exemplo, outros tipos de encoders/relacionadores\), o que pode reduzir a completude da comparação do estado da arte conforme a rubrica\.
- c:observation:sec\_7:related\_work:1:obs\_5: A proposta de arquitetura é apresentada com alguma clareza e com uma diferenciação direta entre as duas configurações avaliadas \(com e sem conexão entre as LSTMs\), o que ajuda a entender a “diferença da proposta” em relação à base conceitual\.

### 4 Experiments and Results

- a:observation:sec\_8:method:1:sec\_8\_obs\_1: O escopo experimental é explicitado: os métodos são avaliados no corpus AltLex e são consideradas as duas versões do corpus, “non bootstrapping” e “bootstrapping”\. Isso facilita a delimitação do experimento\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_2: A avaliação em um único corpus limita a sustentação de conclusões sobre desempenho geral na classificação de causalidade\. O próprio texto justifica essa escolha pela ausência de corpus representativo, mas não apresenta, neste trecho, uma discussão explícita sobre a validade externa dos resultados\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_3: O trecho não informa o número de instâncias de cada versão do corpus; apenas remete à Table 3\. Para reproduzir a seleção dos dados, é necessário que a tabela esteja disponível e que os números sejam associados inequivocamente a cada versão\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_4: A afirmação de que o método de Hidey e McKeown \(2016\) é o estado da arte no corpus AltLex é qualificada por “As far as we know”, mas o trecho não explicita um procedimento de busca ou critérios de comparação que sustentem essa caracterização\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_1: A afirmação de que o método de Hidey e McKeown \(2016\) é o estado da arte no AltLex é justificada apenas pelo fato de o corpus ter sido usado anteriormente somente nesse trabalho; isso não demonstra superioridade empírica nem compara métricas com métodos alternativos\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_2: A avaliação está restrita ao AltLex, o que limita a sustentação de conclusões gerais sobre classificação de causalidade, especialmente porque o próprio texto caracteriza a tarefa como carente de corpora representativos e abrangentes\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_3 [unresolved]: O desenho experimental explicita que foram usadas as duas versões disponíveis do corpus, reduzindo a ambiguidade sobre a fonte dos dados e permitindo a comparação entre as variantes\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_4: O trecho remete ao tamanho das versões do corpus na Tabela 3, mas não informa aqui os números, a distribuição entre classes nem se as duas versões diferem em composição além do bootstrapping; esses detalhes são necessários para avaliar a escala e possíveis efeitos de balanceamento\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_5: A motivação para usar o AltLex é plausível, mas o texto não explicita quais limitações de cobertura do corpus permanecem nem como a escolha de apenas esse conjunto afeta a interpretação dos resultados; a discussão deveria separar desempenho no AltLex de validade externa\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_1: Although the AltLex corpus and its two versions \(&quot;non bootstrapping&quot; and &quot;bootstrapping&quot;\) are identified as data sources, the text lacks specific details regarding data splitting \(e\.g\., train, validation, test sets\), preprocessing steps, or the precise methodology for how each version was utilized in the experiments\. This omission impedes the full reproducibility of the experimental setup\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_2: The authors provide a clear and explicit justification for selecting the AltLex corpus for evaluation, based on its previous exclusive use, which also establishes the method by Hidey and McKeown \(2016\) as the state\-of\-the\-art on this specific dataset\. This transparency enhances the clarity and soundness of the experimental design\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_3: The paper explicitly acknowledges a significant limitation within the field of causality classification, noting the general lack of a &quot;representative or large enough corpus that covers a wide range of causal expressions&quot; without specific construction restrictions\. This critical awareness of data constraints strengthens the soundness of the chosen evaluation scope\.
- b:observation:sec\_8:results:1:obs\_8\_1: O artigo define claramente o estado da arte para o corpus AltLex, justificando a escolha do método de Hidey e McKeown \(2016\) como linha de base devido ao uso limitado do corpus\. Além disso, a justificação para a avaliação exclusiva com este corpus, citando a escassez de corpora representativos na tarefa de classificação de causalidade, demonstra um reconhecimento transparente das limitações do campo\.
- b:observation:sec\_8:results:1:obs\_8\_2: Apesar de mencionar o tamanho do corpus e apresentar um teste de significância de McNemar, a seção carece de detalhes sobre outras análises estatísticas mais profundas dos resultados, como a variância das métricas de desempenho, conforme esperado em uma seção de experimentos e resultados\.
- c:observation:sec\_8:method:1:obs\_sec\_8\_1: O texto afirma que o AltLex corpus foi &quot;only used in the work in which it was presented&quot; e, com base nisso, considera\-se o método citado como &quot;state of the art&quot; para o corpus\.
- c:observation:sec\_8:method:1:obs\_sec\_8\_2: A justificativa para avaliar apenas no AltLex baseia\-se na alegação de que a tarefa carece de corpus representativo/adequado, mas não apresenta detalhes operacionais \(por exemplo, métricas, critérios de cobertura, ou referências a corpora/estudos\) dentro do trecho para sustentar essa limitação\.
- c:observation:sec\_8:method:1:obs\_sec\_8\_3 [unresolved]: O texto especifica que foram usadas duas versões do corpus \(com e sem bootstrapping\) e aponta que o tamanho de cada uma é apresentado em uma tabela\.
- c:observation:sec\_8:method:1:obs\_sec\_8\_4: Embora o trecho mencione que os tamanhos estão na Tabela 3, ele não fornece quaisquer números ou descrições do protocolo de uso das versões do corpus \(ex\.: como o bootstrapping afeta splits/iteração\), o que limita a reprodutibilidade a partir deste trecho apenas\.
- c:observation:sec\_8:results:1:obs\_sec\_8\_1: Há uma justificativa explícita do recorte experimental: “therefore we consider their method as the state of the art on that corpus” e, em seguida, que “Therefore, the methods were only evaluated with the AltLex corpus\.”
- c:observation:sec\_8:results:1:obs\_sec\_8\_2: A afirmação “As far as we know” e a inferência de “state of the art” ficam pouco sustentadas no próprio trecho, pois não apresentam evidência direta \(por exemplo, busca/estatística\) para apoiar a exclusividade do uso do AltLex “only used in the work in which it was presented”\.
- c:observation:sec\_8:results:1:obs\_sec\_8\_3: Há uma justificativa baseada em limitação de dados \(“lacks of representative or large enough corpus\.\.\. without the restriction\.\.\. specific causal constructions”\), mas o texto não explicita qual parte disso é verificada/quantificada, nem conecta de modo verificável a conclusão com o desenho experimental no trecho \(o que foi feito, como e por que isso resolve a limitação\)\.
- c:observation:sec\_8:results:1:obs\_sec\_8\_4 [unresolved]: O trecho diz que “The size of each of them is shown in Table 3”, mas não fornece aqui os valores numéricos/estatísticas; sem esses números no texto, a sustentação imediata \(tamanho e comparação entre versões\) fica dependente de uma tabela não incluída no trecho\.

### 4\.1 Baselines

- a:observation:sec\_9:method:1:sec\_9\_obs\_1: A seção define claramente dois baselines com funções comparativas distintas: B1 representa uma estratégia baseada na classe mais frequente por marcador, enquanto B2 corresponde ao sistema previamente publicado de Hidey e McKeown \(2016\)\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_2 [unresolved]: A descrição de B1 não especifica como são tratados empates entre classes, marcadores ausentes no treinamento, nem a unidade exata usada para estimar a classe majoritária\. Também não informa explicitamente se a contagem é calculada apenas no conjunto de treinamento de cada partição experimental, informação necessária para evitar ambiguidade e possível vazamento de dados\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A descrição de B2 é insuficiente para reproduzir o baseline: não informa a implementação utilizada, a configuração do SVM, os hiperparâmetros, o procedimento de seleção ou combinação das características, nem como os recursos lexicais foram consultados e pré\-processados\. A referência ao trabalho original identifica a origem do sistema, mas não garante que a mesma versão e configuração tenham sido usadas nos experimentos atuais\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_4 [unresolved]: A afirmação de que a arquitetura proposta tem maior capacidade de generalização do que B2 é apresentada como consequência da dependência de recursos lexicais, mas a seção não explicita uma hipótese operacional ou uma comparação controlada que permita atribuir eventual vantagem exclusivamente a essa diferença\.
- b:observation:sec\_9:method:1:obs\_baselines\_1: The description of Baseline 1 \(B1\) lacks explicit details regarding the specific training data used to determine the most common class of causal connectives and how potential ties in frequency are handled\. This omission affects its precise replicability\.
- b:observation:sec\_9:method:1:obs\_baselines\_2: The description of Baseline 2 \(B2\), which refers to an external system, does not provide sufficient technical details about the SVM implementation \(e\.g\., specific kernel, hyperparameters\) or the precise &\#x27;large set of features&\#x27; generated from the &\#x27;original parallel corpus&\#x27; and lexical resources\. This lack of detail hinders the full replicability of this baseline without consulting the referenced paper and potentially its implementation\.
- c:observation:sec\_9:method:1:obs\_9\_1: O baseline B1 é descrito de forma operacional ao definir que, para cada marcador causal, a classe é atribuída como a mais frequente na base de treino \(ex\.: “since” → Causal\)\.
- c:observation:sec\_9:method:1:obs\_9\_2: A descrição de B1 não informa como lidar com empates, conectivos raros/ausentes no treino, nem se a decisão é feita por marcador \(token\) exato ou por forma normalizada \(o que afeta a reprodutibilidade\)\.
- c:observation:sec\_9:method:1:obs\_9\_3: Para o baseline B2, não há parâmetros mínimos para reprodução \(ex\.: configuração do SVM, seleção exata do conjunto de features e detalhes de como as features são geradas/concatenadas\), além de apenas referenciar Hidey and McKeown \(2016\)\.
- c:observation:sec\_9:method:1:obs\_9\_4: A justificativa sobre limitações de B2 \(“restricts the recall\.\.\.”\) não é acompanhada por evidência quantitativa ou dados de avaliação na própria seção, tornando a alegação pouco sustentada dentro do texto fornecido\.
- c:observation:sec\_9:method:1:obs\_9\_5: A comparação para a proposta é feita por uma promessa \(“higher ability of generalization”\) sem especificar que tipo de generalização foi medida \(em que cenário e com quais métricas\) — ainda que remeta “como mostrado depois no artigo”\.

### 4\.2 Results

- a:observation:sec\_10:results:1:sec\_10\_obs\_1: A seção define explicitamente quais métricas avaliam a classe Causal e o desempenho global, distinguindo Precision, Recall e F1 de Accuracy\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_2: A comparação inclui dois baselines, diferentes arquiteturas, otimizadores, estratégias de zero\-padding e duas versões do corpus, além de uma análise adicional com distribuição de classes mais equilibrada\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_3: A seção reporta um teste estatístico explícito para a comparação na versão reduzida do corpus, em vez de apresentar apenas diferenças descritivas entre métricas\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_4 [unresolved]: Há uma inconsistência na identificação da melhor configuração: primeiro “Pair\_LSTM\_Max\_Adadelta” é descrita como a melhor, mas depois “Pair\_LSTM\_Mean\_Adam” é apresentada como a configuração de maior desempenho\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_5: As afirmações sobre superioridade são difíceis de verificar a partir do trecho, pois os valores numéricos das configurações e dos baselines não são reproduzidos; são fornecidos apenas alguns ganhos percentuais e referências às tabelas\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_6: Na seção de resultados fornecida, são reportadas métricas agregadas, diferenças percentuais e testes de significância, mas não são informadas variâncias, intervalos de confiança, número de sementes ou repetições dos treinamentos\. Assim, com base apenas nessa seção, não é possível avaliar a estabilidade das diferenças entre arquiteturas, otimizadores e estratégias de padding\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_7: As conclusões sobre o efeito de arquitetura e otimizador são apresentadas de forma causal ou geral, mas a seção não informa testes estatísticos para essas comparações nem controla possíveis diferenças de treinamento entre configurações\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_8: A interpretação de que maior Precision e menor Recall indicam principalmente conectivos não ambíguos é plausível, mas não é demonstrada de modo suficiente: a distribuição dos conectivos não estabelece, por si só, que esse seja o mecanismo responsável pelo desempenho\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_9: A avaliação com o corpus reduzido altera a distribuição dos dados por subamostragem da classe Non Causal, mas não são informados o procedimento de amostragem, sua aleatoriedade, a preservação dos mesmos splits ou resultados para múltiplas amostras\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_10: O uso de McNemar é uma evidência útil para previsões pareadas, mas a seção não informa a tabela de contingência, o tamanho efetivo da amostra, se o teste foi unilateral ou bilateral, nem como foi tratada a multiplicidade; além disso, P=0\.05 é limítrofe\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_11: A afirmação de que o sistema supera o estado da arte depende da comparação com B2, mas o trecho não explicita se os ganhos de 2\.13% e 7\.72% são absolutos ou relativos, nem apresenta incerteza ou significância para essa comparação\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_12: A apresentação alterna entre identificar a melhor configuração por F1, por Accuracy, por Precision e por equilíbrio entre Precision e Recall, sem declarar previamente uma métrica principal; isso torna a seleção do modelo e a conclusão sobre “highest performance” ambíguas\.
- a:observation:sec\_10:results:1:sec\_10\_obs\_13: A referência inicial a “Table 5\.1” não corresponde ao rótulo de tabela fornecido no mapa documental, que identifica os resultados como Table 5; isso pode dificultar a localização da evidência\.
- b:observation:sec\_10:results:1:obs\_1\_baselines: The paper effectively uses baselines B1 and B2 to benchmark the proposed system configurations, providing a clear reference for performance evaluation\.
- b:observation:sec\_10:results:1:obs\_2\_ablations: The results section presents detailed ablation studies, comparing different architectural choices \(e\.g\., &\#x27;Pair\_LSTM&\#x27; vs &\#x27;Stated\_LSTM&\#x27;\), optimizers \(Adadelta vs Adam\), and zero\-padding strategies \(maximum vs mean\)\. This systematic comparison aids in understanding the contribution of individual components to the overall system performance\.
- b:observation:sec\_10:results:1:obs\_3\_statistics: The paper strengthens its claims of significant improvement by using appropriate statistical tests, specifically McNemar&\#x27;s test, and reporting the corresponding P\-values\. This provides robust evidence for the statistical soundness of the results\.
- b:observation:sec\_10:results:1:obs\_4\_robustness: The authors discuss the consistent performance trends of their proposed network architecture across different experimental setups \(e\.g\., &\#x27;bootstrapping&\#x27; versions and original/reduced datasets\), highlighting the system&\#x27;s robustness and reliability\.
- b:observation:sec\_10:results:1:obs\_5\_metric\_interpretation: The analysis thoughtfully interprets the trade\-offs between Precision and Recall for various systems and configurations\. It clearly explains the implications of these metrics in terms of false positives and how well the systems learn the characteristics of the Causal class, enhancing the clarity and substance of the results discussion\.
- b:observation:sec\_10:results:1:obs\_6\_best\_config\_inconsistency: There is an initial ambiguity regarding the identification of the &\#x27;best configuration&\#x27; or &\#x27;highest performing system&\#x27;\. The text first highlights &\#x27;Pair\_LSTM\_Max\_Adadelta&\#x27; for improving state\-of\-the\-art in &\#x27;this scenario&\#x27;, but later concludes that &\#x27;Pair\_LSTM\_Mean\_Adam&\#x27; achieved the &\#x27;highest performance&\#x27; and &\#x27;best Precision&\#x27; with a better balance between Precision and Recall\. While subsequently clarified, the initial statement could lead to confusion for the reader\.
- b:observation:sec\_10:results:1:obs\_7\_data\_balancing: Os autores demonstram um design experimental sólido ao reconhecer e abordar o desequilíbrio na distribuição de classes do corpus AltLex, mitigando isso ao criar um conjunto de dados reduzido e mais balanceado para avaliação\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_1: Os autores especificam quais métricas foram usadas para avaliar o desempenho do sistema \(Precision, Recall, F1 para a classe Causal e Accuracy para o desempenho geral\)\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_2: Há uma interpretação qualitativa consistente entre métricas \(relação entre diferença Precision/Recall e presença de falsos positivos\), conectando diretamente o comportamento de B2 ao padrão de erro descrito\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_3: Os autores fornecem uma configuração “melhor” e quantificam ganhos em comparação ao estado anterior usando F1 \(classe Causal\) e Accuracy\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_4: O texto conflita sobre qual configuração é a “melhor”: primeiro identifica “Pair\_LSTM\_ Max\_Adadelta” como a melhor, e mais adiante afirma que “Pair\_LSTM\_Mean\_Adam” atingiu o melhor Precision e “melhor balance”\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_5: Algumas afirmações causais/interpretações são apresentadas sem que o desenho experimental comprove diretamente a hipótese \(por exemplo, inferir que “treinamento tem poucos conectores não ambíguos” ou que “a suposição sobre a relação entre significados não se mantém”\), usando termos como “might indicate” e inferências sem evidência quantitativa apresentada no trecho\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_6: O texto atribui comportamentos/“preferências” de otimização \(Adadelta vs Adam\) com base em tendências, mas não fornece no trecho dados específicos \(variações numéricas\) que sustentem diretamente a conclusão de que Adadelta “promove Recall e penaliza Precision” e Adam é “mais desejável”\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_7: Há uma estratégia para lidar com desbalanceamento da classe \(redução de instâncias Non Causal por fator de dez\) e o impacto é reavaliado com baselines e o melhor modelo, incluindo teste estatístico\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_8: Algumas afirmações dependem de figuras/tabelas citadas \(por exemplo, Figura 2\) sem que o trecho forneça os valores/observações específicas; assim, a evidência fica indireta para o leitor apenas com este texto\.

### 4\.3 Analysis


### 5 Conclusions and Future Work

- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_1 [unresolved]: A conclusão delimita claramente o escopo do trabalho ao distinguir classificação do significado causal de classificação dos argumentos causais e explicita que o artigo se concentrou apenas na primeira tarefa\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_2: A conclusão apresenta uma contribuição técnica concreta e a relaciona diretamente ao problema de desambiguação, tornando clara a principal implicação dos resultados para a tarefa estudada\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3 [unresolved]: A afirmação de que o sistema supera o estado da arte é relevante, mas a conclusão não informa a magnitude da melhoria, a métrica ou as condições experimentais; por isso, o impacto demonstrado fica menos verificável a partir desta seção isoladamente\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_4: A conclusão conecta a proposta de trabalho futuro a uma necessidade identificada no estudo — a escassez de recursos — e distingue essa atividade futura dos resultados já apresentados\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_5: A conclusão não sintetiza explicitamente as limitações dos dados ou da avaliação nem delimita até que ponto os resultados podem generalizar além do corpus utilizado\. Isso enfraquece a avaliação do alcance da contribuição, especialmente porque a própria seção identifica a falta de recursos como um problema da tarefa\.
- b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_01: As conclusões articulam de forma clara e impactante os principais resultados do estudo, destacando o avanço do sistema proposto sobre o estado da arte e a sua eficácia em cenários desafiadores, o que se apoia diretamente nos resultados apresentados\.
- b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_02: A seção de conclusões apresenta um plano de trabalho futuro bem definido, que aborda uma lacuna reconhecida na área \(falta de recursos\), demonstrando clareza na identificação de necessidades e um potencial impacto futuro da pesquisa\.
- c:observation:sec\_12:conclusion:1:obs\_1 [unresolved]: A seção conecta a contribuição ao desempenho \(“outperforms the state\-of\-the\-art”\), indicando relevância demonstrada por resultados empíricos\.
- c:observation:sec\_12:conclusion:1:obs\_2 [unresolved]: A conclusão explicita um resultado adicional que reforça o alcance prático em contextos limítrofes \(sucesso em sentenças não\-causativas com verbos comumente causativos\), apoiando o impacto\.
- c:observation:sec\_12:conclusion:1:obs\_3 [unresolved]: Há uma formulação que sugere, mas não explicita claramente o vínculo entre o que foi medido e a alegação \(“encoding \.\.\. is required”\), o que pode deixar a conclusão mais forte do que os resultados apresentados na seção \(sem números nesta parte\)\.
- c:observation:sec\_12:conclusion:1:obs\_4: A redação contém quebras e hifenizações artificiais no texto \(“outper\- forms”, “disambigua\- tion”, “classifi\- cation”\), o que pode prejudicar a clareza e a legibilidade da conclusão, ainda que o conteúdo científico seja compreensível\.

## Evidências

- a:criterion:meaningful\_comparison: A revisão cobre trabalhos relevantes e identifica diferenças metodológicas, incluindo a comparação entre CNN e LSTM; os experimentos também incluem um baseline majoritário e o sistema de Hidey e McKeown\. Contudo, as comparações com trabalhos próximos são predominantemente qualitativas, não padronizam corpus, tarefa e métricas, e não abrangem suficientemente outras arquiteturas neurais e modelos de classificação causal\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_1: A seção cobre uma sequência relevante de trabalhos, desde sistemas baseados em regras e construções sintáticas específicas até abordagens que incorporam informação contextual, distribuição lexical e relações temporais\.
  - sec\_3: Khoo et al\. \(1998\) presented one of the first works related to the classification of causal relations\.
  - sec\_3: The first attempt of encoding the contextual information for causality classification between events is found in Do et al\. \(2011\)\.
  - sec\_3: The novelty lies in the use of features of temporal relations\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_3: A comparação com os trabalhos mais próximos é majoritariamente qualitativa e não informa, para cada abordagem, condições diretamente comparáveis como corpus, definição da tarefa, tipo de relação causal e métricas; isso dificulta estabelecer precisamente em que sentido a proposta supera ou amplia cada alternativa\.
  - sec\_3: Thus, the main drawbacks of those papers are the complex featuring engineering process to detect the causal relation, and the restricted coverage of the resulting knowledge bases\.
  - sec\_3: The work of Mirza and Tonelli \(2016\) has similar issues to the work of \(Bethard and Martin, 2008\), because they use similar features to represent causality\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_4: A síntese final generaliza excessivamente o estado da arte ao afirmar que os trabalhos anteriores definem a causalidade por construções sintáticas específicas ou verbos causativos, embora a própria revisão também descreva abordagens que usam coocorrência entre predicados e argumentos, semântica distribucional e relações temporais\.
  - sec\_3: The previous works support the idea that causality is defined by a specific syntactic construction or the semantics of verbs known as causative verbs\.
  - sec\_3: The authors defined a measure of the causality relation between two events according to the co\-occurrence frequency between the predicates and their arguments\.
  - sec\_3: In these works, the authors attempted to go in the direction of using distributional semantics in order to encode the causal meaning
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_5: A alegação de novidade da codificação neural do contexto é plausível, mas não é delimitada contra alternativas neurais ou abordagens de representação contextual mais recentes; a seção não estabelece claramente se a originalidade está na arquitetura, na tarefa, no corpus ou na combinação desses elementos\.
  - sec\_3: Therefore, we propose the neural encoding of the context of the relation in order to disambiguate its causal meaning\.
  - sec\_3: The first attempt of encoding the contextual information for causality classification between events is found in Do et al\. \(2011\)\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_1: O trabalho mais próximo é identificado explicitamente: Kruengkrai et al\. \(2017\) são apresentados como referência para a identificação do significado causal, e a comparação considera uma diferença metodológica relevante entre CNN e LSTM\.
  - sec\_7: Kruengkrai et al\. \(2017\) describe a Multi\-column Convolutional Neural Network \(CNN\) that uses background knowledge for the identification of the causal meaning of an input sentence in Japanese\.
  - sec\_7: On the other hand, Long short\-term memory \(LSTM\) recurrent neural networks \(RNN\) \(Hochreiter and Schmidhuber, 1997\) can encode the sequential information of the input text\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_2: A diferença proposta em relação ao trabalho baseado em CNN é relativamente clara: o artigo substitui a CNN por LSTM para representar a informação sequencial e considera que isso pode capturar melhor o significado causal, inclusive quando a causalidade não possui uma estrutura sintática fixa\.
  - sec\_7: Convolutional networks excel at pattern learning in input data, however causation does not have a particular syntactic structure as it was mentioned\.
  - sec\_7: Therefore, we propose the use of LSTM RNN instead of a CNN, because we argue that LSTM has a higher capacity of encoding meaning for the task of causality classification\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_4: Falta uma comparação mais ampla com alternativas próximas: além de Kruengkrai et al\. e do uso geral de LSTM citado por Melamud et al\., o trecho não posiciona a arquitetura proposta frente a outros modelos de classificação causal ou a outras arquiteturas neurais de codificação conjunta de dois eventos\.
  - sec\_7: Melamud et al\. \(2016\) also showed that using an LSTM results in a more precise context encoding and substantially improve performance in several tasks upon the common average\-of\-words\-embeddings representation\.
  - sec\_7: Therefore, we propose the use of LSTM RNN instead of a CNN
- b:criterion:impact: O artigo articula claramente o impacto potencial de sua contribuição, abordando a necessidade de desambiguação de causalidade em cenários com &\#x27;Alternative Lexicalizations&\#x27; e sem construções fixas\. Os resultados empíricos apresentados validam as alegações dos autores sobre a eficácia do sistema proposto, demonstrando que ele supera o estado da arte e lida com cenários desafiadores, o que indica uma relevância demonstrada para a área\. Além disso, a seção de conclusões apresenta um plano de trabalho futuro bem definido, focado na criação de novos recursos para a tarefa, o que aborda uma lacuna reconhecida no campo e aponta para um impacto futuro significativo e não especulativo\.
- b:observation:sec\_2:introduction:1:impact\_claim\_1: O impacto potencial da contribuição é afirmado de forma explícita, indicando que os resultados empíricos validarão a afirmação dos autores sobre a eficácia da abordagem proposta para a desambiguação da causalidade, endereçando uma necessidade clara na área\.
  - sec\_2: Empiric results on this corpus show that our claim indeed holds\.
- b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_01: As conclusões articulam de forma clara e impactante os principais resultados do estudo, destacando o avanço do sistema proposto sobre o estado da arte e a sua eficácia em cenários desafiadores, o que se apoia diretamente nos resultados apresentados\.
  - sec\_12: Our proposed system outper\- forms the state\-of\-the\-art\. We also showed the suc\- cess of the system in some non\-causative sentences but with commonly causative verbs \(see Table 8\)\.
- b:observation:sec\_12:conclusion:1:conc\_clarity\_impact\_02: A seção de conclusões apresenta um plano de trabalho futuro bem definido, que aborda uma lacuna reconhecida na área \(falta de recursos\), demonstrando clareza na identificação de necessidades e um potencial impacto futuro da pesquisa\.
  - sec\_12: One of the problems of the task is the lack of resources, so, as future work, we plan the creation of a new corpus for the two subtasks of causality classification, namely causality disambiguation and causality argument classification\.
- b:criterion:substance: O artigo apresenta substância considerável, com um design experimental sólido que inclui a definição clara do estado da arte, a justificativa para as linhas de base e a abordagem do desequilíbrio de classes através de um dataset reduzido e balanceado\. Há estudos de ablação detalhados que comparam diferentes escolhas arquitetônicas, otimizadores e estratégias\. As alegações de melhoria são fortalecidas pelo uso de testes estatísticos apropriados, como o teste de McNemar, e a discussão sobre as tendências de desempenho da rede demonstra robustez\. A interpretação das métricas de Precision e Recall é perspicaz\. Contudo, falta uma análise estatística mais profunda dos resultados, como a variância das métricas de desempenho, o que é uma lacuna notável na seção de experimentos e resultados\.
- b:observation:sec\_8:results:1:obs\_8\_1: O artigo define claramente o estado da arte para o corpus AltLex, justificando a escolha do método de Hidey e McKeown \(2016\) como linha de base devido ao uso limitado do corpus\. Além disso, a justificação para a avaliação exclusiva com este corpus, citando a escassez de corpora representativos na tarefa de classificação de causalidade, demonstra um reconhecimento transparente das limitações do campo\.
  - sec\_8: As far as we know, the AltLex corpus has been only used in the work in which it was presented \(Hidey and McKeown, 2016\), therefore we consider their method as the state of the art on that corpus\.
  - sec\_8: Moreover, as it has been mentioned several times, the task of causality classification lacks of representative or large enough corpus that covers a wide range of causal expressions, as well as without the restriction of being composed of specific causal constructions\. Therefore, the methods were only evaluated with the AltLex corpus\.
- b:observation:sec\_8:results:1:obs\_8\_2: Apesar de mencionar o tamanho do corpus e apresentar um teste de significância de McNemar, a seção carece de detalhes sobre outras análises estatísticas mais profundas dos resultados, como a variância das métricas de desempenho, conforme esperado em uma seção de experimentos e resultados\.
  - sec\_8: As far as we know, the AltLex corpus has been only used in the work in which it was presented \(Hidey and McKeown, 2016\), therefore we consider their method as the state of the art on that corpus\. Moreover, as it has been mentioned several times, the task of causality classification lacks of representative or large enough corpus that covers a wide range of causal expressions, as well as without the restriction of being composed of specific causal constructions\. Therefore, the methods were only evaluated with the AltLex corpus\. We have used the two versions of the corpus \(“non bootstrapping&quot; and &quot;bootstrapping”\) in our experiments\. The size of each of them is shown in Table 3\.
- b:observation:sec\_10:results:1:obs\_1\_baselines: The paper effectively uses baselines B1 and B2 to benchmark the proposed system configurations, providing a clear reference for performance evaluation\.
  - sec\_10: The performance of B1 defines a hard baseline for the two versions of the corpus\.
  - sec\_10: all the configurations in Table 5 outperform the baseline B1, which means that the system learns beyond the class distribution of the lexical markers in the training data\.
  - sec\_10: Most of the configurations of the proposed neural network outperform the baseline B2\.
- b:observation:sec\_10:results:1:obs\_2\_ablations: The results section presents detailed ablation studies, comparing different architectural choices \(e\.g\., &\#x27;Pair\_LSTM&\#x27; vs &\#x27;Stated\_LSTM&\#x27;\), optimizers \(Adadelta vs Adam\), and zero\-padding strategies \(maximum vs mean\)\. This systematic comparison aids in understanding the contribution of individual components to the overall system performance\.
  - sec\_10: the system architecture “Pair\_LSTM” tends to reach better results than the architecture &quot;Stated\_LSTM&quot;\. This behaviour means that our assumption about the relation between the meanings of the two input events does not hold, so it is better to encode each argument independently and then to measure the relation between the arguments by using dense layers\.
  - sec\_10: Concerning the optimizers, the results show a similar behaviour in both architectures\. The Adadelta optimizer promotes the Recall and penalizes Precision, whereas the system reaches a higher value of Precision and a smaller difference between Precision and Recall when Adam optimizer is used, which is a more desirable behaviour\.
  - sec\_10: The best configuration \(“Pair\_LSTM\_ Max\_Adadelta&quot;\) uses the maximum operation for the zero\-padding strategy and Adadelta as learning optimizer\.
  - sec\_10: the system that reached the highest performance is the one that used the mean strategy for zero\-padding and the optimizer Adam\.
- b:observation:sec\_10:results:1:obs\_3\_statistics: The paper strengthens its claims of significant improvement by using appropriate statistical tests, specifically McNemar&\#x27;s test, and reporting the corresponding P\-values\. This provides robust evidence for the statistical soundness of the results\.
  - sec\_10: “Pair\_LSTM\_Mean\_Adam&quot; significantly improves the performance of B1 according to the McNemar&\#x27;s test with a P\-value of 0\.005 and 0\.05 respectively\.
- b:observation:sec\_10:results:1:obs\_4\_robustness: The authors discuss the consistent performance trends of their proposed network architecture across different experimental setups \(e\.g\., &\#x27;bootstrapping&\#x27; versions and original/reduced datasets\), highlighting the system&\#x27;s robustness and reliability\.
  - sec\_10: We observe a similar trend in the performance of the system with the &quot;bootstrapping&quot; version of the corpus
  - sec\_10: our network architecture followed the same trend in both set of experiments and with the both version of the corpus\.
- b:observation:sec\_10:results:1:obs\_5\_metric\_interpretation: The analysis thoughtfully interprets the trade\-offs between Precision and Recall for various systems and configurations\. It clearly explains the implications of these metrics in terms of false positives and how well the systems learn the characteristics of the Causal class, enhancing the clarity and substance of the results discussion\.
  - sec\_10: The behaviour of B2 shows a big difference between Precision and Recall, indicating that the system has many false positives, i\.e\. a large number of sentences without a causal meaning\. This is not a desirable behaviour\.
  - sec\_10: On the other hand, our system has a high Precision with lower Recall, indicating it mainly classifies correctly sentences with unambiguous connectives\. Figure 2 shows that the most frequent connectives in the Causal class do not have any instance in the Non Causal class, which supports our last assertion\.
  - sec\_10: The good Recall value of B2 system entails a drop in the performance according to the Precision\. This behaviour is also developed by the neural network configurations that use maximum strategy for zero\-padding and Adadelta as optimizer, but in those cases the Recall and the Pre\- cision are greater\. As previously mentioned, this means that the systems have a large number of false positive instances, so they might not be correctly learning the characteristics of the Causal class\.
- b:observation:sec\_10:results:1:obs\_7\_data\_balancing: Os autores demonstram um design experimental sólido ao reconhecer e abordar o desequilíbrio na distribuição de classes do corpus AltLex, mitigando isso ao criar um conjunto de dados reduzido e mais balanceado para avaliação\.
  - sec\_10: The class distribution of the AltLex corpus is not balanced \(see Table 3\), so we reduced the number of instances of the Non Causal by a factor of ten with the aim of evaluating our system with a more balanced dataset\. The new corpus size is in Table 6\.
- b:check:figure\_vs\_text:figure\_vs\_text\_1: figure\_vs\_text: consistent
  - sec\_5: The relation can be explicit or implicit, incase it is explicitly expressed, it is signalled by alexical marker \(l\), which may be a verb, a preposi\-tion, an adverb or an expression such as as a resultof, see Table 1\.
  - sec\_6: Causality may be signalled by a verb \(cause\), a preposition \(because\), an adverb \(subsequently\) or an expression such as as a result of\. Some of those causal expressions are almost unambiguous, but the causal meaning of others totally depends on the context\. For instance, according to PDTB, the preposition because is an unambiguous lexical marker of causation, but there are other expressions whose causal meaning is not unarguable, such as since or after that may have a temporal or a causal interpretation, see Table 2\.
  - sec\_6: The corpus size is shown in Table 3\. For further details see \(Hidey and McKeown, 2016\)\.
  - sec\_10: The class distribution of the AltLex corpus is not balanced \(see Table 3\), so we reduced the number of instances of the Non Causal by a factor of ten with the aim of evaluating our system with a more balanced dataset\.
  - sec\_6: Table 4 shows the class distribution of the lexical markers, as well as the the number of unarguable ones and the number of lexical markers with mostly a different mean\-ing in the training and the test set\. According to the Table 4, there are few ambiguous connectives, 121 in the “non bootstrapping&quot; corpus and 147 in the &quot;bootstrapping&quot; version\. However, there is an important difference between the two versions of the corpus: there are no differences between the training and the test set in the “non bootstrapping&quot; version, but there are in the &quot;bootstrapping&quot; one\.
  - sec\_7: We call to this second architecture &quot;Pair\_LSTM&quot; and it is depicted in Figure 1\. According to Figure 1, the first input of the system is the first event of the relation, and the second input is the concatenation of the lexical marker and the second event\.
  - sec\_10: The results reached by our system are shown in Table 5\.1 The Precision, Recall and F1 values were used to measure the performance of the system in the Causal Class, and the Accuracy to measure the overall performance of the system\. The performance of B1 defines a hard baseline for the two versions of the corpus\. On the other hand, the good performance of B1 might indicate that the training corpus is composed of few unambiguous causal connectives\. Concerning the results reached by the proposed systems, all the configurations in Table 5 outperform the baseline B1, which means that the system learns beyond the class distribution of the lexical markers in the training data\.
  - sec\_10: Figure 2 shows that the most frequent connectives in the Causal class do not have any instance in the Non Causal class, which supports our last assertion\.
  - sec\_10: The new corpus size is in Table 6\. We assessed the performance of the baseline B1 and the system “Pair\_LSTM\_Mean\_Adam&quot; and the results are in Table 7\.
  - sec\_11: We present some correctly classified examples by our best configuration and misclassified by B2 in Table 8\. It shows the class of the instance in the test corpus and the value of the most frequent class in the train\- ing corpus\.
  - sec\_11: The behaviour of the verb break should be stressed since it is considered as a causative verb\. However, there are some other uses of break that do not have a causal meaning \(see Table 8\)\.
  - sec\_11: Despite the difficulty of the expression which then, we can see in Table 8 that our proposed system cor\- rectly disambiguate its causal meaning, while the system of Hidey and McKeown \(2016\) does not\. Therefore, the results reached and those examples allow us to confirm our claim that the encoding of the context is required for the disambiguation of the causal meaning as we have shown in this paper\.
  - sec\_12: We also showed the suc\- cess of the system in some non\-causative sentences but with commonly causative verbs \(see Table 8\)\.
- c:criterion:meaningful\_comparison: Há comparação com trabalhos relevantes e alternativas, com menção a limitações \(ambiguidade linguística/projeção de causality; engenharia de features e cobertura restrita; justificativa de mudar a codificação para desambiguar via contexto\)\. Também existe comparação explícita entre CNN com conhecimento de fundo e a alternativa LSTM, conectando limitações percebidas às decisões de arquitetura\. Entretanto, parte das comparações não fica totalmente equivalente/detalhada: em trabalhos próximos, a diferença do que a proposta neural muda concretamente \(representação/uso de contexto/desambiguação\) não é totalmente esclarecida; na comparação CNN vs LSTM, as hipóteses incompatíveis e a transposição da evidência de capacidade/desempenho para o cenário específico do método não são totalmente demonstradas; além disso, há indicação de falta de discussão de outras alternativas além de CNN/LSTM no trecho fornecido\.
- c:observation:sec\_3:related\_work:1:obs\_1: A seção compara múltiplas abordagens anteriores para classificação de relações causais e explicita limitações recorrentes \(ex\.: ambiguidade linguística e projeção de causality\)\.
  - sec\_3: The errors of the system show the common errors of a full linguistically grounded classification system, which are related to the ambiguity of some causal links such as by or as or the lexical and syntactic ambiguity of some causative verbs\.
  - sec\_3: Again, the main source of errors is the ambiguity of the projection of causality in natural language\.
- c:observation:sec\_3:related\_work:1:obs\_2: A comparação com métodos que usam engenharia de características e/ou recursos linguísticos \(WordNet, features léxicas/sintáticas/semânticas\) está explícita, preparando a justificativa para a proposta neural baseada em contexto\.
  - sec\_3: The classification method uses as lexical features whether the verb of the sentence belongs to a list of ambiguous causative verbs, and whether the nouns belongs to one of the nine semantic hierarchies in WordNet\.
  - sec\_3: The authors developed a supervised classification system using syntactic and semantic features from WordNet, and they used SVM as a classification algorithm\.
  - sec\_3: Thus, the main drawbacks of those papers are the complex featuring engineering process to detect the causal relation, and the restricted coverage of the resulting knowledge bases\.
- c:observation:sec\_3:related\_work:1:obs\_3: A diferença da proposta em relação a trabalhos próximos \(Do et al\. 2011; Riaz e Girju 2013/2014\) não fica totalmente clara: o texto indica que eles “ainda dependem de features léxicas e sintáticas”, mas não detalha o que exatamente a proposta neural muda em termos de representação, uso de contexto e desambiguação \(além da motivação geral\)\.
  - sec\_3: In these works, the authors attempted to go in the direction of using distributional semantics in order to encode the causal meaning, but they still rely on the use of lexical and syntactic features\.
  - sec\_3: Therefore, we propose the neural encoding of the context of the relation in order to disambiguate its causal meaning\.
  - sec\_3: Following the work of Do et al\. \(2011\), Riaz and Girju \(2013, 2014\) built a knowledge base for causal events, first for events related by a pair of verbs, and then for events conveyed by pairs of verbs and noun phrases\. In these works, the authors attempted to go in the direction of using distributional semantics in order to encode the causal meaning, but they still rely on the use of lexical and syntactic features\.
- c:observation:sec\_3:related\_work:1:obs\_5: O texto identifica limitações associadas a cobertura/recorte de construções sintáticas e a dependência de padrões linguísticos, alinhando com o racional de desambiguação por representação de contexto\.
  - sec\_3: In contrast, we argue that the representation of causality should not be limited by syntactic patterns or the coverage of semantic resources, due to the lack of a particular linguistic construction for causality\.
  - sec\_3: Therefore, we propose the neural encoding of the context of the relation in order to disambiguate its causal meaning\.
- c:observation:sec\_7:related\_work:1:obs\_1: A seção compara de forma explícita um trabalho anterior \(CNN com conhecimento de fundo\) com a alternativa proposta \(LSTM\), conectando as limitações percebidas de cada abordagem à justificativa da mudança de arquitetura\.
  - sec\_7: Kruengkrai et al\. \(2017\) describe a Multi\-column Convolutional Neural Network \(CNN\) that uses background knowledge for the identification of the causal meaning of an input sentence in Japanese\.
  - sec\_7: Therefore, we propose the use of LSTM RNN instead of a CNN, because we argue that LSTM has a higher capacity of encoding meaning for the task of causality classification\.
- c:observation:sec\_7:related\_work:1:obs\_2: A comparação com a CNN de Kruengkrai et al\. é feita principalmente por alegações gerais \(estrutura sintática da causação e escolha de kernel size\), sem detalhar quais hipóteses/condições da CNN são incompatíveis com o seu problema, o que deixa a comparação menos equivalente\.
  - sec\_7: Convolutional networks excel at pattern learning in input data, however causation does not have a particular syntactic structure as it was mentioned\.
  - sec\_7: Moreover, CNN requires the definition of the kernel size, which means that we should know beforehand the length of the context that projects the causal meaning of the sentence\.
- c:observation:sec\_7:related\_work:1:obs\_3: A justificativa de por que LSTM é superior apoia\-se em uma afirmação de capacidade \(“higher capacity”\) e em evidência citada de desempenho de LSTM vs média de embeddings, mas não fica claro como essa evidência \(Melamud et al\., 2016\) se traduz especificamente para a tarefa de classificação de causalidade e para o cenário do seu método \(dois eventos \+ marcador lexical \+ comparação entre duas entradas\)\.
  - sec\_7: Melamud et al\. \(2016\) also showed that using an LSTM results in a more precise context encoding and substantially improve performance in several tasks upon the common average\-of\-words\-embeddings representation\.
  - sec\_7: Therefore, we propose the use of LSTM RNN instead of a CNN, because we argue that LSTM has a higher capacity of encoding meaning for the task of causality classification\.
- c:observation:sec\_7:related\_work:1:obs\_4: Não há discussão \(neste trecho\) de alternativas além de CNN e LSTM \(por exemplo, outros tipos de encoders/relacionadores\), o que pode reduzir a completude da comparação do estado da arte conforme a rubrica\.
  - sec\_7: Therefore, we propose the use of LSTM RNN instead of a CNN
- c:criterion:originality: O texto afirma contribuir com uma arquitetura/modelo para disambiguation de causalidade, mas a novidade em relação ao estado da arte não é sustentada com comparação direta verificável com métodos anteriores no trecho fornecido\. As passagens descrevem propostas e argumentos gerais \(“we contribute…”, “therefore, we propose…”, “in contrast…”\), porém não explicam com evidência como a arquitetura/representação difere especificamente dos trabalhos citados, nem fornecem um contraste demonstrável do que é novo\.
- c:observation:sec\_2:introduction:1:obs\_3: A alegação de novidade/contribuição em relação ao estado da arte não é sustentada no texto do trecho fornecido \(não há comparação direta com métodos anteriores nem descrição do que diferencia a arquitetura proposta\)\.
  - sec\_2: Herein, we contribute a neural network architecture for the task of causal\-ity disambiguation and we assess it in the corpus of Hidey and McKeown \(2016\)\. Empiric results on this corpus show that our claim indeed holds\.
- c:observation:sec\_3:related\_work:1:obs\_4: A alegação de originalidade \(“we propose\.\.\.”\) é apresentada sem explicitar evidência no texto de que a novidade é distinta do estado da arte nos itens citados; o texto lista ideias gerais, mas não amarra “novidade” a um contraste verificável \(por exemplo, em como o modelo difere arquiteturalmente ou de representação vs\. métodos citados\)\.
  - sec\_3: Therefore, we propose the neural encoding of the context of the relation in order to disambiguate its causal meaning\.
  - sec\_3: On the other hand, some of the works restricted their study to a narrow kind of syntactic constructions, such as the conjoined events of Bethard and Martin \(2008\)\.
  - sec\_3: In contrast, we argue that the representation of causality should not be limited by syntactic patterns or the coverage of semantic resources, due to the lack of a particular linguistic construction for causality\.
- c:criterion:substance: O artigo apresenta resultados empíricos com métricas \(Precision/Recall/F1 e Accuracy\), ganho numérico em relação ao baseline e testes estatísticos \(McNemar\) além de ajustes para desbalanceamento\. Porém, existem lacunas de substância evidencial no trecho: algumas afirmações dependem de tabelas/figuras citadas sem os números/observações no texto fornecido, e certas interpretações sobre comportamento/causas \(ex\.: relação entre desempenho e suposições do modelo\) aparecem mais como inferências do que como análises totalmente suportadas pelos detalhes apresentados aqui\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_5: Algumas afirmações causais/interpretações são apresentadas sem que o desenho experimental comprove diretamente a hipótese \(por exemplo, inferir que “treinamento tem poucos conectores não ambíguos” ou que “a suposição sobre a relação entre significados não se mantém”\), usando termos como “might indicate” e inferências sem evidência quantitativa apresentada no trecho\.
  - sec\_10: On the other hand, the good performance of B1 might indicate that the training corpus is composed of few unambiguous causal connectives\.
  - sec\_10: This behaviour means that our assumption about the relation between the meanings of the two input events does not hold, so it is better to encode each argument independently and then to measure the relation between the arguments by using dense layers\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_7: Há uma estratégia para lidar com desbalanceamento da classe \(redução de instâncias Non Causal por fator de dez\) e o impacto é reavaliado com baselines e o melhor modelo, incluindo teste estatístico\.
  - sec\_10: The class distribution of the AltLex corpus is not balanced \(see Table 3\), so we reduced the number of instances of the Non Causal by a factor of ten with the aim of evaluating our system with a more balanced dataset\.
  - sec\_10: We assessed the performance of the baseline B1 and the system “Pair\_LSTM\_Mean\_Adam&quot; and the results are in Table 7\.
  - sec\_10: “Pair\_LSTM\_Mean\_Adam&quot; significantly improves the performance of B1 according to the McNemar&\#x27;s test with a P\-value of 0\.005 and 0\.05 respectively\.
- c:observation:sec\_10:results:1:sec\_10\_obs\_8: Algumas afirmações dependem de figuras/tabelas citadas \(por exemplo, Figura 2\) sem que o trecho forneça os valores/observações específicas; assim, a evidência fica indireta para o leitor apenas com este texto\.
  - sec\_10: Figure 2 shows that the most frequent connectives in the Causal class do not have any instance in the Non Causal class, which supports our last assertion\.
  - sec\_10: The new corpus size is in Table 6\.
  - sec\_10: The results reached by our system are shown in Table 5\.1

## Integridade

Ainda não verificada: o E3 permanece pass-through.

## Figuras


## Versões

Question: `01a1e04c-7380-7196-b4f6-2f647ca65d56` v2
Taxonomia: `01b47358aa0e61d48a06d876baa73c6212d6e4fa8bff2cf62680391cbc6bf20c`
Modo: `sectioned` · Agregação: `median-v1`

- fast: google / gemini\-2\.5\-flash
- vision: google / gemini\-2\.5\-flash
- adjudicator: google / gemini\-2\.5\-flash
- evaluator\_a: openai / gpt\-5\.6\-luna
- evaluator\_b: google / gemini\-2\.5\-flash
- evaluator\_c: openai / gpt\-5\.4\-nano
- judge\_google: google / gemini\-2\.5\-flash
- judge\_openai: openai / gpt\-5\.6\-luna
- meta\_reviewer: openai / gpt\-5\.6\-luna
- Prompt meta\_reviewer: ff1a3f13c6628ec269202ab00e166efa06f579b15e9eeb531fd2bc45490b14f0
- Prompt profiler\_field: 4267ff15efedcbb8a75eaca4832c468c416d7e7bc135eef60b7dc1e152919a32
- Prompt profiler\_topic: b9db0d168d9a4ec341ddff46b39c4c78c436a32cb85b993ec6d026dc506138c7
- Prompt section\_role\_classifier: 523da7b0278af8655d4a654d0a8d0f86cd7fd3bff240ea021032b7959d54a238
- Prompt document\_extractor: 05635f1ea3e91c32356f6f2ed432682c7b10c384f099aedf075c2acf604c9360, 0a3a6eaf3ab900c16daed26d1d78cfb9abff07871447db44185a6ff3daf6b799, 417580a2a3ff88f770aa88f4baf6deeabad698c6bfad9d24144bc75265e0c42c, 7621c87b6dac48018aed274184b5c4b79f3d31e3e6205e43ff124356cc5fa440, 8ce683c5e1ba918ebbb3b283fba7a41cb9035ea2330c19feb82bb6045c4b5cd5
- Prompt sections/method: bc399c87f9cb4e474ecec5dd99b1034dbe9885660b9af69c902c5a1d46e5fddc
- Prompt sections/introduction: f9dba0ddf60b6a645f8f26bbc0d2493c669d9a46a163b45e168739cc37e555bf
- Prompt sections/related\_work: 2ea6604aedf799b0aca577d09b0061a586c2574324e1570710ee6774127869fd
- Prompt sections/conclusion: c4c502ddea161e91407c1491b62d9a7ccd898f65af92f609463b23499f9122db
- Prompt sections/results: 5389e503fa50e5a61b1c4bb10a858911cb5fe81e90d84953b2542ecc27e3139a
- Prompt cross\_checker: 4e8937f51926f97133f3debc15fa90ceb4162ea26650d19865a5b00fb3392102, 9253d720f45eb59a236b59d2623da920cbcdebd03c3af3e085cb827dc0b00dfe, bc40a3c7bfac8d760e7fc43661e10f4b0c5389afb04ad0e7a7722abcce6f85d2
- Prompt synthesizer: 985cc119b5e4342a2142a88af5f5b4ffb7cc379e92d3fe95fee2009320f100f8
- Prompt judge: 6eed71ce2bb679aa55770792f36a17c264f09b5967f821a3b222acc06eae9e3e
- Prompt reviser: 109193cf84b5b8b3aaae29e293ecec291351eb7773c6e2fa8a276f6ba0ab3b1f, 9f6b0de49ba29121d4c6ebd6694dbbde0fc94d54eaa2c64c6ce1ee0bf100c4de, e596ae66ba9f867cc3dd4dae5cc9bdc733115847e1a55b40233d466ad8147d07

## Itens pendentes

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5
- a:observation:sec\_4:method:1:sec\_4\_obs\_1
- a:observation:sec\_4:method:1:sec\_4\_obs\_2
- a:observation:sec\_6:method:1:sec\_6\_obs\_3
- a:observation:sec\_6:method:1:sec\_6\_obs\_4
- a:observation:sec\_6:method:1:sec\_6\_obs\_5
- a:observation:sec\_8:results:1:sec\_8\_obs\_3
- a:observation:sec\_9:method:1:sec\_9\_obs\_2
- a:observation:sec\_9:method:1:sec\_9\_obs\_4
- a:observation:sec\_10:results:1:sec\_10\_obs\_4
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_1
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3
- a:check:claims\_vs\_results:claims\_vs\_results\_1
- a:check:method\_vs\_question:method\_vs\_question
- a:criterion:clarity
- a:criterion:impact
- a:criterion:replicability
- a:criterion:soundness
- a:criterion:substance
- b:observation:sec\_2:introduction:1:problem\_clarity\_1
- b:observation:sec\_2:introduction:1:contribution\_originality\_1
- b:observation:sec\_3:related\_work:1:obs1
- b:observation:sec\_6:method:1:sec\_6\_obs\_1
- b:observation:sec\_6:method:1:sec\_6\_obs\_2
- b:check:claims\_vs\_results:causality\_classification\_1
- b:check:method\_vs\_question:method\_vs\_question\_1
- b:observation:sec\_4:method:1:replicability\_sec4\_missing\_details
- c:observation:sec\_4:method:1:obs\_sec\_4\_1
- c:observation:sec\_4:method:1:obs\_sec\_4\_2
- c:observation:sec\_6:method:1:obs\_6\_3
- c:observation:sec\_6:method:1:obs\_6\_4
- c:observation:sec\_8:method:1:obs\_sec\_8\_3
- c:observation:sec\_8:results:1:obs\_sec\_8\_4
- c:observation:sec\_12:conclusion:1:obs\_1
- c:observation:sec\_12:conclusion:1:obs\_2
- c:observation:sec\_12:conclusion:1:obs\_3
- c:check:claims\_vs\_results:claims\_vs\_results
- c:check:method\_vs\_question:method\_vs\_question
- c:check:figure\_vs\_text:sec\_5\_fig\_1

## Avisos

- As faixas de recomendação são provisórias e aguardam calibração\.
