# INCREMENTAL NETWORK QUANTIZATION: TOWARDS LOSSLESS CNNS WITH LOW\-PRECISION WEIGHTS

Run: `01a1e74d-e2cc-708f-83af-0cd143f7b823`

Recomendação: **major**
Nota ponderada: **2.33** · Concordância: **indisponível**

Revisão humana sinalizada: sim

## Critérios

### Originalidade

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Solidez

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `unresolved`
- Voto excluído de C: `evidence_not_validated`

### Substância

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Clareza

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- A (rodada 3, nota 2): A organização geral é razoavelmente clara: o problema, a lacuna, a contribuição e o ciclo do INQ são apresentados de modo direto \(sec\_2:introduction:1:sec\_2\_obs\_1; sec\_2:introduction:1:sec\_2\_obs\_2; sec\_3:method:1:sec\_3\_obs\_1; sec\_5:method:1:sec\_5\_obs\_1; sec\_6:method:1:sec\_6\_obs\_1\)\. Contudo, a clareza é prejudicada por notação matemática corrompida, fórmulas ambíguas, símbolos inconsistentes, ambiguidades sobre métricas e afirmações excessivamente abrangentes \(sec\_4:method:1:sec\_4\_obs\_2; sec\_4:method:1:sec\_4\_obs\_3; sec\_4:method:1:sec\_4\_obs\_4; sec\_5:method:1:sec\_5\_obs\_3; sec\_6:method:1:sec\_6\_obs\_3; sec\_6:method:1:sec\_6\_obs\_4; sec\_6:method:1:sec\_6\_obs\_9; sec\_10:method:1:sec\_10\_obs\_6; sec\_12:conclusion:1:sec\_12\_obs\_3\)\.
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Comparação

Nota: 3.00 · Dispersão: indisponível · Votos válidos: 1

- A (rodada 3, nota 3): Os trabalhos próximos são identificados e relacionados à proposta, incluindo pruning, vector quantization, deep compression e DNS; o artigo também explicita diferenças de escopo, precisão e representação dos pesos \(sec\_11:related\_work:1:sec\_11\_obs\_1; sec\_11:related\_work:1:sec\_11\_obs\_2\)\. Há comparações e ablação relevantes, como particionamento aleatório versus inspirado em poda no mesmo modelo e com 5 bits \(sec\_9:method:1:sec\_9\_obs\_1; sec\_9:results:1:sec\_9\_obs\_2; sec\_9:results:1:sec\_9\_obs\_2\)\. Porém, a normalização dos custos de armazenamento, índices, máscaras e Huffman não é suficientemente estabelecida, e alegações de superioridade ou de melhor resultado não são plenamente sustentadas por protocolos uniformes \(sec\_11:related\_work:1:sec\_11\_obs\_3; sec\_11:related\_work:1:sec\_11\_obs\_4; sec\_15:results:1:sec\_15\_obs\_5\)\.
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Impacto

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Reprodutibilidade

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- A (rodada 3, nota 2): Há alguns elementos úteis para reprodução, como a sequência operacional do algoritmo, frações acumuladas de quantização e certos hiperparâmetros experimentais \(sec\_6:method:1:sec\_6\_obs\_2; sec\_8:results:1:sec\_8\_obs\_1; sec\_10:method:1:sec\_10\_obs\_1\)\. Contudo, fórmulas essenciais estão corrompidas, faltam regras determinísticas de arredondamento, parâmetros de iteração, critérios de parada, política de taxa de aprendizado, definições dos objetos do pseudocódigo e detalhes dos protocolos de avaliação \(sec\_4:method:1:sec\_4\_obs\_2; sec\_4:method:1:sec\_4\_obs\_3; sec\_4:method:1:sec\_4\_obs\_4; sec\_6:method:1:sec\_6\_obs\_5; sec\_6:method:1:sec\_6\_obs\_6; sec\_7:results:1:sec\_7\_obs\_4; sec\_8:results:1:sec\_8\_obs\_4\)\.
- Voto excluído de B: `unresolved`
- Voto excluído de C: `evidence_not_validated`

## Pontos fortes

- A organização geral apresenta de forma direta o problema, a lacuna, o escopo do método e o ciclo iterativo de particionamento, quantização e retreinamento\. [a:observation:sec\_2:introduction:1:sec\_2\_obs\_1, a:observation:sec\_2:introduction:1:sec\_2\_obs\_2, a:observation:sec\_3:method:1:sec\_3\_obs\_1, a:observation:sec\_5:method:1:sec\_5\_obs\_1, a:observation:sec\_6:method:1:sec\_6\_obs\_1, a:criterion:clarity]
- O artigo identifica trabalhos próximos relevantes e explicita relações com pruning, vector quantization, deep compression e DNS, além de incluir uma comparação entre estratégias de particionamento\. [a:observation:sec\_11:related\_work:1:sec\_11\_obs\_1, a:criterion:meaningful\_comparison]
- O algoritmo fornece uma sequência operacional útil, incluindo inicialização, iterações, particionamento, determinação do conjunto de quantização, quantização, cálculo da perda e atualização dos pesos restantes\. [a:observation:sec\_6:method:1:sec\_6\_obs\_2, a:criterion:replicability]

## Pontos fracos

- A notação matemática e as fórmulas essenciais estão corrompidas ou inconsistentes, especialmente na definição do conjunto de quantização, no cálculo de n₂, no particionamento e na atualização dos pesos\. Isso compromete a clareza, a solidez e a implementação inequívoca do método\. [a:observation:sec\_4:method:1:sec\_4\_obs\_2, a:observation:sec\_4:method:1:sec\_4\_obs\_3, a:observation:sec\_4:method:1:sec\_4\_obs\_4, a:observation:sec\_5:method:1:sec\_5\_obs\_3, a:observation:sec\_6:method:1:sec\_6\_obs\_3, a:observation:sec\_6:method:1:sec\_6\_obs\_4, a:observation:sec\_6:method:1:sec\_6\_obs\_9, a:criterion:clarity, a:criterion:replicability]
- A descrição não fornece parâmetros suficientes para reprodução determinística, incluindo a escolha dos grupos de pesos, a sequência de frações acumuladas, o número de iterações, o critério de parada, a política de taxa de aprendizado e definições completas dos objetos do pseudocódigo\. [a:observation:sec\_5:method:1:sec\_5\_obs\_2, a:observation:sec\_6:method:1:sec\_6\_obs\_5, a:observation:sec\_6:method:1:sec\_6\_obs\_6, a:observation:sec\_9:method:1:sec\_9\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_4, a:criterion:replicability]
- As comparações de compressão não estabelecem suficientemente a normalização dos custos de índices, máscaras e Huffman, e a expressão dos ganhos como “absolute improvement” é ambígua\. Além disso, a redação das métricas mistura perdas em taxas de reconhecimento com reduções em taxas de erro\. [a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3, a:observation:sec\_11:related\_work:1:sec\_11\_obs\_4, a:observation:sec\_10:method:1:sec\_10\_obs\_6, a:criterion:meaningful\_comparison, a:criterion:clarity]

## Sugestões

- Reescrever integralmente as equações e o pseudocódigo com notação consistente, definindo sem ambiguidade os índices, os conjuntos, as máscaras, a regra de arredondamento, os limites de quantização, o tratamento do sinal e do zero e a atualização protegida dos pesos quantizados\. [a:observation:sec\_4:method:1:sec\_4\_obs\_2, a:observation:sec\_4:method:1:sec\_4\_obs\_3, a:observation:sec\_4:method:1:sec\_4\_obs\_4, a:observation:sec\_5:method:1:sec\_5\_obs\_3, a:observation:sec\_6:method:1:sec\_6\_obs\_3, a:observation:sec\_6:method:1:sec\_6\_obs\_4, a:observation:sec\_6:method:1:sec\_6\_obs\_9]
- Especificar todos os detalhes necessários para reprodução: regra operacional de particionamento, valores e sequência de σ\_n, N, critério de parada, política de taxa de aprendizado, parâmetros de treinamento, sementes ou número de execuções e definições dos objetos usados no algoritmo\. [a:observation:sec\_5:method:1:sec\_5\_obs\_2, a:observation:sec\_6:method:1:sec\_6\_obs\_5, a:observation:sec\_6:method:1:sec\_6\_obs\_6, a:observation:sec\_9:method:1:sec\_9\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_4]
- Uniformizar as comparações com uma convenção explícita de armazenamento, incluindo pesos, índices, máscaras e Huffman; definir precisamente se os ganhos são absolutos ou relativos; e distinguir consistentemente acurácia de taxa de erro\. Também convém qualificar a alegação de aplicabilidade a qualquer CNN para refletir o escopo experimental demonstrado\. [a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3, a:observation:sec\_11:related\_work:1:sec\_11\_obs\_4, a:observation:sec\_10:method:1:sec\_10\_obs\_6, a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3]

## Seções

### 1 INTRODUCTION

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1: A introdução explicita claramente o problema prático: modelos CNN profundos impõem custos elevados de memória e computação, dificultando sua implantação em dispositivos com recursos limitados\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: A lacuna de pesquisa é apresentada de forma direta e organizada em dois problemas específicos da quantização: perda não desprezível de acurácia e aumento do número de iterações de treinamento para obter convergência\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3 [unresolved]: A contribuição central é explicitada e diferenciada das estratégias globais anteriores: o INQ combina particionamento de pesos, quantização por grupos e retreinamento, aplicados iterativamente até que todos os pesos sejam quantizados\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_4: O impacto alegado é sustentado por resultados quantitativos concretos, incluindo ganhos de acurácia em múltiplas arquiteturas, rápida convergência e desempenho em larguras de bits muito baixas\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5 [unresolved]: A formulação da abrangência e do impacto é mais forte do que a evidência apresentada nesta introdução sustenta: expressões como “any pre\-trained” e “lossless” sugerem generalidade universal, embora os resultados descritos estejam concentrados em classificação ImageNet e em um conjunto específico de arquiteturas\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6: A motivação para a vantagem computacional do uso de potências de dois é plausível, mas o impacto em dispositivos reais não é demonstrado na introdução por medições de latência, energia ou hardware; a afirmação permanece no nível de possibilidade de implantação\.
- b:observation:sec\_2:introduction:1:problem\_statement\_clarity [unresolved]: O artigo articula claramente o problema de implantação de redes neurais convolucionais \(CNNs\) profundas em dispositivos com recursos limitados, devido à sua alta demanda computacional e de memória\. Ele também identifica especificamente duas questões críticas não resolvidas na quantização de CNNs: a perda não desprezível de precisão e o aumento do número de iterações de treinamento para garantir a convergência\.
- b:observation:sec\_2:introduction:1:contributions\_originality\_clarity [unresolved]: As contribuições do artigo são claramente apresentadas com a proposta do método Incremental Network Quantization \(INQ\), que visa converter modelos CNN de precisão total em versões de baixa precisão cujos pesos são restritos a potências de dois ou zero\. A originalidade é sustentada pela diferenciação de métodos existentes que adotam uma estratégia global, enquanto o INQ utiliza uma abordagem iterativa de partição de pesos, quantização por grupo e retreinamento, com o benefício explícito de substituir operações de multiplicação por deslocamento de bits\.
- b:observation:sec\_2:introduction:1:impact\_sustained\_evidence: O impacto do método INQ é fortemente sustentado por resultados experimentais abrangentes, demonstrando ganhos de precisão ou desempenho similar em comparação com baselines de precisão total em diversas arquiteturas de CNN \(AlexNet, VGG\-16, GoogleNet e ResNets\) e diferentes quantizações de baixa precisão \(5\-bit, 4\-bit, 3\-bit e 2\-bit\)\. Além disso, o artigo evidencia uma convergência mais fácil e rápida no treinamento e um desempenho superior ao método de compressão profunda, abordando diretamente as questões de perda de precisão e aumento de iterações de treinamento\.
- c:observation:sec\_2:introduction:1:obs\_2\_1 [unresolved]: O problema e as lacunas em quantização \(perda de acurácia e aumento de iterações para convergir\), que motivam o trabalho, estão explicitamente declarados\.
- c:observation:sec\_2:introduction:1:obs\_2\_2 [unresolved]: A novidade/ideia central do método INQ é descrita de forma relativamente concreta \(conjunto de três operações interdependentes e repetição incremental\) e diferenciada de uma estratégia global usada por abordagens existentes\.
- c:observation:sec\_2:introduction:1:obs\_2\_3: O impacto/relevância para aplicação em hardware embarcado/limitado é explicitamente conectado ao tipo de pesos \(potências de dois ou zero\), citando substituição de multiplicações por bit shift em hardware dedicado\.
- c:observation:sec\_2:introduction:1:obs\_2\_4 [unresolved]: Há alegação forte de potencial de “lossless low\-precision CNN model” e de “lossless” também na visão do método, mas a seção de introdução não apresenta evidência quantitativa para sustentar essa “lossless” além de promessas; os números aparecem apenas como pontos gerais \(ex\.: “improved accuracy”, “lossless model with 5\-bit weights in the experiments”\), sem detalhar métrica/definição de “lossless” na própria introdução\.
- c:observation:sec\_2:introduction:1:obs\_2\_5: O texto sugere a ausência de hipótese sobre a arquitetura \(“no assumption on the CNN architecture”\), mas a introdução também enfatiza validação em “ImageNet\.\.\. using almost all known deep CNN architectures”; isso pode criar uma tensão entre generalidade pretendida e escopo efetivamente testado \(sem declarar limites ou tipo de arquiteturas incluídas na introdução\)\.
- c:observation:sec\_2:introduction:1:obs\_2\_6: A introdução não explicita como a importância dos pesos é operacionalizada a partir da “pruning\-inspired measure” \(apenas cita Han et al\. e Guo et al\.\), o que reduz a clareza sobre qual componente garante a diferenciação frente ao estado da arte dentro do próprio texto de introdução\.

