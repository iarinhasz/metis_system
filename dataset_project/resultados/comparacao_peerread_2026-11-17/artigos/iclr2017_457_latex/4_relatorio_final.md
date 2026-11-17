# INCREMENTAL NETWORK QUANTIZATION: TOWARDS LOSSLESS CNNS WITH LOW\-PRECISION WEIGHTS

Run: `01a1e7a9-bb16-7292-bc73-c857c9cf2d0e`

Recomendação: **minor**
Nota ponderada: **3.50** · Concordância: **indisponível**

Revisão humana sinalizada: sim

## Critérios

### Originalidade

Nota: 4.00 · Dispersão: indisponível · Votos válidos: 1

- B (rodada 3, nota 4): O artigo apresenta o método INQ como uma abordagem nova, contrastando\-o com as estratégias de quantização global existentes que negligenciam a importância dos pesos, o que é um ponto chave de originalidade \(sec\_2:introduction:1:intro\_contribution\_originality\)\. Além disso, a originalidade é reforçada pelo fato de que os pesos finais do INQ são potências de dois ou zero, permitindo operações de deslocamento de bits mais eficientes em hardware dedicado, ao contrário de outros métodos que ainda resultam em valores de ponto flutuante \(sec\_11:related\_work:1:obs3\)\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de C: `unresolved`

### Solidez

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Substância

Nota: 3.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 3): O artigo relata experimentos em ImageNet, testando múltiplas arquiteturas \(AlexNet, VGG\-16, GoogleNet, ResNet\-18 e ResNet\-50\) e avaliando top\-1/top\-5, além de análises adicionais \(por exemplo, distribuições de pesos em AlexNet 5\-bit e comparativos em VGG\-16 com pesos 5\-bit e ativações 4\-bit\)\. Porém, a reprodutibilidade e a avaliação completa da contribuição ficam limitadas por falta de detalhes de protocolo \(batch/learning rate/stop criteria\), por tabelas mencionadas mas não apresentadas no recorte fornecido, e por inconsistências/ambiguidade de métricas \(“recognition rates” vs “error rates”\) e escopo de alguns resultados\. Assim, há substância experimental razoável, mas não plenamente verificável\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Clareza

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `unresolved`
- Voto excluído de C: `evidence_not_validated`

### Comparação

Nota: 3.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 3): O artigo identifica e compara com trabalhos relevantes \(Han et al\. 2016; Gong et al\. 2014; além de referência a BWN/TWN e uso de DNS para “fair comparison”\), e discute diferenças em escopo do que é quantizado \(INQ “addresses all network layers simultaneously” vs quantização vetorial focada em fully connected\)\. Contudo, a comparabilidade é parcialmente comprometida por alegações anteriores à definição operacional de “without loss”, por descrições pouco detalhadas de quais partes do pipeline são substituídas/isoladas quando “combina INQ e DNS”, e por dependência de tabelas externas para justificar magnitude e condições específicas\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Impacto

Nota: 4.00 · Dispersão: indisponível · Votos válidos: 1

- B (rodada 3, nota 4): O impacto potencial do INQ é bem articulado, prometendo converter modelos CNN de precisão total em versões de baixa precisão &quot;lossless&quot; \(sem perda de acurácia\) cujos pesos são potências de dois ou zero, permitindo implementações de hardware mais eficientes com operações de deslocamento de bits\. Este impacto é sustentado por um resumo de resultados experimentais impressionantes, demonstrando acurácia melhorada ou similar para diversas arquiteturas com quantização de 5, 4 e 3 bits, abordando diretamente os problemas de perda de acurácia e iterações de treinamento\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Reprodutibilidade

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `unresolved`
- Voto excluído de C: `evidence_not_validated`

## Pontos fortes

- O método INQ é apresentado como uma contribuição original ao considerar a importância relativa dos pesos por meio de quantização incremental e por restringir os pesos finais a potências de dois ou zero, habilitando operações de deslocamento de bits em hardware dedicado\. [b:observation:sec\_2:introduction:1:intro\_contribution\_originality, b:observation:sec\_11:related\_work:1:obs3]
- O estudo avalia o método em ImageNet e em diversas arquiteturas, reportando métricas top\-1 e top\-5 e examinando diferentes larguras de quantização\. Essa abrangência fornece uma base experimental substancial para a contribuição\. [c:observation:sec\_7:results:1:obs\_1]
- O potencial de impacto é claro: o INQ busca produzir versões de baixa precisão com desempenho comparável ou superior ao de modelos de precisão total, reduzindo o custo de implementação por meio de operações de deslocamento de bits\. [b:observation:sec\_2:introduction:1:intro\_impact\_potential, b:observation:sec\_2:introduction:1:intro\_impact\_sustained\_results, b:observation:sec\_12:conclusion:1:con\_impact\_01]
- O artigo identifica trabalhos relacionados relevantes e tenta estabelecer comparações sob condições de avaliação alinhadas, inclusive combinando INQ e DNS para a comparação com Han et al\. [c:observation:sec\_11:related\_work:1:obs\_2]

## Pontos fracos

- A substância experimental é limitada pela ausência de detalhes suficientes do protocolo e pela dependência de tabelas para verificar parte dos resultados; além disso, há ambiguidade entre as métricas e o escopo de algumas alegações\. [c:observation:sec\_8:results:1:obs\_2, c:observation:sec\_7:results:1:obs\_1]
- As comparações com trabalhos anteriores não definem com precisão o significado operacional de “without loss” e não esclarecem quais componentes do pipeline são substituídos ou mantidos quando INQ e DNS são combinados, o que reduz a comparabilidade dos ganhos reportados\. [c:observation:sec\_11:related\_work:1:obs\_5, c:observation:sec\_11:related\_work:1:obs\_3]

## Sugestões

- Detalhar o protocolo experimental — incluindo batch size, taxa de aprendizado e critérios de parada — e apresentar diretamente as tabelas ou os valores numéricos usados para sustentar as conclusões de desempenho\. [c:observation:sec\_8:results:1:obs\_2]
- Definir explicitamente “without loss”, padronizar a terminologia entre taxas de reconhecimento e taxas de erro e especificar quais etapas do pipeline são usadas em cada comparação, especialmente na combinação de INQ com DNS\. [c:observation:sec\_11:related\_work:1:obs\_5, c:observation:sec\_11:related\_work:1:obs\_3, c:observation:sec\_8:results:1:obs\_2]

## Seções

### 1 INTRODUCTION

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1: O problema de implantação de CNNs em dispositivos com recursos limitados é explicitamente motivado por custos de memória e computação, com uma quantificação concreta para o ResNet\-152\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: A introdução situa a proposta em relação a uma sequência ampla de métodos de compressão e quantização, incluindo quantização de pesos, ativações e gradientes, o que ajuda a delimitar o espaço do problema\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3 [unresolved]: As contribuições centrais são apresentadas de forma identificável: particionamento de pesos, quantização por grupos e retreinamento iterativo, com a finalidade de preservar a acurácia\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_4: O impacto alegado é conectado a uma vantagem computacional concreta: substituir multiplicações em ponto flutuante por operações de deslocamento de bits em hardware dedicado\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5: A introdução antecipa resultados quantitativos em múltiplas arquiteturas, precisões e métricas, tornando verificável o alcance empírico reivindicado\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6 [unresolved]: A diferenciação de originalidade em relação ao estado da arte é parcialmente descritiva, mas não explicita com precisão quais limitações dos métodos mais próximos são resolvidas exclusivamente pelo INQ nem como a combinação proposta difere conceitualmente de abordagens anteriores de treinamento incremental ou retreinamento\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_7: A formulação do problema mistura duas dificuldades distintas — perda de acurácia e número de iterações de treinamento — mas a contribuição descrita detalha sobretudo a primeira; a relação causal entre as três operações e a alegada convergência mais rápida permanece pouco estabelecida na introdução\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_8: As alegações de generalidade e ausência de perda são fortes demais para o suporte fornecido nesta seção: “any pre\-trained” e “lossless” não especificam condições, tolerâncias, arquiteturas excluídas ou se a comparação é com a acurácia do modelo de referência sem retreinamento adicional\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_9: A introdução alterna entre uma quantização geral para pesos em potências de dois ou zero e a reivindicação específica de modelos “ternary” de 2 bits, sem explicar imediatamente como esses regimes de representação se relacionam\.
- b:observation:sec\_2:introduction:1:intro\_problem\_clarity: The article explicitly defines the core problem of deploying deep CNNs on resource\-constrained devices due to their heavy computational and memory demands\. It further specifies two critical open issues in CNN quantization: non\-negligible accuracy loss and increased training iterations\.
- b:observation:sec\_2:introduction:1:intro\_contribution\_originality: The paper clearly positions its Incremental Network Quantization \(INQ\) method as novel by explicitly contrasting its iterative, group\-wise approach with existing global quantization strategies that often neglect weight importance, thus highlighting its originality in addressing accuracy drop\.
- b:observation:sec\_2:introduction:1:intro\_impact\_potential: The potential impact of INQ is well\-articulated, promising to convert full\-precision CNN models into lossless low\-precision versions with weights constrained to powers of two or zero, which enables more efficient hardware implementation through bit\-shift operations\.
- b:observation:sec\_2:introduction:1:intro\_impact\_sustained\_results: The impact is strongly sustained by a summary of impressive experimental results, demonstrating improved or similar accuracy for various CNN architectures and bit\-widths \(5\-bit, 4\-bit, 3\-bit, 2\-bit\), and showing easy convergence, directly addressing the stated problems of accuracy loss and training iterations\.
- c:observation:sec\_2:introduction:1:obs\_1: O problema é explicitamente enunciado como dificuldade de usar CNNs profundas em dispositivos com restrições de recursos, com um exemplo concreto \(ResNet\-152\) quantificando custo de modelo e computação\.
- c:observation:sec\_2:introduction:1:obs\_2: As duas limitações que ainda impedem a quantização são declaradas de forma direta e separada \(perda de acurácia e aumento de iterações para convergir\), sustentando a motivação para a proposta\.
- c:observation:sec\_2:introduction:1:obs\_3 [unresolved]: A contribuição proposta \(INQ\) é apresentada como método “novel” e há descrição clara das operações centrais \(weight partition, group\-wise quantization e re\-training\), além do mecanismo iterativo até quantizar todos os pesos\.
- c:observation:sec\_2:introduction:1:obs\_4 [unresolved]: O texto afirma explicitamente o impacto em acurácia e eficiência de treinamento/estabilidade de convergência com resultados quantificados \(ganhos absolutos top\-1/top\-5; convergência com menos de 8 épocas; comparação com baseline e com deep compression\)\.
- c:observation:sec\_2:introduction:1:obs\_5: A alegação de que a contribuição pode produzir “lossless” \(sem perda\) está generalizada na introdução, mas não há aqui evidência/condição precisa \(por exemplo, quais métricas/limites e para quais arquiteturas/bit\-widths exatamente\) — isso limita a sustentação imediata no trecho da introdução\.
- c:observation:sec\_2:introduction:1:obs\_6 [unresolved]: Há uma tensão entre a afirmação de “any full\-precision \.\.\. model” e a lista posterior de resultados em tarefas/arquiteturas específicas; a introdução não explicita o escopo exato \(limitações\) para validar a generalidade “any”\.

