# Evals offline

A base da etapa 6.1 fica em `projects/correction/evals/`. Ela define o formato dos
relatórios, sua gravação sem sobrescrita e a comparação entre variantes de código,
prompts e modelos. O primeiro consumidor é `bench_profiling`, da etapa 2.7.
O app registra comandos de gestão e não possui models ou tasks de produção.

Os [resultados disponíveis e metas revistas](status_and_metrics.md) identificam
o baseline de regras locais, seu alcance e as medições ainda pendentes. Testes
da infraestrutura de evals com fakes não validam o profiler com provedores reais.

## Executar e guardar uma medição

```sh
# Confere a amostra, sem executar o benchmark nem gravar arquivos.
uv run python manage.py bench_profiling

# Regras locais: cria um JSON novo em projects/correction/evals/results/.
uv run python manage.py bench_profiling --execute --mode rules

# Destino explícito, também sem sobrescrever arquivos existentes.
uv run python manage.py bench_profiling --execute --mode rules --output regras.json

# Profiler com LLM: exige taxonomia, chave do papel fast e consome API.
uv run python manage.py bench_profiling --execute --mode llm --limit 30 --max-attempts 1
```

Sem `--execute`, o comando não cria relatórios nem chama provedores. Com
`--execute`, sempre grava um arquivo novo e informa o caminho e a identificação
da variante. O destino padrão usa data/hora UTC e UUID; os JSONs locais ficam
fora do Git. `--output` exige um arquivo novo em um diretório existente.
Falhas de casos continuam no relatório e no denominador das métricas; o comando
retorna erro depois de salvar a medição parcial.

No modo LLM, o `ModelSpec` de `fast` e os templates ficam fixos a partir da primeira
fábrica. Os hashes de código são capturados antes da medição. As versões de prompt
registradas são os hashes dos prompts renderizados realmente utilizados, agrupados
pelo nome do agente; contextos diferentes podem produzir vários hashes para um nome.
As respostas não recebem os rótulos de referência.

## Contrato compartilhado

`EvaluationReport` usa `format="metis.evals"` e `schema_version=1`. Campos principais:

| Campo | Conteúdo |
|---|---|
| `benchmark`, `benchmark_version` | Tarefa e versão da definição de medição |
| `created_at` | Instante com fuso horário |
| `dataset` | Nome, versão, SHA-256 do conjunto e ids dos casos selecionados, na ordem medida |
| `parameters` | Política da medição, como modo, tentativas, limiar e taxonomia |
| `model_specs` | Snapshot completo por papel, sem credenciais |
| `prompt_versions` | Nome do agente → hashes SHA-256 dos prompts usados |
| `source_sha256` | Hashes dos arquivos de código que identificam a implementação |
| `metrics` | Valor numérico ou nulo, unidade e direção: `higher`, `lower` ou `informational` |
| `failures` | Número de casos com falha |
| `usage` | Chamadas, tokens, custo total, parcela conhecida e chamadas sem preço |
| `details`, `notes` | Detalhes específicos e limitações da medição |

O contrato recusa datas sem fuso, versões de schema desconhecidas, hashes
inválidos, ids de casos repetidos e métricas não finitas. Chamadas de LLM exigem
specs e versões de prompt. Custos usam `Decimal`: se houver chamadas sem preço,
`cost_usd` é nulo e `known_cost_usd` guarda somente a parcela conhecida. Tokens de
cache e raciocínio mantêm os contadores do runner, sem recalcular faturamento.

No profiling, `details` guarda previsões e códigos de erro, sem copiar o manuscrito
ou mensagens do provedor. Os rótulos provisórios da amostra continuam identificados
em `parameters.annotation_status`; a medição local não valida o desempenho do LLM.

## A/B dos modos de avaliação (etapa 3.13)

`ab_evaluation_mode` compara `sectioned` e `whole_document` nos mesmos Runs de
origem e com três réplicas por modo. Comece com um manifesto contendo Runs
concluídos, snapshots E1/E2 atuais e ModelSpecs idênticos. Um exemplo editável
está em
[`ab_evaluation_mode_manifest.example.json`](../projects/correction/evals/data/ab_evaluation_mode_manifest.example.json).

```sh
# Valida a amostra e mostra o tamanho do lote, sem chamadas ou gravações.
uv run python manage.py ab_evaluation_mode manifesto.json

# Cria o lote e enfileira os Runs (pode consumir chamadas de LLM).
uv run python manage.py ab_evaluation_mode manifesto.json --execute

# Após todos os Runs concluírem, grava um relatório novo.
uv run python manage.py ab_evaluation_mode manifesto.json --report --batch-id UUID
```

O manifesto pode incluir `human_decision` (`accepted` ou `rejected`), que permite
medir a previsão de aprovação sem depender de notas humanas por critério. Essas
notas continuam opcionais: Spearman/QWK ficam nulos quando ausentes. A previsão
é reportada em duas leituras: estrita (`accept`) e potencial (`accept` ou
`minor`). Runs sem recomendação ou com `needs_human_review` contam como abstenção;
as réplicas precisam formar maioria estrita para gerar uma previsão por artigo.
O relatório inclui acurácia, acurácia balanceada, precisão, recall, especificidade,
F1 e cobertura, além dos números de acertos/erros/abstenções. As demais métricas
existentes (dispersão, concordância, invalidação do juiz, custo e tempo) são mantidas.
Essas métricas descrevem o conjunto rotulado e não calibram o sistema para outras
conferências; é necessário curar a amostra e registrar a decisão sobre o modo padrão.

