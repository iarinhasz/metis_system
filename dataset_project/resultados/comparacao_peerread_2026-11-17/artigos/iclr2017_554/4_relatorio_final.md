# INVESTIGATING RECURRENCE AND ELIGIBILITY TRACES IN DEEP Q\-NETWORKS

Run: `01a1e74d-eaad-749b-8e82-f9e7184bfff7`

Recomendação: **major**
Nota ponderada: **2.50** · Concordância: **0.75**

Revisão humana sinalizada: sim

## Critérios

### Originalidade

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- C (rodada 3, nota 2): A alegação de novidade aparece de forma pouco específica: o texto aponta uma lacuna geral \(uso de eligibility traces em deep RL “limited so far”\) e afirma ganhos com experimentos, mas não delimita precisamente o que é novo \(p\.ex\., qual formulação/variante, configurações combinadas e diferenças concretas frente ao estado da arte\)\. Além disso, o material fornecido de related work não apresenta claramente uma contribuição própria, dificultando sustentar novidade com evidência textual\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`

### Solidez

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Substância

Nota: 3.00 · Dispersão: 1.00 · Votos válidos: 3

- A (rodada 3, nota 3): O artigo contém experimentos comparativos em dois jogos, com variações de traces, arquitetura, otimizadores e taxas de aprendizado, além de interpretações mecanísticas e resultados temporais\. Ainda assim, a cobertura é estreita, as métricas e curvas não estão integralmente disponíveis no material fornecido, faltam variabilidade e testes estatísticos, e não há ablações suficientes para separar os efeitos dos componentes\.
- B (rodada 3, nota 2): O artigo apresenta estudos de ablação abrangentes e análises qualitativas para os jogos testados, fornecendo métricas quantitativas claras em alguns casos\. Demonstra a superioridade de modelos RNN sobre DQN no jogo Tennis e oferece análises perspicazes para o fracasso do DQN nesse ambiente\. No entanto, a substância é enfraquecida pela falta de baselines claras e estatísticas iniciais na introdução dos resultados\. Alegações sobre estabilidade carecem de análise estatística quantitativa\. Uma afirmação forte sobre o sucesso único do algoritmo no Tennis não é totalmente sustentada por detalhes experimentais explícitos de todas as variantes de DQN mencionadas\. Além disso, a inconsistência entre as alegações iniciais e alguns resultados experimentais reduz a força geral das evidências apresentadas\.
- C (rodada 3, nota 3): O trabalho apresenta experimentos em Atari \(Pong e Tennis\) com comparações diretas entre modelos com e sem eligibility traces e entre otimizadores \(RMSprop/Adam\), além de descrever arquitetura e métricas/epocas\. Contudo, há limitações na profundidade/robustez da evidência para certas alegações: hipóteses causais \(propagação de recompensa; diferenças entre otimizadores\) permanecem especulativas; também há lacunas de desenho/definição operacional em trechos cruciais \(implementação exata de traces/ truncamentos\) e evidência de “estabilidade” baseada mais em descrição qualitativa do que em critérios quantitativos\.

### Clareza

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Comparação

Nota: indisponível · Dispersão: indisponível · Votos válidos: 0

- Voto excluído de A: `evidence_not_validated`
- Voto excluído de B: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Impacto

Nota: 3.00 · Dispersão: indisponível · Votos válidos: 1

- B (rodada 3, nota 3): O artigo aborda problemas relevantes em DRL, como recompensas esparsas e o problema de atribuição de crédito, e demonstra um ganho significativo no desempenho e na estabilidade com RNNs em um jogo desafiador como Tennis, e com traces de elegibilidade em Pong\. As sugestões de trabalhos futuros também são promissoras\. No entanto, o impacto é mitigado pela inconsistência entre as alegações iniciais de que traces de elegibilidade impulsionam o desempenho e os resultados experimentais em certos cenários, além do abandono do foco em observabilidade parcial, conforme inicialmente proposto\.
- Voto excluído de A: `evidence_not_validated`
- Voto excluído de C: `evidence_not_validated`

### Reprodutibilidade

Nota: 2.00 · Dispersão: indisponível · Votos válidos: 1

- A (rodada 3, nota 2): A arquitetura, o tamanho das subtrajetórias, o burn\-in, o lote, alguns hiperparâmetros dos otimizadores e a frequência da rede\-alvo são informados\. Porém, faltam ou permanecem ambíguos parâmetros essenciais dos traces, fórmulas dos alvos, regras de terminação e detalhes do ambiente, avaliação, sementes e protocolo experimental; a notação corrompida também impede reconstruir exatamente o algoritmo\.
- Voto excluído de B: `unresolved`
- Voto excluído de C: `evidence_not_validated`

## Pontos fortes

- O estudo realiza comparações diretas entre modelos com e sem eligibility traces, diferentes otimizadores e taxas de aprendizado em Pong e Tennis, incluindo métricas temporais para atingir determinados níveis de desempenho\. [a:observation:sec\_12:results:1:sec\_12\_obs\_1, a:observation:sec\_13:results:1:sec\_13\_obs\_1, a:criterion:substance]
- Os resultados incluem análises mecanísticas úteis sobre propagação de crédito, recorrência e efeitos do otimizador, além de discutirem limitações e possíveis extensões experimentais\. [a:observation:sec\_12:results:1:sec\_12\_obs\_2, b:observation:sec\_13:results:1:obs4\_tennis\_explanations\_provided, b:observation:sec\_14:discussion:1:obs\_2, b:observation:sec\_14:discussion:1:obs\_3]
- A arquitetura da rede, o uso de subtrajetórias para BPTT, o tamanho do lote e vários hiperparâmetros dos otimizadores e da rede\-alvo são especificados, oferecendo uma base parcial para reprodução dos experimentos\. [a:observation:sec\_10:method:1:sec\_10\_obs\_1, a:observation:sec\_10:method:1:sec\_10\_obs\_2, a:observation:sec\_10:method:1:sec\_10\_obs\_6, a:criterion:replicability]

## Pontos fracos

- A contribuição original não é delimitada com precisão frente ao estado da arte: não fica claro qual formulação de eligibility traces, combinação experimental ou avanço específico distingue o trabalho de estudos anteriores\. [c:observation:sec\_2:introduction:1:obs\_3, c:observation:sec\_3:related\_work:1:obs\_4, c:criterion:originality]
- A força das conclusões é reduzida pela ausência de variabilidade, número de sementes e testes estatísticos para as alegações de velocidade e estabilidade, bem como por uma inconsistência entre a alegação geral de benefício dos traces e resultados em que o modelo sem traces apresenta desempenho superior\. [a:observation:sec\_12:results:1:sec\_12\_obs\_4, a:observation:sec\_13:results:1:sec\_13\_obs\_3, a:check:figure\_vs\_text:figure\_vs\_text\_sec\_12\_sec\_13, b:check:claims\_vs\_results:claims\_vs\_results\_1]
- A cobertura experimental permanece limitada a dois jogos e as comparações não isolam completamente os efeitos da recorrência, dos traces, do otimizador e da taxa de aprendizado; além disso, a alegação de superioridade sobre todas as variantes de DQN não é acompanhada por detalhes quantitativos de cada baseline\. [a:observation:sec\_11:results:1:sec\_11\_obs\_5, a:observation:sec\_13:results:1:sec\_13\_obs\_5, a:observation:sec\_13:results:1:sec\_13\_obs\_4, b:observation:sec\_13:results:1:obs5\_tennis\_dqn\_variants\_claim]
- A descrição metodológica não permite reproduzir integralmente o algoritmo: faltam definições matemáticas e pseudocódigo para os retornos e traces, regras completas de Watkins&\#x27;s Q\(X\), parâmetros essenciais da aplicação dos traces e uma notação consistente\. [a:observation:sec\_4:method:1:sec\_4\_obs\_3, a:observation:sec\_4:method:1:sec\_4\_obs\_5, a:observation:sec\_5:method:1:sec\_5\_obs\_3, a:observation:sec\_9:method:1:sec\_9\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_4]

## Sugestões

- Reformular a introdução e o related work para declarar explicitamente a contribuição, a variante de eligibility traces utilizada, as configurações avaliadas e as diferenças concretas em relação aos trabalhos anteriores\. [c:observation:sec\_2:introduction:1:obs\_3, c:observation:sec\_3:related\_work:1:obs\_4, c:criterion:originality]
- Reforçar os resultados com múltiplas sementes, médias e medidas de dispersão, intervalos de incerteza ou testes estatísticos; apresentar curvas e valores das tabelas de forma completa e reconciliar as afirmações sobre os benefícios dos traces entre Pong e Tennis\. [a:observation:sec\_12:results:1:sec\_12\_obs\_4, a:observation:sec\_12:results:1:sec\_12\_obs\_5, a:observation:sec\_13:results:1:sec\_13\_obs\_3, a:check:figure\_vs\_text:figure\_vs\_text\_sec\_12\_sec\_13, b:check:claims\_vs\_results:claims\_vs\_results\_1]
- Adicionar ablações fatoriais e baselines explicitamente documentadas para separar recorrência, traces, otimizador e taxa de aprendizado, e restringir ou sustentar quantitativamente a alegação de que o método é o único entre as variantes de DQN a alcançar desempenho quase ótimo em Tennis\. [a:observation:sec\_13:results:1:sec\_13\_obs\_4, a:observation:sec\_13:results:1:sec\_13\_obs\_5, b:observation:sec\_13:results:1:obs3\_tennis\_ablation\_studies, b:observation:sec\_13:results:1:obs5\_tennis\_dqn\_variants\_claim]
- Fornecer as equações completas dos retornos e das atualizações, pseudocódigo da regra de Watkins&\#x27;s Q\(X\), valores e convenções de λ, tratamento de terminais, protocolo de avaliação, política de exploração, sementes e detalhes do ambiente; também corrigir a notação inconsistente entre X, x e λ\. [a:observation:sec\_4:method:1:sec\_4\_obs\_3, a:observation:sec\_4:method:1:sec\_4\_obs\_7, a:observation:sec\_5:method:1:sec\_5\_obs\_4, a:observation:sec\_9:method:1:sec\_9\_obs\_5, a:observation:sec\_10:method:1:sec\_10\_obs\_3, a:observation:sec\_10:method:1:sec\_10\_obs\_4, a:criterion:replicability]

## Seções

### 1 INTRODUCTION

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1 [unresolved]: A introdução explicita o problema investigado — aprendizagem em ambientes com recompensas esparsas e observabilidade parcial — e relaciona esse problema a duas abordagens concretas: redes recorrentes e traços de elegibilidade\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_2: As contribuições principais são declaradas de forma relativamente direta: avaliar traços de elegibilidade em Deep RL no domínio Atari e examinar o efeito do método de otimização em redes recorrentes\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_3: A originalidade é apenas parcialmente sustentada: a introdução afirma que o uso de traços de elegibilidade com Deep RL foi limitado, mas não especifica claramente qual lacuna em relação aos trabalhos citados é preenchida nem como a combinação proposta difere do estado da arte\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_4: O impacto alegado é plausível, mas permanece amplo e pouco delimitado na introdução: “boost the performance” não informa em quais métricas, em que magnitude ou sob quais condições o benefício ocorre\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_5: A alegação sobre o efeito da otimização é vaga e não identifica os métodos comparados nem antecipa o resultado observado, dificultando avaliar sua relevância e novidade a partir da introdução\.
- a:observation:sec\_2:introduction:1:sec\_2\_obs\_6: A organização do artigo é apresentada de maneira clara, com indicação do conteúdo e da função de cada seção subsequente\.
- b:observation:sec\_2:introduction:1:obs1: The introduction clearly articulates the research problem by identifying a specific challenge within Deep Reinforcement Learning \(DRL\) and a gap in the application of known techniques\.
- b:observation:sec\_2:introduction:1:obs2: The article explicitly states its main contributions, highlighting experimental findings regarding eligibility traces and the impact of optimization methods, which addresses an identified limitation in the field\.
- b:observation:sec\_2:introduction:1:obs3: The potential impact of the research is implied through the stated contributions, as boosting performance in Deep RL and understanding optimization effects can be highly relevant for improving learning agents in complex environments\.
- c:observation:sec\_2:introduction:1:obs\_1 [unresolved]: A seção explicita o problema\-alvo \(recompensas esparsas e observabilidade parcial\) e motiva o uso de duas abordagens complementares \(recorrência e eligibility traces\)\.
- c:observation:sec\_2:introduction:1:obs\_2: Há afirmações de impacto/resultado sustentadas por evidência metodológica prometida \(experimentos no domínio Atari\) e por achados qualitativos específicos \(eligibility traces melhoram performance; efeito forte do otimizador em redes recorrentes\)\.
- c:observation:sec\_2:introduction:1:obs\_3: A contribuição/novidade não é delimitada de modo suficientemente específico em relação ao estado da arte: embora o texto aponte uma lacuna \(“limited so far”\) e anuncie resultados, ele não explicita o que exatamente é novo \(por exemplo, qual formulação/variante de eligibility traces é aplicada em deep RL, em que configurações ou combinações, e o que há de diferente na abordagem dos experimentos\)\.
- c:observation:sec\_2:introduction:1:obs\_4: A introdução menciona “surprisingly strong effect” do otimizador, mas não relaciona explicitamente esse efeito ao critério de importância \(ex\.: métricas, magnitude, ou comparação quantitativa\) dentro do texto fornecido, deixando a força da evidência dependente de seções futuras\.
- c:observation:sec\_2:introduction:1:obs\_5: A estrutura do artigo é apresentada de forma organizada, facilitando a clareza do que o leitor encontrará em cada seção\.

### 2 BACKGROUND

- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_1: A seção organiza de forma progressiva os conceitos básicos de MDP, MC, TD e Q\-learning, oferecendo ao leitor uma base conceitual para entender atualizações por diferença temporal\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_2: A seção não apresenta uma comparação significativa entre trabalhos ou alternativas relevantes\. Sutton &amp; Barto \(1998\) é citado como referência geral, mas não são discutidas diferenças, condições de aplicação ou limitações de métodos próximos, como MC, TD, Q\-learning e as variantes que motivam o artigo\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_3: A diferença entre o conhecimento estabelecido e a proposta do artigo não é explicitada nesta seção\. O texto define Q\-learning e aprendizado off\-policy, mas não indica quais limitações desses métodos a combinação com eligibility traces e redes recorrentes pretende resolver nem por que essa combinação se distingue de trabalhos anteriores\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_4 [unresolved]: Há problemas localizáveis de clareza e notação que dificultam a leitura: a expressão do retorno aparece corrompida, a definição da política usa uma assinatura inadequada ou ambígua, e há erros tipográficos e parênteses não fechados\.
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_5: A distinção entre MC e TD é apresentada principalmente por meio de fórmulas, mas a notação não explica claramente o índice temporal do retorno nem conecta essas equações às escolhas metodológicas do artigo\. Isso reduz a utilidade da seção como ponte entre a revisão conceitual e a contribuição proposta\.
- b:observation:sec\_3:related\_work:1:obs\_1 [unresolved]: A seção &\#x27;BACKGROUND&\#x27; fornece definições básicas de Reinforcement Learning, mas não identifica nem compara os trabalhos relacionados mais próximos que abordam especificamente a combinação de redes recorrentes e traces de elegibilidade em Deep Q\-Networks, que é a proposta central do artigo conforme indicado no resumo\.
- b:observation:sec\_3:related\_work:1:obs\_2 [unresolved]: Nesta seção fundamental, a proposta específica do artigo e como ela se diferencia do conhecimento estabelecido de MDPs, RL, MC, TD e Q\-learning não são explicitadas, prejudicando a compreensão da originalidade do trabalho e a clareza sobre a contribuição específica do autor\.
- c:observation:sec\_3:related\_work:1:obs\_1: A seção fornece definições de MDP e RL, mas não compara métodos alternativos ou discute limitações/condições equivalentes entre abordagens \(ex\.: MC vs TD, on\-policy vs off\-policy\) no sentido de “trabalhos relevantes” do estado da arte\.
- c:observation:sec\_3:related\_work:1:obs\_2: Há inconsistência/erro de redação nas fórmulas e notação: aparece “E\[to vtrt\]”, “V&quot; \(s\)” e índices/detalhes não usuais para a definição do retorno; isso prejudica a clareza científica do que exatamente está sendo definido\.
- c:observation:sec\_3:related\_work:1:obs\_3: Na seção apresentada \(“2 BACKGROUND”\), apesar de serem definidos e contrastados MC/TD e mencionadas formas de atualização \(incluindo Q\-learning\), não há uma ponte explícita que conecte esses conceitos ao tema central do artigo \(eligibility traces em DRQN\) nem que explique como as eligibility traces funcionam como alternativa/ponte entre estimativas tipo MC e atualizações tipo TD para o problema investigado\.
- c:observation:sec\_3:related\_work:1:obs\_4: Não há alegações de novidade/contribuição \(logo não é possível avaliar originalidade com evidência\)\. O texto apenas apresenta conceitos gerais e fórmulas, citando “Sutton &amp; Barto, 1998”, sem diferenciar do conhecimento estabelecido no estado da arte\.

### 2\.1 ELIGIBILITY TRACES

- a:observation:sec\_4:method:1:sec\_4\_obs\_1: A seção explica de forma intuitiva a função das eligibility traces como um compromisso entre TD e MC e relaciona esse mecanismo ao problema de atribuição de crédito em recompensas esparsas ou atrasadas\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_2: A distinção entre forward view e backward view é apresentada de maneira conceitualmente útil, incluindo a motivação computacional para preferir a segunda em atualizações online\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: Faltam as definições matemáticas dos retornos n\-step, do retorno λ e da atualização por eligibility trace\. Sem essas equações, não é possível verificar precisamente a ponderação dos retornos, o tratamento de estados terminais ou a correspondência formal entre as visões forward e backward\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_4: A formulação de que tomar n→∞ produz o alvo MC é apresentada sem as condições necessárias, como a natureza episódica da tarefa, o tratamento de terminação e a relação com o fator de desconto\. A afirmação pode não ser válida literalmente em tarefas contínuas ou quando o limite não é especificado\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: A descrição da ponderação geométrica não informa a normalização dos pesos nem esclarece se λ se refere ao parâmetro da mistura dos retornos, ao fator de decaimento da trace, ou a uma convenção específica com γ\. Isso deixa a implementação subespecificada\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_6: A afirmação de que a visão backward “requires no memory” é imprecisa: embora não exija armazenar toda a experiência futura ou esperar pelo desdobramento da trajetória, o algoritmo precisa manter e atualizar um vetor de traces para estados, ações ou parâmetros\. A própria seção reconhece posteriormente que há uma trace em cada neurônio\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_7: A seção apresenta conceitualmente as visões forward e backward e a ponderação geométrica por λ, mas não especifica uma variante implementável de eligibility trace nem as convenções e parâmetros necessários para reproduzi\-la, como o valor de λ, a regra exata de atualização e o tipo de traço utilizado\. Assim, a descrição não é suficiente para reproduzir uma implementação concreta a partir desta seção isoladamente\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_8: A alegação de que a visão backward “requires no memory” e a caracterização de que as traces são “dense and heavily used at each step” misturam custo de armazenamento de experiência com custo de manutenção e computação do vetor de traces\. A limitação computacional deveria ser quantificada e distinguida desses dois aspectos\.
- b:observation:sec\_4:method:1:sec\_4\_obs\_1: The section describes the concepts of n\-step returns and geometric weighting for eligibility traces verbally, but lacks the explicit mathematical formulas that would be required for a direct and unambiguous implementation, hindering full replicability\.
- b:observation:sec\_4:method:1:sec\_4\_obs\_2: Esta seção oferece um background teórico focado e claro sobre traces de elegibilidade, limitando adequadamente seu escopo a conceitos fundamentais e suas mecânicas\. Ela corretamente se abstém de incluir parâmetros experimentais específicos ou detalhes completos da configuração do estudo, que são apropriadamente reservados para seções metodológicas posteriores e dedicadas à implementação prática\.
- b:observation:sec\_4:method:1:sec\_4\_obs\_3 [unresolved]: The section provides a clear and sound explanation of the fundamental concepts of eligibility traces, including their role in the TD\-MC bias\-variance trade\-off, the mechanisms of n\-step returns and geometric weighting, and the distinctions between forward and backward views, along with their respective advantages and disadvantages\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_1: O texto apresenta a motivação e a intuição do mecanismo \(trade\-off entre TD e MC\) e o problema de variância/viés de cada família, preparando o leitor para o porquê de usar eligibility traces\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_2: Há uma inconsistência/ambiguidade notacional no parágrafo sobre retornos: quando n=1, o texto afirma que é o alvo de TD, e diz que tomando n→∞ yields o alvo de MC, mas não explicita como isso se relaciona com a formulação usual \(com γ e bootstrap\) nem define explicitamente o que é o &\#x27;resultado&\#x27; do enunciado/expressão ausente\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_3 [unresolved]: O texto afirma usar uma ponderação geométrica com λ, e em seguida menciona &\#x27;Using a λ = 0 reduces to using TD&\#x27;, mas existe uma inconsistência com a notação que aparece no corpo do trabalho: mais adiante \(em mapa/figuras\) aparecem &\#x27;X = 0&\#x27; e &\#x27;x = 0\.8&\#x27;, sugerindo possível divergência entre λ e outra variável \(X/x\)\.
- c:observation:sec\_4:method:1:obs\_sec\_4\_4: Apesar de explicar forward vs backward view em nível conceitual, a seção não fornece detalhes operacionais suficientes para reprodução \(p\.ex\., regra exata de atualização com traces, como z\(s,a\) evolui, e como o n\-step return é calculado na prática\), limitando a reprodutibilidade do método descrito\.

### 2\.1\.1 Q\(x\)

- a:observation:sec\_5:method:1:sec\_5\_obs\_1: O trecho apresenta corretamente a motivação conceitual para interromper o traço em um método off\-policy: ações da trajetória histórica podem não coincidir com as ações da política atual, tornando inadequado propagar o traço além desse ponto\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_2: A notação é inconsistente e não define claramente o objeto descrito: o título usa “Q\(x\)”, enquanto o texto alterna entre “Q\(x\)” e “Q\(X\)”\. Também não são definidos formalmente o traço, a política atual ou o critério de seleção de ação\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_3: Falta a formulação matemática ou um pseudocódigo da regra de Watkins&\#x27;s Q\(X\), incluindo em que instante o traço é zerado, como ele é atualizado depois disso e como essa regra entra no alvo ou na atualização dos valores Q\. Sem esses elementos, a implementação não é reproduzível a partir do trecho\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_4: A condição “the action that the current policy would select” é ambígua para políticas exploratórias, como ε\-greedy: não se especifica se a comparação usa a ação greedy, uma amostra da política, os valores Q antes ou depois da atualização, nem como são tratados empates\. Esses parâmetros podem alterar o comportamento do algoritmo\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_5: O trecho não informa a fonte original ou uma referência bibliográfica para Watkins&\#x27;s Q\(X\), nem delimita qual das versões de Q\(x\) está sendo adotada\. Isso dificulta verificar a definição empregada e reproduzir o método com precisão\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_1: The text describes a crucial characteristic of Watkins&\#x27;s Q\(X\) regarding how it handles off\-policy actions by resetting the eligibility trace, but it omits the explicit mathematical formulation for the Q\-value update rule, the eligibility trace accumulation mechanism, and the precise definition of how the &\#x27;current policy would select&\#x27; an action\. This lack of detailed algorithmic steps or equations makes it difficult to reproduce the method without consulting external sources\.
- b:observation:sec\_5:method:1:sec\_5\_obs\_2: The term &\#x27;the trace&\#x27; is used without an explicit definition or reference to its calculation within this specific subsection\. While the general concept of eligibility traces is mentioned in the broader section title, for complete clarity and self\-containment of the Q\(x\) method, the specific formulation of the trace for Watkins&\#x27;s Q\(X\) would be beneficial\.
- c:observation:sec\_5:method:1:obs\_1 [unresolved]: O texto apresenta uma justificativa causal/operacional para quando a trace deve ser interrompida no Watkins’s Q\(X\) devido a discrepância entre ações do trajectory passado e ações da política atual \(off\-policy\)\.
- c:observation:sec\_5:method:1:obs\_2 [unresolved]: A formulação diz como o Watkins’s Q\(X\) trata a divergência \(zera a trace\), mas não especifica formalmente \(ex\.: condição/critério exato em termos de igualdade de ações e ponto temporal\) nem define explicitamente quais variáveis \(por exemplo, “X” e “x”\) correspondem ao parâmetro do método, o que reduz a verificabilidade detalhada\.
- c:observation:sec\_5:method:1:obs\_3 [unresolved]: Não há detalhes sobre como essa regra de truncamento \(quando zera a trace\) é implementada na prática no restante do pipeline \(por exemplo, como isso afeta o cálculo/propagação da trace em atualizações subsequentes, ou como interage com replay, janelas n\-step ou a recorrência\), apesar de o documento tratar de LSTMs/RNN e experiência replay em seções/fotos posteriores\.
- c:observation:sec\_5:method:1:obs\_4 [unresolved]: Há potencial ambiguidade de nomenclatura entre “Q\(X\)” e “Q\(x\)” \(o texto diz “A few versions of Q\(x\) exist” e depois usa “Watkins&\#x27;s Q\(X\)”\), sem esclarecer se é apenas tipografia/estilo ou se o artigo pretende distinguir parâmetros/variantes\.

### 2\.2 DEEP Q\-NETWORKS

- a:observation:sec\_6:related\_work:1:sec\_6\_obs\_1: A seção estabelece o DQN como um baseline relevante e descreve de forma sucinta sua entrada visual e sua saída de valores Q\.
- a:observation:sec\_6:related\_work:1:sec\_6\_obs\_2: A seção não compara o DQN com as alternativas mais próximas da proposta, nem explica claramente como a investigação de recorrência e eligibility traces se diferencia do baseline apresentado\. Assim, a contribuição nova em relação ao DQN não fica estabelecida neste trecho\.
- a:observation:sec\_6:related\_work:1:sec\_6\_obs\_3: A notação da função de custo está ambígua e contém símbolos inconsistentes ou aparentemente corrompidos, o que dificulta identificar os parâmetros treinados, os pesos congelados e o papel do fator de desconto\.
- b:observation:sec\_6:related\_work:1:obs\_1: A descrição da função de custo da DQN e seus parâmetros utiliza símbolos pouco claros ou incorretos, o que prejudica a compreensão da formulação matemática crucial para o trabalho\.
- b:observation:sec\_6:related\_work:1:obs\_2: O trabalho fundamental de Mnih et al\. \(2015\) sobre Deep Q\-Networks \(DQN\) é introduzido, estabelecendo uma base para a discussão de trabalhos relacionados\.
- c:observation:sec\_6:related\_work:1:obs\_1: O texto situa corretamente o DQN como um dos primeiros RL bem\-sucedidos com deep learning para aproximação de função e descreve a arquitetura usada no Atari\.
- c:observation:sec\_6:related\_work:1:obs\_2: A comparação com alternativas relevantes do estado da arte fica implícita \(é essencialmente uma contextualização do DQN\), mas não discute condições/lacunas em relação a métodos que o artigo usa depois \(ex\.: recurrent/DRQN, ou seleção de otimizadores\), nem limitações/por que o DQN precisa de variações\.
- c:observation:sec\_6:related\_work:1:obs\_3: Há problemas de clareza na notação: “@ parameters” e “0\-parameters/0¯” não ficam definidos no trecho, e a equação aparece com símbolos/variáveis potencialmente corrompidos \(ex\.: “L\(st, at\|0\)”, “a&\#x27;”, “0¯”\)\. Isso dificulta verificar o significado do que está sendo otimizado e como a referência de “parâmetros congelados” se relaciona com os termos da loss\.

### 2\.2\.1 DEEP RECURRENT Q\-NETWORKS

- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_1 [unresolved]: A seção apresenta de forma clara a arquitetura DRQN e explica por que a recorrência é relevante em ambientes parcialmente observáveis\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_2 [unresolved]: A discussão distingue duas alternativas de experience replay propostas para DRQN e explicita as limitações computacionais e temporais associadas a cada uma\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_3 [unresolved]: A seção não compara explicitamente DRQN com a proposta do artigo, baseada na combinação de recorrência e eligibility traces; portanto, a diferença em relação ao trabalho mais próximo não fica clara\.
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_4: Falta discutir como eligibility traces se relacionam com as duas estratégias de replay descritas, incluindo quais limitações de DRQN elas pretendem resolver e em que condições os métodos são comparáveis\.
- b:observation:sec\_7:related\_work:1:obs1\_sec7\_clarity: The description of Deep Recurrent Q\-Networks \(DRQN\) is clear and well\-structured, providing a good understanding of its architecture, purpose, and training variants\.
- b:observation:sec\_7:related\_work:1:obs2\_sec7\_meaningful\_comparison: The section clearly outlines how DRQN differs from DQN, specifically highlighting DRQN&\#x27;s ability to handle partial observability more effectively, which provides a meaningful comparison of this relevant related work\.
- c:observation:sec\_7:related\_work:1:obs\_1 [unresolved]: A seção descreve de forma coerente a motivação e a arquitetura do DRQN, incluindo a contribuição de memória para lidar com dependência temporal e observabilidade parcial\.
- c:observation:sec\_7:related\_work:1:obs\_2 [unresolved]: A comparação com alternativas relevantes \(por exemplo, DQN e/ou outras formas de lidar com observabilidade parcial\) aparece, mas não fica explicitada a conexão com o problema específico do artigo \(eligibility traces\) além de mencionar memorizaçao/recorrência\.
- c:observation:sec\_7:related\_work:1:obs\_3 [unresolved]: A seção descreve variantes de experience replay \(trajetórias completas vs sub\-trajetórias\), mas não explicita limitações/condições de uso em paralelo que ajudem a justificar por que isso é pertinente para o desenho do artigo \(comparação equivalente exigida pela rubrica\)\.

### 2\.3 OPTIMIZERS

- a:observation:sec\_8:related\_work:1:sec\_8\_obs\_1: A seção inclui os principais otimizadores usados no estudo e explicita que a variante de RMSprop introduzida no DQN será a convenção adotada no restante do artigo\.
- a:observation:sec\_8:related\_work:1:sec\_8\_obs\_2: A comparação entre os otimizadores é predominantemente descritiva: a seção apresenta as fórmulas de SGD, RMSprop e Adam em sequência, mas não contrasta explicitamente suas vantagens, limitações, condições de uso ou relação com o problema de treinar redes recorrentes com eligibility traces\.
- a:observation:sec\_8:related\_work:1:sec\_8\_obs\_3: A seção não deixa clara a diferença entre o conhecimento estabelecido sobre os otimizadores e a contribuição específica do artigo; em particular, não explica por que comparar RMSprop e Adam é relevante para a investigação proposta nem qual hipótese essa escolha testa\.
- a:observation:sec\_8:related\_work:1:sec\_8\_obs\_4: As equações e a notação estão severamente corrompidas ou incompletas, o que impede verificar com segurança as definições e distinguir precisamente as variantes de RMSprop e Adam apresentadas\.
- a:observation:sec\_8:related\_work:1:sec\_8\_obs\_5: A terminologia e a progressão da explicação ficam pouco claras porque a seção alterna entre descrição textual, notação não definida e fórmulas truncadas; por exemplo, não são apresentados de forma legível os parâmetros, índices temporais e regras completas de atualização\.
- b:observation:sec\_8:related\_work:1:opt\_clarity\_strength [unresolved]: The section provides clear and concise descriptions of key adaptive optimizers \(RMSprop, a DQN variant, and Adam\), including their mathematical formulations and how they build upon each other, enhancing understanding of their mechanisms\.
- b:observation:sec\_8:related\_work:1:opt\_proposal\_link\_missing: While relevant optimizers are presented, this section, acting as background, does not explicitly clarify how the paper&\#x27;s specific proposal \(investigating recurrence and eligibility traces in DRL\) relates to or differentiates itself in the context of these optimizers, beyond a general introduction to adaptive SGD\.
- c:observation:sec\_8:related\_work:1:obs\_8\_1 [unresolved]: A seção contextualiza otimizadores adaptativos \(RMSprop e Adam\) como alternativas ao SGD, mencionando trabalhos relevantes e conectando\-os ao que será usado na pesquisa \(&quot;when mentioning RMSprop, we&\#x27;ll be referring to this version&quot;\)\.
- c:observation:sec\_8:related\_work:1:obs\_8\_2 [unresolved]: A comparação entre RMSprop e Adam é mais descritiva do que contrastiva: descreve fórmulas/termos, mas não deixa claro de forma comparável quais condições/razões práticas levam a diferenças relevantes para o contexto do artigo \(p\.ex\., relação com o restante da arquitetura/eligibility traces\)\.
- c:observation:sec\_8:related\_work:1:obs\_8\_3 [unresolved]: Há inconsistências/erros de notação e texto incompleto nas equações \(ex\.: uso de símbolos truncados/sem correspondência\), o que prejudica a clareza e dificulta entender exatamente o que está sendo definido para RMSprop e Adam\.
- c:observation:sec\_8:related\_work:1:obs\_8\_4 [unresolved]: Não aparece comparação com outras alternativas de otimização relevantes para DQN/treino em Atari \(além de RMSprop e Adam\), o que limita a avaliação de &quot;comparação com trabalhos relevantes&quot; na rubrica\.
- c:observation:sec\_8:related\_work:1:obs\_8\_5 [unresolved]: A seção não evidencia nenhuma alegação de novidade/contribuição própria \(originalidade\) — apenas descreve otimizadores existentes — então não há como avaliar originalidade a partir do texto fornecido\.

### 3 EXPERIMENTAL SETUP

- a:observation:sec\_9:method:1:sec\_9\_obs\_1 [unresolved]: A seção oferece uma justificativa metodológica coerente para combinar a visão forward das eligibility traces com DRQN: o replay reduz a necessidade de armazenar traços, e o processamento de subtrajetórias permite reutilizar as saídas da RNN para calcular os alvos ponderados\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_2: A restrição aos jogos totalmente observáveis é explicitamente declarada e busca controlar a comparação entre arquiteturas, evitando que a memória recorrente introduza uma vantagem adicional associada à observabilidade parcial\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A seção não especifica parâmetros essenciais da aplicação das eligibility traces, como o valor ou os valores de λ, a fórmula exata dos alvos ponderados, o horizonte das subtrajetórias e como é feito o tratamento de estados terminais\. Sem esses detalhes, a implementação do método não é reproduzível\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_4: Embora RMSprop e Adam sejam mencionados, faltam as configurações dos otimizadores e do treinamento, incluindo taxas de aprendizagem, parâmetros de momento ou β, tamanho de lote, frequência de atualização, número de passos/épocas, inicialização e número de sementes\. Esses parâmetros podem afetar diretamente a comparação experimental\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_5: O desenho experimental é descrito apenas em termos gerais: a seção não informa quais jogos foram usados, o protocolo de amostragem do replay, o comprimento das sequências, o burn\-in para o estado oculto, a política de exploração nem o procedimento de avaliação\. A ausência desses elementos impede reproduzir precisamente o experimento a partir desta seção\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_6: A justificativa de que ambientes parcialmente observáveis dariam uma “unfair advantage” à memória é conceitualmente ambígua: em tais ambientes, a memória pode ser precisamente o mecanismo necessário para inferir informação histórica relevante, e não apenas uma vantagem espúria\. A seção deveria explicitar se o objetivo é medir desempenho em observabilidade total, isolar o efeito da recorrência ou evitar confusão entre memória e elegibilidade\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_1: The section mentions the use of RMSprop and Adam optimizers but fails to specify their specific hyperparameters \(e\.g\., learning rates, decay rates, epsilon values\), which are essential for reproducing the experimental setup precisely\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_2: Although the text describes how eligibility traces are computationally managed with DRQN, it does not explicitly state the specific variant of eligibility traces used \(e\.g\., Q\(λ\)\) nor the value of the trace decay parameter \(λ\), making the exact implementation unclear for replication\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_3: The method relies on training with &\#x27;sub\-trajectories of data&\#x27; but does not specify the length of these sub\-trajectories, how they are generated, or any associated parameters, which are crucial details for replicating the training process\.
- b:observation:sec\_9:method:1:sec\_9\_obs\_4: The &\#x27;Experimental Setup&\#x27; section mentions testing algorithms on &\#x27;fully observable games&\#x27; but does not explicitly name the specific Atari games chosen for the experiments, which would enhance clarity and completeness for the setup description\.
- c:observation:sec\_9:method:1:obs\_9\_1 [unresolved]: A redução de custo computacional descrita para “forward view of eligibility traces” depende de um procedimento \(“training on sub\-trajectories…”\) cuja correspondência exata com a implementação/algoritmo de DRQN não é especificada aqui, criando lacuna de inferência sobre o que é efetivamente economizado\.
- c:observation:sec\_9:method:1:obs\_9\_2 [unresolved]: Faltam parâmetros procedimentais para reproduzir o desenho descrito \(p\.ex\., tamanho das sub\-trajetórias, como “all state values as the output” é operacionalizado, como os alvos ponderados por traces são calculados\) e, portanto, a reprodutibilidade fica limitada neste trecho\.
- c:observation:sec\_9:method:1:obs\_9\_3 [unresolved]: A seção explicita claramente o escopo experimental \(DRQN com traces\) e as escolhas do otimizador \(RMSprop e Adam\), que são elementos centrais para comparar desempenho\.
- c:observation:sec\_9:method:1:obs\_9\_4 [unresolved]: A motivação por usar apenas jogos totalmente observáveis para evitar “unfair advantage” em ambientes parcialmente observáveis é razoável, mas não discute como isso afeta a validade externa das conclusões sobre traços de elegibilidade em geral\.

### 3\.1 ARCHITECTURE

- a:observation:sec\_10:method:1:sec\_10\_obs\_1: A arquitetura da rede é descrita com especificidade suficiente para identificar os principais componentes e dimensões, incluindo as camadas convolucionais, a camada densa, a LSTM e a camada de saída dos valores Q\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_2: O procedimento de treinamento recorrente especifica o comprimento das subtrajetórias, o número de estados usados para preencher o estado oculto e o tamanho do lote, tornando explícita a adaptação do experience replay para BPTT\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: A descrição do algoritmo contém notação corrompida ou ambígua, especialmente nos índices do retorno forward\-view e na expressão do custo, o que dificulta reconstruir exatamente o alvo usado no gradiente\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: A notação do parâmetro de elegibilidade é inconsistente: o texto usa X = 0\.8, depois x = 0\.8, e o algoritmo usa λ sem deixar explícita a correspondência entre esses símbolos\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_5: Para reprodução completa, a seção não informa explicitamente vários detalhes do ambiente e do pipeline de entrada, como normalização dos pixels, empilhamento ou tratamento temporal dos frames, conjunto exato de ações e configuração do ambiente Atari; esses detalhes podem estar descritos em outras seções, mas não aparecem aqui\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: Os hiperparâmetros dos dois otimizadores e o procedimento de atualização da rede\-alvo são fornecidos, incluindo taxas de aprendizado, momentum, epsilon e frequência de atualização\.
- b:observation:sec\_10:method:1:arch\_strength\_1: A arquitetura da rede neural, incluindo a sequência de camadas CNN, a camada densa e a LSTM, junto com os tamanhos de filtro, strides e ativações, é bem detalhada\.
- b:observation:sec\_10:method:1:arch\_strength\_2 [unresolved]: Os parâmetros específicos para o Experience Replay modificado, incluindo o comprimento da sub\-trajetória, o número de estados para preenchimento do estado oculto da RNN e o tamanho do batch, são claramente definidos\.
- b:observation:sec\_10:method:1:arch\_strength\_3: Os parâmetros das eligibility traces, como o valor de lambda \(X\), o tipo de Q\(X\) utilizado \(Watkins&\#x27;s Q\(X\)\) e o limite de corte da trace, são especificados, juntamente com a justificativa para o limite\.
- b:observation:sec\_10:method:1:arch\_strength\_4: Os hiperparâmetros para os otimizadores RMSprop e Adam, incluindo momentum, epsilon e taxa de aprendizado, são explicitamente fornecidos\.
- b:observation:sec\_10:method:1:arch\_strength\_5: O protocolo da fase de testes, incluindo a métrica de pontuação \(média ao longo de 125000 frames\) e o valor de epsilon para seleção de ação durante o teste, é bem descrito\.
- b:observation:sec\_10:method:1:arch\_missing\_1: Não é especificado o tipo de padding \(por exemplo, &\#x27;same&\#x27; ou &\#x27;valid&\#x27;\) utilizado nas camadas convolucionais \(CNN\)\. Esta informação é crucial para reproduzir as dimensões exatas de saída das camadas e, consequentemente, a arquitetura da rede\.
- b:observation:sec\_10:method:1:arch\_missing\_2: O valor de epsilon \(ε\) para a política ε\-greedy utilizada durante a fase de treinamento \(para coleta de experiência\) não é fornecido\. Apenas o valor de epsilon para a fase de testes é mencionado\.
- b:observation:sec\_10:method:1:arch\_missing\_3: O fator de desconto \(gamma, γ\) não é explicitamente declarado como um parâmetro de experimento\. Embora mencionado na seção de antecedentes como parte de um MDP, seu valor específico para os experimentos não é fornecido\.
- b:observation:sec\_10:method:1:arch\_weakness\_1: A notação matemática para a função de retorno \`R\(n\)\` \(elegibilidade traces\) e a derivada na etapa de gradiente descendente no Algoritmo 1 são extremamente confusas e parecem incorretas \(\`R\(s−l\+1\)1 k t\+l\` e \`2θ\`\)\. Isso compromete a clareza, a reprodutibilidade e a solidez da descrição do método de otimização\.
- b:observation:sec\_10:method:1:arch\_weakness\_2: Há uma ligeira ambiguidade na descrição de como o estado oculto da RNN é gerenciado: o algoritmo indica &\#x27;Initialize RNN hidden state to 0&\#x27; no início de um episódio para a ação online, enquanto o texto descreve o preenchimento do estado oculto com &\#x27;m&\#x27; estados para o treinamento via BPTT\. Embora possa ser interpretado corretamente, a distinção poderia ser mais explícita no algoritmo\.
- c:observation:sec\_10:method:1:sec\_10\_obs\_1 [unresolved]: A arquitetura CNN\+LSTM \(camadas, tamanhos de filtros, strides, dimensões e tipo de ativação\) é especificada com detalhes suficientes para reprodução do modelo\.
- c:observation:sec\_10:method:1:sec\_10\_obs\_2: Os parâmetros de treinamento ligados ao uso de sub\-trajetórias para BPTT são definidos \(comprimento total, número de estados “filler”, batch size\), aumentando a reprodutibilidade do procedimento\.
- c:observation:sec\_10:method:1:sec\_10\_obs\_3: Há inconsistência/ambiguidade entre a nomenclatura de variáveis usadas na descrição \(“X”, “x”, “limit”\) e os símbolos no algoritmo \(k, m, além de uso de x como expoente/decadência\) dificultando a correspondência exata entre texto e pseudocódigo\.
- c:observation:sec\_10:method:1:sec\_10\_obs\_4: O artigo fornece hiperparâmetros do otimizador e do epsilon, mas não especifica explicitamente valores essenciais de treinamento para a reprodução completa \(ex\.: gamma, arquitetura/implementação do “last linear layer”, critérios completos de parada e configuração exata de atualização do target network além de “Every 10000 steps”\)\.
- c:observation:sec\_10:method:1:sec\_10\_obs\_5 [unresolved]: O procedimento de “eligibility traces” é descrito com cutoff e efeito aproximado \(“21 states ahead”\), mas o vínculo entre “limit”, “cut the trace off” e a fórmula/pseudocódigo \(onde aparece λt e o cálculo de R\(s−l\+1\)1\) fica pouco verificável apenas a partir deste trecho, podendo dificultar auditoria do cálculo exato\.

### 4 EXPERIMENTAL RESULTS

- a:observation:sec\_11:results:1:sec\_11\_obs\_1: A seção delimita claramente os experimentos a Pong e Tennis e oferece uma justificativa funcional para a escolha: Pong permite experimentação rápida, enquanto Tennis é apresentado como um jogo particularmente difícil nos resultados publicados\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_2: No trecho fornecido, são descritos os jogos Pong e Tennis e a justificativa para sua escolha, mas não são apresentadas curvas de desempenho nem métricas operacionais de sucesso que permitam comparar quantitativamente os resultados ou os otimizadores\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_3: No trecho fornecido da seção, não são reportados variância, intervalos de confiança, número de sementes ou repetição dos experimentos\. Assim, com base apenas no material disponível, não é possível avaliar a incerteza ou a robustez estatística dos resultados para Pong e Tennis; a observação não afirma que essas informações estejam ausentes do restante da seção\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_4 [unresolved]: No trecho fornecido para esta seção são apresentados detalhes sobre comparações com baselines ou sobre ablações dos componentes avaliados; o material apenas informa que os experimentos foram realizados nos jogos Pong e Tennis\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_5: A cobertura experimental é estreita: são avaliados apenas dois jogos, escolhidos por razões práticas e de dificuldade\. Isso é suficiente para um estudo exploratório, mas sustenta apenas conclusões limitadas sobre generalização para o domínio Atari como um todo\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_6: No trecho fornecido, a seção informa apenas que os experimentos foram realizados em Pong e Tennis e explica a escolha desses jogos; não há, nesse trecho, descrição de limiares de pontuação, de regras para agregar ou comparar escores e tempos de treinamento, nem de tratamento de resultados abaixo de eventual limiar\. Como esses detalhes podem estar em outras partes do artigo, a ausência é limitada ao material fornecido\.
- b:observation:sec\_11:results:1:obs\_1: A introdução da seção de resultados \(4 EXPERIMENTAL RESULTS\) descreve a escolha dos jogos, mas não apresenta imediatamente baselines, estatísticas iniciais, variância ou detalhes de ablação para contextualizar os experimentos, o que seria esperado para estabelecer a base dos resultados subsequentes\.
- b:observation:sec\_11:results:1:obs\_2: A justificativa para a escolha do jogo Tennis baseia\-se em uma afirmação generalizada de que ele &quot;has proven difficult in all published results on Atari&quot;, sem apresentar citações ou evidências específicas no texto para sustentar essa alegação\.
- c:observation:sec\_11:results:1:obs\_1: We describe experiments in two Atari games: Pong and Tennis\.
- c:observation:sec\_11:results:1:obs\_2: We chose Pong because it permits quick experimentation, and Tennis because it is one of the games that has proven difficult in all published results on Atari\.

### 4\.1 PONG

- a:observation:sec\_12:results:1:sec\_12\_obs\_1: A comparação cobre diretamente os principais fatores experimentais: presença ou ausência de traços e uso de RMSprop ou Adam, incluindo o baseline DQN\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_2: O texto relaciona o padrão observado em Pong a uma hipótese mecanística plausível: as elegibilidade dos traços propagam o crédito do retorno até o momento em que a bola foi atingida\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_3: A seção considera não apenas velocidade de aprendizagem, mas também estabilidade, distinguindo o comportamento do DQN daquele dos modelos recorrentes\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_4: As afirmações quantitativas sobre rapidez e estabilidade não são acompanhadas, no texto, por médias, variâncias, intervalos de confiança, número de sementes ou testes estatísticos\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_5: A comparação depende de referências à Figure 2 e à Table 1, mas o trecho não fornece os valores observados nem a magnitude da variabilidade; assim, a verificabilidade das conclusões fica limitada sem consultar esses elementos\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_6: O desenho permite comparar os fatores principais, mas não isola claramente todas as interações: em particular, a interpretação do efeito dos traços sob Adam é apresentada sem uma análise quantitativa explícita da interação entre traços e otimizador\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_7: A explicação causal sobre a limitação causada pela frequência de atualização da rede congelada é apenas uma intuição; não há, nesta seção, uma ablação ou experimento que varie essa frequência para sustentá\-la\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_8: A afirmação de que o modelo com traços não apresentou épocas de desempenho deprimido é forte, mas não define o critério de &\#x27;depressed performance&\#x27; nem mostra uma análise de episódios ou dispersão que permita verificar essa propriedade\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_9: A notação do parâmetro dos traços é inconsistente: o texto usa tanto &\#x27;X = 0&\#x27; quanto &\#x27;x = 0\.8&\#x27;, embora pareça referir\-se ao mesmo parâmetro\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_10: O termo &\#x27;significantly more&\#x27; é ambíguo, pois não esclarece se significa uma diferença estatisticamente significativa ou apenas uma diferença de magnitude observada\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_11: A conclusão de que o modelo ficou ótimo em seis épocas depende da definição operacional de &\#x27;optimal&\#x27; e da regra de medição; o trecho apenas informa o número de épocas e não explicita se esse marco foi atingido de forma consistente entre execuções\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_12: O trecho da seção compara a taxa de aprendizagem, a estabilidade e o tempo até atingir desempenho quase ótimo, mas não informa claramente o número de execuções, as sementes, os intervalos de treinamento ou o procedimento usado para resumir as curvas; isso dificulta reproduzir essas comparações\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_1: A interpretação oferece uma explicação mecanística plausível para o benefício das eligibility traces em Pong, relacionando o atraso entre a ação relevante e a recompensa à propagação temporal do crédito\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_2: A seção compara explicitamente RMSprop e Adam e distingue o comportamento das redes recorrentes daquele do DQN, o que torna a interpretação mais informativa do que uma comparação isolada entre modelos\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_3: A atribuição causal do ganho às eligibility traces é apresentada com confiança maior do que a sustentação descrita: a seção oferece apenas uma explicação intuitiva e não mostra uma análise que isole esse mecanismo de outros fatores do treinamento\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_4: A explicação para a vantagem relativa de Adam é explicitamente especulativa e não é acompanhada de experimentos de ablação ou de uma análise dos hiperparâmetros que permita verificar a hipótese sobre a frequência de atualização da rede congelada\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_5: Há uma inconsistência de notação no valor do parâmetro da trace: o texto usa “X = 0” e “x = 0\.8” na mesma frase, embora a comparação pareça referir\-se ao mesmo parâmetro Q\(λ\)\. Isso pode dificultar a correspondência com o método e as figuras\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_6: A afirmação de que o modelo com traces aprende “com mais estabilidade” e sem épocas de desempenho deprimido não informa como a estabilidade foi medida, quantas execuções foram realizadas nem a variabilidade entre sementes; portanto, o alcance estatístico dessa conclusão permanece incerto\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_7: A conclusão sobre velocidade de aprendizagem depende de limiares e unidades de comparação que não são definidos nesta passagem: “more than twice as quickly” e “6 epochs” não esclarecem se a métrica é média, melhor execução ou uma única curva, nem fornecem incerteza\.
- a:observation:sec\_12:discussion:1:sec\_12\_obs\_8: A seção extrapola de forma limitada a partir de Pong: os resultados descritos sustentam conclusões sobre esse jogo e essas configurações, mas não justificam, por si só, uma conclusão geral sobre RNNs, eligibility traces ou otimização em Atari\.
- b:observation:sec\_12:results:1:obs\_pong\_1: The experimental results clearly show the benefits of eligibility traces for learning speed and stability when using RMSprop, providing a solid ablation study\.
- b:observation:sec\_12:results:1:obs\_pong\_2: A sound theoretical explanation for the observed benefits of eligibility traces in the context of the Pong game&\#x27;s credit assignment problem is provided\.
- b:observation:sec\_12:results:1:obs\_pong\_3: While qualitative statements about &\#x27;more stability&\#x27; and &\#x27;quite unstable&\#x27; are made, the text lacks quantitative statistical analysis \(e\.g\., standard deviation across multiple runs\) to substantiate claims about variance and stability\.
- b:observation:sec\_12:results:1:obs\_pong\_4: The intuition offered to explain the interaction between traces and the Adam optimizer \(hyper\-parameters limiting the learning rate\) is speculative and not immediately substantiated with further evidence or experiments within the provided text\.
- b:observation:sec\_12:results:1:obs\_pong\_5: The results provide clear quantitative metrics \(epochs to reach near\-optimal performance\) for comparing different configurations, which significantly strengthens the claims of performance improvement\.
- b:observation:sec\_12:discussion:1:pong\_obs\_1: The article provides a clear and plausible interpretation for why eligibility traces are beneficial in Pong, specifically by addressing the credit assignment problem in delayed reward scenarios\.
- b:observation:sec\_12:discussion:1:pong\_obs\_2: The authors acknowledge potential limitations related to hyper\-parameters, such as the frozen network&\#x27;s update frequency, which might be impacting the learning rate, particularly when observing differential gains between models with and without traces using the Adam optimizer\.
- b:observation:sec\_12:discussion:1:pong\_obs\_3: While acknowledging potential hyper\-parameter limitations, the explanation for why the no\-trace model gains significantly more with Adam is presented as &\#x27;intuition&\#x27; and lacks empirical verification within the provided text, leaving an open question about the observed interaction\.
- b:observation:sec\_12:discussion:1:pong\_obs\_4: The section clearly summarizes the main performance improvements, indicating that both eligibility traces and the Adam optimizer contribute positively to learning efficiency and stability, with quantitative references to Table 1\.
- c:observation:sec\_12:results:1:obs\_1: Há uma comparação experimental direta entre modelos com e sem traces \(X = 0 e x = 0\.8\) sob RMSprop, reportando diferenças em velocidade de aprendizado, estabilidade e ausência de desempenho deprimido\.
- c:observation:sec\_12:results:1:obs\_2: A explicação causal \(“probably due to\.\.\. eligibility traces propagating rewards back by many steps in a single update”\) é apresentada como hipótese, mas não é sustentada por evidência quantitativa ou análise observável \(ex\.: medidas do “propagating rewards”/sinal de crédito\)\.
- c:observation:sec\_12:results:1:obs\_3: A hipótese causal é conectada a uma necessidade específica do ambiente \(Pong\), oferecendo uma justificativa contextual para atribuição de crédito em múltiplos time\-steps\.
- c:observation:sec\_12:results:1:obs\_4: Há inconsistência/erro provável de notação ao alternar “x = 0\.8” e “X = 0\.8” ao descrever o mesmo parâmetro, o que pode confundir o leitor e prejudicar a clareza\.
- c:observation:sec\_12:results:1:obs\_5: A explicação para a diferença ao trocar RMSprop por Adam \(“Our current intuition is that some hyper\-parameters, such as the frozen network&\#x27;s update frequency, are limiting\.\.\.”\) é especulativa e não é apoiada por ablações ou varredura de hiperparâmetros no texto fornecido\.
- c:observation:sec\_12:results:1:obs\_6: O texto resume resultados quantitativos via Tabela 1, associando melhorias à combinação “eligibility traces” e “Adam”, incluindo métricas de “número de epochs antes de\.\.\.”\.
- c:observation:sec\_12:discussion:1:obs\_1: O texto interpreta de forma coerente o ganho de estabilidade e velocidade quando há traces \(X = 0\.8\) em Pong, conectando\-o ao papel das eligibility traces em propagar crédito “por muitos passos” em uma única atualização\.
- c:observation:sec\_12:discussion:1:obs\_2: A explicação para a diferença entre RMSprop e Adam é especulativa \(“current intuition”\) e não é sustentada por evidências quantitativas adicionais nem por uma análise de sensibilidade/ablação dos hiperparâmetros citados\.
- c:observation:sec\_12:discussion:1:obs\_3: Há uma afirmação sobre estabilidade/ausência de performance deprimida e um efeito em “epochs”, mas o texto não explicita desenho experimental \(ex\.: número de seeds, intervalo de confiança, critério operacional de estabilidade\) dentro do trecho, limitando a avaliação da solidez da inferência\.
- c:observation:sec\_12:discussion:1:obs\_4: O trecho apresenta interpretações causais para dois fatores \(eligibility traces vs\. tipo de otimizador\) e os descreve como efeitos separados\. Por exemplo, atribui\-se o ganho com traces sob RMSprop a uma causa mecanística \(“eligibility traces propagating rewards back\.\.\.”\); e, em seguida, atribui\-se melhorias ao trocar RMSprop por Adam\. Contudo, não fica explícito se \(ou como\) esses efeitos interagem no RNN — isto é, se a mudança de otimizador altera a eficácia/estabilidade proporcionada pelas traces \(ou vice\-versa\)\. Assim, a leitura pode sugerir causalidade direta para cada contraste sem considerar possíveis interações entre \(traces \+ dinâmica de otimização\) no modelo recorrente\.

### 4\.2 TENNIS

- a:observation:sec\_13:results:1:sec\_13\_obs\_1: A seção apresenta comparações sistemáticas entre RNNs com e sem traces, dois otimizadores e diferentes taxas de aprendizado, incluindo resultados temporais específicos para atingir 20 pontos\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_2: A análise oferece uma explicação mecanística plausível para o comportamento do DQN, relacionando recompensas esparsas e atrasadas à dificuldade de atribuição de crédito; o texto também distingue explicitamente observação de hipótese ao usar linguagem como “suspect” e “might explain”\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_3: As conclusões quantitativas não são acompanhadas por medidas de variabilidade, número de sementes ou intervalos de incerteza; portanto, não é possível avaliar se as diferenças de épocas e a instabilidade observada são reproduzíveis ou estatisticamente robustas\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_4: A alegação de que este é o único algoritmo a obter pontuações quase ótimas entre todas as variantes de DQN não é suficientemente sustentada nesta seção, pois as variantes citadas não são descritas nem comparadas com resultados quantitativos individuais\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_5: A seção não apresenta uma ablação que separe claramente os efeitos da recorrência, dos traces, do otimizador e da taxa de aprendizado; as comparações existentes mostram combinações desses fatores, mas não estabelecem qual componente causa cada ganho\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_6: Os termos “optimal”, “near\-optimal” e “20 points” não são plenamente operacionalizados no texto da seção, embora o jogo seja descrito por uma escala de \-24 a 24; faltam uma definição explícita do critério de optimalidade e uma explicação de como o limiar de 20 se relaciona à vitória ou ao desempenho máximo\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_7: A progressão da seção é clara: começa com a comparação básica entre RNN e DQN, depois examina a taxa de aprendizado com RMSprop e finalmente compara Adam, permitindo acompanhar como cada alteração afeta velocidade e estabilidade\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_1: A seção compara sistematicamente RNNs com e sem traces em diferentes otimizadores e taxas de aprendizado, além de contrastá\-las com DQN\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_2: A análise oferece uma hipótese mecanística plausível para o fracasso do DQN, relacionando a política de adiamento à recompensa atrasada e à esparsidade dos eventos de pontuação\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_3: As explicações causais sobre a superioridade da recorrência, dos traces e do momentum são apresentadas como hipóteses, mas a seção não mostra ablações ou métricas diagnósticas que permitam distingui\-las de efeitos de otimização, exploração ou variância do treinamento\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_4: As conclusões sobre aprendizagem e estabilidade parecem depender de trajetórias individuais ou de observações pontuais, pois são reportadas épocas de atingimento e duas recaídas, sem incerteza, número de sementes, dispersão ou testes estatísticos\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_5: A afirmação de que este é o único algoritmo a obter desempenho quase ótimo em Tennis é ampla em relação à evidência apresentada, porque a seção não especifica de modo suficiente as condições, sementes, critérios de comparação ou resultados quantitativos de todas as variantes de DQN citadas\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_6: A terminologia de desempenho não é totalmente consistente: o texto alterna entre “optimal scores”, “near\-optimal performance” e limiares específicos como 20 pontos, sem explicitar nesta seção como esses termos se relacionam ao máximo possível e à política de teste\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_7: A interpretação do comportamento em loop é baseada em inspeção visual e não é acompanhada por uma definição operacional ou estatísticas da frequência e duração desses loops, o que limita a força da explicação sobre a causa das flutuações de score\.
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_8 [unresolved]: A seção identifica uma interação relevante entre arquitetura, traces, otimizador e taxa de aprendizado, em vez de atribuir o resultado exclusivamente à recorrência\.
- b:observation:sec\_13:results:1:obs1\_tennis\_rnn\_dqn\_perf: The article effectively demonstrates the superior performance of RNN models over DQN on the Tennis game, with RNNs consistently achieving optimal or near\-optimal scores while DQN fails to surpass the zero threshold\.
- b:observation:sec\_13:results:1:obs2\_tennis\_dqn\_qualitative\_analysis: The authors provide a clear and insightful qualitative analysis, based on visual inspection, explaining why the DQN agent fails in Tennis by getting stuck in a looping policy due to delayed and sparse rewards\.
- b:observation:sec\_13:results:1:obs3\_tennis\_ablation\_studies: The paper presents thorough ablation studies by experimenting with different optimizers \(RMSprop vs Adam\), learning rates, and the presence or absence of eligibility traces, providing quantitative data on their impact on learning speed and stability\.
- b:observation:sec\_13:results:1:obs4\_tennis\_explanations\_provided: The authors offer theoretical explanations for the observed performance differences, such as RNN&\#x27;s capacity for implicit credit assignment via BPTT and Adam&\#x27;s momentum assisting in overcoming safe strategies, which enhances the understanding of the results\.
- b:observation:sec\_13:results:1:obs5\_tennis\_dqn\_variants\_claim: The strong claim that RNN is &\#x27;the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN&\#x27; lacks explicit experimental details or results for all the mentioned DQN variants within this section, diminishing the immediate empirical substantiation of this broad assertion\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_1: The DQN agent consistently failed to achieve optimal scores in Tennis, getting stuck in a suboptimal policy of merely delaying the game until the timer runs out\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_2: The analysis provides a clear and plausible interpretation for DQN&\#x27;s failure, attributing it to the challenges of delayed and sparse rewards in propagating credit back to the correct actions, which threatens the validity of DQN in such scenarios\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_3: The study demonstrates the significant advantage of RNN models over all tested DQN variants in the Tennis game, effectively overcoming the &\#x27;bad policy&\#x27; due to their inherent ability for implicit credit assignment through Backpropagation Through Time \(BPTT\)\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_4: The robustness of the RNN model without eligibility traces is questioned, as it lost its ability to achieve optimal scores with a higher learning rate and, even with Adam, occasionally reverted to the delaying policy after initially learning to beat the opponent\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_5: The impact of the optimizer choice is clearly demonstrated, with Adam significantly accelerating learning for RNN models and providing a strong theoretical interpretation connecting Adam&\#x27;s momentum to its ability to overcome the &\#x27;safe strategy&\#x27; in delayed reward environments\.
- c:observation:sec\_13:results:1:obs\_1: A seção fornece caracterização do ambiente e do esquema de pontuação do Tennis, incluindo faixa de pontuação e como é calculada\.
- c:observation:sec\_13:results:1:obs\_2: Há comparação explícita entre RNN e DQN, com descrição do comportamento aprendido pelo agente DQN \(loop de troca da bola\) e efeito nas pontuações\.
- c:observation:sec\_13:results:1:obs\_3: A seção propõe uma hipótese mecanística para a falha do DQN, conectando atraso de recompensa e escassez de experiências a dificuldade de propagação do crédito\.
- c:observation:sec\_13:results:1:obs\_4: Afirmações causais e generalizações são feitas sem evidência quantitativa direta na seção \(ex\.: “only algorithm that succeeds”, e explicação por “escape the bad policy” atribuída ao BPTT\), além de dependerem de interpretação visual e de “might”\.
- c:observation:sec\_13:results:1:obs\_5: A seção apresenta resultados comparativos por configurações \(RMSprop com learning rate padrão vs valores maiores\), incluindo tempos/épocas e efeitos na capacidade de passar o limiar de 0\.
- c:observation:sec\_13:results:1:obs\_6: Há uma explicação de mecanismos para Adam que mistura características típicas de otimização com leitura do efeito \(“over­take the safe strategy”\) sem conexão empírica fornecida \(nenhuma métrica/ablação associando diretamente essa propriedade do gradiente ao comportamento observado\)\.
- c:observation:sec\_13:results:1:obs\_7: A seção afirma estabilidade e regressões de política \(ex\.: “much more stable”, “fell back \.\.\. on two occasions”\) sem especificar quantitativamente o que constitui “stable” nem fornecer distribuição/medidas; a evidência parece qualitativa\.
- c:observation:sec\_13:results:1:obs\_8: Conclusão sobre DQN com Adam ser equivalente ao DQN com RMSprop é declarada sem evidência detalhada \(apenas uma frase\), o que reduz sustentação empírica local\.
- c:observation:sec\_13:discussion:1:obs\_1: A seção descreve uma diferença clara de comportamento entre DQN e RNNs em Tennis \(DQN “never seems to be able to pass the 0 threshold” enquanto RNNs “learned to get optimal scores”\)\.
- c:observation:sec\_13:discussion:1:obs\_2: Há uma interpretação qualitativa baseada em observação do comportamento do agente \(loop de troca de bola\) que conecta diretamente o desempenho ao mecanismo de aprendizagem \(recompensa atrasada e experiências esparsas\)\.
- c:observation:sec\_13:discussion:1:obs\_3: A seção usa linguagem causal \(“explains”, “might explain”\) sem apresentar evidências quantitativas adicionais específicas para Tennis; isso reduz a solidez da inferência\.
- c:observation:sec\_13:discussion:1:obs\_4: Algumas explicações sobre efeitos de hiperparâmetros/otimizadores são plausíveis, mas permanecem especulativas e podem ter ameaças à validade \(ex\.: relação entre tamanho de updates e learning rate efetivo; efeito de momentum “stored” sem validação empírica direta\)\.
- c:observation:sec\_13:discussion:1:obs\_5 [unresolved]: Há comparações diretas, com números, entre configurações \(RMSprop vs Adam; traces vs sem traces; learning rates\), aumentando a clareza do que foi observado\.
- c:observation:sec\_13:discussion:1:obs\_6: A seção faz afirmações de alcance \(“only algorithm that succeeds… out of all variants of DQN”\) sem explicitar o conjunto/condições exatas de comparação e sem discutir limites de generalização \(amenças à validade externa\), o que enfraquece a conclusão\.

### 5 DISCUSSION AND CONCLUSION

- a:observation:sec\_14:discussion:1:sec\_14\_obs\_1: A discussão conecta explicitamente as conclusões aos resultados observados em Pong e distingue o efeito das eligibility traces do efeito do otimizador Adam, evitando apresentar o resultado de Pong como uniformemente positivo para todas as combinações\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_2: A seção reconhece limitações do desenho experimental e propõe hipóteses testáveis para explicar por que o Adam teve pouco efeito em conjunto com eligibility traces, além de sugerir intervenções experimentais concretas\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_3: As conclusões gerais são mais abrangentes do que o escopo explicitamente delimitado na seção: afirmar que eligibility traces podem melhorar e estabilizar o aprendizado e que Adam pode acelerá\-lo fortemente não especifica em quais jogos, arquiteturas, configurações ou condições esses efeitos foram observados\. Embora a discussão posteriormente contextualize parte da análise nos resultados de Pong, a formulação inicial ainda pode sugerir uma generalização além dos experimentos apresentados\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_4: A seção atribui possíveis mecanismos causais ao efeito da frozen network, à propagação de valores e ao desvio off\-policy do replay, mas não indica quais evidências dos experimentos distinguem essas explicações de outras hipóteses\. A linguagem &\#x27;One possible cause&\#x27; é prudente, porém a discussão poderia separar mais claramente resultados demonstrados de mecanismos ainda especulativos\.
- a:observation:sec\_14:discussion:1:sec\_14\_obs\_5: A discussão afirma que os eligibility traces podem melhorar e estabilizar a aprendizagem e que o uso do Adam pode acelerá\-la fortemente, mas não quantifica a magnitude desses efeitos nem informa a variabilidade, o número de replicações ou critérios quantitativos de estabilidade\. Isso limita a avaliação da robustez e do alcance dessas conclusões\.
- a:observation:sec\_14:conclusion:1:sec14\_obs1: A conclusão apresenta de forma direta as duas contribuições centrais alegadas: o efeito das eligibility traces e o impacto do otimizador Adam, o que facilita identificar a mensagem principal do artigo\.
- a:observation:sec\_14:conclusion:1:sec14\_obs2: A relevância da conclusão é apresentada de modo mais amplo do que o trecho demonstra: a formulação não delimita em quais jogos, configurações ou condições as melhorias foram observadas, nem distingue claramente resultados consistentes de efeitos dependentes do experimento\. Isso enfraquece o alcance sustentado pela evidência\.
- a:observation:sec\_14:conclusion:1:sec14\_obs3: A discussão oferece interpretações mecanísticas e propostas futuras explicitamente qualificadas como hipóteses ou possibilidades, evitando apresentá\-las como conclusões já demonstradas\.
- a:observation:sec\_14:conclusion:1:sec14\_obs4: A síntese dos resultados específicos é incompleta: embora a conclusão destaque que o modelo com eligibility traces no Pong não obteve muito benefício adicional com Adam, ela não explicita como esse achado se relaciona aos demais resultados nem em que medida modifica a afirmação geral de que Adam acelera fortemente o aprendizado\.
- b:observation:sec\_14:discussion:1:obs\_1: The article critically analyzes a specific result from the Pong game, where the combination of eligibility traces and Adam optimizer did not yield significant performance gains\. It offers a plausible explanation by identifying the &\#x27;frozen network&\#x27; as a potential causal factor\.
- b:observation:sec\_14:discussion:1:obs\_2: The authors propose concrete improvements for future experiments, such as adjusting the update frequency of the frozen network, which directly addresses a identified limitation and could enhance the propagation of newly learned values\.
- b:observation:sec\_14:discussion:1:obs\_3: The paper suggests a further refinement for future work by considering a reduction in the size of the experience replay buffer\. This acknowledges that with increased learning speed, older observations might become less relevant for eligibility traces, demonstrating an understanding of the intricate interactions between different components of the reinforcement learning setup\.
- b:observation:sec\_14:conclusion:1:conc\-clarity\-impact\-01: As conclusões iniciais são apresentadas de forma concisa e clara, resumindo os principais achados sobre os efeitos das eligibility traces e otimizadores, o que contribui para a clareza geral e impacto do trabalho\.
- b:observation:sec\_14:conclusion:1:conc\-clarity\-impact\-02: A conclusão faz uma referência específica aos resultados de Pong e oferece uma explicação hipotética para o comportamento observado, o que demonstra uma análise aprofundada e leads a sugestões claras e pertinentes para trabalhos futuros, reforçando a relevância e o impacto do estudo\.
- c:observation:sec\_14:discussion:1:obs\_1: O texto conecta diretamente a conclusão geral aos resultados e ao efeito esperado: “Eligibility traces can improve and stabilize learning and using Adam can strongly accelerate learning\.”
- c:observation:sec\_14:discussion:1:obs\_2: A explicação causal para a aparente falta de ganho do Adam com eligibility traces em Pong é especulativa e não é confrontada com evidência adicional \(p\.ex\., ablação da “frozen network” ou métricas de propagação\)\.
- c:observation:sec\_14:discussion:1:obs\_3: Há aparente tensão entre a afirmação geral de que “Adam can strongly accelerate learning” e a observação específica de Pong de que “didn&\#x27;t gain much performance from using Adam” quando combinado com eligibility traces; o texto não reconcilia quantitativamente essa diferença \(por exemplo, apontando em quais condições/variantes Adam acelera e em quais não\)\.
- c:observation:sec\_14:discussion:1:obs\_4: As limitações e ameaças à validade são tratadas apenas como “future experiments” \(p\.ex\., frequência da frozen network e reduzir tamanho do replay\), mas o texto não explicita quais limitações já observadas limitam a inferência no estado atual\.
- c:observation:sec\_14:discussion:1:obs\_5: O texto indica um caminho de verificação para a hipótese levantada \(ajustar “frozen network&\#x27;s update frequency” e tamanho de “experience replay”\), o que melhora a transparência sobre o alcance das conclusões\.
- c:observation:sec\_14:conclusion:1:obs\_1: A conclusão resume os efeitos observados ao relacionar elegibility traces, estabilização e o ganho de velocidade com Adam, conectando\-os diretamente ao que foi analisado no trabalho\.
- c:observation:sec\_14:conclusion:1:obs\_2: A seção afirma resultados específicos \(por exemplo, impacto limitado do Adam com eligibility traces em Pong\), mas o texto fornecido não mostra quais evidências numéricas/figuras suportam diretamente essas alegações, reduzindo a sustentação explícita das conclusões\.
- c:observation:sec\_14:conclusion:1:obs\_3: A explicação causal para o desempenho em Pong \(rede congelada, efeitos em propagação de valores e relação com Double DQN\) é apresentada como hipótese sem apontar diretamente o que os resultados exibem para validá\-la \(ex\.: tendências/valores associados a configurações\)\.
- c:observation:sec\_14:conclusion:1:obs\_4: As limitações e próximos passos estão explicitamente formulados como ações futuras \(frequência de atualização da rede congelada e tamanho do experience replay\), o que ajuda a dar fechamento à discussão com direção experimental\.

## Evidências

- a:criterion:replicability: A arquitetura, o tamanho das subtrajetórias, o burn\-in, o lote, alguns hiperparâmetros dos otimizadores e a frequência da rede\-alvo são informados\. Porém, faltam ou permanecem ambíguos parâmetros essenciais dos traces, fórmulas dos alvos, regras de terminação e detalhes do ambiente, avaliação, sementes e protocolo experimental; a notação corrompida também impede reconstruir exatamente o algoritmo\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_3: Faltam as definições matemáticas dos retornos n\-step, do retorno λ e da atualização por eligibility trace\. Sem essas equações, não é possível verificar precisamente a ponderação dos retornos, o tratamento de estados terminais ou a correspondência formal entre as visões forward e backward\.
  - sec\_4: The central notion for these are n\-step returns, which provide a way of calculating the target by using the value estimate for the state which occurs n steps in the future \(compared to the current state\):
  - sec\_4: Eligibility traces use a geometric weighting of these n\-step returns, where the weight of the k\-step return is λ times the weight of the k \- 1\-step return\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_5: A descrição da ponderação geométrica não informa a normalização dos pesos nem esclarece se λ se refere ao parâmetro da mistura dos retornos, ao fator de decaimento da trace, ou a uma convenção específica com γ\. Isso deixa a implementação subespecificada\.
  - sec\_4: Eligibility traces use a geometric weighting of these n\-step returns, where the weight of the k\-step return is λ times the weight of the k \- 1\-step return\.
  - sec\_4: Using a λ = 0 reduces to using TD, as all n\-steps for n &gt; 1 have a weight of 0\.
- a:observation:sec\_4:method:1:sec\_4\_obs\_7: A seção apresenta conceitualmente as visões forward e backward e a ponderação geométrica por λ, mas não especifica uma variante implementável de eligibility trace nem as convenções e parâmetros necessários para reproduzi\-la, como o valor de λ, a regra exata de atualização e o tipo de traço utilizado\. Assim, a descrição não é suficiente para reproduzir uma implementação concreta a partir desta seção isoladamente\.
  - sec\_4: Eligibility traces use a geometric weighting of these n\-step returns, where the weight of the k\-step return is λ times the weight of the k \- 1\-step return\.
  - sec\_4: There is an equivalent view called the backward view, which allows us to calculate updates for every previous state as we take a single action\.
  - sec\_4: This way of viewing eligibility traces is called the forward view, as states are looking ahead at the rewards received in the future\.
  - sec\_4: However, this view has had limited success in the neural network setting as it requires using a trace on each neuron of the network, which tend to be dense and heavily used at each step resulting in noisy signals\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_3: Falta a formulação matemática ou um pseudocódigo da regra de Watkins&\#x27;s Q\(X\), incluindo em que instante o traço é zerado, como ele é atualizado depois disso e como essa regra entra no alvo ou na atualização dos valores Q\. Sem esses elementos, a implementação não é reproduzível a partir do trecho\.
  - sec\_5: To handle such a case, Watkins&\#x27;s Q\(X\) sets the trace to 0 if the action that the current policy would select is different from the one used in the past\.
- a:observation:sec\_5:method:1:sec\_5\_obs\_4: A condição “the action that the current policy would select” é ambígua para políticas exploratórias, como ε\-greedy: não se especifica se a comparação usa a ação greedy, uma amostra da política, os valores Q antes ou depois da atualização, nem como são tratados empates\. Esses parâmetros podem alterar o comportamento do algoritmo\.
  - sec\_5: sets the trace to 0 if the action that the current policy would select is different from the one used in the past\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_3: A seção não especifica parâmetros essenciais da aplicação das eligibility traces, como o valor ou os valores de λ, a fórmula exata dos alvos ponderados, o horizonte das subtrajetórias e como é feito o tratamento de estados terminais\. Sem esses detalhes, a implementação do método não é reproduzível\.
  - sec\_9: Finally, all that&\#x27;s left to use eligibility traces is simply to calculate the weighted sum of the targets, which is very cheap to do\.
  - sec\_9: Then, by training on sub\-trajectories of data, the states must be run through the RNN with all state values as the output
- a:observation:sec\_9:method:1:sec\_9\_obs\_4: Embora RMSprop e Adam sejam mencionados, faltam as configurações dos otimizadores e do treinamento, incluindo taxas de aprendizagem, parâmetros de momento ou β, tamanho de lote, frequência de atualização, número de passos/épocas, inicialização e número de sementes\. Esses parâmetros podem afetar diretamente a comparação experimental\.
  - sec\_9: In this section we analyze the use of eligibility traces when training DRQN and try both RMSprop and Adam as optimizers\.
- a:observation:sec\_9:method:1:sec\_9\_obs\_5: O desenho experimental é descrito apenas em termos gerais: a seção não informa quais jogos foram usados, o protocolo de amostragem do replay, o comprimento das sequências, o burn\-in para o estado oculto, a política de exploração nem o procedimento de avaliação\. A ausência desses elementos impede reproduzir precisamente o experimento a partir desta seção\.
  - sec\_9: We only tested the algorithms on fully observable games
  - sec\_9: Then, by training on sub\-trajectories of data
- a:observation:sec\_10:method:1:sec\_10\_obs\_1: A arquitetura da rede é descrita com especificidade suficiente para identificar os principais componentes e dimensões, incluindo as camadas convolucionais, a camada densa, a LSTM e a camada de saída dos valores Q\.
  - sec\_10: The frames are converted to gray\-scale and re\-sized to 84x84\. These are then fed to a CNN with the first layer being 32 8x8 filters and a stride of 4, followed by 64 4x4 filters with a stride of 2, then by 64 3x3 filters with a stride of 1\.
  - sec\_10: The output of the CNN is then flattened before being fed to a single dense layer of 512 output neurons, which is finally fed to an LSTM \(Hochreiter &amp; Schmidhuber \(1997\)\) with 512 cells\. We then have a last linear layer that takes the output of the recurrent layer to output the Q\-values\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_2: O procedimento de treinamento recorrente especifica o comprimento das subtrajetórias, o número de estados usados para preencher o estado oculto e o tamanho do lote, tornando explícita a adaptação do experience replay para BPTT\.
  - sec\_10: In our experiments, we selected trajectory lengths of 32, where the first 10 states are used as filler and the remaining 22 are used for the traces and TD costs\. We used a batch size of 4\.
  - sec\_10: We use backprop through time \(BPTT\) to train the RNN, but only train on a sub\-trajectory of experience\.
- a:observation:sec\_10:method:1:sec\_10\_obs\_3: A descrição do algoritmo contém notação corrompida ou ambígua, especialmente nos índices do retorno forward\-view e na expressão do custo, o que dificulta reconstruir exatamente o alvo usado no gradiente\.
  - sec\_10: for l from 0 to k − 1 do R\(s−l\+1\)1 k t\+l = \[∑s=l \(Πi=1 λt\+i\)R\(s−l\+1\)1\]/\[∑s=l \(Πi=1 λt\+i\)\] end Perform gradient descent on \(R\(s−l\+1\)1 t\+s −Q\(s,a\|θ\)\)2 2θ
- a:observation:sec\_10:method:1:sec\_10\_obs\_4: A notação do parâmetro de elegibilidade é inconsistente: o texto usa X = 0\.8, depois x = 0\.8, e o algoritmo usa λ sem deixar explícita a correspondência entre esses símbolos\.
  - sec\_10: All experiments using eligibility traces use X = 0\.8\.
  - sec\_10: We choose the limit of 0\.01, which allows the traces to affect 21 states ahead \(when x = 0\.8\)\.
  - sec\_10: Choose k as number of trace steps and m as RNN\-filler steps
- a:observation:sec\_10:method:1:sec\_10\_obs\_6: Os hiperparâmetros dos dois otimizadores e o procedimento de atualização da rede\-alvo são fornecidos, incluindo taxas de aprendizado, momentum, epsilon e frequência de atualização\.
  - sec\_10: When using RMSprop, we used a momentum of 0\.95, an epsilon of 0\.01 and a learning rate of 0\.00025\.
  - sec\_10: When using Adam, we used a momentum of gradients of 0\.9, a momentum of squared gradients of 0\.999, an epsilon of 0\.001 and a learning rate of 0\.00025\.
  - sec\_10: Every 10000 steps θ¯ ← θ
- a:check:method\_vs\_question:method\_vs\_question\_1: method\_vs\_question: consistent
  - sec\_2: We investigate the use of two methods that are known to mitigate these problems: recurrent networks, which provide a form of memory summarizing past experiences, and eligibility traces, which allow information to propagate over multiple time steps\.
  - sec\_9: In this section we analyze the use of eligibility traces when training DRQN and try both RMSprop and Adam as optimizers\.
  - sec\_10: We tested the algorithms on two Atari 2600 games, part of the Arcade Learning Environment \(Bellemare et al\. \(2012\)\), Pong and Tennis\.
  - sec\_9: We only tested the algorithms on fully observable games as to compare the learning capacities without the unfair advantage of having a memory, as would be the case on partially observable environments\.
  - sec\_10: The architecture used is similar to the one used in Hausknecht &amp; Stone \(2015\)\. The frames are converted to gray\-scale and re\-sized to 84x84\.
  - sec\_10: When using RMSprop, we used a momentum of 0\.95, an epsilon of 0\.01 and a learning rate of 0\.00025\. When using Adam, we used a momentum of gradients of 0\.9, a momentum of squared gradients of 0\.999, an epsilon of 0\.001 and a learning rate of 0\.00025\.
- a:criterion:substance: O artigo contém experimentos comparativos em dois jogos, com variações de traces, arquitetura, otimizadores e taxas de aprendizado, além de interpretações mecanísticas e resultados temporais\. Ainda assim, a cobertura é estreita, as métricas e curvas não estão integralmente disponíveis no material fornecido, faltam variabilidade e testes estatísticos, e não há ablações suficientes para separar os efeitos dos componentes\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_1: A seção delimita claramente os experimentos a Pong e Tennis e oferece uma justificativa funcional para a escolha: Pong permite experimentação rápida, enquanto Tennis é apresentado como um jogo particularmente difícil nos resultados publicados\.
  - sec\_11: We describe experiments in two Atari games: Pong and Tennis\. We chose Pong because it permits quick experimentation, and Tennis because it is one of the games that has proven difficult in all published results on Atari\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_2: No trecho fornecido, são descritos os jogos Pong e Tennis e a justificativa para sua escolha, mas não são apresentadas curvas de desempenho nem métricas operacionais de sucesso que permitam comparar quantitativamente os resultados ou os otimizadores\.
  - sec\_11: We describe experiments in two Atari games: Pong and Tennis\. We chose Pong because it permits quick experimentation, and Tennis because it is one of the games that has proven difficult in all published results on Atari\.
- a:observation:sec\_11:results:1:sec\_11\_obs\_5: A cobertura experimental é estreita: são avaliados apenas dois jogos, escolhidos por razões práticas e de dificuldade\. Isso é suficiente para um estudo exploratório, mas sustenta apenas conclusões limitadas sobre generalização para o domínio Atari como um todo\.
  - sec\_11: We describe experiments in two Atari games: Pong and Tennis\.
  - sec\_11: We chose Pong because it permits quick experimentation, and Tennis because it is one of the games that has proven difficult in all published results on Atari\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_1: A comparação cobre diretamente os principais fatores experimentais: presença ou ausência de traços e uso de RMSprop ou Adam, incluindo o baseline DQN\.
  - sec\_12: We tested an RNN model both with X = 0 and x = 0\.8, trained with RMSprop\.
  - sec\_12: We then tested the same models but using Adam as the optimizer instead of RMSprop\.
  - sec\_12: the DQN model also learns faster with Adam as the optimizer
- a:observation:sec\_12:results:1:sec\_12\_obs\_2: O texto relaciona o padrão observado em Pong a uma hipótese mecanística plausível: as elegibilidade dos traços propagam o crédito do retorno até o momento em que a bola foi atingida\.
  - sec\_12: This is probably due to the eligibility traces propagating rewards back by many steps in a single update\.
  - sec\_12: The traces clearly help send this signal back faster\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_3: A seção considera não apenas velocidade de aprendizagem, mas também estabilidade, distinguindo o comportamento do DQN daquele dos modelos recorrentes\.
  - sec\_12: the model with traces \(X = 0\.8\) learned substantially faster and with more stability
  - sec\_12: the DQN model also learns faster with Adam as the optimizer, but remains quite unstable, in comparison with the recurrent net models\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_4: As afirmações quantitativas sobre rapidez e estabilidade não são acompanhadas, no texto, por médias, variâncias, intervalos de confiança, número de sementes ou testes estatísticos\.
  - sec\_12: learned substantially faster and with more stability
  - sec\_12: While training with RMSProp, the model with traces gets to near optimal perfor\- mance more than twice as quickly as the other models\.
  - sec\_12: All models learn much faster with this setting\.
- a:observation:sec\_12:results:1:sec\_12\_obs\_5: A comparação depende de referências à Figure 2 e à Table 1, mas o trecho não fornece os valores observados nem a magnitude da variabilidade; assim, a verificabilidade das conclusões fica limitada sem consultar esses elementos\.
  - sec\_12: Figure 2 shows that the model without a trace \(X = 0\) learned at the same rate as DQN
  - sec\_12: the results in Table 1 show that both using eligibility traces and Adam provide performance improvements
- a:observation:sec\_12:results:1:sec\_12\_obs\_6: O desenho permite comparar os fatores principais, mas não isola claramente todas as interações: em particular, a interpretação do efeito dos traços sob Adam é apresentada sem uma análise quantitativa explícita da interação entre traços e otimizador\.
  - sec\_12: However, the model with no trace gains significantly more than the model with the trace\.
  - sec\_12: Our current intuition is that some hyper\-parameters, such as the frozen network&\#x27;s update frequency, are limiting the rate at which the model can learn\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_1: A seção apresenta comparações sistemáticas entre RNNs com e sem traces, dois otimizadores e diferentes taxas de aprendizado, incluindo resultados temporais específicos para atingir 20 pontos\.
  - sec\_13: As in Pong, we first tried an RNN trained with RMSprop and the standard learning rate of 0\.00025, both with and without eligibility traces
  - sec\_13: We also trained the models with RMSprop and a higher learning rate of 0\.001\.
  - sec\_13: We then tried using Adam as the optimizer, with the original learning rate of 0\.00025\.
  - sec\_13: The model without traces learned at a faster pace than the one with traces, arriving to a score of 20 in 45 epochs as opposed to 62 for its counterpart\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_3: As conclusões quantitativas não são acompanhadas por medidas de variabilidade, número de sementes ou intervalos de incerteza; portanto, não é possível avaliar se as diferenças de épocas e a instabilidade observada são reproduzíveis ou estatisticamente robustas\.
  - sec\_13: The model without traces learned at a faster pace than the one with traces, arriving to a score of 20 in 45 epochs as opposed to 62 for its counterpart\.
  - sec\_13: With Adam, the gradient for the positive TD is stored in the momentum part of the equation for quite some time\.
  - sec\_13: The model without traces fell back to the policy of delaying the game on two occasions, after having learned to beat the opponent\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_4: A alegação de que este é o único algoritmo a obter pontuações quase ótimas entre todas as variantes de DQN não é suficientemente sustentada nesta seção, pois as variantes citadas não são descritas nem comparadas com resultados quantitativos individuais\.
  - sec\_13: Remarkably, this is the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN \(Mnih et al\. \(2015\), Munos et al\. \(2016\), Wang et al\. \(2015\), Mnih et al\. \(2016\), Schaul et al\. \(2015\)\)
  - sec\_13: DQN, which never seems to be able to pass the 0 threshold, with large fluctuations ranging from \-24 to 0\.
- a:observation:sec\_13:results:1:sec\_13\_obs\_5: A seção não apresenta uma ablação que separe claramente os efeitos da recorrência, dos traces, do otimizador e da taxa de aprendizado; as comparações existentes mostram combinações desses fatores, mas não estabelecem qual componente causa cada ganho\.
  - sec\_13: We also notice that both the RNN with and without eligibility traces manage to learn a near\-optimal policy without getting stuck in the bad policy\.
  - sec\_13: This led to the model with traces getting to 20 points in just 27 epochs, while the model without traces lost its ability to get optimal scores and never passed the 0 threshold\.
  - sec\_13: Both RNN models learned substantially faster than with RMSprop, with the RNN with traces getting to near\-optimal performance in just 13 epochs\.
- a:check:claims\_vs\_results:claims\_vs\_results\_1: claims\_vs\_results: consistent
  - sec\_14: We showed that eligibility traces can improve and stabilize learning and using Adam can strongly accelerate learning\.
  - sec\_12: the model with traces \(X = 0\.8\) learned substantially faster and with more stability
  - sec\_12: With Adam, the model learns to be optimal in just 6 epochs\.
  - sec\_13: Both RNN models learned substantially faster than with RMSprop, with the RNN with traces getting to near\-optimal performance in just 13 epochs\.
  - sec\_13: the model without traces learned at a faster pace than the one with traces
- a:check:figure\_vs\_text:figure\_vs\_text\_sec\_12\_sec\_13: figure\_vs\_text: inconsistent
  - sec\_12: However, the model with no trace gains significantly more than the model with the trace\.
  - sec\_13: The model without traces learned at a faster pace than the one with traces, arriving to a score of 20 in 45 epochs as opposed to 62 for its counterpart\.
- b:criterion:impact: O artigo aborda problemas relevantes em DRL, como recompensas esparsas e o problema de atribuição de crédito, e demonstra um ganho significativo no desempenho e na estabilidade com RNNs em um jogo desafiador como Tennis, e com traces de elegibilidade em Pong\. As sugestões de trabalhos futuros também são promissoras\. No entanto, o impacto é mitigado pela inconsistência entre as alegações iniciais de que traces de elegibilidade impulsionam o desempenho e os resultados experimentais em certos cenários, além do abandono do foco em observabilidade parcial, conforme inicialmente proposto\.
- b:observation:sec\_2:introduction:1:obs3: The potential impact of the research is implied through the stated contributions, as boosting performance in Deep RL and understanding optimization effects can be highly relevant for improving learning agents in complex environments\.
  - sec\_2: We provide experiments in the Atari domain showing that eligibility traces boost the performance of Deep RL\. We also demonstrate a surprisingly strong effect of the optimization method on the performance of the recurrent networks\.
- b:observation:sec\_12:discussion:1:pong\_obs\_4: The section clearly summarizes the main performance improvements, indicating that both eligibility traces and the Adam optimizer contribute positively to learning efficiency and stability, with quantitative references to Table 1\.
  - sec\_12: Finally, the results in Table 1 show that both using eligibility traces and Adam provide performance improvements\. While training with RMSProp, the model with traces gets to near optimal perfor\- mance more than twice as quickly as the other models\. With Adam, the model learns to be optimal in just 6 epochs\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_3: The study demonstrates the significant advantage of RNN models over all tested DQN variants in the Tennis game, effectively overcoming the &\#x27;bad policy&\#x27; due to their inherent ability for implicit credit assignment through Backpropagation Through Time \(BPTT\)\.
  - sec\_13: The RNN has the capacity of sending the signal back to past states with BPTT, allowing it to do credit assignment implicitly, which might explain their ability to escape the bad policy\.
  - sec\_13: Remarkably, this is the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN \(Mnih et al\. \(2015\), Munos et al\. \(2016\), Wang et al\. \(2015\), Mnih et al\. \(2016\), Schaul et al\. \(2015\)\), which tend to get stuck in the policy of delaying\.
- b:observation:sec\_13:discussion:1:obs\_tennis\_5: The impact of the optimizer choice is clearly demonstrated, with Adam significantly accelerating learning for RNN models and providing a strong theoretical interpretation connecting Adam&\#x27;s momentum to its ability to overcome the &\#x27;safe strategy&\#x27; in delayed reward environments\.
  - sec\_13: Both RNN models learned substantially faster than with RMSprop, with the RNN with traces getting to near\-optimal performance in just 13 epochs\.
  - sec\_13: With Adam, the gradient for the positive TD is stored in the momentum part of the equation for quite some time\. Once in momentum, the gradient is part of many updates, which makes it enough to overtake the safe strategy\.
- b:observation:sec\_14:discussion:1:obs\_2: The authors propose concrete improvements for future experiments, such as adjusting the update frequency of the frozen network, which directly addresses a identified limitation and could enhance the propagation of newly learned values\.
  - sec\_14: In future experiments, we must consider eliminating or increasing the frozen network&\#x27;s update frequency\.
- b:observation:sec\_14:discussion:1:obs\_3: The paper suggests a further refinement for future work by considering a reduction in the size of the experience replay buffer\. This acknowledges that with increased learning speed, older observations might become less relevant for eligibility traces, demonstrating an understanding of the intricate interactions between different components of the reinforcement learning setup\.
  - sec\_14: It would also be interesting to reduce the size of experience replay, as with increased learning speed, old observations can become too off\-policy and barely be used in eligibility traces\.
- b:observation:sec\_14:conclusion:1:conc\-clarity\-impact\-01: As conclusões iniciais são apresentadas de forma concisa e clara, resumindo os principais achados sobre os efeitos das eligibility traces e otimizadores, o que contribui para a clareza geral e impacto do trabalho\.
  - sec\_14: In this paper, we analyzed the effects of using eligibility traces and different optimization functions\. We showed that eligibility traces can improve and stabilize learning and using Adam can strongly accelerate learning\.
- b:observation:sec\_14:conclusion:1:conc\-clarity\-impact\-02: A conclusão faz uma referência específica aos resultados de Pong e oferece uma explicação hipotética para o comportamento observado, o que demonstra uma análise aprofundada e leads a sugestões claras e pertinentes para trabalhos futuros, reforçando a relevância e o impacto do estudo\.
  - sec\_14: As shown in the Pong results, the model using eligibility traces didn&\#x27;t gain much performance from using Adam\. One possible cause is the frozen network\. While it has a stabilizing effect in DQN, by stopping policies from drastically changing from a single update, it also stops newly learned values from being propagated back\. Double DQN seems to partially go around this issue, allowing the policy of the next state to change, while keeping the values frozen\. In future experiments, we must consider eliminating or increasing the frozen network&\#x27;s update frequency\. It would also be interesting to reduce the size of experience replay, as with increased learning speed, old observations can become too off\-policy and barely be used in eligibility traces\.
- b:check:claims\_vs\_results:claims\_vs\_results\_1: claims\_vs\_results: inconsistent
  - sec\_2: We provide experiments in the Atari domain showing that eligibility traces boost the performance of Deep RL\.
  - sec\_12: However, the model with no trace gains significantly more than the model with the trace\. Our current intuition is that some hyper\-parameters, such as the frozen network&\#x27;s update frequency, are limiting the rate at which the model can learn\.
  - sec\_13: The model without traces learned at a faster pace than the one with traces, arriving to a score of 20 in 45 epochs as opposed to 62 for its counterpart\.
  - sec\_14: As shown in the Pong results, the model using eligibility traces didn&\#x27;t gain much performance from using Adam\.
- b:criterion:substance: O artigo apresenta estudos de ablação abrangentes e análises qualitativas para os jogos testados, fornecendo métricas quantitativas claras em alguns casos\. Demonstra a superioridade de modelos RNN sobre DQN no jogo Tennis e oferece análises perspicazes para o fracasso do DQN nesse ambiente\. No entanto, a substância é enfraquecida pela falta de baselines claras e estatísticas iniciais na introdução dos resultados\. Alegações sobre estabilidade carecem de análise estatística quantitativa\. Uma afirmação forte sobre o sucesso único do algoritmo no Tennis não é totalmente sustentada por detalhes experimentais explícitos de todas as variantes de DQN mencionadas\. Além disso, a inconsistência entre as alegações iniciais e alguns resultados experimentais reduz a força geral das evidências apresentadas\.
- b:observation:sec\_11:results:1:obs\_1: A introdução da seção de resultados \(4 EXPERIMENTAL RESULTS\) descreve a escolha dos jogos, mas não apresenta imediatamente baselines, estatísticas iniciais, variância ou detalhes de ablação para contextualizar os experimentos, o que seria esperado para estabelecer a base dos resultados subsequentes\.
- b:observation:sec\_11:results:1:obs\_2: A justificativa para a escolha do jogo Tennis baseia\-se em uma afirmação generalizada de que ele &quot;has proven difficult in all published results on Atari&quot;, sem apresentar citações ou evidências específicas no texto para sustentar essa alegação\.
  - sec\_11: Tennis because it is one of the games that has proven difficult in all published results on Atari\.
- b:observation:sec\_12:results:1:obs\_pong\_1: The experimental results clearly show the benefits of eligibility traces for learning speed and stability when using RMSprop, providing a solid ablation study\.
  - sec\_12: Figure 2 shows that the model without a trace \(X = 0\) learned at the same rate as DQN, while the model with traces \(X = 0\.8\) learned substantially faster and with more stability, without exhibiting any epochs with depressed performance\.
- b:observation:sec\_12:results:1:obs\_pong\_3: While qualitative statements about &\#x27;more stability&\#x27; and &\#x27;quite unstable&\#x27; are made, the text lacks quantitative statistical analysis \(e\.g\., standard deviation across multiple runs\) to substantiate claims about variance and stability\.
  - sec\_12: Figure 2 shows that the model without a trace \(X = 0\) learned at the same rate as DQN, while the model with traces \(X = 0\.8\) learned substantially faster and with more stability, without exhibiting any epochs with depressed performance\.
  - sec\_12: Note also that the DQN model also learns faster with Adam as the optimizer, but remains quite unstable, in comparison with the recurrent net models\.
- b:observation:sec\_12:results:1:obs\_pong\_4: The intuition offered to explain the interaction between traces and the Adam optimizer \(hyper\-parameters limiting the learning rate\) is speculative and not immediately substantiated with further evidence or experiments within the provided text\.
  - sec\_12: Our current intuition is that some hyper\-parameters, such as the frozen network&\#x27;s update frequency, are limiting the rate at which the model can learn\.
- b:observation:sec\_12:results:1:obs\_pong\_5: The results provide clear quantitative metrics \(epochs to reach near\-optimal performance\) for comparing different configurations, which significantly strengthens the claims of performance improvement\.
  - sec\_12: Finally, the results in Table 1 show that both using eligibility traces and Adam provide performance improvements\. While training with RMSProp, the model with traces gets to near optimal perfor\- mance more than twice as quickly as the other models\. With Adam, the model learns to be optimal in just 6 epochs\.
- b:observation:sec\_13:results:1:obs1\_tennis\_rnn\_dqn\_perf: The article effectively demonstrates the superior performance of RNN models over DQN on the Tennis game, with RNNs consistently achieving optimal or near\-optimal scores while DQN fails to surpass the zero threshold\.
  - sec\_13: Figure 3 shows that both RNN models learned to get optimal scores after about 50 epochs\. This is in contrast with DQN, which never seems to be able to pass the 0 threshold, with large fluctuations ranging from \-24 to 0\.
  - sec\_13: Finally, we trained DQN with Adam, but the model acted the same way as DQN trained with RMSprop\.
- b:observation:sec\_13:results:1:obs2\_tennis\_dqn\_qualitative\_analysis: The authors provide a clear and insightful qualitative analysis, based on visual inspection, explaining why the DQN agent fails in Tennis by getting stuck in a looping policy due to delayed and sparse rewards\.
  - sec\_13: After visually inspecting the games played in the testing phase, we noticed that the DQN agent gets stuck in a loop, where it exchanges the ball with the opponent until the timer runs out\.
  - sec\_13: We suspect that the agent gets stuck in this policy because the reward for trying to defeat the opponent is delayed, waiting for the ball to reach the opponent and get past it\. Furthermore, the experiences of getting a point are relatively sparse\. Together, it makes it difficult to propagate the reward back to the action of hitting the ball correctly\.
- b:observation:sec\_13:results:1:obs3\_tennis\_ablation\_studies: The paper presents thorough ablation studies by experimenting with different optimizers \(RMSprop vs Adam\), learning rates, and the presence or absence of eligibility traces, providing quantitative data on their impact on learning speed and stability\.
  - sec\_13: both with and without eligibility traces \(using again λ = 0\.8 and λ = 0\)\.
  - sec\_13: The model without traces learned at a faster pace than the one with traces, arriving to a score of 20 in 45 epochs as opposed to 62 for its counterpart\.
  - sec\_13: We also trained the models with RMSprop and a higher learning rate of 0\.001\. This led to the model with traces getting to 20 points in just 27 epochs, while the model without traces lost its ability to get optimal scores and never passed the 0 threshold\.
  - sec\_13: We then tried using Adam as the optimizer, with the original learning rate of 0\.00025\. Both RNN models learned substantially faster than with RMSprop, with the RNN with traces getting to near\-optimal performance in just 13 epochs\.
  - sec\_13: The model without traces fell back to the policy of delaying the game on two occasions, after having learned to beat the opponent\.
- b:observation:sec\_13:results:1:obs4\_tennis\_explanations\_provided: The authors offer theoretical explanations for the observed performance differences, such as RNN&\#x27;s capacity for implicit credit assignment via BPTT and Adam&\#x27;s momentum assisting in overcoming safe strategies, which enhances the understanding of the results\.
  - sec\_13: The RNN has the capacity of sending the signal back to past states with BPTT, allowing it to do credit assignment implicitly, which might explain their ability to escape the bad policy\.
  - sec\_13: It&\#x27;s possible that the updates for model with traces were smaller, due to the weighting of target values, indirectly leading to a lower learning rate\.
  - sec\_13: With Adam, the gradient for the positive TD is stored in the momentum part of the equation for quite some time\. Once in momentum, the gradient is part of many updates, which makes it enough to overtake the safe strategy\.
- b:observation:sec\_13:results:1:obs5\_tennis\_dqn\_variants\_claim: The strong claim that RNN is &\#x27;the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN&\#x27; lacks explicit experimental details or results for all the mentioned DQN variants within this section, diminishing the immediate empirical substantiation of this broad assertion\.
  - sec\_13: Remarkably, this is the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN \(Mnih et al\. \(2015\), Munos et al\. \(2016\), Wang et al\. \(2015\), Mnih et al\. \(2016\), Schaul et al\. \(2015\)\), which tend to get stuck in the policy of delaying\.
- c:criterion:originality: A alegação de novidade aparece de forma pouco específica: o texto aponta uma lacuna geral \(uso de eligibility traces em deep RL “limited so far”\) e afirma ganhos com experimentos, mas não delimita precisamente o que é novo \(p\.ex\., qual formulação/variante, configurações combinadas e diferenças concretas frente ao estado da arte\)\. Além disso, o material fornecido de related work não apresenta claramente uma contribuição própria, dificultando sustentar novidade com evidência textual\.
- c:observation:sec\_2:introduction:1:obs\_3: A contribuição/novidade não é delimitada de modo suficientemente específico em relação ao estado da arte: embora o texto aponte uma lacuna \(“limited so far”\) e anuncie resultados, ele não explicita o que exatamente é novo \(por exemplo, qual formulação/variante de eligibility traces é aplicada em deep RL, em que configurações ou combinações, e o que há de diferente na abordagem dos experimentos\)\.
  - sec\_2: Eligibility traces have been shown empirically to provide faster learning \(Sutton &amp; Barto \(2017\), in preparation\) but their use with deep RL has been limited so far \(van Seijen &amp; Sutton \(2014\), Hausknecht &amp; Stone \(2015\)\)\.
  - sec\_2: We provide experiments in the Atari domain showing that eligibility traces boost the performance of Deep RL\.
  - sec\_2: We also demonstrate a surprisingly strong effect of the optimization method on the performance of the recurrent networks\.
- c:observation:sec\_3:related\_work:1:obs\_4: Não há alegações de novidade/contribuição \(logo não é possível avaliar originalidade com evidência\)\. O texto apenas apresenta conceitos gerais e fórmulas, citando “Sutton &amp; Barto, 1998”, sem diferenciar do conhecimento estabelecido no estado da arte\.
  - sec\_3: Reinforcement learning \(RL\) \(Sutton &amp; Barto, 1998\) is a framework for solving unknown MDPs
  - sec\_3: Monte Carlo \(MC\) and Temporal Difference \(TD\) are two standard methods
  - sec\_3: Q\-learning is an RL algorithm
- c:criterion:substance: O trabalho apresenta experimentos em Atari \(Pong e Tennis\) com comparações diretas entre modelos com e sem eligibility traces e entre otimizadores \(RMSprop/Adam\), além de descrever arquitetura e métricas/epocas\. Contudo, há limitações na profundidade/robustez da evidência para certas alegações: hipóteses causais \(propagação de recompensa; diferenças entre otimizadores\) permanecem especulativas; também há lacunas de desenho/definição operacional em trechos cruciais \(implementação exata de traces/ truncamentos\) e evidência de “estabilidade” baseada mais em descrição qualitativa do que em critérios quantitativos\.
- c:observation:sec\_12:results:1:obs\_1: Há uma comparação experimental direta entre modelos com e sem traces \(X = 0 e x = 0\.8\) sob RMSprop, reportando diferenças em velocidade de aprendizado, estabilidade e ausência de desempenho deprimido\.
  - sec\_12: Figure 2 shows that the model without a trace \(X = 0\) learned at the same rate as DQN, while the model with traces \(X = 0\.8\) learned substantially faster and with more stability, without exhibiting any epochs with depressed performance\.
- c:observation:sec\_12:results:1:obs\_2: A explicação causal \(“probably due to\.\.\. eligibility traces propagating rewards back by many steps in a single update”\) é apresentada como hipótese, mas não é sustentada por evidência quantitativa ou análise observável \(ex\.: medidas do “propagating rewards”/sinal de crédito\)\.
  - sec\_12: This is probably due to the eligibility traces propagating rewards back by many steps in a single update\.
- c:observation:sec\_13:results:1:obs\_4: Afirmações causais e generalizações são feitas sem evidência quantitativa direta na seção \(ex\.: “only algorithm that succeeds”, e explicação por “escape the bad policy” atribuída ao BPTT\), além de dependerem de interpretação visual e de “might”\.
  - sec\_13: Remarkably, this is the only algorithm that succeeds in getting near\-optimal scores on Tennis, out of all variants of DQN \(Mnih et al\. \(2015\), Munos et al\. \(2016\), Wang et al\. \(2015\), Mnih et al\. \(2016\), Schaul et al\. \(2015\)\), which tend to get stuck in the policy of delaying\.
  - sec\_13: The RNN has the capacity of sending the signal back to past states with BPTT, allowing it to do credit assignment implicitly, which might explain their ability to escape the bad policy\.
- c:check:figure\_vs\_text:fig\_vs\_text\_1: figure\_vs\_text: consistent
  - sec\_12: Figure 2 shows that the model without a trace \(X = 0\) learned at the same rate as DQN, while the model with traces \(X = 0\.8\) learned substantially faster and with more stability, without exhibiting any epochs with depressed performance\.
  - sec\_12: Finally, the results in Table 1 show that both using eligibility traces and Adam provide performance improvements\. While training with RMSProp, the model with traces gets to near optimal perfor\- mance more than twice as quickly as the other models\. With Adam, the model learns to be optimal in just 6 epochs\.
  - sec\_13: Figure 3 shows that both RNN models learned to get optimal scores after about 50 epochs\.

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
- Prompt sections/introduction: f9dba0ddf60b6a645f8f26bbc0d2493c669d9a46a163b45e168739cc37e555bf
- Prompt sections/method: bc399c87f9cb4e474ecec5dd99b1034dbe9885660b9af69c902c5a1d46e5fddc
- Prompt sections/related\_work: 2ea6604aedf799b0aca577d09b0061a586c2574324e1570710ee6774127869fd
- Prompt sections/results: 5389e503fa50e5a61b1c4bb10a858911cb5fe81e90d84953b2542ecc27e3139a
- Prompt sections/discussion: 5dd2311d37013e80bba29771733ce044fa987df93b80011fbfd95139abba6837
- Prompt sections/conclusion: c4c502ddea161e91407c1491b62d9a7ccd898f65af92f609463b23499f9122db
- Prompt cross\_checker: 4e8937f51926f97133f3debc15fa90ceb4162ea26650d19865a5b00fb3392102, 9253d720f45eb59a236b59d2623da920cbcdebd03c3af3e085cb827dc0b00dfe, bc40a3c7bfac8d760e7fc43661e10f4b0c5389afb04ad0e7a7722abcce6f85d2
- Prompt synthesizer: 985cc119b5e4342a2142a88af5f5b4ffb7cc379e92d3fe95fee2009320f100f8
- Prompt judge: 6eed71ce2bb679aa55770792f36a17c264f09b5967f821a3b222acc06eae9e3e
- Prompt reviser: 109193cf84b5b8b3aaae29e293ecec291351eb7773c6e2fa8a276f6ba0ab3b1f, 9f6b0de49ba29121d4c6ebd6694dbbde0fc94d54eaa2c64c6ce1ee0bf100c4de, e596ae66ba9f867cc3dd4dae5cc9bdc733115847e1a55b40233d466ad8147d07

## Itens pendentes

- a:observation:sec\_2:introduction:1:sec\_2\_obs\_1
- a:observation:sec\_3:related\_work:1:sec\_3\_obs\_4
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_1
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_2
- a:observation:sec\_7:related\_work:1:sec\_7\_obs\_3
- a:observation:sec\_9:method:1:sec\_9\_obs\_1
- a:observation:sec\_13:discussion:1:sec\_13\_obs\_8
- a:observation:sec\_11:results:1:sec\_11\_obs\_4
- b:observation:sec\_3:related\_work:1:obs\_1
- b:observation:sec\_3:related\_work:1:obs\_2
- b:observation:sec\_4:method:1:sec\_4\_obs\_3
- b:observation:sec\_8:related\_work:1:opt\_clarity\_strength
- b:observation:sec\_10:method:1:arch\_strength\_2
- b:criterion:replicability
- c:observation:sec\_2:introduction:1:obs\_1
- c:observation:sec\_4:method:1:obs\_sec\_4\_3
- c:observation:sec\_5:method:1:obs\_1
- c:observation:sec\_5:method:1:obs\_2
- c:observation:sec\_5:method:1:obs\_3
- c:observation:sec\_5:method:1:obs\_4
- c:observation:sec\_7:related\_work:1:obs\_1
- c:observation:sec\_7:related\_work:1:obs\_2
- c:observation:sec\_7:related\_work:1:obs\_3
- c:observation:sec\_8:related\_work:1:obs\_8\_1
- c:observation:sec\_8:related\_work:1:obs\_8\_2
- c:observation:sec\_8:related\_work:1:obs\_8\_3
- c:observation:sec\_8:related\_work:1:obs\_8\_4
- c:observation:sec\_8:related\_work:1:obs\_8\_5
- c:observation:sec\_9:method:1:obs\_9\_1
- c:observation:sec\_9:method:1:obs\_9\_2
- c:observation:sec\_9:method:1:obs\_9\_3
- c:observation:sec\_9:method:1:obs\_9\_4
- c:observation:sec\_10:method:1:sec\_10\_obs\_1
- c:observation:sec\_10:method:1:sec\_10\_obs\_5
- c:observation:sec\_13:discussion:1:obs\_5
- c:check:claims\_vs\_results:xcheck\_claims\_vs\_results
- c:check:method\_vs\_question:method\_vs\_question

## Avisos

- As faixas de recomendação são provisórias e aguardam calibração\.