### 2 INCREMENTAL NETWORK QUANTIZATION

- a:observation:sec\_3:method:1:sec\_3\_obs\_1: A seção explicita seu escopo metodológico: apresentar a intuição do INQ, seus componentes e sua implementação, o que fornece uma organização geral coerente para a descrição do método\.
- a:observation:sec\_3:method:1:sec\_3\_obs\_2: No trecho fornecido, a seção apenas anuncia que apresentará o insight, os componentes principais e a implementação da INQ; não são apresentados nesse excerto os componentes, parâmetros, hipóteses ou passos operacionais necessários para avaliar sua reprodução\. Com base somente no trecho disponível, não é possível determinar se esses detalhes aparecem em outra parte da seção\.
- b:observation:sec\_3:method:1:sec\_3\_obs\_1: A frase introdutória da Seção 3 estabelece claramente o escopo da discussão do método, indicando a intenção de esclarecer insights, descrever componentes\-chave e detalhar sua implementação\. Esta frase serve eficazmente como um roteiro para o leitor, aumentando a clareza e a compreensibilidade do artigo\.
- c:observation:sec\_3:method:1:obs\_1\_sec\_3: A seção declara explicitamente o objetivo e o que será apresentado: insight, componentes\-chave e implementação do INQ\.

### 2\.1 WEIGHT QUANTIZATION WITH VARIABLE\-LENGTH ENCODING

- a:observation:sec\_4:method:1:sec\_4\_obs\_1: A seção fornece uma especificação matemática relativamente concreta para determinar os limites do conjunto de quantização, incluindo as fórmulas para n\_1 e n\_2, o que favorece a implementação do procedimento\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2: A regra de quantização apresentada na Equação \(4\), tal como transcrita, é inconsistente com o conjunto $P\_l$ e não permite reproduzir inequivocamente o arredondamento alegado\. Quando a condição é satisfeita, a equação retorna apenas $\\operatorname\{sgn\}\(W\_l\(i,j\)\)$, isto é, $\+1$ ou $\-1$, em vez de especificar a potência de dois correspondente entre os valores de $P\_l$; caso contrário, retorna $0$\. Assim, a equação não explicita se o resultado deveria ser $\\operatorname\{sgn\}\(W\_l\(i,j\)\)\\alpha$, $\\operatorname\{sgn\}\(W\_l\(i,j\)\)\\beta$ ou outra potência de dois selecionada pelo arredondamento, comprometendo a replicabilidade da quantização\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: A regra de quantização não é especificada de forma suficiente para reprodução inequívoca\. Embora o artigo defina alpha e beta como elementos adjacentes de P\_l ordenado, P\_l contém potências de dois positivas, negativas e zero, enquanto a condição é aplicada a abs\(W\_l\(i,j\)\)\. O texto não esclarece se a ordenação é numérica com sinal, se deve ser feita sobre os módulos positivos ou como limites assinados devem ser convertidos para a comparação com o módulo do peso\. Além disso, a expressão apresentada retorna apenas sgn\(W\_l\(i,j\)\) quando a condição é satisfeita e não explicita a atribuição da potência de dois correspondente\. Assim, permanecem indefinidos tanto os intervalos efetivamente usados quanto o valor quantizado produzido\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_4: A contagem de valores representáveis e a codificação do sinal não estão completamente especificadas\. Para b=5, o texto afirma que os quatro bits restantes representam no máximo 16 valores para as potências de dois, mas P\_l contém valores positivos e negativos para cada expoente, além de zero, e o texto também afirma que o número de candidatos quânticos é no máximo 2^\{b\-1\}\+1\. Não fica claro se os 16 valores correspondem a expoentes, módulos ou valores já assinados, nem se o sinal é codificado separadamente ou incorporado nesses bits\. Essa ambiguidade impede determinar com precisão a cardinalidade efetiva de P\_l e reproduzir a codificação proposta\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: Faltam regras para casos\-limite necessários à reprodução: como tratar s=0, empates nos limiares de arredondamento, valores exatamente iguais a 3beta/2, e a validade de b quando \(b−1\)/2 não é inteiro\. Também não é informado se b deve ser ímpar ou quais valores de b foram efetivamente utilizados\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_6: O escopo operacional da quantização não está completo para CNNs modernas: a seção restringe a representação a camadas convolucionais e totalmente conectadas, mas não define como são tratados bias, batch normalization, parâmetros de outras camadas ou os operadores de ativação\. Isso impede reproduzir a conversão de uma arquitetura inteira a partir desta seção isolada\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_7: A justificativa para os fatores 4/3 e 3/2 é apenas declarativa; a seção não demonstra que a escolha de n\_1 garante que todos os valores de P\_l sejam compatíveis com os intervalos de arredondamento, nem explicita os intervalos completos para o primeiro e o último nível\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_8: A seção não especifica o formato efetivo do armazenamento nem como o índice é decodificado em sinal, expoente e zero\. A descrição de &\#x27;variable\-length encoding&\#x27; informa a quantidade máxima de candidatos, mas não fornece um mapa de códigos ou uma rotina de codificação/decodificação reproduzível\.
- b:observation:sec\_4:method:1:quantization\_b\_selection [unresolved]: O método de quantização exige o parâmetro &\#x27;expected bit\-width b&\#x27; como entrada, mas a seção não fornece diretrizes claras ou critérios para a sua seleção inicial para um dado modelo ou tarefa, o que pode dificultar a reprodução exata dos experimentos sem conhecimento prévio ou tentativa e erro\.
- b:observation:sec\_4:method:1:rounding\_algorithm\_clarity: Embora a equação de quantização \($	ilde\{W\_l\}\(i, j\)$\) mencione $\\alpha$ e $\\beta$ como &\#x27;two adjacent elements in the sorted $P\_l$&\#x27;, o processo exato para determinar qual par $\(\\alpha, \\beta\)$ é utilizado para arredondar um valor específico $W\_l\(i, j\)$ não é explicitado\. A formulação &\#x27;making the above equation as a numerical rounding&\#x27; sugere um algoritmo de busca, mas os passos não são detalhados\.
- b:observation:sec\_4:method:1:constants\_justification [unresolved]: Os fatores específicos 4/3 na equação \(2\) para $n\_1$ e 3/2 na equação \(4\) para o limite de arredondamento são introduzidos sem uma derivação matemática completa ou justificação teórica clara, além de sua correlação e eficácia prática\. Isso pode limitar a compreensão de por que esses valores específicos foram escolhidos e como eles poderiam ser adaptados ou otimizados\.
- b:observation:sec\_4:method:1:method\_clarity\_strength [unresolved]: As definições de entrada do modelo, a estrutura do conjunto de pesos quantizados $P\_l$, e as fórmulas para calcular $n\_1$ e $n\_2$ são matematicamente explícitas e acompanhadas de um exemplo claro, fornecendo uma base sólida para a compreensão e implementação do mecanismo de quantização\.
- c:observation:sec\_4:method:1:obs\_4\_1 [unresolved]: A seção apresenta um procedimento matemático para converter pesos de 32\-bit para valores em \{±2^n1, …, ±2^n2, 0\}, especificando como calcular n1, n2 e como quantizar cada entrada via uma regra de arredondamento para valores “quantum”\.
- c:observation:sec\_4:method:1:obs\_4\_2 [unresolved]: Há uma dependência explícita de “Equação \(4\)” e de uma relação com “Equação \(2\)”, mas a seção fornecida não inclui essas equações; isso reduz a clareza/reprodutibilidade porque o leitor não vê o enunciado completo da regra citada\.
- c:observation:sec\_4:method:1:obs\_4\_3 [unresolved]: Apesar de declarar que a seção ignora diferenças de dimensionalidade, não detalha como o cálculo de s=max\(abs\(W\_l\)\) e a aplicação da regra de quantização se generalizam para convoluções \(4D\) versus fully connected \(2D\)\.
- c:observation:sec\_4:method:1:obs\_4\_4 [unresolved]: A definição de “expected bit\-width b” é dada como um “exemplo” \(5\-bit\) com “variável\-length encoding”, mas não formaliza explicitamente a regra geral para qualquer b \(ex\.: contagem exata de valores e como isso afeta a construção de P\_l e a largura do índice\)\. Isso cria margem para interpretação na implementação\.
- c:observation:sec\_4:method:1:obs\_4\_5 [unresolved]: O texto justifica a escolha do fator 4/3 e relaciona explicitamente a sincronização entre escalas/constantes no arredondamento \(4/3 versus 3/2\), o que ajuda a sustentar coerência interna do esquema de quantização\.

### 2\.2 INCREMENTAL QUANTIZATION STRATEGY

