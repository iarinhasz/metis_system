# A BASELINE FOR DETECTING MISCLASSIFIED AND OUT\-OF\-DISTRIBUTION EXAMPLES IN NEURAL NETWORKS

Run: `01a1e737-2e92-75a0-a438-cf78d6cee858`

Recomendação: **major**
Nota ponderada: **2.88** · Concordância: **0.62**

Revisão humana sinalizada: sim

## Critérios

### Originalidade

Nota: 2.50 · Dispersão: 1.00 · Votos válidos: 2

- A (rodada 3, nota 3): O artigo declara contribuições identificáveis: um baseline baseado em probabilidades softmax, um método baseado em reconstrução e um conjunto de tarefas e métricas padronizadas, além de avaliação em vários domínios\. Contudo, a introdução não diferencia suficientemente essas contribuições de abordagens anteriores nem especifica quais métodos ou resultados prévios são superados, complementados ou reorganizados\. A novidade alegada é plausível, mas documentada de modo insuficiente para uma nota alta\.
- C (rodada 3, nota 2): O artigo anuncia uma contribuição metodológica \(um baseline baseado em estatísticas de softmax e um “abnormality module”\) e afirma que esse módulo pode superar o baseline em alguns casos, mas na evidência fornecida a novidade fica majoritariamente no nível declarativo e com poucos detalhes verificáveis na introdução \(faltam ganhos/métricas específicas e escopo operacional\)\.
- Voto excluído de B: `evidence_not_validated`

### Solidez

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 2): Há justificativas plausíveis e discussões conceituais \(por exemplo, por que softmax pode falhar como proxy de confiança e por que métricas como AUROC/AUPR são relevantes\), mas a solidez inferencial é prejudicada por lacunas/ambiguidades frequentes em definições operacionais e pela falta de especificação completa de regras de decisão, mapeamentos de rótulos e detalhes de treinamento/detecção para vários cenários \(o que afeta a capacidade de sustentar conclusões com o desenho descrito\)\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Substância

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `unresolved`

### Clareza

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Comparação

Nota: 3.00 · Dispersão: 2.00 · Votos válidos: 3

- A (rodada 3, nota 2): A comparação central com o baseline de probabilidades softmax é relevante e há alguma comparação entre condições e domínios\. Contudo, a introdução não situa adequadamente a proposta no estado da arte, e os resultados fornecidos indicam ausência de outros baselines relevantes e de ablação do decodificador e do módulo\. Assim, a comparação é útil, mas estreita e insuficientemente contextualizada\.
- B (rodada 3, nota 4): O artigo estabelece uma comparação significativa ao avaliar o desempenho do módulo de anormalidade proposto contra um baseline de probabilidade de previsão softmax, que é claramente definido\. Essa comparação é central para a contribuição do trabalho, demonstrando como o módulo de anormalidade pode superar o baseline em cenários específicos\. Embora algumas configurações de datasets sejam referenciadas a seções anteriores, a metodologia de comparação entre os métodos é bem articulada\.
- C (rodada 3, nota 3): O artigo compara explicitamente contra baselines \(por exemplo, baseline de softmax\) e discute por que métricas de detecção não devem ser reduzidas a acurácia\. Porém, nas evidências fornecidas, a comparação com alternativas relevantes aparece com suporte parcial e, em vários trechos, há remissões a tabelas sem detalhar métricas/limiares e condições de teste, dificultando checar se as comparações são justas e equivalentes em termos operacionais\.

### Impacto

Nota: 4.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 4): O problema endereçado é diretamente relevante \(falha silenciosa e detecção de erro/abnormalidade com implicações para segurança e medicina\), e o artigo afirma evidência experimental em múltiplas arquiteturas/datasets e a possibilidade de superar o baseline com um módulo proposto\. Apesar de haver partes especulativas e falta de quantificação completa em alguns trechos, a relevância do tema e a direção de pesquisa derivada dos resultados são sustentadas pelo conteúdo fornecido\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Reprodutibilidade

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

## Pontos fortes

- O artigo apresenta contribuições identificáveis — um baseline baseado em probabilidades softmax, um método de reconstrução e tarefas e métricas padronizadas — e avalia o problema em múltiplos domínios\. [a:observation:sec\_2:introduction:1:sec\_2\_obs\_2]
- O problema é relevante para aplicações em que falhas silenciosas e previsões de alta confiança podem exigir intervenção humana, incluindo contextos de medicina e segurança\. [c:observation:sec\_2:introduction:1:obs\_2\_1, c:observation:sec\_15:conclusion:1:obs\_4]
- A comparação com o baseline de probabilidade softmax é central para avaliar o módulo de anormalidade, e o artigo relata vantagem do módulo em alguns casos testados\. [b:criterion:meaningful\_comparison, c:observation:sec\_15:conclusion:1:obs\_2]

## Pontos fracos

- A novidade é apresentada de forma predominantemente declarativa: a introdução não diferencia suficientemente a proposta de abordagens anteriores nem especifica quais métodos ou resultados prévios são superados, complementados ou reorganizados\. [a:observation:sec\_2:introduction:1:sec\_2\_obs\_3, c:observation:sec\_2:introduction:1:obs\_2\_4]
- A solidez inferencial é limitada por definições operacionais incompletas, especialmente quanto à interpretação das probabilidades softmax, à geração dos exemplos com ruído e à regra de decisão usada para produzir os scores de detecção\. [c:observation:sec\_5:method:1:obs\_4, c:observation:sec\_11:method:1:obs\_11\_3, c:observation:sec\_12:method:1:obs\_12\_4]
- A comparação experimental permanece estreita e insuficientemente contextualizada: faltam, nas evidências fornecidas, outros baselines relevantes e ablações do decodificador e do módulo, além de detalhes suficientes sobre métricas, limiares e condições de teste\. [a:criterion:meaningful\_comparison, c:criterion:meaningful\_comparison]

## Sugestões

- Reformular a introdução para posicionar explicitamente cada contribuição em relação ao estado da arte, indicando quais abordagens são comparadas e em que sentido a proposta as supera, complementa ou reorganiza; incluir também ganhos quantitativos e os cenários em que eles ocorrem\. [a:observation:sec\_2:introduction:1:sec\_2\_obs\_3, c:observation:sec\_2:introduction:1:obs\_2\_4]
- Especificar integralmente o procedimento de treinamento e detecção: transformação usada para interpretar a confiança softmax, tipo e parâmetros do ruído, distribuição dos exemplos ruidosos, função de score, limiar ou estatística de decisão e calibração para AUROC/AUPR\. [c:observation:sec\_5:method:1:obs\_4, c:observation:sec\_11:method:1:obs\_11\_3, c:observation:sec\_12:method:1:obs\_12\_4]
- Ampliar e tornar verificável a avaliação comparativa, incluindo baselines relevantes, ablações separadas do decodificador e do módulo, e a descrição uniforme das métricas, limiares e condições de teste para cada domínio e tarefa\. [a:criterion:meaningful\_comparison, c:criterion:meaningful\_comparison, c:observation:sec\_12:method:1:obs\_12\_4]

## Seções

### 1 INTRODUCTION

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1: O problema central está explicitamente definido como a detecção de exemplos classificados incorretamente e de exemplos fora da distribuição, conectando\-o a uma falha prática importante: modelos podem produzir previsões de alta confiança quando estão errados\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: As contribuições principais são apresentadas de forma relativamente explícita: um baseline baseado em probabilidades softmax, um método adicional baseado na reconstrução da entrada e uma proposta de tarefas e métricas padronizadas para avaliação\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3: A introdução enumera como contribuições um método de reconstrução, tarefas e métricas padronizadas, mas não as diferencia suficientemente de abordagens anteriores\. Embora cite trabalhos prévios e afirme que o método supera o baseline apenas em algumas tarefas, não especifica quais métodos ou resultados anteriores são superados, complementados ou reorganizados pela proposta\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_4: O impacto potencial é motivado por uma necessidade relevante e os limites da contribuição são parcialmente reconhecidos: o texto relaciona a detecção de erros a aplicações críticas e à segurança de IA, mas descreve o resultado principal como um baseline experimental em múltiplos domínios, em vez de afirmar uma solução geral\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5 [unresolved]: A relação entre &\#x27;prediction probability&\#x27;, confiança e detecção é conceitualmente ambígua\. O texto primeiro afirma que a probabilidade softmax tem &\#x27;poor direct correspondence to confidence&\#x27; e depois afirma que estatísticas dessas probabilidades são suficientes para detectar erros; a distinção entre estimar confiança calibrada e ranquear exemplos para detecção deveria ser explicitada\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6: O alcance do impacto é apresentado com exemplos fortes, mas parte da justificativa permanece especulativa: a possibilidade de que diagnósticos não sinalizados possam &\#x27;blockade future machine learning technologies in medicine&\#x27; não é ligada a evidência ou a uma delimitação das condições em que esse risco ocorreria\.
- b:observation:sec\_2:introduction:1:intro\_problem\_clarity [unresolved]: O problema de falhas silenciosas de classificadores de machine learning, especialmente com previsões de alta confiança incorretas e em cenários de distribuição de dados divergentes, é explicitamente articulado e contextualizado com exemplos de alto impacto\.
- b:observation:sec\_2:introduction:1:intro\_baseline\_originality [unresolved]: O artigo apresenta uma nova perspectiva ao demonstrar que, apesar da conhecida limitação das probabilidades softmax como medida direta de confiança, estatísticas derivadas dessas distribuições podem ser surpreendentemente eficazes como um baseline para detecção de erros e exemplos fora da distribuição, uma contribuição original ao problema\.
- b:observation:sec\_2:introduction:1:intro\_other\_contributions: As contribuições secundárias, incluindo um novo método baseado na reconstrução de inputs para detecção de anormalidades e a designação de tarefas e métricas de avaliação padrão, são claramente articuladas, estabelecendo um framework para pesquisa futura\.
- b:observation:sec\_2:introduction:1:intro\_future\_impact: O artigo enfatiza o impacto de suas contribuições ao estabelecer um baseline robusto e propor tarefas padronizadas, visando incentivar e facilitar a pesquisa futura na área de detecção de erros e exemplos fora da distribuição, o que é crucial para a segurança da IA\.
- c:observation:sec\_2:introduction:1:obs\_2\_1: O problema é explicitamente motivado com falhas em cenários reais \(desalinhamento treino\-teste\) e com o efeito de falha silenciosa em alta confiança, incluindo um exemplo concreto de impacto \(medicina/segurança\)\.
- c:observation:sec\_2:introduction:1:obs\_2\_2 [unresolved]: A tese sobre por que softmax não funciona como confiança direta é bem justificada mecanisticamente \(exponencial rápida\) e conectada ao comportamento observado \(ruído gaussiano em MNIST gerando alta confiança\)\.
- c:observation:sec\_2:introduction:1:obs\_2\_3 [unresolved]: Há uma contribuição/ponte explícita entre “softmax não é confiança” e “estatísticas de softmax ainda funcionam para detecção”, reduzindo ambiguidade sobre a interpretação do sinal\.
- c:observation:sec\_2:introduction:1:obs\_2\_4: As contribuições são anunciadas, mas no trecho de introdução elas ficam majoritariamente em nível declarativo; faltam, aqui, detalhes verificáveis do método \(o que exatamente é feito\) e evidências quantitativas específicas \(ex\.: ganhos, métricas, “outperforms” em quais cenários\)\.
- c:observation:sec\_2:introduction:1:obs\_2\_5: Não há, neste trecho, uma delimitação explícita de escopo/assunções \(por exemplo, quais regimes de calibração/limiar são usados ou como se define “confidence” operacionalmente\); isso pode dificultar a replicação só com a introdução\.

### 2 PROBLEM FORMULATION AND EVALUATION