### 2 INCREMENTAL NETWORK QUANTIZATION

- a:observation:sec\_3:method:1:sec\_3\_obs\_1: A seção explicita de forma direta seu escopo: apresentar a intuição do INQ, seus componentes e sua implementação, o que estabelece uma organização adequada para a descrição do método\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_2: A frase introdutória é genérica e não antecipa quais são os componentes centrais nem como eles se relacionam; isso reduz a orientação inicial do leitor, embora as subseções posteriores possam suprir essa informação\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_3: Não é possível verificar, a partir do trecho fornecido, se a seção especifica hipóteses, parâmetros, procedimentos e informações suficientes para reproduzir o INQ; esses elementos deveriam ser explicitamente conferidos na descrição dos componentes e da implementação\.
- b:observation:sec\_3:method:1:method\_missing\_algorithm\_details: Apesar da Seção 2 prometer detalhar a implementação da Quantização Incremental de Rede \(INQ\) em sua introdução \(sec\_3\), o algoritmo central não é imediatamente apresentado nesta subseção, mas sim em uma subseção posterior \(Seção 2\.3\)\. Embora não impeça a reprodução, essa estrutura pode causar uma breve desorientação na leitura\.
- b:observation:sec\_3:method:1:method\_missing\_retraining\_hyperparameters: Embora alguns parâmetros de re\-treinamento, como o otimizador \(SGD com momentum e weight decay\) e tamanhos de batch, sejam mencionados em outras seções, o cronograma completo da taxa de aprendizado e o número exato de épocas para cada etapa de re\-treinamento para todos os bit\-widths não são especificados, dificultando a reprodutibilidade\.
- b:observation:sec\_3:method:1:method\_incomplete\_weight\_partitioning [unresolved]: A seção \`sec\_3\` serve como uma introdução à Seção 2, prometendo detalhar o método INQ\. Embora os detalhes completos dos componentes e implementação sejam apresentados em subseções posteriores, o texto introdutório é excessivamente breve, podendo gerar uma expectativa imediata de conteúdo metodológico que não é entregue nesta frase, o que, de forma menor, afeta a clareza da estrutura do artigo\.
- b:observation:sec\_3:method:1:method\_missing\_quantization\_mapping [unresolved]: A seção 2, embora introduza a Quantização Incremental de Rede \(INQ\) e prometa descrever seus componentes chave e implementação, não detalha explicitamente a representação de pesos de baixa precisão nem a função ou regra precisa para o mapeamento de quantização\. Esses detalhes são cruciais para a compreensão do método e sua replicabilidade\.
- b:observation:sec\_3:method:1:method\_general\_data\_description [unresolved]: Embora a tarefa de classificação ImageNet seja identificada como o conjunto de dados, detalhes específicos sobre pré\-processamento de dados, estratégias de aumento de dados ou a divisão exata usada para validação/teste não são descritos nas seções do método, o que é importante para uma replicação exata\.
- c:observation:sec\_3:method:1:sec\_3\_obs\_1: A seção anuncia explicitamente o que será feito: esclarecer a “insight” do INQ, descrever componentes\-chave e detalhar a implementação\.
- c:observation:sec\_3:method:1:sec\_3\_obs\_2: Não há, no trecho disponível desta seção, especificação de hipóteses, parâmetros, variáveis, ou passos operacionais; isso reduz a reprodutibilidade a partir do texto aqui observado\.
- c:observation:sec\_3:method:1:sec\_3\_obs\_3: O trecho não define formalmente componentes e, portanto, não permite verificar diretamente a consistência entre a promessa \(“key components”/“detail its implementation”\) e os detalhes necessários para inferir as alegações do método\.

### 2\.1 WEIGHT QUANTIZATION WITH VARIABLE\-LENGTH ENCODING

- a:observation:sec\_4:method:1:sec\_4\_obs\_1: A seção explicita o objetivo operacional da quantização: converter pesos de ponto flutuante de 32 bits em valores que sejam potências de dois ou zero, e relaciona a escolha do conjunto de valores ao orçamento de bits esperado\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2: A notação matemática está corrompida ou inconsistente em pontos essenciais: os expoentes das potências de dois, os índices dos pesos e a regra de arredondamento não são apresentados de forma inequívoca\. Isso impede determinar exatamente o conjunto de quantização e implementar a transformação sem recorrer a uma fonte externa ou ao contexto original da publicação\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: A expressão que determina n₂ não está suficientemente especificada: ela contém um termo fixo aparentemente dependente de uma variável ou parâmetro ausente, enquanto o texto afirma que n₂ é calculado a partir de b e n₁\. Assim, não é possível reproduzir os limites do conjunto de quantização para valores de b diferentes do exemplo fornecido\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_4: Faltam especificações necessárias para uma implementação determinística da regra de arredondamento, incluindo o tratamento de valores exatamente iguais aos limiares, a definição da primeira e da última vizinhança de potência, e a forma de atribuir valores fora do intervalo coberto\. A descrição também não deixa explícito como o sinal e o zero são tratados na própria equação\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: A explicação do orçamento de bits é conceitualmente útil, mas a cardinalidade do conjunto de candidatos também aparece com notação corrompida e não esclarece completamente como são codificados o sinal, o zero e os índices\. Isso dificulta verificar se o número de valores representáveis é compatível com o bit\-width declarado\.
- b:observation:sec\_4:method:1:quant\_B\_ambiguity [unresolved]: The variable &\#x27;B&\#x27; in Equation \(4\) is not explicitly defined\. While it is implied to be a quantum value from the set P₁, the specific rule for selecting &\#x27;B&\#x27; within the given interval \`\[\(α \+ β\)/2, 3β/2\)\` is not stated\. This ambiguity hinders the precise replication of the rounding logic\.
- b:observation:sec\_4:method:1:quant\_intervals\_incomplete: A Equação \(4\) descreve uma regra de arredondamento para valores que caem em um intervalo positivo específico \`\[\(α \+ β\)/2, 3β/2\)\` e atribui \`10\` para valores fora desse intervalo\. No entanto, uma definição abrangente de como todos os valores possíveis de números reais \(incluindo valores negativos, valores fora deste intervalo positivo específico e valores que seriam mapeados para outras potências de dois em P₁\) são mapeados para o conjunto completo de valores quânticos \`P₁ = \{±2^n1, \.\.\., ±2^n2, 0\}\` não é fornecida\. O uso de \`10\` como um valor &\#x27;otherwise&\#x27; também é inconsistente com a definição de \`P₁\`, que contém apenas potências de dois e zero, dificultando ainda mais a replicabilidade\. Uma partição completa da linha de números reais em intervalos de arredondamento, incluindo a clarificação de como \`B\` é escolhido a partir de \`α\` ou \`β\`, é crucial para a replicabilidade completa\.
- b:observation:sec\_4:method:1:n2\_formula\_typo: The formula for \`n₂\` is stated as \`n₂ = n₁ \+ 1 \- 2\(6\-1\)/2\`\. However, the provided example \(\`b = 3\` and \`n₁ = −1\` leading to \`n₂ = \-2\`\) strongly suggests a typographical error and that the formula should likely be \`n₂ = n₁ \+ 1 \- 2^\(\(b\-1\)/2\)\`\. While the example clarifies the intended computation, the written formula creates ambiguity and impacts clarity\.
- b:observation:sec\_4:method:1:correlation\_factors\_unexplained: The paper states that the factor \`4/3\` in Equation \(2\) and \`3/2\` in Equation \(4\) are correlated to ensure consistency in the quantization process\. However, the mechanistic explanation or derivation for this specific correlation is not provided\. While the formulas are given, a deeper understanding of the design choice would improve clarity and soundness, especially if the methodology needed to be adapted\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_1: A seção explicita uma regra de quantização baseada em um conjunto de valores discretos e condicionais por intervalo, o que favorece solidez e operacionalização\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_2: Há variáveis e notações cujo significado não fica completo no trecho \(por exemplo, α, β, Bsgn, e o uso do marcador “10”\), o que reduz clareza e reprodutibilidade\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_3: Existe inconsistência/possível erro de notação entre α/β e a/ẞ \(ou entre símbolos esperados para os limites\), dificultando a implementação fiel do mapeamento intervalar\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_4: A seção afirma “sem perda de model accuracy” e “lossless”, mas este trecho não apresenta condições/hipóteses verificáveis, nem demonstração, nem critérios operacionais para garantir a alegação\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_5: Apesar de definir b como “expected bit\-width”, faltam detalhes formais e completos sobre como converter b em um número exato de quantizações candidatas \(além do exemplo\), o que limita a reprodutibilidade para valores gerais de b\.

### 2\.2 INCREMENTAL QUANTIZATION STRATEGY

- a:observation:sec\_5:method:1:sec\_5\_obs\_1: A seção apresenta de forma conceitualmente coerente o ciclo central do INQ: particionamento dos pesos, quantização de um grupo, retreinamento do outro e repetição iterativa até que todos os pesos sejam convertidos\. Essa descrição conecta cada operação ao seu papel na redução da perda de acurácia\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_2: O procedimento não especifica nesta seção como os grupos de pesos devem ser escolhidos\. Como o particionamento determina quais pesos são quantizados e quais são retreinados, faltam critérios operacionais — por exemplo, a medida usada, o limiar, a proporção dos grupos e sua eventual variação entre iterações — para reproduzir o método\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_3: A definição matemática do particionamento contém problemas de notação e formatação que dificultam determinar precisamente o método: a união e a interseção dos conjuntos aparecem sem operadores completos, A\(2\) é posteriormente referido como A2, e a matriz binária é indicada ora por Ti, ora por Tr\. Também há inconsistência entre os índices de camada usados em W₁ e Wi\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_4 [unresolved]: A justificativa científica do procedimento é apresentada como uma conjectura derivada de trabalhos de poda, mas a seção não estabelece condições sob as quais o retreinamento necessariamente compensa o erro de quantização\. Assim, a afirmação ampla de obter quantização sem perda para qualquer CNN pré\-treinada não é sustentada apenas pela descrição metodológica e depende de validação experimental e de hipóteses adicionais\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_1: The method relies on a &\#x27;weight partition&\#x27; operation, dividing weights into two groups, but the specific strategies for this partition are not detailed in this section, hindering replicability\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_2: The &\#x27;group\-wise quantization&\#x27; step refers to using &\#x27;Equation \(4\)&\#x27; for quantization, but this equation is not provided or defined within the given text, making the quantization process irreproducible\.
- c:observation:sec\_5:method:1:obs\_5\_1: A seção explicita a motivação e o problema observado em baixas precisões \(queda de acurácia\) ao quantizar CNNs pré\-treinadas, conectando\-o diretamente ao objetivo de “lossless low\-precision quantization”\.
- c:observation:sec\_5:method:1:obs\_5\_2: A seção constrói um vínculo causal plausível entre a perda de acurácia em quantização global e a estratégia incremental do INQ, usando comparação com trabalhos existentes \(estratégia global vs\. estratégia particionada \+ re\-treinamento\)\.
- c:observation:sec\_5:method:1:obs\_5\_3 [unresolved]: O texto menciona “a well\-proven measure” para a partição \(weight partition\) e afirma que há um “assumption” crítico, mas não define qual métrica/medida é usada nem descreve como ela operacionaliza a partição \(o que limita a replicabilidade\)\.
- c:observation:sec\_5:method:1:obs\_5\_4: Embora a seção descreva o fluxo \(quantize grupo 1, re\-treine grupo 2 e itere\), ela não fornece parâmetros operacionais de treinamento \(ex\.: taxa de aprendizado, número de iterações, critério de parada, detalhes do re\-treinamento\), o que impede reprodução fiel\.
- c:observation:sec\_5:method:1:obs\_5\_5: Há uma inconsistência potencial de redação/organização: o texto afirma “Noticeable accuracy loss appeared \.\.\. when using small bit\-width values \(e\.g\., 5\-bit, 4\-bit, 3\-bit and 2\-bit\)”, mas o trabalho é apresentado como tendo potencial de “lossless” para 5\-bit/4\-bit/3\-bit \(o que pode gerar ambiguidade sobre em quais condições a perda ocorre e para quais arquiteturas/treinos\)\.
- c:observation:sec\_5:method:1:obs\_5\_6: A formulação de partição define conjuntos e uma matriz binária T, mas não especifica como Ti\(i, j\) é determinado \(isto depende das “strategies for group partition”\), nem fornece como isso se conecta a “Equation \(4\)” \(logo, a regra de quantização do grupo 1 não é recuperável apenas com este trecho\)\.

### 2\.3 INCREMENTAL NETWORK QUANTIZATION ALGORITHM

- a:observation:sec\_6:method:1:sec\_6\_obs\_1: A seção explicita a motivação da otimização incremental e conecta as três operações — particionamento, quantização e retreinamento — a um procedimento iterativo até a conversão de todos os pesos\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_2: O algoritmo fornece uma sequência operacional relativamente clara, incluindo inicialização, número de iterações, atualização da política de aprendizagem, particionamento, determinação do conjunto de quantização, quantização, cálculo da perda e atualização dos pesos restantes\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_3: A formula do passo de atualização está corrompida ou mal formatada, impedindo determinar com segurança a variável atualizada, o gradiente e a forma exata de aplicação da máscara\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_4: Há inconsistência notacional entre a restrição da otimização e a regra de atualização: a primeira usa explicitamente o gradiente da perda, enquanto a equação transcrita do retreinamento não mostra de forma legível esse gradiente nem deixa claro se a máscara multiplica o gradiente ou o incremento completo\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_5: O pseudocódigo não define suficientemente os objetos centrais usados na implementação, como A^\(1\), A^\(2\), T\_l, P\_l e os valores acumulados de quantização; além disso, a inicialização contém notação ambígua\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_6: O algoritmo não especifica os valores ou a sequência de \{σ\_n\}, o número total de iterações N, o critério de parada, nem a política concreta de reinicialização da taxa de aprendizagem\. Sem esses parâmetros, a reprodução exata do treinamento não é possível a partir desta seção\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_7: A afirmação de que o procedimento pode produzir um modelo sem perda de acurácia é apresentada como potencial, mas esta seção não fornece um critério operacional para definir ou verificar &\#x27;lossless&\#x27;, nem especifica tolerância, conjunto de avaliação ou comparação usada para essa decisão\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_8 [unresolved]: A justificativa para a aplicabilidade de SGD é plausível depois que P\_l e T\_l são fixados, mas a seção não esclarece como o gradiente é tratado nos pesos quantizados nem como os valores quantizados são mantidos exatamente no conjunto permitido durante as atualizações numéricas\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_9: A notação de índices e símbolos apresenta diversos erros de transcrição ou inconsistências — por exemplo, &\#x27;1 &lt; 1 &lt; L&\#x27;, &\#x27;Pı&\#x27;, &\#x27;Tı&\#x27; e &\#x27;σπ&\#x27; — que dificultam mapear inequivocamente as etapas do pseudocódigo às equações anteriores\.
- b:observation:sec\_6:method:1:M\-R\-1: The method relies on a set P\_l consisting of specific powers of two plus zero, but the process for determining these &\#x27;fixed number&\#x27; values is not explicitly described in this section, hindering reproducibility\.
- b:observation:sec\_6:method:1:M\-R\-2: The crucial Equation \(4\), which is used for quantizing weights in Algorithm 1, is not provided in the text\. Without this equation, the quantization step cannot be replicated\.
- b:observation:sec\_6:method:1:M\-R\-3: The details of the &\#x27;weight partition&\#x27; operation are insufficiently described\. Specifically, how &\#x27;ση&\#x27; is used to perform layer\-wise weight partition and how weights are divided into groups A\(1\) and A\(2\) is not clear\. The &\#x27;well\-proven measure&\#x27; mentioned in the abstract is not detailed here\.
- b:observation:sec\_6:method:1:M\-R\-4 [unresolved]: Key training hyperparameters for the stochastic gradient descent \(SGD\) method, such as the specific optimizer variant \(e\.g\., Adam, plain SGD with momentum\), batch size, and the number of epochs for re\-training within each iteration \(Step 7 of Algorithm 1\), are not specified\.
- b:observation:sec\_6:method:1:M\-R\-5: The learning rate schedule or &\#x27;learning policy&\#x27; mentioned in Algorithm 1 \(Step 3\) is not detailed\. Knowing how the base learning rate is reset and what policy is applied is essential for replicating the training process\.
- b:observation:sec\_6:method:1:M\-C\-1: The variables A\(1\) and A\(2\) are used in Algorithm 1 without explicit definition of what they represent, though their roles can be inferred from context \(quantized vs\. floating\-point weights\)\.
- b:observation:sec\_6:method:1:M\-C\-2: There appears to be a typo in Algorithm 1, Step 4, where &\#x27;A\(1\)&\#x27; is updated twice\. This may cause confusion about the intended operation\.
- b:observation:sec\_6:method:1:M\-C\-3: The number of iterations &\#x27;N&\#x27; for the main loop in Algorithm 1 is not defined, making it unclear how many times the incremental quantization and re\-training procedure is performed\.
- c:observation:sec\_6:method:1:obs\_1: A passagem afirma que resolver o problema de otimização com restrição direta é “challenging” por risco de “convergence problem”, mas não especifica quais condições causam esse problema \(hipóteses, mecanismo, exemplo\) nem fornece evidência empírica ou análise para sustentar essa justificativa\.
- c:observation:sec\_6:method:1:obs\_2: Há uma formulação de reconfiguração do problema e uma troca para uma versão “easier” via partição e quantização em grupo, mas o texto não descreve formalmente o que muda entre as duas formulações \(equivalência, aproximação ou relaxamento\) nem como exatamente as operações “reshape” o problema para a forma usada na otimização\.
- c:observation:sec\_6:method:1:obs\_3: A notação do gradiente/atualização apresenta inconsistência/ambiguidade: é apresentado um esquema do tipo “ΔE/ W\(i, j\) – Wi\(i, j\) \- \(W₁\(i, j\)\) Ti\(i, j\),” sem deixar claro o que é ΔE, qual variável é derivada, e se a atualização usa gradiente com sinal e passo \(ou substituição\)\. Isso compromete clareza e reprodutibilidade\.
- c:observation:sec\_6:method:1:obs\_4: O algoritmo \(Algorithm 1\) não define explicitamente detalhes necessários para reproduzir o procedimento: faltam descrições concretas do conteúdo e atualização de A\(1\), A\(2\), A\(l\), como “perform layer\-wise weight partition” altera A e T, e quais procedimentos embutidos em “Equation \(4\)” e “Equation \(8\)” devem ser implementados\.
- c:observation:sec\_6:method:1:obs\_5: A afirmação “lossless low\-precision CNN model” é apresentada como potencial/merit, mas aqui não são incluídos critérios, condições ou garantias verificáveis no trecho \(ex\.: quais hipóteses sobre bit\-width/partição permitem, como se valida “lossless”\)\. Isso limita a solidez da alegação dentro desta seção\.
- c:observation:sec\_6:method:1:obs\_6: A seção afirma que a matriz binária T₁ “forces zero update”, mas a explicação ainda poderia explicitar melhor \(i\) como T₁ aparece formalmente na regra de atualização e \(ii\) como isso corresponde diretamente a “masked re\-training” \(congelar entradas quantizadas\) ao longo das iterações\. Embora a regra inclua um termo com T₁, falta um esclarecimento textual mais explícito ligando esse termo ao efeito de máscara/cálculo do update para garantir que as entradas com T₁=0 permanecem congeladas durante o treino\.

### 3 EXPERIMENTAL RESULTS

- a:observation:sec\_7:results:1:sec\_7\_obs\_1: A avaliação cobre cinco arquiteturas CNN representativas e usa métricas padrão de classificação ImageNet, permitindo verificar se o método se aplica a modelos com arquiteturas distintas\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_2: O texto explicita a origem dos modelos de referência e identifica a exceção do ResNet\-18, incluindo a conversão entre frameworks; isso melhora a transparência da comparação e a replicabilidade do protocolo\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_3: A alegação de comparação justa não é plenamente sustentada: usar modelos de fontes e frameworks diferentes pode introduzir diferenças de pré\-processamento, implementação ou pesos, mas o trecho não informa verificações de equivalência nem quantifica o impacto dessa escolha, especialmente para o ResNet\-18\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_4: Não são especificados neste protocolo detalhes necessários para reproduzir exatamente a avaliação, como versão e divisão do dataset, normalização e demais transformações, política de avaliação além do center crop, e detalhes do processo de retreinamento da INQ\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_5: O protocolo não menciona repetições, sementes aleatórias, intervalos de confiança ou variância\. Assim, eventuais diferenças pequenas entre o modelo quantizado e o baseline não podem ser avaliadas quanto à estabilidade estatística a partir desta descrição\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_6: A formulação “covering almost all known deep CNN architectures” é excessiva e pouco verificável: cinco arquiteturas não estabelecem cobertura de “quase todas” as arquiteturas conhecidas, e o critério de seleção não é definido\.
- b:observation:sec\_7:results:1:ob\_baselines\_metrics: O artigo estabelece claramente os modelos de baseline \(full\-precision de 32 bits\) e as métricas de avaliação padrão \(taxas de erro top\-1 e top\-5\), o que contribui para a clareza e comparabilidade dos resultados\.
- b:observation:sec\_7:results:1:ob\_arch\_coverage: A seleção de diversas arquiteturas de CNN, como AlexNet, VGG\-16, GoogleNet, ResNet\-18 e ResNet\-50, demonstra a ampla aplicabilidade do método proposto, aumentando a substância dos experimentos\.
- b:observation:sec\_7:results:1:ob\_missing\_variance: O trecho não menciona a apresentação de variância ou testes de significância estatística para as taxas de erro \(top\-1 e top\-5\)\. A ausência dessas informações pode comprometer a solidez das conclusões sobre melhorias de acurácia ou perdas mínimas\.
- b:observation:sec\_7:results:1:ob\_missing\_ablation\_setup [unresolved]: Estudos de ablação para analisar estratégias de particionamento, que poderiam contribuir para a clareza e substância da compreensão do método, não são explicitamente apresentados na seção de resultados\. A subseção 3\.2, onde tais estudos seriam introduzidos, não está presente no texto fornecido, impossibilitando sua avaliação\.
- c:observation:sec\_7:results:1:obs\_1: A seção descreve um desenho experimental amplo para avaliar o INQ: “we perform extensive experiments on the ImageNet large scale classification task”\.
- c:observation:sec\_7:results:1:obs\_2: Há especificação concreta do benchmark \(tamanho do treino/validação e número de classes\) e dos critérios de avaliação \(top\-1 e top\-5 erro\), o que sustenta comparabilidade dentro do experimento\.
- c:observation:sec\_7:results:1:obs\_3: A cobertura de arquiteturas é explicitada \(AlexNet, VGG\-16, GoogleNet, ResNet\-18, ResNet\-50\), alinhando\-se com a alegação de avaliação em “almost all known deep CNN architectures”\.
- c:observation:sec\_7:results:1:obs\_4: O texto tenta garantir “fair comparison” ao especificar que modelos baseline são “pre\-trained full\-precision \(i\.e\., 32\-bit floating\-point\)” e de fontes públicas, reduzindo risco de viés por diferenças de treinamento/implementação\.
- c:observation:sec\_7:results:1:obs\_5: A seção \(como fornecida\) não apresenta números/estatísticas de resultados \(apenas descreve métricas e setup\), portanto a sustentação de afirmações de eficácia fica fora deste trecho\.

### 3\.1 RESULTS ON IMAGENET

- a:observation:sec\_8:results:1:sec\_8\_obs\_1: A seção cobre arquiteturas CNN substancialmente diferentes e fornece, para cada uma, detalhes relevantes de configuração, como proporção acumulada de pesos quantizados, tamanho do lote, weight decay e momentum\. Isso favorece a avaliação da aplicabilidade do INQ além de um único modelo\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_2: A principal conclusão é apresentada sem quantificar no texto a magnitude das melhorias nem sua variabilidade\. Para sustentar a afirmação de melhoria consistente sobre referências full\-precision, seriam necessários os valores completos de top\-1 e top\-5, diferenças absolutas, número de execuções e alguma medida de dispersão ou intervalo de confiança\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_3: A comparação com os modelos full\-precision pode não isolar o efeito da quantização, pois a seção não esclarece se os modelos de referência e quantizados usam exatamente os mesmos procedimentos de avaliação, inicialização, pré\-processamento, treinamento e seleção do melhor checkpoint\. Sem essa informação, a inferência de que a melhoria decorre do INQ fica incompleta\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_4 [unresolved]: O protocolo de treinamento ainda não é suficientemente reprodutível: não são especificados, nesta seção, taxa de aprendizado, agenda de decaimento, critério de parada, procedimento de seleção de checkpoints, política de avaliação e detalhes do cálculo dos limiares de partição\. A expressão &\#x27;no more than 8 epochs&\#x27; também deixa ambígua quantas épocas foram efetivamente usadas em cada arquitetura\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_5: A seção anuncia a comparação entre particionamento aleatório e particionamento inspirado em pruning, mas não apresenta seus resultados aqui e adota diretamente a segunda estratégia\. Como a escolha do particionamento pode afetar diretamente a quantização e o retreinamento, a justificativa depende de uma comparação quantitativa acessível e de uma ablação controlada\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_6: A afirmação sobre ResNet\-18 e ResNet\-34 é potencialmente imprecisa: dizer que a única diferença é o número de filtros não descreve integralmente a diferença entre essas arquiteturas, que também envolve profundidade e número de blocos\. Isso pode induzir a uma interpretação errada da generalização dos hiperparâmetros para outras ResNets\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_7: A melhoria simultânea de acurácia em relação ao modelo full\-precision não é suficiente, por si só, para sustentar a caracterização de quantização &\#x27;lossless&\#x27;: seria necessário esclarecer se &\#x27;lossless&\#x27; significa não degradar acurácia dentro da variabilidade experimental ou preservar exatamente o desempenho, além de relatar custos e eventuais mudanças no procedimento de treinamento\.
- b:observation:sec\_8:results:1:obs\_1: O artigo estabelece claramente modelos de precisão total \(full\-precision\) como baselines de comparação, o que é fundamental para avaliar o desempenho do método de quantização proposto\.
- b:observation:sec\_8:results:1:obs\_2: Embora o artigo afirme que os modelos quantizados apresentam &quot;taxas de reconhecimento top\-1 e top\-5 consistentemente melhoradas&quot;, o texto desta seção não inclui medidas estatísticas como variância ou desvio padrão para os resultados apresentados na Tabela 1 \(que é referenciada\)\. Isso dificulta a avaliação da estabilidade e significância estatística das melhorias alegadas com base apenas no texto\.
- b:observation:sec\_8:results:1:obs\_3: O artigo referencia claramente a Seção 3\.2 para justificar a escolha da estratégia de particionamento de pesos, e esta seção de fato existe e contém a análise prometida, contribuindo positivamente para a clareza e substância do artigo\.
- b:observation:sec\_8:results:1:obs\_4: O artigo fornece configurações de parâmetros detalhadas \(porções acumuladas de pesos quantizados, tamanho do lote, decaimento de peso, momentum\) para cada arquitetura CNN testada \(AlexNet, VGG\-16, GoogleNet, ResNet\-18, ResNet\-50\)\. Este nível de detalhe é crucial para a replicabilidade dos experimentos\.
- c:observation:sec\_8:results:1:obs\_1: O desenho experimental é apresentado explicitamente para comparar INQ em arquiteturas CNN diferentes sob um mesmo cenário de quantização \(bit\-width esperado\)\.
- c:observation:sec\_8:results:1:obs\_2: A conclusão de “consistently improved top\-1 and top\-5 recognition rates” é afirmada sem reproduzir valores/relatos numéricos nesta seção \(remete\-se à Tabela 1 sem citar números ou resultados concretos aqui\)\.
- c:observation:sec\_8:results:1:obs\_3: Não há indicação do critério estatístico/variância \(por exemplo, número de repetições e variação\) para suportar a afirmação de melhoria consistente\.
- c:observation:sec\_8:results:1:obs\_4: A seção afirma que a estratégia de partição escolhida será justificada por resultados em “Section 3\.2”, mas este conteúdo de análise não aparece aqui; a justificativa depende de outra seção\.
- c:observation:sec\_8:results:1:obs\_5 [unresolved]: Os hiperparâmetros de treinamento/otimização são detalhados por arquitetura \(batch size, weight decay, momentum e escalonamento de “accumulated portions of quantized weights”\), o que melhora reprodutibilidade\.
- c:observation:sec\_8:results:1:obs\_6: A descrição do “re\-training” é vaga quanto a detalhes críticos \(por exemplo, taxa de aprendizado, agendamentos e esquema de otimização\), apesar de informar o limite de épocas\.

### 3\.2 ANALYSIS OF WEIGHT PARTITION STRATEGIES

- a:observation:sec\_9:method:1:sec\_9\_obs\_1: O desenho compara diretamente duas estratégias de particionamento sob a mesma largura de 5 bits e apresenta os resultados para o mesmo modelo, permitindo uma comparação controlada no escopo do experimento\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_2: Os valores reportados no texto correspondem aos valores da Tabela 2, incluindo as reduções de 1,09 ponto percentual no erro top\-1 e 0,83 ponto percentual no erro top\-5 para a estratégia pruning\-inspired\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A definição operacional da estratégia pruning\-inspired não é suficientemente especificada neste trecho: não se informa o limiar ou a regra exata baseada no valor absoluto, nem como os pesos são distribuídos entre os dois grupos\. Isso dificulta reproduzir precisamente a comparação\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_4: A descrição remete os parâmetros ao Section 3\.1, em vez de apresentá\-los neste experimento; portanto, a reprodução depende de localizar essa seção e de saber quais configurações foram mantidas, além das 4 épocas de re\-treinamento explicitamente informadas\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_5: A conclusão de que a estratégia pruning\-inspired é superior baseia\-se em uma única execução aparente em um único modelo, sem informação sobre repetições, sementes aleatórias, variabilidade ou significância estatística\. Assim, os dados sustentam a vantagem observada, mas não estabelecem sua generalidade ou robustez\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_6: Falta uma comparação de variabilidade ou incerteza dos erros top\-1 e top\-5, bem como uma avaliação em mais arquiteturas ou modelos, para verificar se a vantagem do particionamento pruning\-inspired não é específica ao ResNet\-18 ou à execução apresentada\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_1: A comparação mantém constantes as configurações experimentais declaradas, o que favorece uma atribuição mais direta da diferença de desempenho à estratégia de particionamento\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_2: A seção apresenta uma ablação diretamente relevante para o método: compara particionamento aleatório e particionamento inspirado em poda no mesmo modelo e com a mesma largura de quantização\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_3: A tabela reporta duas métricas de erro para ambas as estratégias, e os valores permitem verificar a diferença observada: 1,09 ponto percentual no top\-1 e 0,83 ponto percentual no top\-5\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_4: A evidência é limitada a um único backbone, ResNet\-18, e a uma única largura de quantização; portanto, o experimento não sustenta por si só a generalização de que a estratégia inspirada em poda é superior para outras arquiteturas ou configurações\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_5: Não são reportadas repetições, sementes aleatórias, desvios\-padrão, intervalos de confiança ou testes estatísticos\. Assim, não é possível avaliar se as diferenças de 1,09 e 0,83 ponto percentual são robustas à variabilidade de treinamento e particionamento\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_6: A seção não especifica detalhes essenciais das estratégias, como a proporção de pesos alocada a cada grupo, o critério exato usado pelo particionamento inspirado em poda e o procedimento de amostragem do particionamento aleatório\. Isso dificulta reproduzir e interpretar a ablação\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_7: A comparação fixa quatro épocas de retreinamento, mas não justifica que esse orçamento seja suficiente ou igualmente adequado para as duas estratégias; diferenças de convergência podem, portanto, contribuir para o resultado\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_8: O texto chama as diferenças de “decrease” de 1,09% e 0,83%, mas a tabela fornece taxas em porcentagem; a diferença calculada é mais precisamente de 1,09 e 0,83 pontos percentuais, não necessariamente uma redução percentual relativa\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_1: The specific algorithm or thresholding mechanism used for the &\#x27;pruning\-inspired strategy&\#x27; for weight partition is not explicitly detailed, making it difficult to reproduce\. While the intuition &\#x27;weights with larger absolute values are more important&\#x27; is provided, the precise method for translating this into a partitioning scheme \(e\.g\., a specific percentile cut\-off, a dynamic threshold, or the exact process of forming the &\#x27;low\-precision base&\#x27;\) is absent\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_2: The &\#x27;random strategy&\#x27; for weight partition is described as weights having &\#x27;equal probability to fall into the two disjoint groups&\#x27;, but it lacks details on how these two groups are formed \(e\.g\., the specific proportion of weights assigned to each group in a layer\) which is essential for reproduction\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_3: The section clearly specifies key experimental parameters such as the test case \(ResNet\-18\), the number of epochs for re\-training \(4 epochs\), and the quantization bit\-width \(5\-bit\)\. It also explicitly refers to &\#x27;Section 3\.1&\#x27; for other parameter settings, which is a good practice for maintaining clarity and avoiding redundancy if Section 3\.1 provides these details comprehensively\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_4: The conclusion that &\#x27;pruning\-inspired partition is better than random partition&\#x27; is well\-supported by the quantitative results presented in Table 2, which clearly show a decrease in both top\-1 and top\-5 error rates for the pruning\-inspired method under consistent experimental conditions\.
- b:observation:sec\_9:results:1:obs\_9\_1: The section presents a clear and justified ablation study comparing two weight partition strategies \(random vs\. pruning\-inspired\)\. The experimental setup and the resulting performance metrics \(Top\-1 and Top\-5 error rates\) are explicitly provided, supporting the choice of the pruning\-inspired strategy for the proposed method\.
- b:observation:sec\_9:results:1:obs\_9\_2: While the comparison between the two weight partition strategies shows a clear numerical difference in error rates, the results are presented as single point estimates without any discussion or presentation of variance \(e\.g\., standard deviation over multiple runs\)\. This limits the statistical robustness of the conclusions regarding the superiority of the pruning\-inspired strategy\.
- c:observation:sec\_9:method:1:obs\_1: O texto descreve um desenho comparativo entre duas estratégias de partição \(aleatória vs\. baseada em poda\) e usa ResNet\-18 como caso de teste\.
- c:observation:sec\_9:method:1:obs\_2: A afirmação de melhora \(diferenças percentuais de erro top\-1 e top\-5\) é apresentada sem discutir variação estatística/repetições, limitações do experimento \(p\.ex\., número de runs\) e robustez\.
- c:observation:sec\_9:method:1:obs\_3: O texto afirma que as configurações são idênticas às descritas na Seção 3\.1, mas não as detalha aqui; isso reduz a reprodutibilidade a partir apenas desta seção\.
- c:observation:sec\_9:method:1:obs\_4: A estratégia “pruning\-inspired” é caracterizada conceitualmente \(usar valores absolutos maiores\), mas não é especificado o critério operacional exato de particionamento \(p\.ex\., por camada, percentuais/tamanhos dos grupos, ordenação e tie\-breaking\)\.
- c:observation:sec\_9:method:1:obs\_5: A Tabela 2 fornece os números correspondentes às duas estratégias sob bit\-width 5, conectando diretamente as conclusões quantitativas ao quadro de resultados\.
- c:observation:sec\_9:results:1:obs\_1: O texto apresenta uma comparação experimental direta entre duas estratégias de weight partition, usando o mesmo modelo \(ResNet\-18\) e configuração equivalente, com métricas top\-1 e top\-5 para quantização de 5\-bit\.
- c:observation:sec\_9:results:1:obs\_2: A hipótese motivacional para a estratégia pruning\-inspired é explicitada \(maiores valores absolutos como base de baixa precisão\), conectando o racional ao procedimento de particionamento\.
- c:observation:sec\_9:results:1:obs\_3 [unresolved]: Há uma inconsistência/ambiguidade numérica entre a variação declarada \(top\-5 de 11\.73% para 10\.90%\) e a “decrease” reportada como 0\.83% \(diferença aritmética exata seria 0\.83% apenas se 11\.73\-10\.90=0\.83\), mas o valor na tabela está em formato que não explicita claramente o cálculo de arredondamento; isso reduz a rastreabilidade/precisão do resultado\.
- c:observation:sec\_9:results:1:obs\_4: O texto não informa repetição estatística/variância \(ex\.: múltiplas sementes, desvio\-padrão ou testes de significância\) para sustentar que a diferença observada \(especialmente em top\-5\) é robusta\.
- c:observation:sec\_9:results:1:obs\_5: O texto conclui diretamente que a estratégia pruning\-inspired é a escolhida “in this paper”, mas a evidência apresentada está restrita a um único backbone \(ResNet\-18\) e a uma única configuração de bit\-width \(5\-bit\), limitando a generalização implícita\.
- c:observation:sec\_9:results:1:obs\_6: O mecanismo exato de “pruning\-inspired strategy” não é especificado \(apenas o critério geral por valor absoluto\), o que limita a replicabilidade do particionamento\.

### 3\.3 THE TRADE\-OFF BETWEEN EXPECTED BIT\-WIDTH AND MODEL ACCURACY

- a:observation:sec\_10:method:1:sec\_10\_obs\_1: O procedimento experimental explicita as frações acumuladas de pesos quantizados para os modelos de 4, 3 e 2 bits, além de informar que o número de épocas aumenta até 30 no modelo ternário de 2 bits\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_2: A comparação inclui três níveis de precisão, permitindo investigar empiricamente o compromisso entre bit\-width e acurácia e testar o limite alegado de quantização de baixa precisão\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: A seção não informa explicitamente os valores de batch size, weight decay e momentum, remetendo apenas aos parâmetros do segundo conjunto de experimentos\. A reprodução depende de localizar essa configuração em outra seção e de confirmar que todos os demais parâmetros também permanecem inalterados\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: Não são especificados nesta passagem detalhes necessários para reproduzir integralmente o treinamento, como taxa de aprendizado, política de ajuste da taxa, inicialização, critério de parada, número de execuções e sementes aleatórias\. A menção a que os parâmetros são os mesmos do segundo conjunto não esclarece se esses aspectos também foram mantidos\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_5: A conclusão de que os modelos são melhores que BWN e TWN não é sustentada quantitativamente nesta passagem: os valores dos baselines, seus protocolos de treinamento e a definição exata da métrica são deixados para as tabelas mencionadas\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: A redação das métricas é ambígua e potencialmente inconsistente: primeiro são relatadas perdas em top\-1 e top\-5 recognition rates, mas depois se afirma uma decrease em top\-1 e top\-5 error rate\. Uma redução da taxa de erro representa melhora, enquanto uma perda na taxa de reconhecimento representa piora; é necessário indicar claramente se os números são diferenças de acurácia ou de erro e seus sinais\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_7: A afirmação de que o modelo de 4 bits tem acurácia melhor que o modelo de 5 bits e que o modelo de 3 bits apresenta perdas específicas não vem acompanhada, nesta passagem, dos valores absolutos, intervalos de incerteza ou número de repetições\. Assim, a magnitude e a significância dessas diferenças não podem ser avaliadas apenas pelo texto\.
- b:observation:sec\_10:method:1:sec\_10\_obs1: Os autores referenciam de forma eficaz os parâmetros de treinamento \(batch size, weight decay e momentum\) a um &\#x27;segundo conjunto de experimentos&\#x27;\. Esta abordagem evita a repetição desnecessária de informações detalhadas, contribuindo para a concisão e clareza geral do texto, sem comprometer a replicabilidade do experimento, uma vez que a informação está disponível em outra seção\.
- b:observation:sec\_10:method:1:sec\_10\_obs2: O número de épocas de treinamento para os modelos de 4\-bit e 3\-bit não é especificado\. Embora seja mencionado que aumenta com a redução da largura de bits e atinge 30 para o modelo de 2\-bit, a ausência dos valores exatos para os outros modelos de baixa precisão dificulta a reprodução completa do método\.
- b:observation:sec\_10:method:1:sec\_10\_obs3: As porções acumuladas de pesos quantizados em cada etapa iterativa são claramente detalhadas para os modelos de 4\-bit, 3\-bit e 2\-bit\. Essa especificação precisa dos hiperparâmetros contribui positivamente para a clareza e replicabilidade do método\.
- c:observation:sec\_10:method:1:obs\_1: O procedimento experimental para o “limite do expected bit\-width” é descrito com um conjunto específico de valores de “accumulated portions of quantized weights at iterative steps” para 4\-bit, 3\-bit e 2\-bit ternary models\.
- c:observation:sec\_10:method:1:obs\_2: A descrição afirma que parâmetros como “batch size”, “weight decay” e “momentum” são “completely the same” do segundo conjunto, mas não fornece os valores aqui, exigindo referência a outra seção para reprodutibilidade completa\.
- c:observation:sec\_10:method:1:obs\_3: O texto usa “accumulated portions of quantized weights at iterative steps”, mas não define claramente como esses percentuais se conectam ao número de iterações/rodadas de INQ \(ex\.: quantas iterações correspondem a cada conjunto e como isso é implementado\), o que pode gerar interpretações divergentes\.
- c:observation:sec\_10:method:1:obs\_4: A alegação de “lossless network quantization” não é formalizada por um critério operacional mensurável no texto\. Apesar de serem reportadas quedas em top\-1/top\-5, não há definição explícita de o que “lossless” significa \(por exemplo, acurácia idêntica/igualdade exata, ou queda tolerada abaixo de um limiar em top\-1/top\-5\)\. Isso reduz a verificabilidade e a replicabilidade da conclusão sobre o limite do expected bit\-width\.
- c:observation:sec\_10:method:1:obs\_5 [unresolved]: Há comparação com referências específicas \(full\-precision e modelos BWN/TWN\), com métricas de reconhecimento/erro para apoiar a argumentação de desempenho relativo em bit\-widths baixos\.
- c:observation:sec\_10:method:1:obs\_6: O texto menciona o aumento do número de epochs conforme o expected bit\-width diminui e dá o valor para 2\-bit \(30 epochs\), mas não especifica os números de epochs para 4\-bit e 3\-bit neste trecho\.

### 3\.4 Low\-BIT DEEP COMPRESSION

- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_1: Os trabalhos mais próximos aparecem de forma explícita: deep compression de Han et al\. \(2016\), pruning de Han et al\. \(2015\), vector quantization de Gong et al\. \(2014\) e DNS de Guo et al\. \(2016\)\. O texto também explica como esses componentes se relacionam, o que torna o posicionamento da proposta verificável\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_2: A diferença da proposta em relação aos trabalhos citados está clara em três dimensões: o INQ é aplicado a todas as camadas, busca ausência de perda de acurácia e restringe os pesos a potências de dois ou zero\. Além disso, o texto explicita a consequência para hardware, distinguindo a proposta de métodos cujos pesos finais permanecem em ponto flutuante\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3: A comparação de compressão combina INQ e DNS e a contrapõe ao deep compression, que também combina várias técnicas\. Embora essa escolha seja plausível, o texto não explicita suficientemente, neste trecho, se as taxas reportadas usam exatamente a mesma convenção de armazenamento, os mesmos custos de índices/máscaras e o mesmo tratamento do código Huffman\. Sem essa normalização, a alegação de superioridade pode não ser plenamente comparável\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_4: A formulação dos ganhos de compressão é ambígua: “51\.43%/96\.30% absolute improvement in compression performance” não deixa claro se os valores são diferenças relativas ou absolutas, nem a que referências correspondem exatamente\. Essa ambiguidade dificulta avaliar a magnitude da contribuição e deveria ser resolvida no texto ou diretamente na explicação da Tabela 5\.
- b:observation:sec\_11:related\_work:1:sec\_11\_obs\_1 [unresolved]: The section provides a clear and detailed comparison with the deep compression method \(Han et al\., 2016\), highlighting its components, limitations, and how the proposed INQ combined with DNS achieves superior compression and accuracy\.
- b:observation:sec\_11:related\_work:1:sec\_11\_obs\_2: The comparison between INQ and vector quantization \(Gong et al\., 2014\) is clearly articulated, detailing experimental conditions and highlighting the specific advantages of INQ in handling all network layers simultaneously without accuracy loss\.
- b:observation:sec\_11:related\_work:1:sec\_11\_obs\_3: The paper clearly distinguishes INQ&\#x27;s unique contribution by emphasizing that its final weights are powers of two or zero, enabling cheaper binary bit shift operations, which is a significant architectural and computational advantage over existing floating\-point weight methods\.
- c:observation:sec\_11:related\_work:1:obs\_1: O texto compara explicitamente o método do estado da arte \(Han et al\., 2016\) com a proposta do artigo, descrevendo a composição do método anterior e como a abordagem combinada \(INQ\+DNS\) busca superar resultados\.
- c:observation:sec\_11:related\_work:1:obs\_2 [unresolved]: A diferença da proposta em relação a Han et al\. \(2016\) é apresentada com especificidade operacional: o artigo explicita limitações atribuídas ao pruning \(menor ganho em convoluções e tempo de processamento\) e o papel do DNS para acelerar e melhorar a etapa de pruning\.
- c:observation:sec\_11:related\_work:1:obs\_3: O texto faz uma comparação adicional com outra alternativa \(vector quantization de Gong et al\., 2014\) sob um critério de comparação explícito \(re\-training para ser justo\) e declara a diferença de onde a quantização atua \(parâmetros FC vs\. todas as camadas\)\.
- c:observation:sec\_11:related\_work:1:obs\_4: A seção afirma que a comparação é “for fair comparison”, mas não deixa claro como a “fairness” é garantida em todos os aspectos \(por exemplo, como a penalidade/condição de precisão é comparada entre composições\), deixando a correspondência com as tabelas mais dependente de consulta externa\.
- c:observation:sec\_11:related\_work:1:obs\_5 [unresolved]: Há uma afirmação categórica sobre “no accuracy loss” para INQ em 5\-bit e 4\-bit, enquanto a comparação com vector quantization inclui perdas de acurácia quantificadas; porém, a base dessa alegação de ausência de perda não é suportada dentro do trecho \(remete ao conjunto de experimentos/Tabelas\), o que pode reduzir a clareza e exigir confirmação no material completo\.

### 4 CONCLUSIONS

- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_1: A conclusão apresenta de forma clara a contribuição central — o INQ — e resume seus principais componentes operacionais, permitindo relacionar diretamente o método ao objetivo de obter CNNs de baixa precisão\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_2: O impacto demonstrado é relevante: a conclusão reporta resultados em várias arquiteturas e em diferentes precisões, incluindo modelos ternários de 2 bits, o que sustenta a aplicabilidade ampla do método no cenário experimental avaliado\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3: A formulação universal de que o método converte “any pre\-trained” CNN em uma versão “lossless” é mais abrangente do que o alcance explicitamente demonstrado, que se concentra em modelos específicos e na classificação ImageNet\. A conclusão deveria qualificar essa alegação como ausência de perda de acurácia nos experimentos realizados\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_4: As aplicações em ativações, gradientes e hardware são apresentadas como trabalhos futuros; portanto, a conclusão distingue parcialmente resultados obtidos de potencial futuro, mas poderia explicitar que eficiência computacional e energética ainda não foram demonstradas no artigo\.
- b:observation:sec\_12:conclusion:1:concl\_clarity\_method [unresolved]: A seção de conclusão resume de forma clara e concisa o problema abordado e a metodologia proposta \(INQ\), incluindo suas operações centrais e natureza iterativa\.
- b:observation:sec\_12:conclusion:1:concl\_clarity\_results\_support: As conclusões sobre os resultados são apresentadas de forma clara e são amplamente apoiadas pelos experimentos extensivos descritos, demonstrando que a maioria dos modelos quantizados mantém ou supera a precisão dos baselines de precisão total, com algumas exceções pontuais para os modelos ternários de 2 bits\.
- b:observation:sec\_12:conclusion:1:concl\_impact\_future\_work: A seção de conclusão articula eficazmente o impacto do método proposto, destacando sua capacidade de quantização de baixa precisão sem perdas, e distingue claramente as conquistas atuais de futuras direções de pesquisa, o que contribui para a clareza e o impacto geral\.
- c:observation:sec\_12:conclusion:1:obs\_1: A conclusão explicita claramente o objetivo central do método \(converter CNNs pré\-treinadas em baixa precisão com restrição aos valores permitidos\)\.
- c:observation:sec\_12:conclusion:1:obs\_2: A conclusão afirma resultados amplos \(melhor ou comparável à referência\) e menciona múltiplos bit\-widths, mas sem conectar explicitamente essas alegações a tabelas/figuras/quantificações dentro desta seção de conclusão\.
- c:observation:sec\_12:conclusion:1:obs\_3: Fica faltando um fechamento mais alinhado aos resultados apresentados \(por exemplo, citar diretamente quais configurações/arquiteturas e o nível de bit\-width onde houve melhoria, com evidência numérica\), para tornar o impacto demonstrado mais verificável nesta seção\.

### A APPENDIX 1: STATISTICAL ANALYSIS OF THE QUANTIZED WEIGHTS

- a:observation:sec\_14:results:1:sec14\-strength\-1: A tabela fornece uma análise quantitativa por camada, cobrindo todas as camadas convolucionais e totalmente conectadas do AlexNet, e permite verificar diretamente as principais concentrações de pesos\.
- a:observation:sec\_14:results:1:sec14\-strength\-2 [unresolved]: As afirmações quantitativas sobre Conv1, Conv2 e FC6 são compatíveis com os percentuais da tabela: os conjuntos indicados somam aproximadamente 60,8%, 94,1% e 98,1%, respectivamente\.
- a:observation:sec\_14:results:1:sec14\-weakness\-1: A afirmação de que a segunda camada totalmente conectada apresenta resultados semelhantes aos de FC6 é pouco sustentada pela tabela: o conjunto de valores especificado soma cerca de 93,0% em FC7, contra cerca de 98,1% em FC6\. A diferença de aproximadamente cinco pontos percentuais deveria ser discutida ou a linguagem deveria ser qualificada\.
- a:observation:sec\_14:results:1:sec14\-weakness\-2 [unresolved]: As conclusões de que as distribuições das camadas convolucionais são &\#x27;mais dispersas&\#x27; e de que isso explica parcialmente a maior dificuldade de compressão não são operacionalizadas nem testadas\. A tabela mostra frequências, mas não apresenta uma métrica de dispersão, entropia, número efetivo de valores, taxa de compressão ou uma ablação que isole esse mecanismo\.
- a:observation:sec\_14:results:1:sec14\-missing\-1: A análise não informa os números absolutos de pesos por camada, nem apresenta variância, intervalos de confiança ou replicações\. Isso limita a avaliação da estabilidade dos percentuais, especialmente para valores muito pequenos como &\#x27;1e\-5%&\#x27; e &\#x27;0\.002%&\#x27;\.
- a:observation:sec\_14:results:1:sec14\-weakness\-3: A conclusão sobre a largura necessária de quatro bits depende de uma convenção de codificação que não é explicitada novamente nesta seção: o modelo é chamado de “5\-bit”, mas a linha “Bit\-width” registra 4 para todas as camadas\. O texto deveria distinguir claramente largura dos valores não nulos, bit reservado para zero e largura total esperada\.
- a:observation:sec\_14:results:1:sec14\-missing\-2: A generalização para que as distribuições das camadas convolucionais 3–5 sejam semelhantes à da Conv2 é apenas qualitativa\. Seria necessário indicar um critério de similaridade ou fornecer estatísticas agregadas para sustentar essa comparação entre camadas\.
- b:observation:sec\_14:results:1:obs1: The statistical analysis of the quantized weights for the 5\-bit AlexNet model is thoroughly presented, detailing the distribution of weight values across different convolutional and fully connected layers\.
- b:observation:sec\_14:results:1:obs2: The claims regarding the statistical distributions of quantized weights in various layers of the 5\-bit AlexNet model are accurately substantiated by the data presented in Table 6\.
- c:observation:sec\_14:results:1:obs\_1: A seção apresenta uma análise estatística da distribuição de pesos quantizados e remete diretamente à Tabela 6 para os resultados detalhados\.
- c:observation:sec\_14:results:1:obs\_2 [unresolved]: As afirmações \(1\) e \(3\) indicam agregações percentuais específicas \(por exemplo, &gt;60%, 94% e \~98%\) para camadas convolucionais e totalmente conectadas, sustentadas por valores percentuais na Tabela 6\.
- c:observation:sec\_14:results:1:obs\_3: A seção afirma que conjuntos específicos de valores “occupy over 60%” \(Conv1\) e “94%” \(Conv2\), mas não apresenta explicitamente a soma dos percentuais da Tabela 6 \(quais entradas são somadas\) para demonstrar como esses valores são obtidos\. Embora seja plausível, a sustentação fica inferencial\.
- c:observation:sec\_14:results:1:obs\_4: A explicação causal “may be partially the reason” \(mais fácil comprimir FC do que convolucional\) é especulativa e não é acompanhada de experimentos adicionais ou análise causal na seção\.
- c:observation:sec\_14:results:1:obs\_5: A seção tira uma conclusão específica sobre o “bit\-width requerido” por camada \(4 em vez de 5\) para o modelo de AlexNet de 5 bits, o que é um resultado direto e verificável a partir da distribuição exibida \(Tabela 6\)\.
- c:observation:sec\_14:results:1:obs\_6: A seção não define explicitamente como o “bit\-width required” é derivado \(por exemplo, via contagem de valores distintos com não\-zero, ou outro critério\), o que limita a replicabilidade e a clareza metodológica desse ponto \(apesar de a Tabela 6 listar Bit\-width\)\.

### B APPENDIX 2: LOSSLESS CNNS WITH LOW\-PRECISION WEIGHTS AND LOW\-PRECISION ACTIVATIONS

- a:observation:sec\_15:results:1:sec\_15\_obs\_1: A tabela fornece uma comparação direta entre o modelo quantizado e uma referência de precisão total, reportando top\-1 e top\-5 error, além das diferenças absolutas\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_2: As diferenças numéricas declaradas são consistentes com os valores da tabela: 31\.46%\-29\.82%=1\.64 ponto percentual e 11\.35%\-10\.19%=1\.16 ponto percentual\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_3: A conclusão de que o modelo quantizado é &\#x27;lossless&\#x27; ou superior não é acompanhada de variância, repetições, intervalos de confiança ou testes estatísticos; portanto, não é possível avaliar se as diferenças de 1\.64 e 1\.16 pontos percentuais são robustas\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_4: O apêndice não informa o protocolo experimental necessário para reproduzir ou interpretar a comparação, como subconjunto de avaliação, número de exemplos, procedimento de quantização das ativações, calibração e condições de treinamento ou ajuste fino\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_5: A afirmação de que este seria o melhor resultado já reportado para VGG\-16 não é sustentada por uma comparação explícita com trabalhos anteriores, nem por referências ou critérios uniformes de avaliação\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_6: A nomenclatura mistura &\#x27;decrease in top\-1/top\-5 error&\#x27; com a afirmação de &\#x27;improved recognition rates&\#x27;\. Embora os números indiquem redução do erro, seria mais claro declarar explicitamente que são diferenças absolutas em pontos percentuais, não reduções percentuais relativas\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_7: A comparação usa uma referência pré\-treinada, mas não esclarece se o modelo 5/4 recebeu exatamente o mesmo treinamento, pré\-processamento e avaliação; assim, a tabela isolada não permite atribuir a melhoria exclusivamente à quantização proposta\.
- b:observation:sec\_15:results:1:obs\_1: A afirmação de que os resultados são &\#x27;os melhores relatados até agora na arquitetura VGG\-16&\#x27; carece de evidência comparativa explícita com outras abordagens de quantização de baixa precisão para VGG\-16 nesta seção, além da linha de base de precisão total\. Para sustentar essa afirmação, seria necessária uma comparação com outros baselines de métodos de quantização existentes\.
- b:observation:sec\_15:results:1:obs\_2: O uso do termo &\#x27;Lossless CNNs&\#x27; no título do apêndice e no texto pode ser ambíguo ou potencialmente enganoso\. Embora os resultados mostrem uma melhoria nas taxas de reconhecimento \(diminuição do erro\), &\#x27;lossless&\#x27; tipicamente implica ausência de perda de precisão em comparação com o modelo original, e não uma melhoria de desempenho\.
- b:observation:sec\_15:results:1:obs\_3: A Tabela 7 fornece evidências numéricas claras e concisas, mostrando uma diminuição nos erros Top\-1 e Top\-5 para o modelo VGG\-16 quantizado \(5/4 bits\) em comparação com a referência de precisão total \(32/32 bits\)\. Esses dados sustentam diretamente a afirmação de que o modelo quantizado apresenta taxas de reconhecimento melhoradas, demonstrando substância e solidez nos resultados apresentados\.
- c:observation:sec\_15:results:1:obs\_1: A seção apresenta evidência quantitativa \(Table 7\) comparando diretamente a VGG\-16 com 5\-bit weights e 4\-bit activations contra a referência de 32/32\.
- c:observation:sec\_15:results:1:obs\_2: As alegações de superioridade e “best results so far” não são suportadas por comparação explícita com outros trabalhos \(não há citações/benchmark externo nesta seção\)\.
- c:observation:sec\_15:results:1:obs\_3: Há possível ambiguidade conceitual entre “improved recognition rates” \(maior é melhor\) e a tabela que mostra “Top\-1 error” e “Top\-5 error” \(menor é melhor\)\.
- c:observation:sec\_15:results:1:obs\_4: A seção declara progresso \(“good progress”\) mas não fornece nenhum detalhe adicional do que mudou/melhorou \(por ex\., atualização do INQ, hiperparâmetros, ou justificativa metodológica\) além de citar a tabela\.

## Evidências

- a:criterion:clarity: A organização geral é razoavelmente clara: o problema, a lacuna, a contribuição e o ciclo do INQ são apresentados de modo direto \(sec\_2:introduction:1:sec\_2\_obs\_1; sec\_2:introduction:1:sec\_2\_obs\_2; sec\_3:method:1:sec\_3\_obs\_1; sec\_5:method:1:sec\_5\_obs\_1; sec\_6:method:1:sec\_6\_obs\_1\)\. Contudo, a clareza é prejudicada por notação matemática corrompida, fórmulas ambíguas, símbolos inconsistentes, ambiguidades sobre métricas e afirmações excessivamente abrangentes \(sec\_4:method:1:sec\_4\_obs\_2; sec\_4:method:1:sec\_4\_obs\_3; sec\_4:method:1:sec\_4\_obs\_4; sec\_5:method:1:sec\_5\_obs\_3; sec\_6:method:1:sec\_6\_obs\_3; sec\_6:method:1:sec\_6\_obs\_4; sec\_6:method:1:sec\_6\_obs\_9; sec\_10:method:1:sec\_10\_obs\_6; sec\_12:conclusion:1:sec\_12\_obs\_3\)\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1: A introdução explicita claramente o problema prático: modelos CNN profundos impõem custos elevados de memória e computação, dificultando sua implantação em dispositivos com recursos limitados\.
  - sec\_2: However, this in turn lays heavy burdens on the memory and other computational resources\.
  - sec\_2: Therefore, it is very challenging to deploy deep CNNs on the devices with limited computation and power budgets\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: A lacuna de pesquisa é apresentada de forma direta e organizada em dois problemas específicos da quantização: perda não desprezível de acurácia e aumento do número de iterações de treinamento para obter convergência\.
  - sec\_2: The first issue is the non\-negligible accuracy loss for CNN quantization methods, and the other issue is the increased number of training iterations for ensuring convergence\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_1: A seção explicita de forma direta seu escopo: apresentar a intuição do INQ, seus componentes e sua implementação, o que estabelece uma organização adequada para a descrição do método\.
  - sec\_3: In this section, we clarify the insight of our INQ, describe its key components, and detail its imple\-mentation\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2: A notação matemática está corrompida ou inconsistente em pontos essenciais: os expoentes das potências de dois, os índices dos pesos e a regra de arredondamento não são apresentados de forma inequívoca\. Isso impede determinar exatamente o conjunto de quantização e implementar a transformação sem recorrer a uma fonte externa ou ao contexto original da publicação\.
  - sec\_4: P₁ = \{±21,………,±22,0\}
  - sec\_4: W₁\(i, j\) = \[Bsgn\(W₁\(i, j\)\) if \(α \+ β\)/2 ≤ abs\(W₁\(i, j\)\) &lt; 3β/2
10
otherwise,
  - sec\_4: a and ẞ are two adjacent elements in the sorted Pī
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: A expressão que determina n₂ não está suficientemente especificada: ela contém um termo fixo aparentemente dependente de uma variável ou parâmetro ausente, enquanto o texto afirma que n₂ é calculado a partir de b e n₁\. Assim, não é possível reproduzir os limites do conjunto de quantização para valores de b diferentes do exemplo fornecido\.
  - sec\_4: n2 can be naturally determined as n2 = n1 \+ 1 \- 2\(6\-1\)/2\.
  - sec\_4: n₂ can be naturally computed once b and n₁ are available\.
  - sec\_4: For instance, if b = 3 and n₁ = −1, it is easy to get n2 = \-2\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_4: Faltam especificações necessárias para uma implementação determinística da regra de arredondamento, incluindo o tratamento de valores exatamente iguais aos limiares, a definição da primeira e da última vizinhança de potência, e a forma de atribuir valores fora do intervalo coberto\. A descrição também não deixa explícito como o sinal e o zero são tratados na própria equação\.
  - sec\_4: where a and ẞ are two adjacent elements in the sorted Pī, making the above equation as a numerical rounding to the quantum values\.
  - sec\_4: network weights with absolute values smaller than 2n2 will be pruned away \(i\.e\., set to zero\)
  - sec\_4: W₁\(i, j\) = \[Bsgn\(W₁\(i, j\)\) if \(α \+ β\)/2 ≤ abs\(W₁\(i, j\)\) &lt; 3β/2
10
otherwise,
- a:observation:sec\_5:method:1:sec\_5\_obs\_1: A seção apresenta de forma conceitualmente coerente o ciclo central do INQ: particionamento dos pesos, quantização de um grupo, retreinamento do outro e repetição iterativa até que todos os pesos sejam convertidos\. Essa descrição conecta cada operação ao seu papel na redução da perda de acurácia\.
  - sec\_5: We present INQ which incorporates three interdependent operations: weight partition, group\-wise quantization and re\-training\.
  - sec\_5: Once the first run of the quantization and re\-training operations is finished, all the three operations are further conducted on the second weight group in an iterative manner, until all the weights are converted to be either powers of two or zero
- a:observation:sec\_5:method:1:sec\_5\_obs\_3: A definição matemática do particionamento contém problemas de notação e formatação que dificultam determinar precisamente o método: a união e a interseção dos conjuntos aparecem sem operadores completos, A\(2\) é posteriormente referido como A2, e a matriz binária é indicada ora por Ti, ora por Tr\. Também há inconsistência entre os índices de camada usados em W₁ e Wi\.
  - sec\_5: A\(1\) UA\(2\) = \{W₁\(i,j\)\}, and A\(1\) A\(1\) ∩ A\(2\) = 0,
  - sec\_5: That is, Ti\(i, j\) 0 means Wi\(i,j\) ∈ A\(1\), and Tr\(i, j\) = 1 means W₁\(i, j\) ∈ A\(2\)\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_1: A seção explicita a motivação da otimização incremental e conecta as três operações — particionamento, quantização e retreinamento — a um procedimento iterativo até a conversão de todos os pesos\.
  - sec\_6: The whole procedure of our INQ is summarized as Algorithm 1\.
  - sec\_6: By integrating the operations of weight partition, group\-wise quantization and re\-training into a nested loop, our INQ has the potential to obtain lossless low\-precision CNN model from the pre\-trained full\-precision reference\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_3: A formula do passo de atualização está corrompida ou mal formatada, impedindo determinar com segurança a variável atualizada, o gradiente e a forma exata de aplicação da máscara\.
  - sec\_6: ДЕ
W\(i, j\) – Wi\(i, j\) \- \(W₁\(i, j\)\) Ti\(i, j\),
  - sec\_6: where y is a positive learning rate\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_4: Há inconsistência notacional entre a restrição da otimização e a regra de atualização: a primeira usa explicitamente o gradiente da perda, enquanto a equação transcrita do retreinamento não mostra de forma legível esse gradiente nem deixa claro se a máscara multiplica o gradiente ou o incremento completo\.
  - sec\_6: min E \(W1\) = L\(W1\) \+ &gt;R\(W1\)
  - sec\_6: W\(i, j\) – Wi\(i, j\) \- \(W₁\(i, j\)\) Ti\(i, j\),
  - sec\_6: Note that the binary matrix T₁ forces zero update to the weights that have been quantized\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_9: A notação de índices e símbolos apresenta diversos erros de transcrição ou inconsistências — por exemplo, &\#x27;1 &lt; 1 &lt; L&\#x27;, &\#x27;Pı&\#x27;, &\#x27;Tı&\#x27; e &\#x27;σπ&\#x27; — que dificultam mapear inequivocamente as etapas do pseudocódigo às equações anteriores\.
  - sec\_6: s\.t\. W₁\(i, j\) ∈ Pı, 1 ≤ l &lt; L,
  - sec\_6: s\.t\. W₁\(i, j\) ∈ Pı, if Tı\(i, j\) = 0, 1 &lt; 1 &lt; L,
  - sec\_6: \{W₁: 1 &lt; 1 &lt; L\}
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: A redação das métricas é ambígua e potencialmente inconsistente: primeiro são relatadas perdas em top\-1 e top\-5 recognition rates, mas depois se afirma uma decrease em top\-1 e top\-5 error rate\. Uma redução da taxa de erro representa melhora, enquanto uma perda na taxa de reconhecimento representa piora; é necessário indicar claramente se os números são diferenças de acurácia ou de erro e seus sinais\.
  - sec\_10: our low\-precision model shows only 0\.19% and 0\.33% losses in top\-1 and top\-5 recognition rates, respectively\.
  - sec\_10: it incurs 2\.25% decrease in top\-1 error rate and 1\.56% decrease in top\-5 error rate in comparison to the pre\-trained full\-precision reference
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3: A formulação universal de que o método converte “any pre\-trained” CNN em uma versão “lossless” é mais abrangente do que o alcance explicitamente demonstrado, que se concentra em modelos específicos e na classificação ImageNet\. A conclusão deveria qualificar essa alegação como ausência de perda de acurácia nos experimentos realizados\.
  - sec\_12: to convert any pre\-trained full\-precision \(i\.e\., 32\-bit floating\-point\) CNN model into a lossless low\-precision version
  - sec\_12: On the ImageNet large scale classification task, we conduct extensive experiments
- a:check:figure\_vs\_text:figure\_vs\_text: figure\_vs\_text: unclear
  - sec\_10: As for our 2\-bit ternary model, although it incurs 2\.25% decrease in top\-1 error rate and 1\.56% decrease in top\-5 error rate in comparison to the pre\-trained full\-precision reference, its accuracy is considerably better than state\-of\-the\-art results reported for binary\-weight network \(BWN\) \(Rastegari et al\., 2016\) and ternary weight network \(TWN\) \(Li &amp; Liu, 2016\)\. Detailed results are summarized in Table 3 and Table 4\.
- a:criterion:meaningful\_comparison: Os trabalhos próximos são identificados e relacionados à proposta, incluindo pruning, vector quantization, deep compression e DNS; o artigo também explicita diferenças de escopo, precisão e representação dos pesos \(sec\_11:related\_work:1:sec\_11\_obs\_1; sec\_11:related\_work:1:sec\_11\_obs\_2\)\. Há comparações e ablação relevantes, como particionamento aleatório versus inspirado em poda no mesmo modelo e com 5 bits \(sec\_9:method:1:sec\_9\_obs\_1; sec\_9:results:1:sec\_9\_obs\_2; sec\_9:results:1:sec\_9\_obs\_2\)\. Porém, a normalização dos custos de armazenamento, índices, máscaras e Huffman não é suficientemente estabelecida, e alegações de superioridade ou de melhor resultado não são plenamente sustentadas por protocolos uniformes \(sec\_11:related\_work:1:sec\_11\_obs\_3; sec\_11:related\_work:1:sec\_11\_obs\_4; sec\_15:results:1:sec\_15\_obs\_5\)\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_1: Os trabalhos mais próximos aparecem de forma explícita: deep compression de Han et al\. \(2016\), pruning de Han et al\. \(2015\), vector quantization de Gong et al\. \(2014\) e DNS de Guo et al\. \(2016\)\. O texto também explica como esses componentes se relacionam, o que torna o posicionamento da proposta verificável\.
  - sec\_11: Han et al\. \(2016\) is a hybrid network compression solution combining three different techniques, namely network pruning \(Han et al\., 2015\), vector quantization \(Gong et al\., 2014\) and Huffman coding\.
  - sec\_11: We solved this problem by our dynamic network surgery \(DNS\) method \(Guo et al\., 2016\) which achieves about 7× speed\-up in training and improves the performance of network pruning from 9× to 17\.7×\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3: A comparação de compressão combina INQ e DNS e a contrapõe ao deep compression, que também combina várias técnicas\. Embora essa escolha seja plausível, o texto não explicita suficientemente, neste trecho, se as taxas reportadas usam exatamente a mesma convenção de armazenamento, os mesmos custos de índices/máscaras e o mesmo tratamento do código Huffman\. Sem essa normalização, a alegação de superioridade pode não ser plenamente comparável\.
  - sec\_11: For fair comparison, we combine our proposed INQ and DNS, and compare the resulting method with Han et al\. \(2016\)\.
  - sec\_11: When combing our proposed INQ and DNS, we achieve much better compression results compared with Han et al\. \(2016\)\.
  - sec\_11: In Han et al\. \(2016\), after network pruning, vector quantization further improves com\- pression ratio from 9× to 27×, and Huffman coding finally boosts compression ratio up to 35×\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_4: A formulação dos ganhos de compressão é ambígua: “51\.43%/96\.30% absolute improvement in compression performance” não deixa claro se os valores são diferenças relativas ou absolutas, nem a que referências correspondem exatamente\. Essa ambiguidade dificulta avaliar a magnitude da contribuição e deveria ser resolvida no texto ou diretamente na explicação da Tabela 5\.
  - sec\_11: yielding 51\.43%/96\.30% absolute improvement in compression performance compared with full version/fair version \(i\.e\., the combination of network pruning and vector quantization\) of Han et al\. \(2016\), respectively\.
  - sec\_11: Detailed results are summarized in Table 5\.
- a:criterion:replicability: Há alguns elementos úteis para reprodução, como a sequência operacional do algoritmo, frações acumuladas de quantização e certos hiperparâmetros experimentais \(sec\_6:method:1:sec\_6\_obs\_2; sec\_8:results:1:sec\_8\_obs\_1; sec\_10:method:1:sec\_10\_obs\_1\)\. Contudo, fórmulas essenciais estão corrompidas, faltam regras determinísticas de arredondamento, parâmetros de iteração, critérios de parada, política de taxa de aprendizado, definições dos objetos do pseudocódigo e detalhes dos protocolos de avaliação \(sec\_4:method:1:sec\_4\_obs\_2; sec\_4:method:1:sec\_4\_obs\_3; sec\_4:method:1:sec\_4\_obs\_4; sec\_6:method:1:sec\_6\_obs\_5; sec\_6:method:1:sec\_6\_obs\_6; sec\_7:results:1:sec\_7\_obs\_4; sec\_8:results:1:sec\_8\_obs\_4\)\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_3: Não é possível verificar, a partir do trecho fornecido, se a seção especifica hipóteses, parâmetros, procedimentos e informações suficientes para reproduzir o INQ; esses elementos deveriam ser explicitamente conferidos na descrição dos componentes e da implementação\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: A explicação do orçamento de bits é conceitualmente útil, mas a cardinalidade do conjunto de candidatos também aparece com notação corrompida e não esclarece completamente como são codificados o sinal, o zero e os índices\. Isso dificulta verificar se o número de valores representáveis é compatível com o bit\-width declarado\.
  - sec\_4: since zero value cannot be written as the power of two, we use 1 bit to represent zero value, and the remaining 4 bits to represent at most 16 different values for the powers of two\.
  - sec\_4: the number of candidate quantum values is at most 26−1 \+ 1
  - sec\_4: our quantization method actually adopts a variable\-length encoding scheme\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_2: O procedimento não especifica nesta seção como os grupos de pesos devem ser escolhidos\. Como o particionamento determina quais pesos são quantizados e quais são retreinados, faltam critérios operacionais — por exemplo, a medida usada, o limiar, a proporção dos grupos e sua eventual variação entre iterações — para reproduzir o método\.
  - sec\_5: We leave the strategies for group partition to be chosen in the experiment section\.
  - sec\_5: Weight partition is to divide the weights in each layer of a pre\-trained full\-precision CNN model into two disjoint groups
- a:observation:sec\_6:method:1:sec\_6\_obs\_2: O algoritmo fornece uma sequência operacional relativamente clara, incluindo inicialização, número de iterações, atualização da política de aprendizagem, particionamento, determinação do conjunto de quantização, quantização, cálculo da perda e atualização dos pesos restantes\.
  - sec\_6: 2: for n = 1,2,\.\.\., N do
  - sec\_6: 3: Reset the base learning rate and the learning policy
  - sec\_6: 4: According to ση, perform layer\-wise weight partition and update A \(1\), A\(1\), A\(2\) and Ti
  - sec\_6: 5: Based on on A\(1\), determine P₁ layer\-wisely
  - sec\_6: 6: Quantize the weights in A\(1\) by Equation \(4\) layer\-wisely
  - sec\_6: 7: Calculate feed\-forward loss, and update weights in \{A^2\) : 1 ≤ I ≤ L\} by Equation \(8\)
- a:observation:sec\_6:method:1:sec\_6\_obs\_5: O pseudocódigo não define suficientemente os objetos centrais usados na implementação, como A^\(1\), A^\(2\), T\_l, P\_l e os valores acumulados de quantização; além disso, a inicialização contém notação ambígua\.
  - sec\_6: Input: X: the training data, \{W₁ : 1 &lt; 1 &lt; L\}: the pre\-trained full\-precision CNN model, \{01,02,···,σπ\}: the accumulated portions of weights quantized at iterative steps
  - sec\_6: 1: Initialize A\{1\) ← Ø, A\{2\) ← \{W₁\(i, j\)\}, T₁ ← 1, for 1 &lt; 1 &lt; L
  - sec\_6: 4: According to ση, perform layer\-wise weight partition and update A \(1\), A\(1\), A\(2\) and Ti
- a:observation:sec\_6:method:1:sec\_6\_obs\_6: O algoritmo não especifica os valores ou a sequência de \{σ\_n\}, o número total de iterações N, o critério de parada, nem a política concreta de reinicialização da taxa de aprendizagem\. Sem esses parâmetros, a reprodução exata do treinamento não é possível a partir desta seção\.
  - sec\_6: \{01,02,···,σπ\}: the accumulated portions of weights quantized at iterative steps
  - sec\_6: 2: for n = 1,2,\.\.\., N do
  - sec\_6: 3: Reset the base learning rate and the learning policy
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A definição operacional da estratégia pruning\-inspired não é suficientemente especificada neste trecho: não se informa o limiar ou a regra exata baseada no valor absoluto, nem como os pesos são distribuídos entre os dois grupos\. Isso dificulta reproduzir precisamente a comparação\.
  - sec\_9: pruning\-inspired strategy considers that the weights with larger absolute values are more important than the smaller ones to form a low\-precision base for the original CNN model\.
  - sec\_9: we use pruning\-inspired strategy for weight partition\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: A seção não informa explicitamente os valores de batch size, weight decay e momentum, remetendo apenas aos parâmetros do segundo conjunto de experimentos\. A reprodução depende de localizar essa configuração em outra seção e de confirmar que todos os demais parâmetros também permanecem inalterados\.
  - sec\_10: Similar to the second set of experiments, we also use ResNet\-18 as a test case, and the parameter settings for the batch size, the weight decay and the momentum are completely the same\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: Não são especificados nesta passagem detalhes necessários para reproduzir integralmente o treinamento, como taxa de aprendizado, política de ajuste da taxa, inicialização, critério de parada, número de execuções e sementes aleatórias\. A menção a que os parâmetros são os mesmos do segundo conjunto não esclarece se esses aspectos também foram mantidos\.
  - sec\_10: The required number of epochs also increases when the expected bit\-width goes down, and it reaches 30 when training our 2\-bit ternary model\.
- a:check:method\_vs\_question:method\_vs\_question\_1: method\_vs\_question: consistent
  - sec\_5: Recall that our main goal is to achieve lossless low\-precision quantization for any pre\-trained full\-precision CNN model with no assumption on its architecture\.
  - sec\_5: we present INQ which incorporates three interdependent operations: weight partition, group\-wise quantization and re\-training\.
  - sec\_6: only the weights still keep with floating\-point values are updated
  - sec\_6: the final low\-precision model with the weights constrained to be either powers of two or zero

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
- Prompt sections/results: 5389e503fa50e5a61b1c4bb10a858911cb5fe81e90d84953b2542ecc27e3139a
- Prompt sections/related\_work: 2ea6604aedf799b0aca577d09b0061a586c2574324e1570710ee6774127869fd
- Prompt sections/conclusion: c4c502ddea161e91407c1491b62d9a7ccd898f65af92f609463b23499f9122db
- Prompt cross\_checker: 4e8937f51926f97133f3debc15fa90ceb4162ea26650d19865a5b00fb3392102, 9253d720f45eb59a236b59d2623da920cbcdebd03c3af3e085cb827dc0b00dfe, bc40a3c7bfac8d760e7fc43661e10f4b0c5389afb04ad0e7a7722abcce6f85d2
- Prompt synthesizer: 985cc119b5e4342a2142a88af5f5b4ffb7cc379e92d3fe95fee2009320f100f8
- Prompt judge: 6eed71ce2bb679aa55770792f36a17c264f09b5967f821a3b222acc06eae9e3e
- Prompt reviser: 109193cf84b5b8b3aaae29e293ecec291351eb7773c6e2fa8a276f6ba0ab3b1f, 9f6b0de49ba29121d4c6ebd6694dbbde0fc94d54eaa2c64c6ce1ee0bf100c4de, e596ae66ba9f867cc3dd4dae5cc9bdc733115847e1a55b40233d466ad8147d07

## Itens pendentes

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5
- a:observation:sec\_5:method:1:sec\_5\_obs\_4
- a:observation:sec\_6:method:1:sec\_6\_obs\_8
- a:observation:sec\_8:results:1:sec\_8\_obs\_4
- a:observation:sec\_14:results:1:sec14\-strength\-2
- a:observation:sec\_14:results:1:sec14\-weakness\-2
- b:observation:sec\_2:introduction:1:problem\_statement\_clarity
- b:observation:sec\_2:introduction:1:contributions\_originality\_clarity
- b:observation:sec\_3:method:1:method\_general\_data\_description
- b:observation:sec\_4:method:1:quant\_B\_ambiguity
- b:observation:sec\_6:method:1:M\-R\-4
- b:observation:sec\_11:related\_work:1:sec\_11\_obs\_1
- b:observation:sec\_12:conclusion:1:concl\_clarity\_method
- b:criterion:replicability
- b:observation:sec\_3:method:1:method\_incomplete\_weight\_partitioning
- b:observation:sec\_3:method:1:method\_missing\_quantization\_mapping
- b:observation:sec\_7:results:1:ob\_missing\_ablation\_setup
- b:criterion:soundness
- c:observation:sec\_2:introduction:1:obs\_2\_1
- c:observation:sec\_2:introduction:1:obs\_2\_2
- c:observation:sec\_2:introduction:1:obs\_2\_4
- c:observation:sec\_5:method:1:obs\_5\_3
- c:observation:sec\_8:results:1:obs\_5
- c:observation:sec\_10:method:1:obs\_5
- c:observation:sec\_11:related\_work:1:obs\_2
- c:observation:sec\_11:related\_work:1:obs\_5
- c:observation:sec\_14:results:1:obs\_2
- c:check:claims\_vs\_results:ex\_001
- c:check:method\_vs\_question:method\_vs\_question
- c:check:figure\_vs\_text:crosscheck\_figure\_vs\_text
- c:observation:sec\_9:results:1:obs\_3

## Avisos

- As faixas de recomendação são provisórias e aguardam calibração\.