- a:observation:sec\_5:method:1:sec\_5\_obs\_1: A estratégia é apresentada como um procedimento incremental coerente, no qual quantização, particionamento e retreinamento são repetidos até que todos os pesos sejam convertidos; isso conecta explicitamente a redução de precisão ao mecanismo de compensação de acurácia\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_2: O procedimento não especifica, nesta seção, como executar o retreinamento nem quais parâmetros controlam cada iteração — por exemplo, função objetivo, número de épocas, taxa de aprendizado, critério de parada e tratamento das camadas\. Esses detalhes são necessários para reproduzir o método, embora possam estar descritos na seção de algoritmo ou nos experimentos\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_3 [unresolved]: A regra de particionamento é deixada em aberto nesta seção, apesar de o particionamento determinar quais pesos são quantizados e quais permanecem treináveis em cada etapa\. Sem a regra, os resultados não são reproduzíveis a partir desta descrição isolada e a alegação de aplicabilidade geral fica dependente de escolhas experimentais não especificadas aqui\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_4: A justificativa causal para a ausência de perda de acurácia é apresentada como conjectura, não como hipótese operacionalizada ou condição verificável: a seção afirma que a importância variável dos pesos seria crítica, mas não define como medir essa importância nem quais evidências distinguiriam esse mecanismo de outras explicações\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_5: A formulação sugere uma promessa forte de supressão da perda de acurácia, mas a própria seção parte da observação de que a quantização em pequenas larguras de bits produz perda perceptível\. Seria necessário delimitar se “lossless” significa ausência de perda em todos os modelos e larguras de bits ou apenas desempenho comparável nos experimentos apresentados\.
- b:observation:sec\_5:method:1:inq\_method\_missing\_partition\_strategy: As estratégias específicas para &\#x27;group partition&\#x27;, cruciais para a divisão dos pesos para quantização e retreinamento, são explicitamente adiadas para a seção de experimentos\. Embora essas informações sejam fornecidas posteriormente no artigo, sua ausência nesta seção de método dedicada torna a compreensão do processo INQ incompleta apenas com base nesta seção\.
- b:observation:sec\_5:method:1:inq\_method\_missing\_eq4\_retraining\_details: The method references &\#x27;Equation \(4\)&\#x27; for group\-wise quantization and general &\#x27;re\-training steps&\#x27; without detailing them within this section\. While Equation \(4\) might be described in a preceding section \(\`sec\_4\`\), the parameters and specifics of the re\-training procedure \(e\.g\., optimizer, learning rate, loss function, number of epochs\) are not provided, which are essential for fully replicating the method\.
- b:observation:sec\_5:method:1:inq\_method\_iterative\_process\_clarity: While the iterative nature of the quantization and re\-training process is clearly stated, the precise method or rule for how the &\#x27;second weight group&\#x27; is repeatedly partitioned in subsequent iterations to achieve the &\#x27;incremental network quantization&\#x27; is not explicitly defined in the text\. This lack of explicit detail on the iterative splitting criteria could make exact replication challenging\.
- b:observation:sec\_5:method:1:inq\_method\_explicit\_conjecture: The method is built upon a clearly stated conjecture regarding the criticality of changing network weight importance for achieving lossless quantization, explicitly linking the proposed approach to its inspiration from network pruning\. This enhances the logical foundation and clarity of the method&\#x27;s rationale\.
- c:observation:sec\_5:method:1:sec\_5\_obs\_1: A alegação de “lossless low\-precision quantization” é introduzida como objetivo e intenção, mas nesta seção não há critérios operacionais, condição de sucesso \(ex\.: “quando” e “para quais arquiteturas/bit\-widths”\) nem evidência numérica para sustentar a conclusão no nível do método descrito\.
- c:observation:sec\_5:method:1:sec\_5\_obs\_2: O texto exige escolhas de projeto para a partição dos pesos \(“strategies for group partition”\), mas nesta seção elas são postergadas para “experiment section”, sem indicar quais alternativas foram avaliadas aqui, o que reduz reprodutibilidade do procedimento apenas a partir desta seção\.
- c:observation:sec\_5:method:1:sec\_5\_obs\_3 [unresolved]: A definição afirma “dividir em duas disjoint groups” e usa conjuntos A\_l^\{\(1\)\} e A\_l^\{\(2\)\}; porém, o fluxo do algoritmo iterativo menciona que a operação se repete “no latest re\-trained group”, o que não está formalmente conectado aqui com como T\_l é atualizado a cada iteração nem como se determina o “latest” além da descrição textual\.
- c:observation:sec\_5:method:1:sec\_5\_obs\_4: Há referência a “quantized by using Equation \(4\)” sem reproduzir a equação nem especificar o mapeamento de quantização nesta seção, dificultando verificar a consistência entre a partição descrita e o esquema de quantização aplicado ao grupo A\_l^\{\(1\)\}\.
- c:observation:sec\_5:method:1:sec\_5\_obs\_5 [unresolved]: A formulação da partição por conjuntos disjuntos e a introdução da matriz binária T\_l para rotular pesos são descritas de modo relativamente objetivo, o que ajuda a definir o que são A\_l^\{\(1\)\} e A\_l^\{\(2\)\} no nível conceitual\.

### 2\.3 INCREMENTAL NETWORK QUANTIZATION ALGORITHM

- a:observation:sec\_6:method:1:sec\_6\_obs\_1 [unresolved]: A formulação explicita a função objetivo, a restrição de quantização, o papel da máscara binária e uma regra de atualização, conectando as operações de quantização e re\-treinamento em um procedimento iterativo coerente\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_2: O algoritmo não especifica parâmetros essenciais para reproduzir o treinamento: número de épocas ou iterações de SGD em cada passo, tamanho de minibatch, valor ou programação de $\\gamma$, definição de $\\lambda$, política de aprendizado, critério de parada e procedimento exato de cálculo da perda durante o re\-treinamento\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_3: Os valores ou regra para os acumulados $\\\{\\sigma\_1,\\ldots,\\sigma\_N\\\}$ e, consequentemente, o número de passos $N$, não são fornecidos nesta seção\. Como esses valores determinam a fração de pesos quantizada em cada iteração, sua ausência impede reproduzir a trajetória do algoritmo\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_4: A descrição do retreinamento não especifica formalmente como os pesos ainda flutuantes, associados a $T\_l\(i,j\)=1$ e mantidos em $A\_l^\{\(2\)\}$, participam do forward, do cálculo da perda e da computação do gradiente\. O texto informa que os pesos quantizados satisfazem a restrição $W\_l\(i,j\)\\in P\_l$ quando $T\_l\(i,j\)=0$ e não recebem atualização, e que os pesos em $A\_l^\{\(2\)\}$ são atualizados; porém, não define explicitamente a representação usada no forward para cada grupo nem a forma como a máscara afeta o gradiente além da regra de atualização da Equação \(8\)\. Essa lacuna reduz a clareza e a replicabilidade do procedimento de retreinamento\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_5: A etapa de quantização não é reproduzível a partir desta seção isoladamente: o algoritmo remete à Equação \(4\), mas não informa aqui a regra de arredondamento, os expoentes permitidos, o tratamento do zero, nem como os conjuntos $P\_l$ são construídos para cada grupo e camada\.
- a:observation:sec\_6:method:1:sec\_6\_obs\_6: A afirmação de que o procedimento pode obter um modelo de baixa precisão sem perda de acurácia não é demonstrada pelo algoritmo: nesta seção não há critério operacional para definir ou verificar “lossless”, nem comparação, tolerância estatística ou condição que garanta recuperação da acurácia\.
- b:observation:sec\_6:method:1:obs\_6\_1 [unresolved]: The method description refers to &\#x27;Equation \(4\)&\#x27; for quantizing weights, but this equation is not provided in the given text, making a crucial step of the algorithm unreproducible\.
- b:observation:sec\_6:method:1:obs\_6\_2: The exact procedure for &\#x27;layer\-wise weight partition&\#x27; and how it is performed &\#x27;According to $\\sigma\_n$&\#x27; is not detailed\. The article mentions &\#x27;A well\-proven measure is employed to divide the weights&\#x27; in the abstract, but the specific measure or criteria are not provided within the method description, hindering replicability\.
- b:observation:sec\_6:method:1:obs\_6\_3: The specific method for determining the set $P\_l$ \(powers of two plus zero\) is not explicitly described\. While it states &\#x27;$P\_l$ is determined at group\-wise quantization operation&\#x27;, the mechanism of this determination \(e\.g\., which specific powers of two are chosen, or how many unique values are selected\) is absent\.
- b:observation:sec\_6:method:1:obs\_6\_4: Step 3 of Algorithm 1, &\#x27;Reset the base learning rate and the learning policy&\#x27;, lacks specific details\. It is unclear how the learning rate is reset and what &\#x27;learning policy&\#x27; refers to or how it is implemented\.
- b:observation:sec\_6:method:1:obs\_6\_5 [unresolved]: The input parameter &\#x27;accumulated portions of weights quantized at iterative steps&\#x27; \($\\sigma\_n$\) is crucial for the incremental process, but no example values or a strategy for choosing these values are provided, making it difficult to fully replicate the incremental nature of the quantization\.
- b:observation:sec\_6:method:1:obs\_6\_6: The overall Incremental Network Quantization \(INQ\) algorithm is clearly structured and presented in &\#x27;Algorithm 1&\#x27;, offering a good high\-level overview of the entire process, which enhances clarity\.
- b:observation:sec\_6:method:1:obs\_6\_7 [unresolved]: The justification for the incremental approach, citing challenges with direct optimization and the benefits of weight partitioning and group\-wise quantization, appears sound and well\-reasoned, supporting the method&\#x27;s underlying principles\.
- c:observation:sec\_6:method:1:obs\_1 [unresolved]: O texto afirma que o problema reescrito &quot;can be solved using popular stochastic gradient decent \(SGD\) method&quot;, mas não explicita como os termos relevantes em \(7\) são definidos/derivados nem como a restrição/parametrização se materializa durante o treino \(além do mascaramento via T\_l\)\.
- c:observation:sec\_6:method:1:obs\_2 [unresolved]: Há dependência de definições e equações anteriores \(por exemplo, &quot;Equation \(4\)&quot;, &quot;Equation \(8\)&quot;, e a &quot;basic optimization problem \.\.\. expressed as&quot; em \(6\)\), mas esta seção não fornece as definições/expressões necessárias para implementar exatamente o procedimento \(INQ\) a partir do que foi descrito aqui\.
- c:observation:sec\_6:method:1:obs\_3: A restrição \(&quot;weights \.\.\. should be chosen from the set $P\_l$&quot;\) é apresentada, mas o esquema de atualização mostrado só zera gradientes via T\_l; não está claro aqui como a atualização garante que as entradas atualizadas continuem pertencendo a $P\_l$ \(ex\.: manutenção estrita de &quot;powers of two or zero&quot;\), além de ser mencionado que T\_l força zero atualização de certos pesos\.
- c:observation:sec\_6:method:1:obs\_4: O passo &quot;Reset the base learning rate and the learning policy&quot; é genérico e não define quais políticas/valores são usados, nem como dependem de n \(iterativo\) ou de \(σ\_n\), prejudicando a reprodutibilidade\.
- c:observation:sec\_6:method:1:obs\_5: Há um ponto potencialmente confuso entre &quot;pesos quantizados&quot; e &quot;weights still keep with floating\-point values&quot;: o texto descreve uma máscara T\_l que impede atualização dos pesos quantizados, mas não explica explicitamente como/quando A\_l^\(1\) e A\_l^\(2\) alternam seus papéis ao longo das iterações, além de depender da operação de partição mencionada no algoritmo\.

### 3 EXPERIMENTAL RESULTS