A amostra piloto PeerRead, com 10 PDFs identificados por hash e veredito binário,
está em
[`peerread_iclr2017_test_candidates.json`](../projects/correction/evals/data/peerread_iclr2017_test_candidates.json).
Os Runs precisam compartilhar a Question, configuração de avaliação e ModelSpecs.
Depois que o fluxo regular gerar um único Run elegível por artigo,
`manage.py peerread_ab_manifest --execute` monta o manifesto A/B usando o
`external_id` e SHA-256. O README da amostra documenta o download verificado e
o percurso pelos módulos existentes.

## Comparar relatórios

```sh
# Somente leitura: imprime compatibilidade e diferenças de métricas.
uv run python manage.py compare_evals referencia.json candidato.json

# Guarda a comparação em um arquivo novo.
uv run python manage.py compare_evals referencia.json candidato.json --execute --output comparacao.json
```

A leitura expõe três identificações determinísticas: `report_id` identifica todo o
relatório; `variant_id` identifica código, prompts e specs, incluindo parâmetros do
modelo; `comparison_key` identifica tarefa, amostra, política e definições das
métricas. A comparação registra os ids dos dois relatórios e das duas variantes.

Para calcular diferenças, precisam coincidir benchmark e sua versão, dataset e seu
hash, casos na mesma ordem, parâmetros e definições das métricas. Modelos, prompts
e hashes de código podem mudar: são as variantes comparadas. Diferenças incompatíveis
geram uma justificativa, nenhuma diferença numérica e saída de erro. Valores não
medidos continuam nulos. A indicação de melhoria considera a direção da métrica;
empate, ausência de medição e métricas informativas não recebem essa indicação.

O baseline histórico `evals/data/baseline_rules.json`, do formato da 2.7, pode ser
lido diretamente: a adaptação é feita em memória, preservando o arquivo original.
Uma nota identifica as limitações desse formato; metadados ausentes não são
reconstruídos a partir da configuração atual. Quando o legado não guardou a parcela
conhecida de um custo incompleto, ela permanece nula.
Contadores de cache e raciocínio ausentes no legado também ficam nulos.

## Integrar os próximos benchmarks

### `bench_reviews` — notas e previsão de aprovação

O comando `bench_reviews` compara `FinalReport`s existentes com notas humanas
curadas por critério e, quando disponíveis, o veredito `accepted`/`rejected`.
Usa o mesmo formato de manifesto do A/B; o
[`exemplo`](../projects/correction/evals/data/bench_reviews_manifest.example.json)
mostra os rótulos. A comparação de notas inclui Spearman e QWK geral e por
critério; QWK arredonda notas previstas para o inteiro mais próximo, com empate
para cima. A previsão binária estrita (`accept`) e potencial (`accept`/`minor`)
inclui acurácia, precisão, recall, especificidade, F1 e cobertura. Ausência de
recomendação ou pedido de revisão humana é abstenção.

```sh
uv run python manage.py bench_reviews manifesto.json
uv run python manage.py bench_reviews manifesto.json --execute
```

O modo padrão valida e calcula sem gravar; `--execute` grava um relatório novo.
Não chama provedores: lê Runs concluídos e exige a mesma Question, configuração,
modo e ModelSpecs. As notas do manifesto devem ser agregadas e curadas por
artigo antes da comparação. O preparo local acessa somente os campos numéricos
de score dos JSONs PeerRead; comentários não entram nos rótulos nem são enviados
aos provedores.

Para a amostra PeerRead, `peerread_review_manifest` lê arquivos brutos
`<peerread_id>.json`, mantém apenas escores numéricos por critério, exclui
meta-reviews e agrega a mediana inteira por artigo/critério. A mediana `.5` é
arredondada para cima. Os comentários não entram no manifesto resultante.

```sh
uv run python manage.py peerread_review_manifest manifesto_runs.json /tmp/metis-peerread/reviews
uv run python manage.py peerread_review_manifest manifesto_runs.json /tmp/metis-peerread/reviews --execute
uv run python manage.py bench_reviews caminho/manifesto-peerread.json --execute
```

### `bench_judge` — detecção de erros plantados

O comando usa um Run concluído somente para carregar os ModelSpecs e o contexto
de avaliação. Julga um artigo sintético com um controle válido e três erros
plantados: citação inventada, evidência localizada na seção errada e nota que
contradiz as evidências. Exercita os slots A e B para cobrir as duas famílias de
juiz cruzado. Mede recall dos erros, precisão, F1, taxa de falso positivo e
cobertura. As chamadas são reais e exigem as chaves configuradas.

```sh
uv run python manage.py bench_judge UUID_DO_RUN
uv run python manage.py bench_judge UUID_DO_RUN --execute
```

O modo padrão valida a origem e não chama modelos. `--execute` faz até oito
julgamentos sintéticos (podem ocorrer chamadas adicionais para corrigir citações
de saída), guarda o uso e grava um relatório novo. Não cria Runs nem grava dados
no banco. O resultado caracteriza esses cenários controlados, não a precisão do
juiz em manuscritos reais.

`bench_plagiarism` e os benchmarks da Fase 2 ainda dependem dos contratos de
resultado da integridade: a saída integrada do E3 para plágio e a saída de
alinhamento de citações da Fase 2. Esses resultados ainda não estão disponíveis
em `projects/correction/`; os runners devem ser conectados depois que as etapas
4.10 e 5.4–5.5 fornecerem esses contratos. Isso evita criar nesta camada uma
segunda implementação dos detectores ou escolher um formato que conflite com o
módulo de integridade. Cada runner então emitirá um `EvaluationReport` com
amostra, política, versões e métricas próprias, usando `output_path` e
`write_artifact`. Mudanças na definição das métricas ou na aplicação dos rótulos
exigem uma nova `benchmark_version`.

As execuções de desempenho e com provedores reais ficam fora do CI. Os testes
regulares verificam contratos, histórico, comparação, dry-run e integração com
fakes; não impõem metas de desempenho com base no baseline histórico.
