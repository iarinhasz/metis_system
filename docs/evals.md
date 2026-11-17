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

## Benchmarks de integridade

Os comandos `bench_plagiarism` e `bench_integrity_phase2` adaptam seus resultados
ao mesmo `EvaluationReport` e usam `output_path`/`write_artifact` para criar
artefatos imutáveis quando `--execute` é informado:

```sh
# Plágio sintético derivado das fixtures locais do PeerRead.
uv run python manage.py bench_plagiarism --execute --limit 5

# Exige JSONL local de referências ou casos de alinhamento normalizados.
uv run python manage.py bench_integrity_phase2 \
  --dataset planted_references --input references.jsonl --execute
uv run python manage.py bench_integrity_phase2 \
  --dataset sciciteval --input sciciteval-normalized.jsonl --execute
uv run python manage.py bench_integrity_phase2 \
  --dataset citation_integrity --input citation-integrity-normalized.jsonl --execute
```

`bench_plagiarism` mede os tipos literal, paráfrase, tradução e negativo; sem
`--with-llm`, paráfrases e traduções não são geradas. Essa opção chama o agente
reescritor e pode gerar custo externo. O comando de Fase 2 chama o agente de
alinhamento para `sciciteval`/`citation_integrity`; `--execute` controla apenas
a gravação do artefato, não a execução do benchmark nem as chamadas do agente.
Ambos imprimem o relatório especializado em stdout sem `--execute`; com a opção,
imprimem o formato `metis.evals` e o caminho do novo arquivo. `--output` escolhe
um destino explícito em diretório existente e recusa sobrescrever arquivos.

Os artefatos registram versão do benchmark (`plagiarism-1` ou
`integrity-phase2-1`), hash e ids do conjunto, parâmetros, métricas e hashes do
código. Quando há chamadas a LLM, incluem `ModelSpec`, hashes dos prompts e
resumo de uso. Os datasets SciCiteVal e Citation Integrity não são baixados pelo
comando: o operador fornece JSONL normalizado e registra a procedência/versão.
Testes com fakes verificam integração e formato, mas não calibram limiares nem
comprovam qualidade científica. Mudanças na definição das métricas ou aplicação
dos rótulos exigem nova `benchmark_version`.

`bench_reviews` e `bench_judge` continuam como integrações futuras do plano.

As execuções de desempenho e com provedores reais ficam fora do CI. Os testes
regulares verificam contratos, histórico, comparação, dry-run e integração com
fakes; não impõem metas de desempenho com base no baseline histórico.