- a:observation:sec\_7:results:1:sec\_7\_obs\_1: A seção delimita um cenário experimental relevante e abrangente, usando ImageNet e cinco arquiteturas de CNN de famílias distintas, o que favorece a avaliação da generalidade do método\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_2: O uso de top\-1 e top\-5 error rate, com center crops na validação, torna o protocolo compatível com práticas padrão de avaliação em ImageNet e facilita a comparação com referências\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_3: A seção explicita a origem dos modelos de referência e identifica a exceção do ResNet\-18, incluindo a fonte da reimplementação e a conversão entre frameworks; isso melhora a transparência da comparação\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_4: O protocolo não informa repetições independentes, sementes aleatórias, variância ou intervalos de confiança\. Assim, eventuais diferenças pequenas entre o INQ e as referências não podem ser avaliadas quanto à estabilidade estatística\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_5: Faltam detalhes operacionais necessários para reproduzir a avaliação, como pré\-processamento completo, tamanho do batch, procedimento de treinamento/re\-treinamento, número de épocas, critério de seleção de checkpoints e configuração exata da conversão do ResNet\-18\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_6 [unresolved]: O parágrafo estabelece apenas os modelos full\-precision como referência e não especifica aqui baselines quantitativos alternativos, como outros métodos de quantização, nem critérios uniformes para comparar ganhos de acurácia e custo de representação\.
- a:observation:sec\_7:results:1:sec\_7\_obs\_7: A afirmação de que ImageNet é “the most challenging image classification benchmark so far” é ampla e não é sustentada por evidência ou referência neste trecho; uma formulação mais específica evitaria uma generalização desnecessária\.
- b:observation:sec\_7:results:1:baselines\_clarity: The experimental setup clearly defines the full\-precision 32\-bit CNN models from the Caffe model zoo as baselines for comparison and justifies the source for ResNet\-18, contributing to a fair evaluation\.
- b:observation:sec\_7:results:1:metrics\_standard: The use of standard evaluation metrics \(top\-1 and top\-5 error rates\) ensures the results are comparable with existing literature and widely understood in the field\.
- b:observation:sec\_7:results:1:missing\_variance: The description of experimental results in this section does not include statistical information such as variance or standard deviation across multiple runs, which would enhance the understanding of result robustness and stability\.
- b:observation:sec\_7:results:1:missing\_ablation\_details\_in\_snippet: A seção de resultados experimentais \(Seção 3\) não introduz ou resume os estudos de ablação para avaliar a contribuição individual de cada componente do método \(partição de pesos, quantização por grupo e re\-treinamento\)\. A referência original à Seção 3\.2 como local desses estudos estava incorreta, pois aquela seção se concentra em estratégias de partição de pesos e não em ablações completas dos componentes\.
- c:observation:sec\_7:results:1:obs\_1: O texto especifica o benchmark, o tamanho do conjunto de dados e as métricas de avaliação usadas \(top\-1 e top\-5 error rate\)\.
- c:observation:sec\_7:results:1:obs\_2: Há uma descrição do conjunto de arquiteturas CNN avaliadas, incluindo modelos representativos \(AlexNet, VGG\-16, GoogleNet, ResNet\-18 e ResNet\-50\)\.
- c:observation:sec\_7:results:1:obs\_3: A afirmação de que é o “benchmark mais desafiador” é uma caracterização sem evidência ou definição operacional no trecho\.
- c:observation:sec\_7:results:1:obs\_4: O texto não fornece detalhes de protocolo experimental além de “center crops” e métricas \(por exemplo, batch size, learning rate, número de épocas, critérios de parada\), limitando a reprodutibilidade a partir apenas desta seção\.
- c:observation:sec\_7:results:1:obs\_5: A construção “For fair comparison” é seguida por um conjunto de escolhas para modelos de referência, mas o trecho não explicita como a “justiça” é garantida \(e\.g\., detalhes de treinamento/ajuste para cada modelo, ou se as mesmas escolhas de fine\-tuning/quantização foram comparadas\)\.

### 3\.1 RESULTS ON IMAGENET

- a:observation:sec\_8:results:1:sec\_8\_obs\_1: A seção cobre arquiteturas CNN substancialmente diferentes — AlexNet, VGG\-16, GoogleNet, ResNet\-18 e ResNet\-50 — o que fornece evidência de aplicabilidade além de um único modelo\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_2 [unresolved]: Os hiperparâmetros principais e os cronogramas de quantização são explicitados separadamente para cada arquitetura, favorecendo a reprodutibilidade do protocolo experimental\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_3: A afirmação de melhoria consistente não é acompanhada, no trecho apresentado, por medidas de variância, intervalos de confiança, número de execuções ou sementes aleatórias\. Como o particionamento aleatório é uma estratégia considerada, a ausência desses controles é particularmente relevante para avaliar a robustez das diferenças\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_4: O texto identifica os modelos de referência como versões full\-precision, mas não especifica aqui sua origem, o procedimento de treinamento, o checkpoint utilizado nem se todos os modelos foram comparados sob condições equivalentes\. Isso limita a interpretação causal de que a melhoria decorre do INQ\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_5: A seção não apresenta no texto os valores numéricos de top\-1 e top\-5, nem as diferenças absolutas ou relativas entre cada modelo quantizado e seu baseline\. A conclusão de melhoria consistente fica, portanto, dependente da inspeção da Table 1 e não é verificável a partir da descrição textual isolada\.
- a:observation:sec\_8:results:1:sec\_8\_obs\_6: A seção remete à Section 3\.2 a justificativa para escolher a estratégia de particionamento pruning\-inspired, mas os resultados de 3\.1 combinam essa escolha com a quantização incremental e o retreinamento\. Como a comparação apresentada é entre os modelos de 5 bits gerados pelo INQ e referências full\-precision, sem uma ablação ou comparação explícita entre estratégias de particionamento no trecho, não é possível atribuir isoladamente os ganhos de acurácia ao particionamento ou ao método completo\. Uma ablação conjunta, ou uma referência explícita aos resultados comparativos da Section 3\.2, fortaleceria essa atribuição causal\.
- b:observation:sec\_8:results:1:R\_IMAGENET\_OBS1: A seção afirma &\#x27;precisão do modelo consistentemente melhorada&\#x27;, e embora a Tabela 1 seja referenciada para detalhes, a ausência de uma breve síntese dos resultados numéricos mais impactantes no texto pode dificultar a compreensão imediata da magnitude da melhoria para o leitor\.
- b:observation:sec\_8:results:1:R\_IMAGENET\_OBS2: A afirmação de precisão &\#x27;consistentemente melhorada&\#x27; não é suportada por medidas estatísticas como variância ou resultados de múltiplas execuções experimentais, o que forneceria evidências mais robustas para a consistência\.
- b:observation:sec\_8:results:1:R\_IMAGENET\_OBS3: A seção afirma diretamente o uso de uma &\#x27;estratégia inspirada em poda&\#x27; para a partição de pesos, mas adia sua justificativa para uma seção posterior \(Seção 3\.2\), o que pode dificultar a compreensão imediata das escolhas metodológicas nesta visão geral dos resultados\.
- b:observation:sec\_8:results:1:R\_IMAGENET\_OBS4: O artigo detalha claramente as configurações específicas de parâmetros \(porções acumuladas de pesos quantizados, tamanho do batch, weight decay e momentum\) para cada modelo CNN avaliado \(AlexNet, VGG\-16, GoogleNet, ResNet\-18, ResNet\-50\), o que é crucial para a reprodutibilidade\.
- c:observation:sec\_8:results:1:obs\_1: A seção fundamenta a afirmação de eficácia com evidência experimental explícita: conversão de múltiplas arquiteturas para 5\-bit e melhoria consistente de acurácia\.
- c:observation:sec\_8:results:1:obs\_2: A conclusão de melhoria \(top\-1/top\-5\) é declarada sem apresentar números ou intervalo de variação diretamente no texto, dependendo da Tabela 1 não incluída aqui\.
- c:observation:sec\_8:results:1:obs\_3 [unresolved]: O texto afirma que “the first set of experiments” testa INQ em diferentes arquiteturas, mas o trecho contém também justificativa e comparação de estratégias \(random vs pruning\-inspired\) que são descritas como fazendo parte de experimentos posteriores/anteriores \(mencionando Section 3\.2\), criando possível descompasso de escopo com a seção 3\.1\.

### 3\.2 ANALYSIS OF WEIGHT PARTITION STRATEGIES