- a:observation:sec\_3:method:1:sec\_3\_obs\_1: A seção define explicitamente as duas tarefas de detecção — erro/sucesso de classificação e dados dentro/fora da distribuição — e distingue a classe positiva da negativa\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_2: A escolha de AUROC e AUPR é bem motivada em relação às limitações da acurácia sob desequilíbrio de classes, e as fórmulas de TPR, FPR, precisão e recall são fornecidas\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_3: A seção explicita os valores de referência conceituais para detectores aleatórios e perfeitos, o que facilita a interpretação dos resultados posteriores\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_4 [unresolved]: Não é especificado como as curvas são agregadas ou integradas na prática: por exemplo, tratamento de empates, discretização/interpolação da curva PR, macro ou micro\-averaging, e eventual agregação entre execuções\. Esses detalhes podem alterar os valores reportados e são necessários para reprodução exata\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_5: A seção não informa o protocolo de avaliação: tamanho e composição dos conjuntos positivo e negativo, se as métricas são calculadas por exemplo ou por sequência, número de repetições, variabilidade estatística e intervalos de confiança\. Sem isso, a comparação quantitativa entre detectores não é plenamente reproduzível\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_6 [unresolved]: A afirmação de que a AUPR “adjusts for” diferentes taxas\-base é potencialmente imprecisa: a própria seção reconhece que a taxa\-base da classe positiva influencia fortemente a AUPR\. Seria necessário distinguir entre a curva PR refletir a prevalência e uma métrica corrigir ou normalizar essa prevalência\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_7: A transformação dos escores para trocar a classe positiva é descrita apenas de forma resumida\. Para garantir equivalência e reprodução, seria útil especificar se a transformação é aplicada antes de qualquer normalização, como os empates são tratados e se a mesma convenção de orientação é usada para AUROC e AUPR\.
- b:observation:sec\_3:method:1:sec\_3\_obs\_1 [unresolved]: The section provides a clear and sound justification for selecting AUROC and AUPR as evaluation metrics, addressing the limitations of simple accuracy for detection tasks, particularly concerning imbalanced class distributions\.
- b:observation:sec\_3:method:1:sec\_3\_obs\_2 [unresolved]: The definitions for true positive rate, false positive rate, precision, and recall are explicitly stated, along with guidance on how to interpret AUROC and AUPR values relative to random and perfect classifiers, which aids in understanding and reproducing the evaluation methodology\.
- b:observation:sec\_3:method:1:sec\_3\_obs\_3 [unresolved]: The paper specifies the procedure for addressing the influence of class base rates on AUPR by evaluating both success/normal and error/abnormal classes as positive, including the method of multiplying scores by \-1, which is a sound approach for thorough evaluation\.
- b:observation:sec\_3:method:1:sec\_3\_obs\_4: The final sentence of the section is incomplete, potentially omitting a key detail about AUROC&\#x27;s invariance to class labeling when scores are appropriately adjusted, which slightly impacts clarity\.
- c:observation:sec\_3:method:1:obs\_1 [unresolved]: A seção introduz claramente dois problemas relacionados \(erro/sucesso e detecção in/out\-of\-distribution\) e contextualiza que será apresentado um baseline e métricas de avaliação\.
- c:observation:sec\_3:method:1:obs\_2 [unresolved]: Justifica a escolha das métricas para detecção via problema de threshold e desbalanceamento, citando explicitamente por que acurácia pode ser enganosa\.
- c:observation:sec\_3:method:1:obs\_3 [unresolved]: Define AUROC como métrica independente de threshold e fornece interpretações \(curva ROC e interpretação probabilística\)\.
- c:observation:sec\_3:method:1:obs\_4 [unresolved]: Explica a razão para usar AU\(PR\) além da AUROC, especialmente em presença de base rates diferentes e descreve como obter AUPR via definição da classe positiva\.
- c:observation:sec\_3:method:1:obs\_5 [unresolved]: O texto descreve fórmulas e interpretação, mas não especifica explicitamente como construir os rótulos positivos/negativos \(por exemplo, mapeamento exato entre “success/error/normal/abnormal”\) para cada tarefa definida na seção\.
- c:observation:sec\_3:method:1:obs\_6 [unresolved]: Há uma interrupção/trecho truncado no final \(“Note that treating error/abnormal classes as positive classes does not change the AU\-”\), o que prejudica clareza e pode indicar falta de continuação essencial para replicação\.
- c:observation:sec\_3:method:1:obs\_7 [unresolved]: A descrição da relação entre “áreas” e “AUPRs” parece inconsistente \(uso de “areas” em vez de “AUPRs/areas under PR curve”\), o que pode confundir o leitor\.

### 3 SOFTMAX PREDICTION PROBABILITY AS A BASELINE