- a:observation:sec\_9:method:1:sec\_9\_obs\_1: O experimento compara diretamente duas estratégias de particionamento no mesmo modelo e informa que as configurações dos parâmetros foram mantidas constantes, reduzindo uma possível fonte de confusão na comparação\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_2: O procedimento reporta explicitamente a duração do retreinamento e apresenta os resultados numéricos para ambas as estratégias, permitindo verificar a diferença observada: 1,09 ponto percentual no erro top\-1 e 0,83 ponto percentual no erro top\-5\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A estratégia pruning\-inspired não é especificada com precisão suficiente para reprodução: o texto descreve a importância relativa dos pesos pelo valor absoluto, mas não informa a regra exata de seleção, a fração atribuída a cada grupo, o tratamento de empates ou como o particionamento é aplicado em cada iteração e camada\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_4: A conclusão de que o particionamento pruning\-inspired é superior é apoiada por um único modelo e por uma comparação sem medidas de variabilidade ou repetição de execuções; assim, os dados apresentados sustentam uma vantagem neste teste, mas não estabelecem robustez geral da estratégia\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_5: Não são fornecidos nesta seção detalhes suficientes sobre a aleatoriedade da partição e do treinamento, como sementes, número de execuções, critério de avaliação, checkpoint utilizado e condições exatas do retreinamento\. A referência à Seção 3\.1 pode conter parte dessas informações, mas a reprodutibilidade deste experimento não é assegurada pelo trecho isoladamente\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_1: A comparação é diretamente relevante para a decisão metodológica: as duas estratégias são avaliadas no mesmo ResNet\-18, com os mesmos parâmetros experimentais e 4 épocas de re\-treinamento, isolando razoavelmente o efeito da estratégia de particionamento\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_2: A tabela apresenta uma diferença consistente nos dois indicadores reportados: a estratégia pruning\-inspired reduz o erro top\-1 de 32,11% para 31,02% e o erro top\-5 de 11,73% para 10,90%, com as diferenças numéricas declaradas corretamente no texto\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_3: A comparação não reporta variância, múltiplas execuções, intervalos de confiança ou testes estatísticos\. Como a estratégia random é estocástica e as diferenças são relativamente pequenas, não é possível determinar se os ganhos observados são robustos ou atribuíveis ao particionamento em vez de à aleatoriedade experimental\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_4: A conclusão de que a estratégia pruning\-inspired é superior é sustentada por um único modelo, um único nível de bit\-width e uma única configuração de re\-treinamento\. Falta avaliar se o resultado generaliza para outras arquiteturas, camadas, taxas de particionamento ou níveis de quantização\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_5: A seção não fornece detalhes suficientes para reproduzir precisamente a comparação, como a proporção de pesos atribuída a cada grupo, o critério exato de ordenação ou seleção dos pesos na estratégia pruning\-inspired, as sementes aleatórias e o protocolo de avaliação\.
- a:observation:sec\_9:results:1:sec\_9\_obs\_6: A redação &\#x27;Apparently&\#x27; e a conclusão categórica de superioridade não qualificam a limitação do desenho experimental nem distinguem associação observada de evidência estatisticamente robusta; a conclusão deveria ser restringida ao ResNet\-18, à quantização de 5 bits e à configuração testada\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_1: The exact algorithm or threshold used for the &\#x27;pruning\-inspired strategy&\#x27; is not detailed, only its guiding principle is provided, making it difficult to precisely reproduce the method\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_2: The specific implementation details for the &\#x27;random strategy&\#x27; for weight partition, such as how weights are assigned to disjoint groups and their relative sizes, are not described\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_3: Embora alguns parâmetros sejam declarados, o experimento depende de configurações de parâmetros &\#x27;completamente iguais às descritas na Seção 3\.1&\#x27;, exigindo que o leitor consulte outra seção para a configuração experimental completa\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_4: The experimental setup \(model, bit\-width, re\-training epochs\) and the comparison results for the two strategies are clearly presented and summarized, enhancing clarity of findings\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_5: The underlying hypothesis for the pruning\-inspired strategy, based on the importance of larger absolute weight values, is a sound and commonly accepted heuristic in model compression literature\.
- b:observation:sec\_9:results:1:sec9\_obs1: The article conducts a clear and well\-justified ablation study by comparing two distinct weight partition strategies \(random vs\. pruning\-inspired\)\. It provides quantitative results \(Top\-1 and Top\-5 error rates\) that effectively sustain the affirmation that the pruning\-inspired method is superior and thus chosen for the paper\.
- b:observation:sec\_9:results:1:sec9\_obs2: While the comparison of weight partition strategies presents specific Top\-1 and Top\-5 error rates, the results are single data points without any measure of statistical variance \(e\.g\., standard deviation across multiple runs or confidence intervals\)\. This makes it challenging to ascertain the statistical significance and robustness of the observed performance differences between the two strategies, particularly for the relatively small improvements reported\.
- c:observation:sec\_9:method:1:obs\_1: A comparação entre duas estratégias de partição de pesos \(aleatória vs\. inspirada em pruning\) é diretamente vinculada ao impacto nas etapas seguintes de quantização por grupos e re\-treinamento\.
- c:observation:sec\_9:method:1:obs\_2: A hipótese operacional da estratégia inspirada em pruning é formulada de modo coerente: pesos de maior valor absoluto seriam mais importantes para formar a base de baixa precisão\.
- c:observation:sec\_9:method:1:obs\_3: O texto apresenta resultados quantitativos comparando as duas estratégias no mesmo backbone \(ResNet\-18\) e no mesmo regime de quantização \(5\-bit\), incluindo variação em top\-1 e top\-5\.
- c:observation:sec\_9:method:1:obs\_4: Não há detalhamento suficiente do critério exato de partição para a estratégia pruning\-inspired \(por exemplo, como se define o limiar/quantil, proporção entre os grupos, e como isso é aplicado por camada\), o que prejudica a reprodutibilidade\.
- c:observation:sec\_9:method:1:obs\_5: O procedimento de re\-treinamento está parcialmente descrito \(apenas o número de épocas\), mas faltam detalhes essenciais para reconstruir o experimento \(otimizador, learning rate/ schedule, batch size, critério de parada etc\.\), com referência genérica à Seção 3\.1\.
- c:observation:sec\_9:method:1:obs\_6: O texto afirma diminuição em top\-5 para o método pruning\-inspired \(0\.83%\), mas o valor na Tabela 2 para top\-5 parece ser 11\.73% \(random\) vs 10\.90% \(pruning\-inspired\), o que corresponde a 0\.83% \(coerente\), porém o texto decrimina &\#x27;0\.83% decrease&\#x27; sem indicar claramente se é ponto percentual absoluto ou diferença relativa; isso é uma ambiguidade de interpretação\.
- c:observation:sec\_9:method:1:obs\_7: A justificativa para escolher pruning\-inspired é qualitativa \(“é melhor”\) e baseada em uma única comparação; não há medidas de significância, variância entre execuções ou discussão sobre estabilidade, o que limita a força da conclusão\.
- c:observation:sec\_9:results:1:obs\_1: Há um desenho experimental comparando duas estratégias de partition \(random vs pruning\-inspired\) usando o mesmo backbone e configurações, com métricas reportadas em tabela\.
- c:observation:sec\_9:results:1:obs\_2 [unresolved]: A seção apresenta números concretos de top\-1 e top\-5 para as duas estratégias e quantifica a melhoria \(diferenças percentuais\)\.
- c:observation:sec\_9:results:1:obs\_3: A justificativa do uso da estratégia pruning\-inspired se apoia apenas em um caso \(ResNet\-18\) e em um regime de 5\-bit; a seção não indica avaliação estatística/variância nem repetição para sustentar robustez da diferença\.
- c:observation:sec\_9:results:1:obs\_4: O texto deve esclarecer a unidade da queda: para top\-5, de 11\.73% \(random\) para 10\.90% \(pruning\-inspired\) a diferença é 0\.83 ponto percentual \(p\.p\.\)\. Portanto, a frase “0\.83% decrease” pode ser ambígua; recomenda\-se corrigir para “0\.83 p\.p\. decrease” \(ou explicitar que se trata de diferença absoluta em pontos percentuais\)\.
- c:observation:sec\_9:results:1:obs\_5: A seção declara a lógica por trás da estratégia \(maiores valores absolutos são mais importantes\) mas não descreve qual “pruning\-inspired” medida/critério específico é usado para formar os grupos, o que limita replicabilidade a partir apenas deste trecho\.

### 3\.3 THE TRADE\-OFF BETWEEN EXPECTED BIT\-WIDTH AND MODEL ACCURACY

- a:observation:sec\_10:method:1:sec\_10\_obs\_1: A seção explicita os pontos de acumulação das frações quantizadas para os modelos de 4, 3 e 2 bits, permitindo reproduzir a principal programação iterativa da quantização\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_2: O desenho experimental testa progressivamente precisões de 4, 3 e 2 bits no mesmo caso de estudo, e ajusta o número de etapas iterativas e de épocas à redução da precisão, o que é coerente com a investigação do limite de desempenho do método\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: A descrição não fornece todos os parâmetros necessários para reproduzir o treinamento: os valores de batch size, weight decay e momentum são apenas remetidos a um experimento anterior, e não são apresentados aqui; também não são informados explicitamente os números de épocas para os modelos de 4 e 3 bits\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: A seção não especifica como são calculados os números de candidatos quânticos, nem detalha a regra de quantização aplicada a cada largura de bit e ao caso de pesos ternários\. Sem esses elementos, a correspondência entre “4\-bit”, “3\-bit” e “2\-bit ternary” e o procedimento efetivamente executado permanece incompleta\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_5: As conclusões de superioridade e de perda de acurácia não são plenamente verificáveis a partir do texto da seção, pois os valores numéricos são descritos sem indicar claramente se as diferenças são absolutas ou relativas, sem incerteza ou repetição experimental, e as tabelas citadas não estão incluídas no trecho fornecido\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: A redação usa convenções métricas e de sinal diferentes ao comparar os modelos de 3 e 2 bits com a referência: para o modelo de 3 bits, relata perdas nas taxas de reconhecimento, enquanto para o modelo de 2 bits relata diminuições nas taxas de erro\. Como o texto não esclarece de modo uniforme se os percentuais são variações de acurácia ou de erro, e uma diminuição da taxa de erro pode indicar melhora, a direção e o significado das diferenças de desempenho ficam ambíguos para o leitor\.
- b:observation:sec\_10:method:1:sec10\_obs1: Os parâmetros específicos para o tamanho do batch, weight decay e momentum não são fornecidos explicitamente nesta seção, sendo apenas referido que são os mesmos da &\#x27;segunda série de experimentos&\#x27;\.
- b:observation:sec\_10:method:1:sec10\_obs2: O número exato de épocas para os modelos de 4\-bit e 3\-bit não é especificado, apenas que &\#x27;aumenta quando a largura de bit esperada diminui&\#x27; e atinge 30 para o modelo de 2\-bit\.
- b:observation:sec\_10:method:1:sec10\_obs3: As porções acumuladas de pesos quantizados em passos iterativos \(cronogramas de quantização\) são detalhadas explicitamente para cada largura de bit \(4\-bit, 3\-bit e 2\-bit\)\.
- c:observation:sec\_10:method:1:obs\_10\_1 [unresolved]: O desenho experimental afirma explorar o “limit of the expected bit\-width” e relaciona isso a “lossless network quantization”, mas o texto não define operacionalmente o que conta como “lossless” nem como o “expected bit\-width” é calculado, reduzindo a solidez da inferência\.
- c:observation:sec\_10:method:1:obs\_10\_2 [unresolved]: Apesar de indicar que “lower\-precision models with 4\-bit, 3\-bit and even 2\-bit ternary weights are generated”, não especifica as regras/propriedades exatas do esquema ternário \(ex\.: quais valores são permitidos além de zero e potências de dois; como se mapeia 3\-bit/2\-bit para os valores candidatos\)\.
- c:observation:sec\_10:method:1:obs\_10\_3 [unresolved]: O texto fornece listas de “accumulated portions of quantized weights at iterative steps”, mas não explica como essas frações determinam o número de iterações, a atualização dos grupos de pesos em cada passo \(além de frações acumuladas\), nem como isso se traduz diretamente em “candidate quantum values” e na discretização final\.
- c:observation:sec\_10:method:1:obs\_10\_4 [unresolved]: Apresenta resultados quantitativos comparando explicitamente perdas em top\-1 e top\-5 contra referência full\-precision para diferentes bit\-widths, o que melhora a verificabilidade dos achados\.
- c:observation:sec\_10:method:1:obs\_10\_5 [unresolved]: Há possível inconsistência/ambiguidade entre métricas: para bit\-width=3 fala\-se em “losses in top\-1 and top\-5 recognition rates”, enquanto para 2\-bit fala\-se em “decrease in top\-1 error rate and top\-5 error rate”\. Isso pode confundir a interpretação direta \(rate vs error\) sem explicitar a relação/transformação\.
- c:observation:sec\_10:method:1:obs\_10\_6 [unresolved]: As afirmações de comparação com resultados de BWN/TWN citam as referências, mas não indicam se as configurações/treinos e o backbone são estritamente comparáveis \(exceto implicitamente “approximations of ResNet\-18”\), nem como exatamente a comparação é feita; os valores detalhados são remetidos para “Table 3 and Table 4”\.

### 3\.4 Low\-BIT DEEP COMPRESSION

- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_1: A seção cobre os trabalhos mais próximos e relevantes para a alegação de compressão: deep compression, pruning, vector quantization, Huffman coding e DNS\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_2: A diferença central da proposta em relação à quantização vetorial é explicitada: INQ atua em todas as camadas, preserva a acurácia nos experimentos de 5 e 4 bits e restringe os pesos a potências de dois ou zero, enquanto os métodos comparados mantêm pesos em ponto flutuante\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3 [unresolved]: A comparação considera dimensões relevantes e equivalentes, incluindo razão de compressão, acurácia, camadas convolucionais versus fully connected, custo de retreinamento e representação final dos pesos\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_4: A comparação entre INQ\+DNS e deep compression não separa claramente o ganho atribuível ao INQ daquele atribuível ao DNS, embora o trabalho de Han seja uma combinação de técnicas e o método proposto também seja avaliado como combinação\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_5: A alegação de comparação justa é insuficientemente qualificada: os números de compressão são apresentados para combinações diferentes de componentes, mas a seção não explicita no texto as condições completas de treinamento, codificação, representação da arquitetura e cálculo da razão de compressão necessários para verificar a equivalência\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_6: A conclusão de superioridade é mais forte do que a evidência textual apresentada, pois a seção afirma que INQ é &\#x27;much better&\#x27; e &\#x27;evident&\#x27; com base principalmente em acurácia e compressão, sem discutir limitações ou possíveis custos adicionais da solução combinada\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_7: A contribuição de implementação é diferenciada de forma concreta em relação aos trabalhos próximos: pesos em potências de dois ou zero permitem substituir multiplicações por operações de deslocamento de bits em hardware dedicado\.
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_8: A distinção entre compressão de modelo e aceleração de inferência em hardware é apresentada como consequência direta, mas não fica claro nesta seção se a vantagem de deslocamento de bits foi medida experimentalmente ou apenas inferida da forma dos pesos\.
- b:observation:sec\_11:related\_work:1:obs1 [unresolved]: O artigo compara de forma abrangente e quantitativa a abordagem proposta \(INQ combinada com DNS\) com o método de compressão profunda de última geração \(Han et al\., 2016\), demonstrando claramente as vantagens de compressão e eficiência\.
- b:observation:sec\_11:related\_work:1:obs2: A comparação entre o INQ e a quantização vetorial \(Gong et al\., 2014\) é clara, destacando que o INQ aborda todas as camadas da rede sem perda de precisão para certas quantizações, ao contrário da quantização vetorial que se foca principalmente nas camadas totalmente conectadas e incorre em perdas de precisão\.
- b:observation:sec\_11:related\_work:1:obs3: A originalidade do INQ é bem estabelecida pela explicação clara de que seus pesos finais são em potências de dois ou zero, diferentemente de outros métodos que resultam em valores de ponto flutuante, e que isso permite operações de deslocamento de bits mais baratas em hardware dedicado\.
- c:observation:sec\_11:related\_work:1:obs\_1 [unresolved]: O texto identifica trabalhos relevantes e discute explicitamente as técnicas que compõem o método de Han et al\. \(2016\), permitindo comparação direta com a proposta \(INQ\)\.
- c:observation:sec\_11:related\_work:1:obs\_2: Há comparação em termos de condições de avaliação \(combinação ‘fair comparison’ e reuso de setup\), incluindo o uso de DNS junto com INQ para enfrentar limitações do pipeline de Han et al\.
- c:observation:sec\_11:related\_work:1:obs\_3: A clareza da diferença de proposta vs\. alternativa está parcialmente explícita \(INQ vs\. vector quantization\), mas a comparação com Han et al\. depende de tabelas externas sem explicitar quais partes do pipeline são substituídas/isoladas além da frase geral de “combining”\.
- c:observation:sec\_11:related\_work:1:obs\_4: O texto explica a diferenciação do INQ em relação à quantização vetorial \(Gong et al\., 2014\) tanto em escopo \(todas as camadas\) quanto em impacto de acurácia \(afirma ‘no accuracy loss’ para 5\-bit/4\-bit\) e também em formato do peso \(potências de dois ou zero\)\.
- c:observation:sec\_11:related\_work:1:obs\_5: A alegação de que Han et al\. “reports so far best results … without loss of model accuracy” é feita antes de detalhar a configuração/definição de “without loss” \(ex\.: quais métricas/níveis\), o que pode prejudicar a comparação justa, especialmente porque o texto atribui ganhos numéricos ao INQ vs\. uma “fair version”\.
- c:observation:sec\_11:related\_work:1:obs\_6 [unresolved]: A originalidade da contribuição \(INQ\) é inferida principalmente por contrastes com outros métodos, mas o texto não fornece evidência textual específica ligada ao mecanismo \(ex\.: “incremental network quantization”\) nesta seção; foca em comparação de resultados e diferenças de hardware/formatos\.

### 4 CONCLUSIONS

- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_1: A conclusão apresenta de forma clara a contribuição central — o INQ — e resume seus componentes operacionais, permitindo relacionar diretamente o método ao objetivo de obter CNNs de baixa precisão\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_2: O impacto alegado é apoiado por resultados concretos em arquiteturas relevantes e por diferentes larguras de representação; a conclusão também diferencia a contribuição demonstrada das extensões futuras, ao apresentar hardware, ativações e gradientes como trabalhos planejados\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_3: A conclusão emprega afirmações mais amplas do que o alcance experimental explicitamente descrito: “any pre\-trained” e “lossless” sugerem validade geral, enquanto os resultados citados estão delimitados à classificação no ImageNet e a um conjunto específico de arquiteturas\. Seria mais claro qualificar essas afirmações como demonstradas para os modelos e configurações avaliados\.
- a:observation:sec\_12:conclusion:1:sec\_12\_obs\_4: O significado de “lossless” não é explicitado na própria conclusão: o texto informa acurácia “improved or at least comparable”, mas não esclarece se a ausência de perda se refere exclusivamente à acurácia, nem em que condições a comparação foi realizada\. Uma definição breve evitaria ambiguidade terminológica\.
- b:observation:sec\_12:conclusion:1:con\_clarity\_support\_01: As conclusões apresentam claramente o método INQ e apoiam suas afirmações com os resultados experimentais\. A menção explícita da obtenção de acurácia melhorada ou comparável em diversas arquiteturas de CNN com pesos de baixa precisão \(2\-5 bits\) na tarefa ImageNet, demonstra um sucesso considerável em alcançar quantização de baixa precisão com preservação da acurácia\.
- b:observation:sec\_12:conclusion:1:con\_impact\_01: O texto da conclusão realça de forma eficaz o impacto do método INQ ao propor uma solução para converter modelos CNN de precisão total em versões de baixa precisão com desempenho comparável ou superior aos baselines, o que é crucial para a aplicação de redes neurais profundas em dispositivos com recursos limitados\.
- c:observation:sec\_12:conclusion:1:obs\_1: A conclusão explicita claramente o objetivo e a restrição do problema \(converter modelos 32\-bit para um formato “lossless” com pesos limitados a potências de 2 ou zero\)\.
- c:observation:sec\_12:conclusion:1:obs\_2: A conclusão afirma que o método resolve o problema proposto \(“lossless”\), mas o trecho da seção fornecido não apresenta evidência quantitativa/relacionamento direto com resultados \(tabelas/figuras\) para sustentar essa alegação dentro da própria conclusão\.
- c:observation:sec\_12:conclusion:1:obs\_3: O texto da conclusão \(como apresentado\) não sintetiza resultados específicos mencionados no restante do artigo \(ex\.: 5\-bit/4\-bit/3\-bit/2\-bit e “improved or at least comparable accuracy”\), nem remete explicitamente a Tabelas/Figuras, reduzindo o impacto e a rastreabilidade das conclusões\.

### A APPENDIX 1: STATISTICAL ANALYSIS OF THE QUANTIZED WEIGHTS

- a:observation:sec\_14:results:1:sec\_14\_obs\_1 [unresolved]: A tabela fornece distribuições percentuais por camada e permite verificar diretamente várias afirmações quantitativas, como a concentração de aproximadamente 60% em Conv1 e 94% em Conv2 nos conjuntos de valores especificados\.
- a:observation:sec\_14:results:1:sec\_14\_obs\_2 [unresolved]: A afirmação de que há mais pesos zero nas camadas Conv2–Conv5 do que em Conv1 é sustentada pela tabela, mas a redação pode induzir uma interpretação incorreta de que essas camadas também crescem monotonicamente entre si: as proporções são 5,51% \(Conv1\), 11,30% \(Conv2\), 12,24% \(Conv3\), 9,70% \(Conv4\) e 8,97% \(Conv5\)\.
- a:observation:sec\_14:results:1:sec\_14\_obs\_3 [unresolved]: A alegação de que a mesma concentração de aproximadamente 98% ocorre na segunda camada totalmente conectada não é confirmada uniformemente pela tabela\. O conjunto indicado soma cerca de 92,97% em FC7 e cerca de 73,19% em FC8, enquanto soma cerca de 98,09% em FC6\. O texto também não esclarece se “2nd fully connected layer” significa FC7 ou se FC8 foi deliberadamente excluída\.
- a:observation:sec\_14:results:1:sec\_14\_obs\_4 [unresolved]: A comparação entre distribuições “mais dispersas” nas camadas convolucionais e totalmente conectadas é qualitativa e não apresenta uma métrica de dispersão, concentração ou entropia\. Além disso, a inferência causal de que essa diferença explica o melhor desempenho de hashing e quantização vetorial não é testada neste apêndice\.
- a:observation:sec\_14:results:1:sec\_14\_obs\_5: A conclusão de que o modelo de 5 bits requer efetivamente largura de 4 bits não explica como o valor de bit\-width 4 registrado para todas as camadas se relaciona com a representação do zero e dos demais valores quantizados apresentados na tabela\.
- a:observation:sec\_14:results:1:sec\_14\_obs\_6 [unresolved]: A apresentação da tabela contém notação ambígua para os pesos, como “\-2\-10” e “2\-10”, em vez de uma forma que preserve explicitamente os expoentes\. Isso dificulta a correspondência entre os rótulos da tabela e os conjuntos matemáticos descritos no texto\.
- b:observation:sec\_14:results:1:obs1\_sec14: The claim that for the 2nd fully connected layer \(FC7\), specific quantized weight values occupy about 98% of all weights is inaccurate\. Calculations based on Table 6 show this sum to be approximately 92\.97% for FC7, which is a noticeable difference from the stated &\#x27;about 98%&\#x27;\. While &\#x27;similar results&\#x27; is qualitative, the specific percentage provided for FC6 sets an expectation that isn&\#x27;t met by FC7&\#x27;s data\.
- b:observation:sec\_14:results:1:obs2\_sec14 [unresolved]: The section provides a clear and comprehensive statistical analysis of quantized weight distributions across different layers of the AlexNet model\. The five enumerated findings are well\-supported by the detailed data presented in Table 6, effectively highlighting patterns, concentrations, and differences between convolutional and fully connected layers\. This robust statistical examination contributes significantly to the understanding of the quantization method&\#x27;s effects\.
- b:observation:sec\_14:results:1:obs3\_sec14: The appendix provides crucial clarity by explicitly stating that despite being referred to as a &\#x27;5\-bit AlexNet model,&\#x27; the actual required bit\-width for each layer is 4\. This directly addresses potential ambiguity arising from the model&\#x27;s overall naming versus the per\-layer quantization scheme, which is consistent with the abstract&\#x27;s description of a variable\-length encoding \(1 bit for zero, 4 bits for values\)\.
- c:observation:sec\_14:results:1:obs\_1: A seção apresenta uma análise estatística específica das distribuições de pesos quantizados no modelo AlexNet de 5\-bit e remete ao conteúdo da Tabela 6 como evidência\.
- c:observation:sec\_14:results:1:obs\_2 [unresolved]: Há quantificação direta \(percentuais\) sobre quais valores discretos dominam as distribuições nas camadas convolucionais 1 e 2, alinhada com a alegação de cobertura percentual\.
- c:observation:sec\_14:results:1:obs\_3: A alegação sobre “distributions … are similar” entre as camadas 3/4/5 e a 2ª não explicita um critério operacional \(ex\.: métrica de similaridade\) e, portanto, pode ficar interpretativa sem sustentação formal além da tabela\.
- c:observation:sec\_14:results:1:obs\_4: A afirmação de que o conjunto de valores no 1º fully connected layer “ocupa about 98%” precisa explicitar explicitamente o cálculo/soma usado para obter \~98% a partir da Tabela 6 \(isto é, quais entradas exatas foram somadas para formar o conjunto citado\), para evitar inferência por agregação implícita\.
- c:observation:sec\_14:results:1:obs\_5: A seção afirma explicitamente que “for 5\-bit AlexNet model, the required bit\-width for each layer is actually 4 but not 5”, e isso contradiz a rotulagem geral “5\-bit” do modelo, sem explicar como essa redução de bit\-width é operacionalizada\.
- c:observation:sec\_14:results:1:obs\_6: A explicação causal “This may be partially the reason …” conecta dispersão estatística à facilidade de compressão, mas não oferece evidência adicional \(ex\.: comparação quantitativa de dispersão vs\. ganho de compressão\) para sustentar a inferência\.