- a:observation:sec\_4:method:1:sec\_4\_obs\_1 [unresolved]: O procedimento define de forma operacional o escore principal: a probabilidade máxima da distribuição softmax, isto é, a probabilidade da classe predita\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2: A seção explicita as convenções de rotulagem e o sinal dos escores para as tarefas de sucesso, erro, dados in\-distribution e out\-of\-distribution, reduzindo a ambiguidade sobre a direção da classificação\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: A descrição não informa detalhes necessários para reproduzir exatamente o cálculo das curvas e das áreas: implementação ou interpolação de ROC/PR, tratamento de empates, tamanho e composição das amostras usadas em cada comparação e forma de cálculo dos valores\-base\. Embora a prevalência determine o AUPR de um detector aleatório, a seção não fornece as prevalências nem a fórmula ou o procedimento adotado\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_4: A alegação de alta significância estatística não é reproduzível nesta seção: faltam os valores de p, o número de observações, a definição das amostras comparadas, a unidade de replicação e detalhes sobre unilateralidade, empates e eventual correção para múltiplos testes\. Também não é esclarecido como o teste de Wilcoxon foi aplicado às áreas ou aos escores\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: A formulação inicial agrupa detecção de erro de classificação e detecção OOD sob o mesmo procedimento, mas não explicita nesta seção quais conjuntos, pareamentos ou critérios definem cada comparação; isso deixa a validade da comparação dependente de informações apresentadas em outras partes do artigo\.
- b:observation:sec\_4:method:1:obs\_4\_1: O método de detecção é claramente definido, usando a probabilidade máxima da distribuição softmax para identificar exemplos incorretamente classificados ou fora de distribuição \(OOD\)\.
- b:observation:sec\_4:method:1:obs\_4\_2: As definições para as classes positivas nas tarefas de classificação binária \(&\#x27;Success&\#x27;, &\#x27;Error&\#x27;, &\#x27;In&\#x27;, &\#x27;Out&\#x27;\) são explícitas, incluindo a manipulação das pontuações \(uso de probabilidades negativas para &\#x27;Error&\#x27; e &\#x27;Out&\#x27; como classes positivas\)\.
- b:observation:sec\_4:method:1:obs\_4\_3: As métricas de avaliação \(AU\-PR e AU\-ROC\) e as métricas adicionais \(probabilidade média prevista para exemplos incorretos e OOD\) são claramente especificadas\.
- b:observation:sec\_4:method:1:obs\_4\_4: O uso do teste de Wilcoxon rank\-sum para avaliar a significância estatística em relação às linhas de base aleatórias é mencionado, fornecendo um método para validação estatística\.
- b:observation:sec\_4:method:1:obs\_4\_5: A seção não detalha como as linhas de base aleatórias \(&\#x27;Base&\#x27;\) são calculadas, o que poderia impactar a reprodutibilidade dos valores de referência de AUPR\.
- b:observation:sec\_4:method:1:obs\_4\_6: Faltam detalhes sobre o setup experimental para o teste de Wilcoxon rank\-sum, como o número de repetições ou como a distribuição dos resultados da linha de base é formada, o que é crucial para replicar as afirmações de significância estatística\.
- b:observation:sec\_4:method:1:obs\_4\_7: A natureza e a fonte dos exemplos &\#x27;out\-of\-distribution&\#x27; não são definidas nesta seção, sendo uma informação fundamental para replicar os experimentos de detecção de OOD\.
- b:observation:sec\_4:method:1:obs\_4\_8: A seção descreve o método de avaliação da probabilidade softmax, mas não especifica as arquiteturas de rede neural subjacentes ou os procedimentos de treinamento usados para gerar as distribuições softmax, que são pré\-requisitos para a aplicação do método\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_1 [unresolved]: O método de pontuação do detector está explicitado: usa\-se a máxima probabilidade do softmax para a classe predita e, conforme o caso, inverte\-se o sinal para OOD ou erro\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_2 [unresolved]: A forma de avaliação \(PR e ROC\) é descrita para o classificador binário que discrimina entre positivo e negativo com base nos escores definidos\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_3 [unresolved]: A seção explicita o mapeamento do que é tratado como classe positiva para cada cenário \(Success/Error/In/Out\)\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_4 [unresolved]: Há definições de rótulos/linhagens ‘Base’ e colunas \(ex\.: Pred Prob Wrong/Pred\. Prob\) mencionadas, mas sem formalizar exatamente como essas estatísticas são computadas \(ex\.: médias em que subconjunto, unidades, exclusões\)\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_5 [unresolved]: A descrição não especifica detalhes operacionais necessários para reproduzir a detecção: como é definido o limiar/score ordering para PR/ROC, e como são feitos os cortes entre conjuntos \(ex\.: separar ‘correctly’/‘incorrectly’ no test set e formar ‘In’/‘Out’ quando há múltiplas fontes OOD\)\.
- c:observation:sec\_4:method:1:sec\_4\_obs\_6 [unresolved]: A seção declara que ‘base’ e resultados são discutidos mais adiante, mas também afirma um achado estatístico \(“AU\-ROCs differ\.\.\.”\), sem fornecer o que exatamente foi testado \(quais pares, nível de significância, e se a hipótese comparou contra ‘random’ ou outra distribuição\)\.

### 3\.1 COMPUTER VISION

- a:observation:sec\_5:method:1:sec\_5\_obs\_1: A seção identifica explicitamente os conjuntos de dados, seus tamanhos de treino e teste e, para os experimentos OOD, descreve as principais fontes de exemplos negativos e as transformações gerais aplicadas\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_2: O desenho experimental distingue exemplos positivos in\-distribution de exemplos negativos out\-of\-distribution e inclui tanto dados realistas quanto ruído sintético, permitindo avaliar o baseline em condições de dificuldade distintas\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_3: A descrição dos exemplos OOD não informa quantidades, critérios de amostragem, resolução final, canais, normalização ou procedimento exato de redimensionamento\. Assim, não é possível reproduzir precisamente a composição dos conjuntos avaliados\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_4: Os hiperparâmetros de treinamento permanecem insuficientemente especificados: não são dados, neste trecho, a taxa de aprendizado, o cronograma ou número de reinícios do SGD, o tamanho de lote, o critério de seleção do modelo e os parâmetros da transformação de dados\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_5: A definição apresentada para a GELU está malformada no texto fornecido: aparece como “x\(x\), where Φ\(x\) is the CDF\.\.\.”, sem a expressão matemática completa\. Embora a forma usual seja x·Φ\(x\), o trecho não a apresenta de modo verificável, o que impede confirmar e implementar exatamente a não linearidade usada\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_6: As conclusões sobre discriminação confiável e desempenho elevado são apresentadas como baseadas nas Tabelas 1 e 2, mas os valores numéricos, os tamanhos das amostras negativas e os detalhes de cálculo dos AUROC/AUPR não estão presentes no trecho\. Sem esses elementos, a força da comparação e a incerteza dos resultados não podem ser avaliadas aqui\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_7: A validade externa da avaliação OOD é limitada pelo uso de fontes negativas selecionadas e, em parte, de ruído sintético; a seção não estabelece se esses exemplos representam as distribuições OOD de interesse em aplicações reais nem testa variações sistemáticas de dificuldade\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_1: O artigo não especifica as dimensões alvo exatas ou o método de interpolação usado para redimensionar as imagens\. A frase &\#x27;Images are resized when necessary&\#x27; é vaga e impede a reprodução exata dos dados de entrada, especialmente ao misturar conjuntos de dados como CIFAR\-10bw com MNIST\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_2: Não são fornecidos os hiperparâmetros completos para os otimizadores utilizados\. Para o Adam \(MNIST\), faltam detalhes como taxa de aprendizado, betas e epsilon\. Para o SGD com restarts \(CIFAR\-10/100\), faltam informações sobre o agendamento da taxa de aprendizado, momentum, peso de decaimento e parâmetros específicos dos restarts\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_3: A descrição &\#x27;standard mirroring and cropping data augmentation&\#x27; para CIFAR\-10 e CIFAR\-100 carece de parâmetros específicos, como a quantidade de preenchimento para o corte \(padding\), o tamanho exato do corte e a probabilidade de espelhamento\. Embora &\#x27;standard&\#x27; possa implicar práticas comuns, a falta de detalhes impede a replicação exata do pré\-processamento de dados\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_4: A inicialização dos pesos é referenciada a um trabalho anterior, &\#x27;We initialize our weights according to \(Hendrycks &amp; Gimpel, 2016c\)&\#x27;, mas não especifica o método exato ou quaisquer parâmetros que ele possa exigir\. Embora a citação seja útil, a explicitação direta do método de inicialização \(e\.g\., &\#x27;Xavier uniform&\#x27; ou &\#x27;Kaiming normal&\#x27;\) seria benéfica para a replicabilidade\.
- c:observation:sec\_5:method:1:obs\_1: Há uma descrição explícita e numericamente específica dos datasets usados \(MNIST, CIFAR\-10, CIFAR\-100\), incluindo tamanhos de treino/teste e número de classes\.
- c:observation:sec\_5:method:1:obs\_2: O texto fornece uma formulação operacional para o baseline de detecção via softmax, especificando exatamente como escolhe exemplos in\-distribution e out\-of\-distribution, incluindo várias fontes/transformações\.
- c:observation:sec\_5:method:1:obs\_3: A evidência de que “corretamente classificados” e “incorretamente classificados” são distinguíveis é apresentada como afirmação textual e dependente de “Table 1”, mas sem explicar o mecanismo, métrica/limiar ou que método de separação foi usado no próprio texto desta seção\.
- c:observation:sec\_5:method:1:obs\_4: A seção critica o uso de probabilidade máxima de softmax como “confiança”, mas não define explicitamente como “translated to confidence” é implementado \(por exemplo, mapeamento/transformação\), dificultando reprodutibilidade do argumento quantitativo dentro da seção\.
- c:observation:sec\_5:method:1:obs\_5: Embora as arquiteturas e parte do treino sejam especificados, faltam detalhes reproduzíveis críticos \(p\.ex\., otimizador/valores concretos do Adam, parâmetros do SGD com restarts, tamanhos de batch, learning rate, agendamento e critérios de early stopping\)\.
- c:observation:sec\_5:method:1:obs\_6: O procedimento de inferência/detecção com softmax é mencionado conceitualmente, mas a regra operacional exata \(por exemplo, usar “maximum softmax probability” e como isso entra na construção das curvas PR/ROC\) não é explicitada nesta seção\.

### 3\.2 NATURAL LANGUAGE PROCESSING

- a:observation:sec\_6:method:1:sec\_6\_obs\_1: A seção delimita claramente seu escopo ao indicar que tratará de tarefas e arquiteturas variadas de processamento de linguagem natural, preparando a organização das subseções subsequentes\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_2: A abertura da seção não especifica quais tarefas, arquiteturas, conjuntos de dados, procedimentos de treinamento ou parâmetros serão usados; portanto, isoladamente, não permite reproduzir o protocolo experimental de NLP\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_3: A seção introdutória não explicita como as diferentes tarefas e arquiteturas serão comparadas nem quais métricas avaliarão a detecção de exemplos incorretamente classificados ou fora da distribuição\.
- b:observation:sec\_6:method:1:sec\_6\_nlp\_missing\_method\_overview: A seção &\#x27;3\.2 NATURAL LANGUAGE PROCESSING&\#x27; introduz as tarefas e arquiteturas de PLN, mas não detalha as hipóteses gerais, os parâmetros ou os conjuntos de dados que seriam aplicados consistentemente em todas as tarefas de PLN, impedindo uma compreensão inicial da metodologia global antes dos detalhes específicos de cada subtarefa\.
- c:observation:sec\_6:method:1:obs\_1: A transição para o bloco de NLP é feita de forma explícita, introduzindo o escopo: “Let us turn to a variety of tasks and architectures used in natural language processing\.”
- c:observation:sec\_6:method:1:obs\_2: A seção apresenta apenas uma frase introdutória e não fornece parâmetros, hipóteses, procedimentos ou definição operacional do que será feito nas tarefas de NLP \(o que reduz reprodutibilidade a partir desta seção específica\)\.

### 3\.2\.1 SENTIMENT CLASSIFICATION

- a:observation:sec\_7:method:1:sec\_7\_obs\_1: A seção especifica elementos importantes do procedimento de classificação: dataset utilizado, tamanhos dos conjuntos IMDB, dimensão dos vetores, inicialização aleatória, arquitetura linear, número de épocas, otimizador e uso de validação interna para early stopping\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_2: O desenho separa explicitamente exemplos in\-distribution e out\-of\-distribution e identifica os conjuntos usados para cada finalidade, incluindo os tamanhos das amostras OOD\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_3: A alegação de que as probabilidades permitem detectar de forma confiável quais exemplos estão corretos e incorretos não é quantificada no texto fornecido; sem os valores e métricas da Tabela 3, a força dessa conclusão não pode ser verificada diretamente nesta seção\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_4: Faltam detalhes necessários para reproduzir o treinamento, incluindo tokenização e pré\-processamento, vocabulário e tratamento de palavras desconhecidas, regra exata de parada antecipada, particionamento dos 5000 exemplos e hiperparâmetros do Adam\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_5: A inicialização aleatória é mencionada, mas não há semente, número de execuções ou procedimento de agregação; portanto, a variabilidade dos resultados e a possibilidade de reproduzir os valores reportados permanecem indeterminadas\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_6: A correspondência entre os tamanhos 500 e 1000 e os dois datasets OOD é inferível pela ordem da frase, mas não é explicitada de forma inequívoca; além disso, não são informados os critérios de seleção desses exemplos nem se houve balanceamento por classe\.
- a:observation:sec\_7:method:1:sec\_7\_obs\_7: A seção fornece uma comparação conceitualmente relevante entre IMDB e dois domínios próximos, distinguindo diferenças de produto versus filme e de resenhas amadoras completas versus trechos de críticos profissionais\.
- b:observation:sec\_7:method:1:nlp\_method\_clarity\_linear\_classifier: The description of the &\#x27;linear classifier&\#x27; is somewhat ambiguous, lacking specific details that would ensure exact replication of the model architecture\.
- b:observation:sec\_7:method:1:nlp\_method\_missing\_adam\_params: The specific parameters for the Adam optimizer \(e\.g\., learning rate, beta values, epsilon\) are not provided, which are essential for precise reproduction of the training process\.
- b:observation:sec\_7:method:1:nlp\_method\_missing\_early\_stopping\_metric: The specific metric used for early stopping \(e\.g\., validation loss, validation accuracy\) is not mentioned\. This detail is crucial for consistently reproducing the model&\#x27;s training termination condition\.
- c:observation:sec\_7:method:1:obs\_1 [unresolved]: O protocolo experimental para a tarefa de sentimento é descrito de forma relativamente concreta \(dados, modelo, treino e critério de early stopping\), o que favorece a replicabilidade\.
- c:observation:sec\_7:method:1:obs\_2 [unresolved]: Há dependência explícita de resultados em tabelas \(Tabela 3\) para sustentar a alegação sobre separação entre exemplos corretos e incorretos, mas a seção não define o métrico/limiar usado para essa detecção nem detalha como a separação é quantificada\.
- c:observation:sec\_7:method:1:obs\_3 [unresolved]: O mecanismo exato do baseline de detecção usando softmax \(ex\.: “max softmax probability” como score e como isso é convertido em decisão\) não é especificado nesta seção, apesar de ser mencionado como suporte à detecção\.
- c:observation:sec\_7:method:1:obs\_4 [unresolved]: A definição de in\-distribution vs out\-of\-distribution para NLP é relativamente clara, incluindo quais conjuntos são usados e quantos exemplos são reservados para OOD\.
- c:observation:sec\_7:method:1:obs\_5 [unresolved]: O texto afirma que a detecção tem “similar story” a uma seção anterior, mas não fornece detalhes adicionais sobre métricas, calibração ou configuração de avaliação específicas para esta comparação \(apenas remete à Tabela 4\)\.
- c:observation:sec\_7:method:1:obs\_6 [unresolved]: A seção menciona explicitamente “prediction probabilities” como base para detecção, mas não está claro, a partir do que foi apresentado aqui, se o mesmo mecanismo \(por exemplo, “max softmax”\) é usado tanto para erro quanto para OOD\.

### 3\.2\.2 TEXT CATEGORIZATION

- a:observation:sec\_8:method:1:sec\_8\_obs\_1: A seção especifica os conjuntos de dados, o número de classes e uma descrição geral dos modelos e regimes de treinamento, incluindo dimensão dos vetores, número de épocas, função de ativação e otimizador\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_2: O desenho experimental explicita a criação de exemplos fora da distribuição por exclusão de classes do treinamento, e informa quantas classes foram excluídas em cada conjunto\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_3: A descrição não informa quais sujeitos foram incluídos ou excluídos, como foram formados os conjuntos de treinamento, validação e teste, nem como foi garantido que os exemplos fora da distribuição não aparecessem no treinamento; esses detalhes são necessários para reproduzir o protocolo e avaliar a validade da comparação\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_4: Faltam parâmetros de pré\-processamento e treinamento relevantes para reprodução, como construção e normalização dos vetores de palavras, vocabulário, representação exata do bag\-of\-words, dimensões das camadas, inicialização, taxa de aprendizado, tamanho de lote, critérios de parada e sementes aleatórias\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_5: A conclusão de que os erros são detectados “dependably” e de que as probabilidades softmax permitem detectar sujeitos fora da distribuição é apresentada sem métricas, intervalos de incerteza, número de repetições ou resultados quantitativos nesta seção; a sustentação depende das Tabelas 5 e 6, que são apenas referenciadas\.
- a:observation:sec\_8:method:1:sec\_8\_obs\_6: O nome do conjunto de dados “Reuters 52” aparece grafado incorretamente como “Retuers 52” na descrição da arquitetura; a grafia correta é “Reuters 52”\. Esse erro tipográfico pode dificultar buscas ou scripts de reprodução, embora o conjunto seja identificável pelo contexto\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_1: A descrição do classificador linear e da geração dos vetores de palavras de 30 dimensões para o dataset 20 Newsgroups carece de detalhes críticos para a reprodução\. O método de geração dos vetores de palavras \(p\.ex\., pré\-treinados, treinados do zero, modelo específico, corpus\) e o tipo específico de classificador linear, função de perda e regularização não são fornecidos\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_2: O termo &quot;one\-layer neural networks&quot; para os datasets Reuters 8 e Reuters 52 é ambíguo\. Não está claro se se refere a uma rede com uma única camada oculta ou a um modelo linear com uma única camada de saída\. O número de neurônios em qualquer camada oculta \(se presente\) também não é especificado\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_3: Para os datasets Reuters 8 e Reuters 52, o texto carece de detalhes sobre como a &quot;bag\-of\-words input&quot; foi gerada\. Especificamente, informações sobre os passos de pré\-processamento de texto \(p\.ex\., tokenização, remoção de stop\-words, stemming/lemmatization\), tamanho do vocabulário e o método específico de vetorização \(p\.ex\., binário, contagem, TF, TF\-IDF\) não são fornecidas\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_4: Embora o Adam seja mencionado como o otimizador para Reuters 8 e Reuters 52, hiperparâmetros específicos, como a taxa de aprendizado, beta1, beta2 e epsilon, não são fornecidos, dificultando a reprodução exata\.
- b:observation:sec\_8:method:1:sec\_8\_obs\_5: O método não especifica como os datasets in\-distribution foram divididos em conjuntos de treinamento, validação e teste\. Além disso, os sujeitos específicos escolhidos como &quot;out\-of\-distribution examples&quot; para cada dataset \(5 de 20 Newsgroups, 2 de Reuters 8, 12 de Reuters 52\) não são identificados, nem o processo de seleção \(p\.ex\., aleatório, critérios específicos, semente\) é descrito\. Isso pode afetar significativamente os resultados e sua generalização\.
- c:observation:sec\_8:method:1:obs\_1: O protocolo descreve explicitamente como construir o conjunto out\-of\-distribution via exclusão de sujeitos \(análogo a classes/temas\) e reutiliza o mesmo tipo de tarefa \(predição do assunto do texto\)\.
- c:observation:sec\_8:method:1:obs\_2: A seção afirma que há “detect errors dependably” e que “softmax prediction probabilities” permitem detectar sujeitos OOD, mas não especifica métricas/limiares nem quais números em Table 5/6 sustentam a alegação \(remete às tabelas sem descrevê\-las aqui\)\.
- c:observation:sec\_8:method:1:obs\_3: Faltam detalhes essenciais de reprodutibilidade do treinamento: para o classificador linear em 20 Newsgroups não são descritos hiperparâmetros além de “30\-dimensional word vectors” e “20 epochs” \(ex\.: regularização, otimizador, batch size, learning rate\); para as redes em Reuters não são descritos o tamanho das embeddings/rede, tamanho do vocabulário ou parâmetros de treinamento além de “optimized with Adam for 5 epochs”\.
- c:observation:sec\_8:method:1:obs\_4: Há possível erro de digitação no nome do dataset \(“Retuers 52” em vez de “Reuters 52”\), o que pode causar confusão na reprodução e na correspondência com referências externas\.
- c:observation:sec\_8:method:1:obs\_5: Não é especificado como os “30\-dimensional word vectors” são obtidos \(fonte, pré\-treino, como lidar com vocabulário fora do conjunto\), nem como o bag\-of\-words é construído \(ex\.: contagens, TF\-IDF, normalização\), o que impede replicação fiel\.

### 3\.2\.3 PART\-OF\-SPEECH TAGGING

- a:observation:sec\_9:method:1:sec\_9\_obs\_1: A seção especifica os corpora e informa o número de classes POS de cada domínio, distinguindo claramente newswire e mídia social\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_2 [unresolved]: A descrição fornece vários hiperparâmetros relevantes dos dois taggers, incluindo arquitetura, tamanho das camadas, inicialização, número de épocas, otimizador e tamanho de lote ou validação\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A descrição não informa detalhes necessários para reproduzir integralmente o treinamento e a avaliação: particionamento completo do WSJ, conjunto de teste, pré\-processamento e tokenização, representação das sequências, taxa de aprendizado, critérios de parada e sementes aleatórias\. No caso dos tweets, também não é informado o tamanho ou a composição do conjunto de teste\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_4 [unresolved]: A arquitetura do tagger de tweets permanece ambígua: “two\-layer neural network” não esclarece se as duas camadas incluem a camada de saída, nem como as previsões são produzidas para sequências de palavras; também não são especificados detalhes como a dimensão e o treinamento da camada de saída\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_5: A interpretação de que weblogs são mais difíceis de detectar como fora da distribuição do que tweets é plausível, mas a seção não apresenta os valores de Table 8 nem define formalmente a métrica, o limiar ou o procedimento de agregação das decisões por palavra e por sentença; portanto, a conclusão não é verificável a partir da descrição fornecida\.
- b:observation:sec\_9:method:1:pos\_tag\_missing\_hp\_wsj: A descrição do &\#x27;WSJ tagger&\#x27; não especifica hiperparâmetros cruciais para o otimizador &\#x27;stochastic gradient descent&\#x27; \(como taxa de aprendizado ou momentum\) nem detalhes sobre os vetores de palavras inicializados aleatoriamente \(como a dimensão do embedding ou a distribuição de inicialização\), o que prejudica a reprodutibilidade do método\.
- b:observation:sec\_9:method:1:pos\_tag\_split\_wsj: Embora 90% do corpus WSJ seja usado para treinamento, a forma como os 10% restantes são utilizados \(para validação ou teste\) não é explicitamente declarada, nem o detalhe da divisão específica do Penn Treebank, dificultando a replicação exata do ambiente de treinamento e avaliação\.
- b:observation:sec\_9:method:1:pos\_tag\_vague\_arch\_tweet: A descrição da arquitetura do &\#x27;tweet tagger&\#x27; como uma &\#x27;two\-layer neural network&\#x27; é vaga, não especificando o tipo de camadas \(e\.g\., feed\-forward, recorrentes\) ou sua disposição, tornando difícil a reprodução precisa do modelo\.
- b:observation:sec\_9:method:1:pos\_tag\_missing\_wv\_adam\_tweet: Embora os vetores de palavras pré\-treinados para o &\#x27;tweet tagger&\#x27; sejam mencionados, detalhes como a dimensão do embedding ou a acessibilidade desses vetores não são fornecidos\. Além disso, os hiperparâmetros específicos para o otimizador Adam \(e\.g\., taxa de aprendizado\) estão ausentes\.
- b:observation:sec\_9:method:1:pos\_tag\_missing\_early\_stop\_tweet: Os critérios exatos para &\#x27;early stopping&\#x27; durante o treinamento do &\#x27;tweet tagger&\#x27; não são especificados \(e\.g\., qual métrica é monitorada, paciência\), o que é importante para replicar o processo de treinamento\.
- b:observation:sec\_9:method:1:pos\_tag\_missing\_tagsets: Embora o número de tags POS distintas para o WSJ \(45\) e para mídias sociais \(25\) seja fornecido, os conjuntos de tags específicos utilizados \(e\.g\., referências diretas às definições exatas das tags\) não são detalhados, o que pode ser relevante para uma replicação profunda\.
- b:observation:sec\_9:method:1:pos\_tag\_ood\_clarity: A explicação sobre por que a detecção de &\#x27;out\-of\-distribution&\#x27; é mais difícil para dados de &\#x27;weblog&\#x27; do que para &\#x27;tweets&\#x27; é claramente articulada, conectando\-a à semelhança estilística dos &\#x27;weblogs&\#x27; com &\#x27;newswire&\#x27; e à abordagem de detecção em nível de palavra\. Isso demonstra solidez e clareza na justificativa dos resultados esperados\.
- c:observation:sec\_9:method:1:obs\_9\_1: A seção descreve de forma direta a configuração de modelos e de treino para POS tagging tanto para WSJ quanto para tweets, com parâmetros concretos \(arquitetura, camadas, tamanhos, épocas, otimizadores e critérios de parada\)\.
- c:observation:sec\_9:method:1:obs\_9\_2: O texto afirma que há detecção de out\-of\-distribution usando o WSJ tagger em tweets e weblog data, mas não especifica o critério/score de detecção \(por exemplo, qual função usa softmax máxima, limiar, ou métrica\) nem como isso é aplicado no nível de palavra\.
- c:observation:sec\_9:method:1:obs\_9\_3: A seção referencia resultados em Tabelas 7 e 8, mas não fornece os números nem descreve exatamente como a detecção é avaliada \(p\.ex\., quais métricas/limiares, e quais classes compõem o OOD/corretas/erradas\), o que limita a capacidade de verificar a conclusão a partir do texto local\.
- c:observation:sec\_9:method:1:obs\_9\_4: Há uma afirmação explicativa \(“mais difícil detectar weblog\.\.\.”\), mas o texto não explicita uma hipótese testável nem um mecanismo quantitativo; a conclusão é apenas qualitativa e depende de interpretação do estilo entre domínios\.

### 3\.3 AUTOMATIC SPEECH RECOGNITION

- a:observation:sec\_10:method:1:sec\_10\_obs\_1: A seção adapta o uso da probabilidade softmax ao caso de reconhecimento de fala com CTC e identifica corretamente que o símbolo blank pode dominar as distribuições em muitos passos temporais, tornando necessária uma representação alternativa para detecção\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_2: O desenho inclui dois tipos complementares de dados fora da distribuição: áudio do TIMIT com ruído e exemplos de um corpus de fala em chinês, permitindo testar tanto distorção acústica quanto mudança de domínio\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: O procedimento de detecção para sequências não é suficientemente especificado: não se informa como as probabilidades por passo temporal são agregadas em um único escore por exemplo, nem como o escore é convertido em uma decisão ou avaliado\. Isso impede reproduzir diretamente a alegação de que as probabilidades detectam exemplos fora da distribuição\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: Faltam detalhes essenciais da configuração do modelo e do treinamento, incluindo o tamanho das camadas LSTM, a definição exata do clipped GELU, a taxa de aprendizado e demais parâmetros do RMSProp, o critério de seleção do modelo e os detalhes da função de custo CTC\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_5: A preparação dos dados e a composição das avaliações não são descritas com precisão suficiente: não são informados o número de exemplos, a separação entre treino, validação e teste, o vocabulário de telefones, o procedimento de extração e normalização dos MFCCs, nem como os ruídos Aurora\-2 são selecionados e misturados\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: A caracterização da dificuldade das condições degradadas é apenas parcial: a seção afirma que a distância de edição mais que dobra, mas não fornece os valores de referência, a métrica exata ou a distribuição por condição, dificultando verificar a magnitude da degradação e relacioná\-la ao desempenho de detecção\.
- b:observation:sec\_10:method:1:sec\_10\_obs\_1: A descrição das características de entrada menciona MFCCs, energia e deltas para um quadro de 25ms, mas não especifica o número de coeficientes MFCC ou o deslocamento de quadro \(frame shift\) utilizado para a extração de características\. Esses detalhes são cruciais para a replicação precisa das características acústicas\.
- b:observation:sec\_10:method:1:sec\_10\_obs\_2: Os dados de treinamento são descritos como &\#x27;80% do corpus TIMIT&\#x27;, mas o método de divisão do corpus \(por exemplo, seleção aleatória, partições predefinidas específicas\) não é explicitamente declarado, o que pode afetar a replicação exata\.
- b:observation:sec\_10:method:1:sec\_10\_obs\_3: Embora o texto afirme &\#x27;computamos as probabilidades softmax ignorando o logit do símbolo em branco&\#x27;, o mecanismo preciso para ignorar o logit do símbolo em branco \(por exemplo, definir o logit para infinito negativo antes do softmax, ou re\-normalizar as probabilidades após remover a probabilidade do branco\) não é detalhado, o que pode impactar a reprodutibilidade exata do método de detecção\.
- c:observation:sec\_10:method:1:obs\_sec\_10\_1 [unresolved]: A seção explicita um procedimento específico de treinamento e inferência para detecção em ASR, destacando que o modelo usa softmax de um sistema de predição de sequências com CTC e que, na fase de detecção, as probabilidades softmax são computadas ignorando o logit do símbolo em branco\.
- c:observation:sec\_10:method:1:obs\_sec\_10\_2 [unresolved]: Há falta de detalhes operacionais sobre como exatamente a pontuação de detecção é agregada ao longo do tempo/da sequência quando se “ignora o blank symbol&\#x27;s logit” \(por exemplo, se usa máximo por timestep, soma, média, ou outra regra\)\.
- c:observation:sec\_10:method:1:obs\_sec\_10\_3 [unresolved]: O texto indica que “não mostra” desempenho em correção/incorreção por não ser binário e que os erros estão em uma faixa de distâncias de edição, mas ainda faz afirmações anteriores sobre detecção usando softmax \(e menciona “Table 9 shows the results” para OOD\)\. Isso pode criar lacuna interpretativa sobre quais métricas/targets a seção cobre de fato\.
- c:observation:sec\_10:method:1:obs\_sec\_10\_4 [unresolved]: A descrição do experimento de OOD fornece uma receita de mistura de ruído \(Aurora\-2\) com proporções de volume e SNR aproximado, mas não especifica detalhes como tipo de sinalização \(como ruído é amostrado/selecionado, alinhamento temporal, duração, ou repetibilidade do protocolo\), o que reduz reprodutibilidade completa\.

### 4 ABNORMALITY DETECTION WITH AUXILIARY DECODERS

- a:observation:sec\_11:method:1:sec\_11\_obs\_1: A seção descreve de forma conceitualmente clara a arquitetura em três componentes — classificador, decodificador auxiliar e módulo de anormalidade — e explicita a ordem geral de treinamento, incluindo o congelamento das camadas azuis antes do treinamento das camadas vermelhas\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_2: O procedimento define explicitamente a supervisão do módulo de anormalidade: exemplos limpos recebem a classe normal, exemplos com ruído recebem a classe anormal, e a saída sigmoide estima a classe correspondente\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_3: A descrição não especifica como o ruído é gerado: tipo de perturbação, intensidade, distribuição, proporção de exemplos limpos e ruidosos, nem se esses parâmetros variam entre tarefas\. Sem essas informações, o conjunto anormal de treinamento não é reproduzível e a conclusão sobre detecção pode depender fortemente da escolha das perturbações\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_4: Faltam detalhes necessários para reproduzir o treinamento conjunto do classificador e do decodificador, incluindo arquitetura e dimensões das camadas, função de perda e pesos relativos entre classificação e reconstrução, otimizador, taxa de aprendizado, número de épocas, inicialização e critérios de parada\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_5: O texto não define operacionalmente o escore de anormalidade: não informa quais representações são usadas pelas camadas vermelhas, como a reconstrução é combinada com a representação ou com o vetor de probabilidades, nem qual é a função exata calculada antes da saída sigmoide\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_6: Há uma ambiguidade terminológica entre treinar o decodificador e o classificador &\#x27;jointly&\#x27; e, depois, congelar as &\#x27;blue layers&\#x27;: o texto não delimita quais componentes pertencem às camadas azuis, quais são o &\#x27;scorer&\#x27; e o decodificador, nem se todos os parâmetros previamente treinados permanecem fixos durante o treinamento do módulo vermelho\.
- a:observation:sec\_11:method:1:sec\_11\_obs\_7: A afirmação de que os ganhos do módulo demonstram possibilidades de superar a linha de base depende de uma comparação controlada com o baseline, mas este trecho não informa o protocolo de avaliação, as métricas, os conjuntos de teste ou se o módulo recebe informação adicional equivalente\. A conclusão não pode ser verificada apenas com a descrição apresentada\.
- b:observation:sec\_11:method:1:obs\_s11\_1: The method describes training a &quot;normal classifier&quot; as the initial step but omits critical details regarding its architecture, the specific training dataset \(beyond &quot;in\-distribution examples&quot;\), and training hyperparameters \(e\.g\., optimizer, learning rate, number of epochs, loss function\)\.
- b:observation:sec\_11:method:1:obs\_s11\_2: The auxiliary decoder&\#x27;s architecture and the specific loss function used for input reconstruction are not fully detailed, which is crucial for reproducing this component of the method\.
- b:observation:sec\_11:method:1:obs\_s11\_3: The description of joint training for the decoder and scorer lacks specifics on how the different objectives \(classification and reconstruction\) are combined in a single loss function, including any weighting schemes, and the specific optimizer and hyperparameters used\.
- b:observation:sec\_11:method:1:obs\_s11\_4: The method described in this section relies on &quot;noised training examples&quot; to define the abnormal class but does not specify how these examples are generated \(e\.g\., type of noise, intensity, distribution of noise levels\)\. This omission hinders the full reproducibility of the abnormality module&\#x27;s training, even if some details are provided in later sections\.
- b:observation:sec\_11:method:1:obs\_s11\_5: The architecture of the &quot;red layers&quot; constituting the abnormality module and their specific training hyperparameters \(e\.g\., specific loss function for abnormality scoring, optimizer, learning rate, number of epochs\) are not detailed\.
- c:observation:sec\_11:method:1:obs\_11\_1: O método está motivado por uma comparação direta com a linha de base \(softmax\) e apresenta explicitamente um caminho alternativo usando “informação” das representações internas\.
- c:observation:sec\_11:method:1:obs\_11\_2: O texto descreve o treinamento/uso de um classificador “normal” e um módulo de anomalia, mas não especifica objetivos numéricos, funções de perda, balanceamento entre “limpos” e “noised”, nem detalhes do “auxiliary decoder” e do “scorer”, o que prejudica a reprodutibilidade\.
- c:observation:sec\_11:method:1:obs\_11\_3: A geração de “noised training examples” é central para a classe anormal, mas não é descrita \(como se aplica ruído, quais transformações, parâmetros e distribuição do ruído\)\.
- c:observation:sec\_11:method:1:obs\_11\_4: O critério de “aprendizado” para congelar camadas \(“blue layers”\) é descrito em termos gerais, mas sem quantificar quais camadas/arquitetura são “blue” e quais são “red”, nem como ocorre a interface \(tensores/representações\) com o decoder e o módulo de anomalia\.
- c:observation:sec\_11:method:1:obs\_11\_5: O texto define claramente a semântica da saída do módulo \(sigmoid\), conectando\-a às classes normal/abnormal\.
- c:observation:sec\_11:method:1:obs\_11\_6: As alegações de melhoria \(“gains”\) e a atribuição causal \(“demonstrate”\) são feitas sem detalhar quais resultados métricos suportam a afirmação dentro deste trecho; a evidência quantitativa não aparece aqui\.

### 4\.1 TIMIT

- a:observation:sec\_12:method:1:sec\_12\_obs\_1: O desenho testa generalização para distorções não vistas durante o treinamento, uma hipótese relevante para detecção de exemplos fora da distribuição\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_2: A alegação de que as distorções permitem uma detecção efetiva não é verificável a partir da descrição metodológica, pois os valores, métricas, limiares e procedimentos de avaliação da Table 10 não são apresentados neste trecho\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_3: Faltam detalhes necessários para reproduzir o classificador e o módulo: arquitetura do decodificador e do módulo de anormalidade, função de perda, otimizador, taxa de aprendizado, tamanho de lote, regularização, sementes e demais hiperparâmetros de treinamento\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_4: A especificação das distorções de áudio é insuficiente para reprodução: não são informados os procedimentos exatos de geração, a relação sinal\-ruído ou escala usada para &\#x27;various volumes&\#x27;, nem como o valor de 30% é aplicado e quais ruídos compõem os conjuntos de treinamento e teste\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_5: O procedimento de detecção não define operacionalmente como os &\#x27;typical abnormality module outputs&\#x27; são estimados, qual estatística ou escore é usado, nem como o desempenho é convertido em uma métrica de detecção\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_6: A comparação entre TIMIT e THCHS\-30 não especifica claramente os conjuntos usados como referência, treinamento e avaliação, nem o protocolo que sustenta a afirmação de detecção fora da distribuição para o chinês\.
- a:observation:sec\_12:method:1:sec\_12\_obs\_7 [unresolved]: Há uma ambiguidade sobre a origem das distorções: o módulo é descrito como treinado com ruído branco, marrom e rosa, enquanto a avaliação é descrita como baseada em ruídos do Aurora\-2; não fica explícito se estes são os mesmos tipos de ruído, outras gravações ou outro procedimento de corrupção\.
- b:observation:sec\_12:method:1:obs\_timit\_1: The detailed architecture for the auxiliary decoder and the abnormality module is not provided, hindering replication\. While a three\-layer, 1024\-neuron wide classifier is mentioned, the specifics of these auxiliary components, including their internal structure, activation functions, and how they connect to the main classifier, are absent\.
- b:observation:sec\_12:method:1:obs\_timit\_2: Key training hyperparameters such as the optimizer, learning rate, batch size, and loss functions for the main network, auxiliary decoder, and abnormality module are not specified\. This lack of detail makes it impossible to reproduce the training process\.
- b:observation:sec\_12:method:1:obs\_timit\_3: The description of noise application during the abnormality module&\#x27;s training is vague, stating &quot;various volumes\.&quot; This imprecision makes it difficult to replicate the exact training conditions, especially concerning the range or distribution of noise levels used\.
- b:observation:sec\_12:method:1:obs\_timit\_4: The specific method for comparing the abnormality module outputs to detect abnormal examples is not detailed\. The text mentions &quot;comparing the typical abnormality module outputs for clean examples with the outputs for the distorted examples,&quot; but does not specify the metric, thresholding strategy, or decision rule used for this comparison\.
- b:observation:sec\_12:method:1:obs\_timit\_5 [unresolved]: While datasets are named \(TIMIT, Aurora\-2, THCHS\-30\), the specific versions, preprocessing steps, and exact splits used for training and testing are not explicitly stated\. This information is crucial for ensuring identical data conditions during reproduction\.
- c:observation:sec\_12:method:1:obs\_12\_1: O método descreve componentes e entradas de forma relativamente concreta \(arquitetura, janela temporal, número de features\), permitindo entender o experimento de TIMIT com o módulo de anormalidade\.
- c:observation:sec\_12:method:1:obs\_12\_2: Faltam detalhes operacionais essenciais para reproduzir a arquitetura e o treinamento \(por exemplo, especificação das ativações/camadas exatas, definição do decodificador auxiliar, e como o “abnormality module” é acoplado e treinado; apenas há descrições de alto nível\)\.
- c:observation:sec\_12:method:1:obs\_12\_3: O texto afirma que o módulo de anormalidade não é treinado com o mesmo tipo de ruído do teste, mas também descreve que ele treina com ruídos em múltiplos tipos e volumes; a distinção exata entre “tipo de ruído” e o “ruído adicionado aos testes” não está especificada com precisão suficiente \(pode gerar ambiguidade sobre o que exatamente muda no OOD\)\.
- c:observation:sec\_12:method:1:obs\_12\_4: A regra de decisão/score usada para detecção não é totalmente especificada \(apenas “comparando” saídas; falta a métrica/funcional concreto, como distância, limiar, estatística e como é calibrado para AUROC/AUPR da Tabela 10\)\.
- c:observation:sec\_12:method:1:obs\_12\_5: O texto contrasta explicitamente degradação de desempenho com evidência de detecção OOD usando o módulo de anormalidade, conectando a observação a métricas de erro de classificação\.
- c:observation:sec\_12:method:1:obs\_12\_6: Embora seja indicado por que se usa THCHS\-30 \(treino vs teste\) e a justificativa de eficiência, faltam números de split/exatos exemplos usados \(quais porções do conjunto de treino, como são processados/rotulados\) para reproduzir a avaliação na parte chinesa\.

### 4\.2 MNIST

- a:observation:sec\_13:method:1:sec\_13\_obs\_1: A seção apresenta uma comparação direta entre o módulo de anormalidade e as probabilidades de predição do softmax, além de considerar exemplos fora da amostra e exemplos altamente dissimilares\.
- a:observation:sec\_13:method:1:sec\_13\_obs\_2: A descrição não fornece detalhes suficientes para reproduzir o experimento: faltam, nesta seção, a definição operacional de desempenho e do ganho, os valores numéricos da Tabela 11, os limiares ou métricas utilizados, os parâmetros do decoder e do módulo de anormalidade e os procedimentos de treinamento\.
- a:observation:sec\_13:method:1:sec\_13\_obs\_3: As transformações usadas para gerar exemplos anormais são nomeadas, mas não parametrizadas: não são informados o nível de desfoque, os ângulos de rotação, a variância do ruído gaussiano, a distribuição desses parâmetros nem a forma de aplicação às imagens de treinamento\.
- a:observation:sec\_13:method:1:sec\_13\_obs\_4: A afirmação de melhoria consistente e de benefício para exemplos altamente dissimilares não pode ser avaliada quantitativamente a partir do trecho, pois não informa magnitude, incerteza, número de execuções ou comparações estatísticas; a sustentação depende dos resultados da Tabela 11\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_1: A seção compara explicitamente o módulo de anormalidade com as probabilidades de predição do softmax e inclui um conjunto de perturbações anômalas diversificado — borramento, rotação e ruído gaussiano\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_2: O desenho testa generalização fora da amostra, o que é diretamente relevante para a tarefa de detecção de exemplos anômalos\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_3: A afirmação de melhoria consistente não é quantificada no trecho fornecido: não são informados os valores de desempenho, a métrica utilizada, o número de exemplos nem a magnitude da diferença em relação ao baseline\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_4: Não há evidência visível sobre variância ou incerteza estatística, como múltiplas sementes, desvios\-padrão, intervalos de confiança ou testes de significância; portanto, a consistência da melhoria não pode ser avaliada estatisticamente a partir do trecho\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_5: Faltam detalhes necessários para reproduzir o experimento, incluindo a arquitetura e o treinamento do decodificador e do módulo de anormalidade, a quantidade e o tipo de transformações aplicadas, os particionamentos de dados e o protocolo de avaliação\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_6: A comparação parece limitada ao baseline de probabilidades softmax; não são apresentados, no trecho, outros baselines relevantes nem uma ablação que isole o efeito do decodificador do efeito específico do módulo de anormalidade\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_7: A frase sobre exemplos “highly dissimilar” não define quais distribuições ou conjuntos correspondem a essa categoria, dificultando verificar o alcance da conclusão e se ela se aplica a diferentes níveis de deslocamento de distribuição\.
- b:observation:sec\_13:method:1:obs\_1: The architectural description for the MNIST classifier, while specifying layer count and width, lacks crucial details like activation functions, initialization methods, and specific layer types \(e\.g\., dense, convolutional\), which are necessary for exact reproduction\.
- b:observation:sec\_13:method:1:obs\_2: Essential training hyperparameters for the MNIST classifier and its auxiliary components, such as the optimizer, learning rate, batch size, and total number of epochs, are not provided\.
- b:observation:sec\_13:method:1:obs\_3: The text mentions using an &\#x27;auxiliary decoder and abnormality module&\#x27; but provides no architectural details, loss functions, or clear functional descriptions for these key components, making their reproduction challenging without further information\.
- b:observation:sec\_13:method:1:obs\_4: While the methods for generating &\#x27;abnormal examples&\#x27; \(blur, rotate, add Gaussian noise\) are listed, the specific parameters or ranges for these transformations are not given, which is critical for replicating the training data for the abnormality module\.
- b:observation:sec\_13:method:1:obs\_5: The methodology lacks a description of how the main MNIST classifier, auxiliary decoder, and abnormality module are integrated and trained together, including their respective loss functions, weighting, and overall training strategy\.
- b:observation:sec\_13:method:1:obs\_6: The experiment&\#x27;s outcome regarding the abnormality module&\#x27;s performance improvement is clearly stated and referenced to a specific table, facilitating the understanding of the results and comparison\.
- b:observation:sec\_13:results:1:obs\_1: The method for generating abnormal examples \(blur, rotate, Gaussian noise\) for the abnormality module is clearly specified, which contributes to the replicability and clarity of the experimental setup\.
- b:observation:sec\_13:results:1:obs\_2: The article explicitly compares the proposed abnormality module against a clearly defined baseline \(softmax prediction probabilities\) and refers to a specific table \(Table 11\) for showing the demonstrated gains, which strengthens the substance and clarity of the reported results and provides a meaningful comparison\.
- b:observation:sec\_13:results:1:obs\_3: While the article claims &\#x27;consistent out\-of\-sample detection improvement&\#x27; and refers to &\#x27;Table 11&\#x27; for gains, the provided text does not include explicit statistical details \(e\.g\., variance, confidence intervals\) or further textual elaboration on the nature of this &\#x27;consistency&\#x27;, which would strengthen the textual substantiation and soundness of the claims\.
- c:observation:sec\_13:method:1:obs\_1: O procedimento experimental para MNIST é parcialmente descrito, incluindo a arquitetura base e a introdução dos componentes adicionais \(auxiliary decoder e abnormality module\)\.
- c:observation:sec\_13:method:1:obs\_2: A seção menciona tipos de distorções para exemplos anormais, mas não especifica parâmetros concretos \(intensidade/alcance, distribuições, faixas de rotação, sigma do ruído, tamanho/σ do blur\), nem como elas são aplicadas/selecionadas durante o treino\.
- c:observation:sec\_13:method:1:obs\_3: Embora a afirmação de ganhos seja atribuída à Tabela 11, o texto não apresenta números nem descreve métricas/escala \(ex\.: AUROC/AUPR\) diretamente na seção, dificultando avaliar magnitude e significância sem consultar a tabela\.
- c:observation:sec\_13:method:1:obs\_4: A seção afirma melhora em detecção até para exemplos altamente dissimilares, mas não define operacionalmente o que é “highly dissimilar” nem quais conjuntos/condições compõem esse cenário, deixando ambiguidade sobre a validade da generalização alegada\.
- c:observation:sec\_13:results:1:obs\_1: “Finally, much like in a previous experiment, we train an MNIST classifier with three layers of width 256\.”
- c:observation:sec\_13:results:1:obs\_2: “This time, we also use an auxiliary decoder and abnormality module rather than relying on only softmax statistics\.”
- c:observation:sec\_13:results:1:obs\_3: “For abnormal examples we blur, rotate, or add Gaussian noise to training images\.”
- c:observation:sec\_13:results:1:obs\_4 [unresolved]: “Gains from the abnormality module are shown in Table 11, and there is a consistent out\-of\-sample detection improvement compared to softmax prediction probabilities\.”
- c:observation:sec\_13:results:1:obs\_5 [unresolved]: “Even for highly dissimilar examples the abnormality module can further improve detection\.”

### 5 DISCUSSION AND FUTURE WORK

- a:observation:sec\_14:discussion:1:sec\_14\_obs\_1: A seção identifica direções de pesquisa concretas e tecnicamente plausíveis, incluindo o uso da variância intraclasse, sequências de ativações em uma RNN e detecção mais granular de tipos de exemplos fora da distribuição\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_2: As recomendações de avaliação incluem tarefas, modalidades e arquiteturas diversas, o que reconhece explicitamente o risco de que resultados obtidos apenas em visão não se transfiram para outros contextos\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_3: A seção oferece uma cautela metodológica importante ao exigir que o desempenho do detector seja interpretado junto com a acurácia do classificador subjacente, evitando uma leitura enganosa da AUPR em cenários degenerados\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_4: A afirmação de que o baseline pode ser superado é qualificada como ocorrendo “em alguns casos”, mas a discussão não resume quais tarefas, arquiteturas ou magnitudes de ganho sustentam essa conclusão\. Isso reduz a capacidade do leitor de avaliar o alcance e a robustez da melhoria\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_5: Falta uma discussão explícita das principais ameaças à validade externa e interna das recomendações: como definir e amostrar diferentes tipos de distribuição fora da distribuição, como evitar que a escolha dos datasets favoreça um detector e como controlar comparações entre arquiteturas e níveis de acurácia distintos\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_6: A distinção entre “probabilidade de uma detecção correta” e “probabilidade de uma classificação correta” não é suficientemente clara, embora sejam objetivos potencialmente diferentes\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_7: Embora a seção recomende AUPR, AUROC e acurácia, ela não especifica critérios para reportar incerteza, variabilidade entre execuções ou significância das diferenças entre detectores\. Isso limita a replicabilidade e a interpretação de pequenas melhorias sobre o baseline\.
- b:observation:sec\_14:discussion:1:obs\_14\_1: The article explicitly identifies a limitation regarding the generalizability of results obtained solely from vision\-only demonstrations, suggesting they may not transfer effectively to diverse architectures and datasets\.
- b:observation:sec\_14:discussion:1:obs\_14\_2: A crucial caveat is presented regarding the interpretation of AUPR, noting that a classifier that is consistently incorrect can still achieve a maximum AUPR for error detection, which highlights a potential threat to the sound interpretation of evaluation metrics\.
- b:observation:sec\_14:discussion:1:obs\_14\_3: The paper provides clear guidance for future research by recommending a variety of datasets and architectures for testing new detection methods, emphasizing that evaluations should not be rigidly tied to the exact setups presented in this paper due to the evolving nature of machine learning systems\. This fosters broader applicability and long\-term relevance\.
- b:observation:sec\_14:discussion:1:obs\_14\_4: The discussion section effectively outlines several promising future research directions, such as utilizing intra\-class variance, RNNs for activation patterns, fine\-grained known/unknown detection, and estimating detection probabilities, thereby demonstrating the potential impact of the work on the field\.
- b:observation:sec\_14:discussion:1:obs\_14\_5: The scope of the conclusions regarding the abnormality module&\#x27;s effectiveness is appropriately limited by the phrase &\#x27;in some cases&\#x27;, indicating a balanced and sound interpretation of its capabilities rather than overgeneralizing its superiority\.
- c:observation:sec\_14:discussion:1:obs\_1: A seção explicita que resultados experimentais permitem apontar caminhos futuros, conectando a possibilidade de superar o baseline ao uso de representações internas\.
- c:observation:sec\_14:discussion:1:obs\_2: São apresentados exemplos concretos de direções futuras \(variância intra\-classe, RNN sobre ativações por camada, detecção fine\-grained e estimação de probabilidade de acerto\), com promessa de ligação a elementos do método e avaliação do artigo \(p\.ex\., &quot;Appendix B&quot; e &quot;baseline and evaluation metrics&quot;\)\.
- c:observation:sec\_14:discussion:1:obs\_3: Algumas recomendações permanecem especulativas quanto à efetividade esperada; há poucas condições/limitações sobre quando cada abordagem tende a funcionar \(p\.ex\., &quot;Some promising future avenues may\.\.\.&quot; e &quot;Others could\.\.\.&quot;\), o que reduz a inferência suportada para cada hipótese\.
- c:observation:sec\_14:discussion:1:obs\_4: A recomendação de avaliação enfatiza AUPR/AUROC e acurácia do classificador, mas não discute explicitamente ameaças à validade externas \(p\.ex\., sensibilidade a escolha do detector/limiar, distribuição de erro como classe positiva em AUPR, ou como comparar com base em softmax em cenários com calibração diferente\), o que pode limitar a clareza sobre o alcance das conclusões de comparabilidade\.

### 6 CONCLUSION

- a:observation:sec\_15:conclusion:1:sec\_15\_obs\_1: A conclusão sintetiza claramente as duas contribuições centrais: o baseline baseado em probabilidade softmax e o módulo de anormalidade, mantendo correspondência com o escopo experimental descrito\.
- a:observation:sec\_15:conclusion:1:sec\_15\_obs\_2: A afirmação de que o módulo de anormalidade produziu resultados superiores é pouco específica: a conclusão não identifica as métricas, os cenários ou a extensão da superioridade, dificultando avaliar o impacto efetivamente demonstrado\.
- a:observation:sec\_15:conclusion:1:sec\_15\_obs\_3: A conclusão comunica a relevância prática do problema, mas não explicita quais resultados sustentam o alcance da contribuição; a passagem para recomendações de pesquisa futura permanece ampla e parcialmente especulativa\.
- b:observation:sec\_15:conclusion:1:conc\_clarity\_1: As conclusões são claras e concisas, resumindo os principais resultados apresentados no artigo de forma direta e sem ambiguidades\. Elas refletem de maneira precisa as contribuições demonstradas\.
- b:observation:sec\_15:conclusion:1:conc\_impact\_1: As conclusões articulam o impacto da pesquisa ao estabelecer uma linha de base robusta e demonstrar melhorias com o módulo de anormalidade, enquanto também delineiam claramente direções para futuras pesquisas, conectando a relevância da área a uma necessidade importante\.
- c:observation:sec\_15:conclusion:1:obs\_1: A conclusão reafirma um resultado experimental amplo \(baseline\) em múltiplas arquiteturas e datasets, alinhando\-se com o que o artigo descreve na introdução do experimento e nos testes\.
- c:observation:sec\_15:conclusion:1:obs\_2: O texto apresenta a contribuição específica do módulo proposto e posiciona claramente sua vantagem como evidência de superação do baseline em alguns casos\.
- c:observation:sec\_15:conclusion:1:obs\_3: A conclusão faz afirmações de desempenho \(“superior scores”, “beaten in some cases”\) sem indicar métricas/valores ou quais tarefas/figuras suportam diretamente, o que reduz a clareza da correspondência com resultados concretos\.
- c:observation:sec\_15:conclusion:1:obs\_4: A conclusão conecta a relevância do problema a uma necessidade prática \(detectar quando falha um sistema de ML\), o que reforça impacto, ainda que sem quantificar utilidade\.
- c:observation:sec\_15:conclusion:1:obs\_5 [unresolved]: A redação mistura proposição \(investigar arquiteturas e métodos mais confiáveis\) com a evidência apresentada na seção final, mas isso não é sustentado por detalhes do que funcionou melhor ou em quais cenários, podendo soar mais especulativa do que o artigo permite concluir diretamente\.

### ACKNOWLEDGMENTS


### A ABNORMALITY MODULE EXAMPLE

- a:observation:sec\_18:method:1:sec\_18\_obs\_1: A legenda identifica de forma clara os principais componentes do módulo — classificador, decodificador auxiliar e módulo de anormalidade — e descreve a sequência das operações de reconstrução, subtração e quadratura elemento a elemento\.
- a:observation:sec\_18:method:1:sec\_18\_obs\_2 [unresolved]: A legenda explicita as funções de ativação e diferencia visualmente quais camadas são treinadas apenas com dados dentro da distribuição e quais usam exemplos dentro e fora da distribuição, o que ajuda a interpretar o fluxo de treinamento representado\.
- a:observation:sec\_18:method:1:sec\_18\_obs\_3 [unresolved]: A figura não fornece detalhes suficientes para reproduzir a arquitetura: faltam dimensões das camadas, conectividade completa, dimensões das representações, forma exata do decodificador e definição operacional do módulo de anormalidade\.
- a:observation:sec\_18:method:1:sec\_18\_obs\_4: Não são informados nesta seção os hiperparâmetros e procedimentos de treinamento necessários para reproduzir o módulo, como funções de perda, pesos relativos entre objetivos, otimizador, taxa de aprendizagem, número de épocas, inicialização e critérios de parada\.
- a:observation:sec\_18:method:1:sec\_18\_obs\_5: A legenda não especifica quais exemplos fora da distribuição são usados, como são construídas as distorções ou reconstruções e como o escore de anormalidade é calculado a partir das saídas do módulo; sem essas definições, não é possível verificar plenamente a validade do procedimento nem reproduzir sua avaliação\.
- b:observation:sec\_18:method:1:obs\_1: The caption lacks specific details regarding the neural network&\#x27;s architecture, such as the number of layers, their widths \(number of neurons\), and specific connectivity, which are crucial for reproducing the method\.
- b:observation:sec\_18:method:1:obs\_2: The internal structure and specific operational mechanisms of the auxiliary decoder and the abnormality module are not detailed, making it impossible to replicate these components\.
- b:observation:sec\_18:method:1:obs\_3: The process of &\#x27;blurred diamond reconstruction&\#x27; is not explained, nor are the specific inputs to &\#x27;subtraction and elementwise squaring&\#x27; defined, which are critical steps in the illustrated method\.
- b:observation:sec\_18:method:1:obs\_4: Crucial training parameters such as the optimizer, learning rate, number of epochs, batch size, and the specific loss function\(s\) used for training the &\#x27;blue&\#x27; and &\#x27;red&\#x27; layers are not provided\.
- b:observation:sec\_18:method:1:obs\_5 [unresolved]: The specific dataset used for the &\#x27;diamond image&\#x27; example and the methodology for defining or generating in\-distribution and out\-of\-distribution examples for this illustration are not described\.
- c:observation:sec\_18:method:1:obs\_1: A figura descreve a arquitetura do “abnormality module”, incluindo componentes e etapas do pipeline \(reconstrução borrada, subtração e quadratura elementwise\), o que ajuda a entender o mecanismo proposto\.
- c:observation:sec\_18:method:1:obs\_2: Não há, neste trecho/descrição, detalhes do método que permitam inferir o funcionamento quantitativo do módulo \(por exemplo, como a saída do abnormality module é computada e como é usada na detecção\)\.
- c:observation:sec\_18:method:1:obs\_3: O texto/descrição disponibiliza algumas escolhas arquiteturais \(GELU vs sigmoid; azul vs vermelho para tipos de dados\), mas não fornece parâmetros necessários \(dimensões, perdas, critérios de treinamento, calibração do sinal, limiares/decisão\) para reprodutibilidade\.
- c:observation:sec\_18:method:1:obs\_4: Há possíveis problemas de consistência/clareza na rotulagem textual do termo “abnormal\-ity module” \(quebra de palavra\), o que pode prejudicar a legibilidade e a busca por termos no documento\.

### B METRICS FOR MEANINGFUL CONFIDENCE VALUES

- a:observation:sec\_19:method:1:sec\_19\_obs\_1: A seção motiva adequadamente por que a acurácia obtida após limiarizar a confiança em 0,5 pode ser pouco informativa e propõe métricas contínuas que preservam a resolução numérica das previsões\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_2: A seção explicita a função de confiança, a interpretação de valores próximos de 1 e as duas métricas propostas, tornando clara a intenção de avaliar alinhamento entre confiança e correção\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_3: A definição transcrita do probability alignment score é ambígua: a notação parece usar corretamente o fator 2·1\(f\(x\)=y\)−1, mas a ausência de uma explicitação da distribuição de expectativa, do conjunto de avaliação e da forma de agregação impede verificar exatamente como o valor foi calculado\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_4: As definições de tp, fp e fn estão incompletas na apresentação: faltam índices e somatórios necessários para especificar claramente a agregação sobre o conjunto de teste\. Como pr, rc e o soft F1 dependem dessas quantidades, a métrica não é plenamente reproduzível a partir do trecho fornecido sem inferência externa\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_5: O artigo descreve o baseline como baseado em informação da softmax, mas sua definição operacional é c\(x\_i\)=σ\(max l\_i\), isto é, a sigmoide do maior logit, e não o maior valor da distribuição softmax\. Como essas quantidades não são, em geral, equivalentes, o texto deve esclarecer se o baseline pretende usar logits da softmax ou probabilidades softmax e justificar a relação entre essa escolha e a interpretação de confiança\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_6: A seção não informa parâmetros essenciais para reproduzir o baseline experimental: fórmula exata de agregação das métricas no conjunto de teste, detalhes de treinamento, número de épocas, otimizador, taxa de aprendizado, inicialização, pré\-processamento, divisão usada e sementes\. A referência a configurações anteriores pode tornar parte dessas informações disponível em outra seção, mas isso não é indicado de modo explícito aqui\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_7: A Tabela 12 apresenta resultados agregados, mas não fornece dispersão entre as cinco execuções, intervalos de incerteza nem a definição operacional de “median result”\. Assim, não é possível avaliar a variabilidade ou a robustez dos valores reportados\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_8: A conclusão de que há “wide room for improvement” é plausível como interpretação qualitativa, mas não é sustentada por comparação quantitativa com outro modelo de confiança, intervalo de referência ou ablação na própria seção\.
- a:observation:sec\_19:method:1:sec\_19\_obs\_9 [unresolved]: Embora a tabela declare que todos os valores são percentuais, a seção não especifica como interpretar a escala do probability alignment score e do soft F1 score nem verifica propriedades básicas dessas métricas, como limites, comportamento em classificadores constantes e sensibilidade à prevalência de erros\.
- b:observation:sec\_19:method:1:soft\_f1\_summation\_missing: As definições de &\#x27;tp&\#x27; e &\#x27;fn&\#x27; para o &\#x27;soft&\#x27; F1 score parecem estar faltando uma notação explícita de somatório sobre o conjunto de teste, tornando o cálculo ambíguo e dificultando a replicabilidade\. Enquanto &\#x27;fp&\#x27; inclui um somatório, &\#x27;tp&\#x27; e &\#x27;fn&\#x27; não, o que gera inconsistência\.
- b:observation:sec\_19:method:1:soft\_f1\_indicator\_ambiguity: O termo &\#x27;1\(1 \- c\(xi\)\)&\#x27; na definição de &\#x27;tp&\#x27; para o &\#x27;soft&\#x27; F1 score é ambíguo\. Funções indicadoras são tipicamente usadas com condições booleanas, não com valores contínuos como &\#x27;1 \- c\(xi\)&\#x27; diretamente\. Não fica claro se &\#x27;\(1 \- c\(xi\)\)&\#x27; em si deve ser a contribuição &\#x27;soft&\#x27; ou se há um limiar implícito, o que impacta a clareza e a replicabilidade\.
- b:observation:sec\_19:method:1:soft\_f1\_unconventional\_definition [unresolved]: As definições de &\#x27;tp&\#x27;, &\#x27;fp&\#x27; e &\#x27;fn&\#x27; para o cálculo do &\#x27;soft&\#x27; F1 score são altamente não convencionais para a avaliação de um modelo de confiança\. Embora o objetivo seja avaliar a capacidade de identificar classificações incorretas, a formulação específica é contraintuitiva e carece de uma justificação clara sobre por que essa métrica específica é adequada para medir a &\#x27;confiança&\#x27; de forma sã, impactando a clareza e a solidez\.
- b:observation:sec\_19:method:1:prob\_alignment\_expectation\_implicit: O cálculo prático do &\#x27;probability alignment score&\#x27;, especificamente como a expectativa &\#x27;E\(x,y\)\~\(x,y\)&\#x27; é estimada, não é explicitamente detalhado\. Embora seja implicitamente assumido como uma média sobre um conjunto de teste, para uma replicabilidade estrita, isso deveria ser declarado explicitamente\.
- b:observation:sec\_19:method:1:external\_dataset\_setups: A avaliação do modelo de confiança baseline remete a &\#x27;mesmas configurações de MNIST, Twitter e IMDB de antes&\#x27; sem detalhar essas configurações nesta seção\. Isso significa que a replicabilidade completa da configuração experimental para esses conjuntos de dados depende da consulta de outras partes do documento, que podem não fornecer detalhes granulares suficientes \(ex: arquiteturas de modelo específicas para o modelo de classificação subjacente f, hiperparâmetros, procedimentos de treinamento\)\.
- b:observation:sec\_19:method:1:baseline\_model\_clarity: O modelo de confiança baseline proposto, c\(xi\) = σ\(maxli\), é definido de forma clara usando notação padrão \(σ para sigmoide logística, li para vetor de logits\), tornando\-o fácil de entender e replicar\.
- c:observation:sec\_19:method:1:obs\_19\_1: O texto fundamenta o argumento de que a probabilidade do softmax é um proxy pobre para “confiança”, discutindo limites e a necessidade de uma métrica mais informativa do que a probabilidade em si\.
- c:observation:sec\_19:method:1:obs\_19\_2: São definidos explicitamente notação e um par de métricas para avaliar modelos de confiança, incluindo uma justificativa para evitar thresholding\.
- c:observation:sec\_19:method:1:obs\_19\_3: Há inconsistências/ambiguidade de símbolos e possivelmente erro tipográfico na definição de métrica \(ex\.: uso de “e” e “1\(b\)” com descrições pouco consistentes; além de termos quebrados que dificultam a leitura exata da fórmula\)\. Isso reduz clareza e pode afetar replicabilidade\.
- c:observation:sec\_19:method:1:obs\_19\_4: A fórmula do “soft F1 score” aparece com trechos quebrados/ambíguos \(por exemplo, “im”/“pr\. rc” e a forma final com apóstrofo\), o que impede reconstrução inequívoca para replicação\.
- c:observation:sec\_19:method:1:obs\_19\_5: O baseline de confiança é descrito de modo direto usando logits e uma função sigmoide aplicada ao máximo logit\.
- c:observation:sec\_19:method:1:obs\_19\_6: O texto menciona avaliar “mesmos setups” e usar MNIST/Twitter/IMDB e CIFAR\-10, mas os detalhes essenciais para replicar \(arquiteturas exatas, hiperparâmetros de treino, tamanhos de batch, seeds etc\.\) ficam fora deste trecho; isso limita a reprodutibilidade neste apêndice/ seção\.
- c:observation:sec\_19:method:1:obs\_19\_7: As métricas são reportadas em Table 12, mas não há explicitação neste trecho do significado preciso de “Test Set Error” e como exatamente foi calculado em relação ao problema de confiança \(ex\.: quais rótulos y correspondem; se é erro de classificação do modelo f, ou erro associado ao limiar/score\)\.

## Evidências

- a:criterion:meaningful\_comparison: A comparação central com o baseline de probabilidades softmax é relevante e há alguma comparação entre condições e domínios\. Contudo, a introdução não situa adequadamente a proposta no estado da arte, e os resultados fornecidos indicam ausência de outros baselines relevantes e de ablação do decodificador e do módulo\. Assim, a comparação é útil, mas estreita e insuficientemente contextualizada\.
- a:criterion:originality: O artigo declara contribuições identificáveis: um baseline baseado em probabilidades softmax, um método baseado em reconstrução e um conjunto de tarefas e métricas padronizadas, além de avaliação em vários domínios\. Contudo, a introdução não diferencia suficientemente essas contribuições de abordagens anteriores nem especifica quais métodos ou resultados prévios são superados, complementados ou reorganizados\. A novidade alegada é plausível, mas documentada de modo insuficiente para uma nota alta\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: As contribuições principais são apresentadas de forma relativamente explícita: um baseline baseado em probabilidades softmax, um método adicional baseado na reconstrução da entrada e uma proposta de tarefas e métricas padronizadas para avaliação\.
  - sec\_2: These prediction probabilities form our detection baseline
  - sec\_2: we contribute one method which outperforms the baseline on some \(but not all\) tasks\. This new method evaluates the quality of a neural network&\#x27;s input reconstruction to determine if an example is abnormal\.
  - sec\_2: another contribution of this work is the designation of standard tasks and evaluation metrics for assessing the automatic detection of errors and out\-of\-distribution examples\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3: A introdução enumera como contribuições um método de reconstrução, tarefas e métricas padronizadas, mas não as diferencia suficientemente de abordagens anteriores\. Embora cite trabalhos prévios e afirme que o método supera o baseline apenas em algumas tarefas, não especifica quais métodos ou resultados anteriores são superados, complementados ou reorganizados pela proposta\.
  - sec\_2: To give ideas for future detection research, we contribute one method which outperforms the baseline on some \(but not all\) tasks\.
  - sec\_2: In addition to the baseline methods, another contribution of this work is the designation of standard tasks and evaluation metrics for assessing the automatic detection of errors and out\-of\-distribution examples\.
  - sec\_2: This is consistent with a great deal of anecdotal evidence from researchers \(Nguyen &amp; O&\#x27;Connor, 2015; Yu et al\., 2010; Provost et al\., 1998; Nguyen et al\., 2015\)\.
- b:criterion:meaningful\_comparison: O artigo estabelece uma comparação significativa ao avaliar o desempenho do módulo de anormalidade proposto contra um baseline de probabilidade de previsão softmax, que é claramente definido\. Essa comparação é central para a contribuição do trabalho, demonstrando como o módulo de anormalidade pode superar o baseline em cenários específicos\. Embora algumas configurações de datasets sejam referenciadas a seções anteriores, a metodologia de comparação entre os métodos é bem articulada\.
- c:criterion:impact: O problema endereçado é diretamente relevante \(falha silenciosa e detecção de erro/abnormalidade com implicações para segurança e medicina\), e o artigo afirma evidência experimental em múltiplas arquiteturas/datasets e a possibilidade de superar o baseline com um módulo proposto\. Apesar de haver partes especulativas e falta de quantificação completa em alguns trechos, a relevância do tema e a direção de pesquisa derivada dos resultados são sustentadas pelo conteúdo fornecido\.
- c:observation:sec\_2:introduction:1:obs\_2\_1: O problema é explicitamente motivado com falhas em cenários reais \(desalinhamento treino\-teste\) e com o efeito de falha silenciosa em alta confiança, incluindo um exemplo concreto de impacto \(medicina/segurança\)\.
  - sec\_2: When machine learning classifiers are employed in real\-world tasks, they tend to fail when the training and test distributions differ\. Worse, these classifiers often fail silently by providing high\-confidence predictions while being woefully incorrect
  - sec\_2: For example, a medical diagnosis model may consistently classify with high confidence, even while it should flag difficult examples for human intervention\.
  - sec\_2: More generally and importantly, estimating when a model is in error is of great concern to AI Safety
- c:observation:sec\_15:conclusion:1:obs\_2: O texto apresenta a contribuição específica do módulo proposto e posiciona claramente sua vantagem como evidência de superação do baseline em alguns casos\.
  - sec\_15: We then presented the abnormality module, which provided superior scores for discriminating between normal and abnormal examples on tested cases\.
  - sec\_15: The abnormality module demonstrates that the baseline can be beaten in some cases, and this implies there is room for future research\.
- c:observation:sec\_15:conclusion:1:obs\_4: A conclusão conecta a relevância do problema a uma necessidade prática \(detectar quando falha um sistema de ML\), o que reforça impacto, ainda que sem quantificar utilidade\.
  - sec\_15: because knowing when a machine learn\- ing system fails strikes us as highly important\.
- c:criterion:meaningful\_comparison: O artigo compara explicitamente contra baselines \(por exemplo, baseline de softmax\) e discute por que métricas de detecção não devem ser reduzidas a acurácia\. Porém, nas evidências fornecidas, a comparação com alternativas relevantes aparece com suporte parcial e, em vários trechos, há remissões a tabelas sem detalhar métricas/limiares e condições de teste, dificultando checar se as comparações são justas e equivalentes em termos operacionais\.
- c:criterion:originality: O artigo anuncia uma contribuição metodológica \(um baseline baseado em estatísticas de softmax e um “abnormality module”\) e afirma que esse módulo pode superar o baseline em alguns casos, mas na evidência fornecida a novidade fica majoritariamente no nível declarativo e com poucos detalhes verificáveis na introdução \(faltam ganhos/métricas específicas e escopo operacional\)\.
- c:observation:sec\_2:introduction:1:obs\_2\_4: As contribuições são anunciadas, mas no trecho de introdução elas ficam majoritariamente em nível declarativo; faltam, aqui, detalhes verificáveis do método \(o que exatamente é feito\) e evidências quantitativas específicas \(ex\.: ganhos, métricas, “outperforms” em quais cenários\)\.
  - sec\_2: To give ideas for future detection research, we contribute one method which outperforms the baseline on some \(but not all\) tasks\.
  - sec\_2: This new method evaluates the quality of a neural network&\#x27;s input reconstruction to determine if an example is abnormal\.
  - sec\_2: In addition to the baseline methods, another contribution of this work is the designation of standard tasks and evaluation metrics
- c:criterion:soundness: Há justificativas plausíveis e discussões conceituais \(por exemplo, por que softmax pode falhar como proxy de confiança e por que métricas como AUROC/AUPR são relevantes\), mas a solidez inferencial é prejudicada por lacunas/ambiguidades frequentes em definições operacionais e pela falta de especificação completa de regras de decisão, mapeamentos de rótulos e detalhes de treinamento/detecção para vários cenários \(o que afeta a capacidade de sustentar conclusões com o desenho descrito\)\.
- c:observation:sec\_5:method:1:obs\_4: A seção critica o uso de probabilidade máxima de softmax como “confiança”, mas não define explicitamente como “translated to confidence” é implementado \(por exemplo, mapeamento/transformação\), dificultando reprodutibilidade do argumento quantitativo dentro da seção\.
  - sec\_5: Notice that the mean predicted/maximum class probabilities \(Pred\. Prob \(mean\)\) are above 75%, but if the prediction probability alone is translated to confidence, the softmax distribution should be more uniform for CIFAR\-100\.
  - sec\_5: This again shows softmax probabilities should not be viewed as a direct representation of confidence\.
- c:observation:sec\_11:method:1:obs\_11\_3: A geração de “noised training examples” é central para a classe anormal, mas não é descrita \(como se aplica ruído, quais transformações, parâmetros e distribuição do ruído\)\.
  - sec\_11: Then we train red layers on clean and noised training examples, and the sigmoid output of the red layers scores how normal the input is\.
  - sec\_11: Consequently, noised examples are in the abnormal class, clean examples are of the normal class, and the sigmoid is trained to output to which class an input belongs\.
- c:observation:sec\_12:method:1:obs\_12\_4: A regra de decisão/score usada para detecção não é totalmente especificada \(apenas “comparando” saídas; falta a métrica/funcional concreto, como distância, limiar, estatística e como é calibrado para AUROC/AUPR da Tabela 10\)\.
  - sec\_12: We detect abnormal examples by comparing the typical abnormality module outputs for clean examples with the outputs for the distorted examples\.

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
- Prompt sections/method: bc399c87f9cb4e474ecec5dd99b1034dbe9885660b9af69c902c5a1d46e5fddc
- Prompt sections/introduction: f9dba0ddf60b6a645f8f26bbc0d2493c669d9a46a163b45e168739cc37e555bf
- Prompt sections/conclusion: c4c502ddea161e91407c1491b62d9a7ccd898f65af92f609463b23499f9122db
- Prompt sections/discussion: 5dd2311d37013e80bba29771733ce044fa987df93b80011fbfd95139abba6837
- Prompt sections/results: 5389e503fa50e5a61b1c4bb10a858911cb5fe81e90d84953b2542ecc27e3139a
- Prompt cross\_checker: 4e8937f51926f97133f3debc15fa90ceb4162ea26650d19865a5b00fb3392102, 9253d720f45eb59a236b59d2623da920cbcdebd03c3af3e085cb827dc0b00dfe, bc40a3c7bfac8d760e7fc43661e10f4b0c5389afb04ad0e7a7722abcce6f85d2
- Prompt synthesizer: 985cc119b5e4342a2142a88af5f5b4ffb7cc379e92d3fe95fee2009320f100f8
- Prompt judge: 6eed71ce2bb679aa55770792f36a17c264f09b5967f821a3b222acc06eae9e3e
- Prompt reviser: 109193cf84b5b8b3aaae29e293ecec291351eb7773c6e2fa8a276f6ba0ab3b1f, 9f6b0de49ba29121d4c6ebd6694dbbde0fc94d54eaa2c64c6ce1ee0bf100c4de, e596ae66ba9f867cc3dd4dae5cc9bdc733115847e1a55b40233d466ad8147d07

## Itens pendentes

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5
- a:observation:sec\_3:method:1:sec\_3\_obs\_4
- a:observation:sec\_3:method:1:sec\_3\_obs\_6
- a:observation:sec\_4:method:1:sec\_4\_obs\_1
- a:observation:sec\_9:method:1:sec\_9\_obs\_2
- a:observation:sec\_9:method:1:sec\_9\_obs\_4
- a:observation:sec\_12:method:1:sec\_12\_obs\_7
- a:observation:sec\_18:method:1:sec\_18\_obs\_2
- a:observation:sec\_18:method:1:sec\_18\_obs\_3
- a:observation:sec\_19:method:1:sec\_19\_obs\_9
- a:check:claims\_vs\_results:claims\_vs\_results\_1
- a:check:method\_vs\_question:method\_vs\_question
- b:observation:sec\_2:introduction:1:intro\_problem\_clarity
- b:observation:sec\_2:introduction:1:intro\_baseline\_originality
- b:observation:sec\_3:method:1:sec\_3\_obs\_1
- b:observation:sec\_3:method:1:sec\_3\_obs\_2
- b:observation:sec\_3:method:1:sec\_3\_obs\_3
- b:observation:sec\_12:method:1:obs\_timit\_5
- b:observation:sec\_18:method:1:obs\_5
- b:observation:sec\_19:method:1:soft\_f1\_unconventional\_definition
- b:check:figure\_vs\_text:figure\_vs\_text\_review
- c:observation:sec\_2:introduction:1:obs\_2\_2
- c:observation:sec\_2:introduction:1:obs\_2\_3
- c:observation:sec\_3:method:1:obs\_1
- c:observation:sec\_3:method:1:obs\_2
- c:observation:sec\_3:method:1:obs\_3
- c:observation:sec\_3:method:1:obs\_4
- c:observation:sec\_3:method:1:obs\_5
- c:observation:sec\_3:method:1:obs\_6
- c:observation:sec\_3:method:1:obs\_7
- c:observation:sec\_4:method:1:sec\_4\_obs\_1
- c:observation:sec\_4:method:1:sec\_4\_obs\_2
- c:observation:sec\_4:method:1:sec\_4\_obs\_3
- c:observation:sec\_4:method:1:sec\_4\_obs\_4
- c:observation:sec\_4:method:1:sec\_4\_obs\_5
- c:observation:sec\_4:method:1:sec\_4\_obs\_6
- c:observation:sec\_7:method:1:obs\_1
- c:observation:sec\_7:method:1:obs\_2
- c:observation:sec\_7:method:1:obs\_3
- c:observation:sec\_7:method:1:obs\_4
- c:observation:sec\_7:method:1:obs\_5
- c:observation:sec\_7:method:1:obs\_6
- c:observation:sec\_10:method:1:obs\_sec\_10\_1
- c:observation:sec\_10:method:1:obs\_sec\_10\_2
- c:observation:sec\_10:method:1:obs\_sec\_10\_3
- c:observation:sec\_10:method:1:obs\_sec\_10\_4
- c:observation:sec\_13:results:1:obs\_4
- c:observation:sec\_13:results:1:obs\_5
- c:observation:sec\_15:conclusion:1:obs\_5
- c:check:claims\_vs\_results:crosscheck\_1
- c:check:figure\_vs\_text:fig\_vs\_text\_sec\_5\_3\.1\_computer\_vision
- c:criterion:substance

## Avisos

- As faixas de recomendação são provisórias e aguardam calibração\.