### B APPENDIX 2: LOSSLESS CNNS WITH LOW\-PRECISION WEIGHTS AND LOW\-PRECISION ACTIVATIONS

- a:observation:sec\_15:results:1:sec\_15\_obs\_1 [unresolved]: A tabela fornece uma comparação direta entre o modelo quantizado e a referência, reportando as larguras de bits e os erros Top\-1 e Top\-5, o que torna a alegação de melhoria numericamente verificável\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_2 [unresolved]: A comparação não informa variância, número de execuções, intervalos de confiança ou significância estatística; portanto, não é possível determinar se as melhorias de 1,64 e 1,16 pontos percentuais são robustas ou podem resultar de variação experimental\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_3 [unresolved]: Faltam detalhes essenciais do protocolo experimental, incluindo conjunto de avaliação, procedimento de treinamento ou ajuste após a quantização das ativações, hiperparâmetros e confirmação de que a referência e o modelo 5/4 foram avaliados sob condições idênticas\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_4 [unresolved]: A alegação de que este é o melhor resultado publicado em VGG\-16 não é sustentada pela tabela: não há baselines externos, referências bibliográficas, critérios de seleção nem comparação com outros métodos de quantização de ativações\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_5 [unresolved]: O resultado mostra menor erro no modelo quantizado do que na referência, mas o texto o descreve como &quot;lossless&quot; sem distinguir preservação de acurácia de melhoria de acurácia; essa terminologia pode induzir a uma interpretação imprecisa da conclusão\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_6 [unresolved]: Não são apresentados resultados de ablação que separem o efeito de quantizar pesos para 5 bits do efeito de quantizar ativações para 4 bits\. Assim, a tabela não permite atribuir a melhoria à quantização conjunta nem avaliar o custo específico de cada componente\.
- a:observation:sec\_15:results:1:sec\_15\_obs\_7 [unresolved]: A apresentação da tabela contém problemas de formatação e nomenclatura que reduzem a clareza, como &quot;Bit\-width forweight/activation&quot;, &quot;float\-point&quot; e a ausência explícita de unidades ou de um rótulo para a linha de variação dos erros\.
- b:observation:sec\_15:results:1:obs\_1: The comparison between the quantized VGG\-16 model and the full\-precision baseline is clearly presented, demonstrating improved top\-1 and top\-5 error rates with specific numerical values and calculated decreases\.
- b:observation:sec\_15:results:1:obs\_2: The results in Table 7 do not include statistical measures such as variance or standard deviation for the error rates, which hinders the assessment of the statistical significance of the reported improvements\.
- b:observation:sec\_15:results:1:obs\_3: A strong claim of achieving &\#x27;the best results reported on VGG\-16 architecture so far&\#x27; is made, but it is primarily supported by a subjective &\#x27;to the best of our knowledge&\#x27; statement within this appendix section, without explicit references or detailed comparisons to other state\-of\-the\-art methods in the provided text\.
- c:observation:sec\_15:results:1:sec\_15\_obs\_1: O apêndice apresenta um comparativo quantitativo entre a versão quantizada \(5\-bit weights/4\-bit activations\) e a referência de 32\-bit, incluindo métricas \(Top\-1 e Top\-5\) e uma indicação de “Decrease”\.
- c:observation:sec\_15:results:1:sec\_15\_obs\_2: A afirmação “shows improved top\-5 and top\-1 recognition rates” é menos precisa porque a tabela reporta explicitamente “Top\-1 error” e “Top\-5 error” \(erros\), não taxas de reconhecimento; além disso, não fica explicitado se “recognition rates” foi intencionalmente convertido a partir dos erros\.
- c:observation:sec\_15:results:1:sec\_15\_obs\_3: A conclusão “To the best of our knowledge, this should be the best results reported on VGG\-16 architecture so far” é uma alegação de superioridade/estado\-da\-arte não sustentada por evidência documental dentro do trecho \(não há comparação com outros trabalhos nem citações nesta seção/excerto\)\.

## Evidências

- b:criterion:impact: O impacto potencial do INQ é bem articulado, prometendo converter modelos CNN de precisão total em versões de baixa precisão &quot;lossless&quot; \(sem perda de acurácia\) cujos pesos são potências de dois ou zero, permitindo implementações de hardware mais eficientes com operações de deslocamento de bits\. Este impacto é sustentado por um resumo de resultados experimentais impressionantes, demonstrando acurácia melhorada ou similar para diversas arquiteturas com quantização de 5, 4 e 3 bits, abordando diretamente os problemas de perda de acurácia e iterações de treinamento\.
- b:observation:sec\_2:introduction:1:intro\_impact\_potential: The potential impact of INQ is well\-articulated, promising to convert full\-precision CNN models into lossless low\-precision versions with weights constrained to powers of two or zero, which enables more efficient hardware implementation through bit\-shift operations\.
  - sec\_2: In our INQ, there is no assumption on the CNN architecture, and its basic goal is to efficiently convert any pre\-trained full\-precision \(i\.e\., 32\-bit floating\-point\) CNN model into a low\-precision version whose weights are constrained to be either powers of two or zero\.
  - sec\_2: The advantage of such kind of low\-precision models is that the original floating\-point multiplication operations can be replaced by cheaper binary bit shift operations on dedicated hardware like FPGA\.
  - sec\_2: The main insight of our INQ is that a compact combination of the proposed weight partition, group\-wise quantization and re\-training operations has the potential to get a lossless low\-precision CNN model from any full\-precision reference\.
- b:observation:sec\_2:introduction:1:intro\_impact\_sustained\_results: The impact is strongly sustained by a summary of impressive experimental results, demonstrating improved or similar accuracy for various CNN architectures and bit\-widths \(5\-bit, 4\-bit, 3\-bit, 2\-bit\), and showing easy convergence, directly addressing the stated problems of accuracy loss and training iterations\.
  - sec\_2: We conduct extensive experiments on the ImageNet large scale classification task using almost all known deep CNN architectures to validate the effective\-ness of our method\.
  - sec\_2: \(1\) For AlexNet, VGG\-16, GoogleNet and ResNets with 5\-bit quantization, INQ achieves improved accuracy in comparison with their respective full\-precision baselines\. The absolute top\-1 accuracy gain ranges from 0\.13% to 2\.28%, and the absolute top\-5 accuracy gain is in the range of 0\.23% to 1\.65%\.
  - sec\_2: \(2\) INQ has the property of easy convergence in training\. In general, re\-training with less than 8 epochs could consistently generate a lossless model with 5\-bit weights in the experiments\.
  - sec\_2: \(3\) Taking ResNet\-18 as an example, our quantized models with 4\-bit, 3\-bit and 2\-bit ternary weights also have improved or very similar accuracy compared with its 32\-bit floating\-point baseline\.
  - sec\_2: \(4\) Taking AlexNet as an example, the combination of our network pruning and INQ outperforms deep compression method \(Han et al\., 2016\) with significant margins\.
- b:observation:sec\_12:conclusion:1:con\_impact\_01: O texto da conclusão realça de forma eficaz o impacto do método INQ ao propor uma solução para converter modelos CNN de precisão total em versões de baixa precisão com desempenho comparável ou superior aos baselines, o que é crucial para a aplicação de redes neurais profundas em dispositivos com recursos limitados\.
  - sec\_12: In this paper, we present INQ, a new network quantization method, to address the problem of how to convert any pre\-trained full\-precision \(i\.e\., 32\-bit floating\-point\) CNN model into a lossless low\-precision version whose weights are constrained to be either powers of two or zero\.
  - sec\_12: our quantized CNN models with 5\-bit, 4\-bit, 3\-bit and even 2\-bit ternary weights have improved or at least comparable accuracy against their full\-precision baselines, including AlexNet, VGG\-16, GoogleNet and ResNets\.
- b:criterion:originality: O artigo apresenta o método INQ como uma abordagem nova, contrastando\-o com as estratégias de quantização global existentes que negligenciam a importância dos pesos, o que é um ponto chave de originalidade \(sec\_2:introduction:1:intro\_contribution\_originality\)\. Além disso, a originalidade é reforçada pelo fato de que os pesos finais do INQ são potências de dois ou zero, permitindo operações de deslocamento de bits mais eficientes em hardware dedicado, ao contrário de outros métodos que ainda resultam em valores de ponto flutuante \(sec\_11:related\_work:1:obs3\)\.
- b:observation:sec\_2:introduction:1:intro\_contribution\_originality: The paper clearly positions its Incremental Network Quantization \(INQ\) method as novel by explicitly contrasting its iterative, group\-wise approach with existing global quantization strategies that often neglect weight importance, thus highlighting its originality in addressing accuracy drop\.
  - sec\_2: In this paper, we attempt to address these two issues by presenting a novel incremental network quantization \(INQ\) method\.
  - sec\_2: We noticed that most existing network quantization methods adopt a global strategy in which all the weights are simultaneously converted to low\-precision ones \(that are usually in the floating\-point types\)\. That is, they have not considered the different importance of network weights, leaving the room to retain network accu\-racy limited\. In sharp contrast to existing methods, our INQ makes a very careful handling for the model accuracy drop from network quantization\.
  - sec\_2: Furthermore, these three operations are repeated on the latest re\-trained weight group in an iterative manner until all the weights are quantized, acting as an incremental network quantization and accuracy enhancement procedure \(as illustrated in Figure 1\)\.
- b:observation:sec\_11:related\_work:1:obs3: A originalidade do INQ é bem estabelecida pela explicação clara de que seus pesos finais são em potências de dois ou zero, diferentemente de outros métodos que resultam em valores de ponto flutuante, e que isso permite operações de deslocamento de bits mais baratas em hardware dedicado\.
  - sec\_11: Last but not least, the final weights for vector quantization \(Gong et al\., 2014\), network pruning \(Han et al\., 2015\) and deep compression \(Han et al\., 2016\) are still floating\-point values, but the final weights for our INQ are in the form of either powers of two or zero\.
  - sec\_11: The direct advantage of our INQ is that the original floating\-point multiplication operations can be replaced by cheaper binary bit shift operations on dedicated hardware like FPGA\.
- c:criterion:meaningful\_comparison: O artigo identifica e compara com trabalhos relevantes \(Han et al\. 2016; Gong et al\. 2014; além de referência a BWN/TWN e uso de DNS para “fair comparison”\), e discute diferenças em escopo do que é quantizado \(INQ “addresses all network layers simultaneously” vs quantização vetorial focada em fully connected\)\. Contudo, a comparabilidade é parcialmente comprometida por alegações anteriores à definição operacional de “without loss”, por descrições pouco detalhadas de quais partes do pipeline são substituídas/isoladas quando “combina INQ e DNS”, e por dependência de tabelas externas para justificar magnitude e condições específicas\.
- c:observation:sec\_11:related\_work:1:obs\_2: Há comparação em termos de condições de avaliação \(combinação ‘fair comparison’ e reuso de setup\), incluindo o uso de DNS junto com INQ para enfrentar limitações do pipeline de Han et al\.
  - sec\_11: For fair comparison, we combine our proposed INQ and DNS, and compare the resulting method with Han et al\. \(2016\)\. Detailed results are summarized in Table 5\.
  - sec\_11: It will cost at least several weeks for compressing AlexNet\. We solved this problem by our dynamic network surgery \(DNS\) method \(Guo et al\., 2016\) which achieves about 7× speed\-up in training and improves the performance of network pruning from 9× to 17\.7×\.
- c:observation:sec\_11:related\_work:1:obs\_3: A clareza da diferença de proposta vs\. alternativa está parcialmente explícita \(INQ vs\. vector quantization\), mas a comparação com Han et al\. depende de tabelas externas sem explicitar quais partes do pipeline são substituídas/isoladas além da frase geral de “combining”\.
  - sec\_11: For fair comparison, we combine our proposed INQ and DNS, and compare the resulting method with Han et al\. \(2016\)\. Detailed results are summarized in Table 5\.
  - sec\_11: When combing our proposed INQ and DNS, we achieve much better compression results compared with Han et al\. \(2016\)\.
- c:observation:sec\_11:related\_work:1:obs\_5: A alegação de que Han et al\. “reports so far best results … without loss of model accuracy” é feita antes de detalhar a configuração/definição de “without loss” \(ex\.: quais métricas/níveis\), o que pode prejudicar a comparação justa, especialmente porque o texto atribui ganhos numéricos ao INQ vs\. uma “fair version”\.
  - sec\_11: In the literature, recently proposed deep compression method \(Han et al\., 2016\) reports so far best results on network compression without loss of model accuracy\.
  - sec\_11: Specif\- ically, with 5\-bit quantization, we can achieve 53× compression with slightly larger gains both in top\-5 and top\-1 recognition rates, yielding 51\.43%/96\.30% absolute improvement in compression performance compared with full version/fair version \(i\.e\., the combination of network pruning and vector quantization\) of Han et al\. \(2016\), respectively\.
- c:criterion:substance: O artigo relata experimentos em ImageNet, testando múltiplas arquiteturas \(AlexNet, VGG\-16, GoogleNet, ResNet\-18 e ResNet\-50\) e avaliando top\-1/top\-5, além de análises adicionais \(por exemplo, distribuições de pesos em AlexNet 5\-bit e comparativos em VGG\-16 com pesos 5\-bit e ativações 4\-bit\)\. Porém, a reprodutibilidade e a avaliação completa da contribuição ficam limitadas por falta de detalhes de protocolo \(batch/learning rate/stop criteria\), por tabelas mencionadas mas não apresentadas no recorte fornecido, e por inconsistências/ambiguidade de métricas \(“recognition rates” vs “error rates”\) e escopo de alguns resultados\. Assim, há substância experimental razoável, mas não plenamente verificável\.
- c:observation:sec\_7:results:1:obs\_1: O texto especifica o benchmark, o tamanho do conjunto de dados e as métricas de avaliação usadas \(top\-1 e top\-5 error rate\)\.
  - sec\_7: we perform extensive experiments on the ImageNet large scale classification task
  - sec\_7: ImageNet dataset has about 1\.2 million training images and 50 thousand validation images\.
  - sec\_7: Using the center crops of validation images, we report the results with two standard measures: top\-1 error rate and top\-5 error rate\.
- c:observation:sec\_8:results:1:obs\_2: A conclusão de melhoria \(top\-1/top\-5\) é declarada sem apresentar números ou intervalo de variação diretamente no texto, dependendo da Tabela 1 não incluída aqui\.
  - sec\_8: It can be concluded that the 5\-bit CNN models generated by our INQ show consistently improved top\-1 and top\-5 recognition rates compared with respective full\-precision references\.
  - sec\_8: we obtain the results as shown in Table 1\.

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
- Prompt document\_extractor: 0033c4ee536d3bd8184a0cfbfe4c97b44fde5665344ae081a4b84ad158becca5, 1140d4ec249168ee0cc5b1a0aaa83d390fac9f193bb551e8a5877a949783c6ad, 4433d15d42ee0e724e3dc3e85033e2a0d99dd3b2575cf6330abff40ddb663758, 857234b8fdc3dbc0830669610df8b478c916024a6d89719b3ae55ec39818579c, a27f734df6e9efe83cbba9f99f5617507cdff9a97bc13162b0069f1059f4b622
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
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6
- a:observation:sec\_5:method:1:sec\_5\_obs\_3
- a:observation:sec\_6:method:1:sec\_6\_obs\_1
- a:observation:sec\_7:results:1:sec\_7\_obs\_6
- a:observation:sec\_8:results:1:sec\_8\_obs\_2
- a:observation:sec\_11:related\_work:1:sec\_11\_obs\_3
- a:observation:sec\_14:results:1:sec\_14\_obs\_1
- a:observation:sec\_14:results:1:sec\_14\_obs\_2
- a:observation:sec\_14:results:1:sec\_14\_obs\_3
- a:observation:sec\_14:results:1:sec\_14\_obs\_4
- a:observation:sec\_14:results:1:sec\_14\_obs\_6
- a:observation:sec\_15:results:1:sec\_15\_obs\_1
- a:observation:sec\_15:results:1:sec\_15\_obs\_2
- a:observation:sec\_15:results:1:sec\_15\_obs\_3
- a:observation:sec\_15:results:1:sec\_15\_obs\_4
- a:observation:sec\_15:results:1:sec\_15\_obs\_5
- a:observation:sec\_15:results:1:sec\_15\_obs\_6
- a:observation:sec\_15:results:1:sec\_15\_obs\_7
- a:check:claims\_vs\_results:claims\_vs\_results\_1
- b:observation:sec\_4:method:1:quantization\_b\_selection
- b:observation:sec\_4:method:1:constants\_justification
- b:observation:sec\_4:method:1:method\_clarity\_strength
- b:observation:sec\_6:method:1:obs\_6\_5
- b:observation:sec\_6:method:1:obs\_6\_7
- b:observation:sec\_11:related\_work:1:obs1
- b:check:method\_vs\_question:INQ\_method\_vs\_question\_1
- b:observation:sec\_6:method:1:obs\_6\_1
- b:observation:sec\_14:results:1:obs2\_sec14
- b:criterion:clarity
- b:criterion:replicability
- c:observation:sec\_2:introduction:1:obs\_3
- c:observation:sec\_2:introduction:1:obs\_4
- c:observation:sec\_2:introduction:1:obs\_6
- c:observation:sec\_4:method:1:obs\_4\_1
- c:observation:sec\_4:method:1:obs\_4\_2
- c:observation:sec\_4:method:1:obs\_4\_3
- c:observation:sec\_4:method:1:obs\_4\_4
- c:observation:sec\_4:method:1:obs\_4\_5
- c:observation:sec\_5:method:1:sec\_5\_obs\_3
- c:observation:sec\_5:method:1:sec\_5\_obs\_5
- c:observation:sec\_6:method:1:obs\_1
- c:observation:sec\_6:method:1:obs\_2
- c:observation:sec\_8:results:1:obs\_3
- c:observation:sec\_9:results:1:obs\_2
- c:observation:sec\_10:method:1:obs\_10\_1
- c:observation:sec\_10:method:1:obs\_10\_2
- c:observation:sec\_10:method:1:obs\_10\_3
- c:observation:sec\_10:method:1:obs\_10\_4
- c:observation:sec\_10:method:1:obs\_10\_5
- c:observation:sec\_10:method:1:obs\_10\_6
- c:observation:sec\_11:related\_work:1:obs\_1
- c:observation:sec\_11:related\_work:1:obs\_6
- c:observation:sec\_14:results:1:obs\_2
- c:check:claims\_vs\_results:crosscheck\_1
- c:check:method\_vs\_question:crosscheck\_method\_vs\_question
- c:check:figure\_vs\_text:crosscheck\_figure\_vs\_text
- c:criterion:originality

## Avisos

- As faixas de recomendação são provisórias e aguardam calibração\.
