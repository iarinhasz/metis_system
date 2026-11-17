# Amostra de profiling — etapa 2.7

`profiling.json` contém 30 artigos reais da PLOS ONE: 10 de Computação (OpenAlex
field 17), 10 de Física/Astronomia com foco quântico (31) e 10 de Medicina (27).
Os casos intercalam as áreas para que `--limit` preserve alguma diversidade.

Esta é uma amostra de desenvolvimento, com **rótulos provisórios**. Os fields
foram registrados de `primary_topic.field` do OpenAlex em 13/11/2026; são
classificações automáticas de referência, não um gold humano independente.
Os tipos de artigo e papéis das seções foram anotados pelo Codex após leitura
dos títulos e trechos do editor. A revisão por especialistas ainda está pendente.
Essa condição acompanha cada relatório em `annotation_status`.

## Origem e licença

Cada caso registra DOI, autores, ano, id OpenAlex, URL do XML do editor, licença,
declaração de licença e SHA-256 dos bytes do XML consultado. O conteúdo provém
de `https://journals.plos.org/plosone/article/file?id=<DOI>&type=manuscript`.
As licenças CC BY ou CC0 foram conferidas no XML de cada artigo. Alguns artigos
antigos declaram CC BY sem informar a versão; isso está preservado, sem inferir
uma versão. A atribuição está no próprio caso, em `article.authors` e `source`.

As entradas contêm o abstract e os primeiros 1.000 caracteres de parágrafos de
cada seção de primeiro nível do corpo JATS, normalizados em espaço. Não são
extrações completas de PDF e não medem o extractor. Equações e citações podem
perder formatação ao converter XML em texto. Os XMLs integrais não são incluídos.

Fontes primárias: [PLOS — acesso aberto](https://plos.org/open-science/open-access/),
[OpenAlex — topics](https://docs.openalex.org/api-entities/topics) e
[OpenAlex — Work](https://docs.openalex.org/api-entities/works/work-object).

## Seleção

Consultas ao endpoint `https://api.openalex.org/works`, com
`primary_location.source.id:S202381698`, `sort=cited_by_count:desc`:

- Computação: `primary_topic.field.id:17`, primeiros 14 candidatos; selecionados
  os índices 0, 1, 2, 3, 4, 5, 6, 10, 11 e 12 (base zero).
- Física: `primary_topic.field.id:31,title.search:quantum,is_retracted:false`,
  primeiros 25 candidatos; índices 1, 2, 4, 5, 8, 10, 12, 14, 16 e 20.
  Excluíram-se retratação, correção e parte dos estudos de modelos psicológicos
  para obter casos mais próximos de sistemas físicos. Não é amostragem aleatória.
- Medicina: `primary_topic.field.id:27`, `search=randomized trial`, primeiros
  10 candidatos. A busca também retornou revisões e estudos observacionais;
  os rótulos de tipo refletem o desenho descrito, não o termo da busca.

A ordem e os metadados da API podem mudar. Os DOIs e hashes versionados são a
identidade da amostra. Há forte viés de revista, idioma inglês e citações; ela
não representa a produção de cada field nem serve para estimar desempenho geral.

## Convenção dos papéis

Cada seção tem um ou mais papéis compatíveis com o tipo de artigo. Seções
compostas podem ter dois rótulos, como `results` + `discussion`. Nas revisões,
o protocolo de busca recebe `search_protocol` e a integração dos achados recebe
`synthesis`, mesmo quando o título publicado é “Methods” ou “Results”. Em
trabalhos teóricos, `theorems` denota resultados teóricos e `proofs` a derivação.
Abstract e material suplementar recebem `other`. São decisões revisáveis;
casos interdisciplinares devem ter seu field conferido por um curador.

Para revisar, altere os rótulos de forma independente das previsões, incremente
`version` e atualize `annotation_status` e a documentação da revisão. Não altere
um rótulo apenas para fazer coincidir com a resposta de um modelo. O benchmark
separa `article` de `labels`: o LLM recebe título/abstract no profiler e somente
título/trecho na classificação de papéis ambíguos.

## Métricas e baseline

`bench_profiling` usa todo caso selecionado no denominador, inclusive falhas.
O acerto de papéis compara conjuntos, portanto sua ordem não importa. Também
registra precisão, recall e F1 micro dos pares (seção, papel), por área e geral.
Abstract e referências são excluídos dessas métricas; material suplementar é
incluído como `other`, conforme o fluxo atual do E2.

O modo `rules` não chama provedores nem consulta a taxonomia. Usa o **tipo de
referência** para testar a regra de papéis de forma condicional. `field_accuracy`
é `null`: esse modo não classifica fields nem mede o E2 completo. O modo `llm`
executa field, topic e o classificador das seções ambíguas com os mesmos serviços
do E2, usando o tipo previsto. Não resolve Question nem grava Runs/LLMCalls no banco;
o uso fica no relatório através de `MemoryUsageSink`.

`baseline_rules.json` é a primeira medição local, calculada sobre esta amostra.
Seu alvo serve para comparação apenas com a mesma versão, status de revisão e
modo. Ele não é um número de acerto de LLM. Relatórios registram hash do conjunto
validado, hashes do código de classificação, taxonomia, ModelSpec e versões de
prompts efetivamente usados, tokens, custo estimado e chamadas sem preço conhecido.
O custo fica `null` se alguma chamada não tem preço cadastrado.

Relatórios históricos são imutáveis pelo comando: `--output` exige arquivo novo
em diretório existente. O modo padrão é dry-run. Exemplos completos estão em
[questions_and_profiling.md](../../../../docs/questions_and_profiling.md).

## Benchmark A/B dos modos E4 — etapa 3.13

`ab_evaluation_mode` recebe um manifesto com `name`, `version` e casos. Cada
caso referencia um Run de avaliação concluído e pode trazer o veredito humano
`human_decision` (`accepted` ou `rejected`). Notas humanas de 1 a 5 por critério
continuam opcionais e só são necessárias para Spearman/QWK. O exemplo
[`ab_evaluation_mode_manifest.example.json`](ab_evaluation_mode_manifest.example.json)
mostra o formato; substitua o UUID por um Run elegível e use uma amostra
curada, idealmente com 10–20 artigos PeerRead e da equipe. Todos os Runs devem
ter snapshots atuais de E1/E2, a mesma Question e configuração de avaliação, e
os mesmos ModelSpecs.

```sh
uv run python manage.py ab_evaluation_mode caminho/manifesto.json
uv run python manage.py ab_evaluation_mode caminho/manifesto.json --execute
uv run python manage.py ab_evaluation_mode caminho/manifesto.json --report --batch-id UUID
```

O primeiro comando valida e estima o lote sem gravar Runs nem chamar modelos.
`--execute` cria três réplicas para cada caso em cada modo, reutiliza os
snapshots de extração e profiling e inicia o pipeline. Guarde o UUID exibido.
Após todos os Runs terminarem, `--report` produz um artefato novo; informe
`--replicates` se o lote foi criado com quantidade diferente de três. As
métricas mantêm dispersão entre réplicas, diferença média entre avaliadores,
invalidações do juiz, correlação Spearman/QWK com notas humanas, custo e tempo.
Também medem a previsão do veredito: estrita (`accept`) e potencial (`accept` ou
`minor`), com acurácia, acurácia balanceada, precisão, recall, especificidade,
F1 e cobertura. Ausência de recomendação ou sinalização de revisão humana gera
abstenção; a maioria estrita das réplicas decide a previsão do artigo. Correlações
ficam nulas sem notas por critério. A previsão binária mede alinhamento no conjunto
rotulado, não calibração para artigos ou conferências futuras.

### Amostra PeerRead reproduzível

[`peerread_iclr2017_test_candidates.json`](peerread_iclr2017_test_candidates.json)
fixa uma amostra piloto estratificada de 10 artigos (5 aceitos e 5 rejeitados)
do split `test` do ICLR 2017. A seleção é determinística (seed 313) sobre os
15 aceitos e 23 rejeitados identificados nessa revisão do dataset. O catálogo
fixa o commit de origem, o título, o veredito `accepted`, URLs e SHA-256 dos PDFs.
O catálogo serve à previsão binária da 3.13; notas numéricas de parecer podem ser
preparadas separadamente para `bench_reviews`. A amostra pequena serve para
validar o fluxo e comparar modos, não para afirmar desempenho geral ou
significância estatística.

Os PDFs não são versionados aqui. Baixe-os e confira cada hash antes da submissão.
O trecho abaixo salva os arquivos em `/tmp/metis-peerread` e interrompe se algum
byte não corresponder ao catálogo:

```sh
uv run python - <<'PY'
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

catalog = json.loads(Path("projects/correction/evals/data/peerread_iclr2017_test_candidates.json").read_text())
destination = Path("/tmp/metis-peerread")
destination.mkdir(parents=True, exist_ok=True)
reviews_dir = destination / "reviews"
reviews_dir.mkdir(parents=True, exist_ok=True)
for case in catalog["cases"]:
    content = urlopen(case["pdf_url"], timeout=60).read()
    digest = hashlib.sha256(content).hexdigest()
    if digest != case["pdf_sha256"]:
        raise SystemExit(f"SHA-256 divergente para {case['id']}: {digest}")
    (destination / f"{case['peerread_id']}.pdf").write_bytes(content)
    review_json = urlopen(case["decision_url"], timeout=60).read()
    json.loads(review_json)
    (reviews_dir / f"{case['peerread_id']}.json").write_bytes(review_json)
    print(case["id"], digest)
PY
```

Submeta os dez PDFs pelo endpoint normal de artigos (`POST /api/attempts`), com
`external_id` igual ao `source_run_external_id` do catálogo. Rode o fluxo normal
do projeto em cada artigo até obter um Run de avaliação `done`, com snapshots
atuais de E1 e E2. Esta amostra não cria atalhos nem importa resultados antigos:
E1 deve extrair os PDFs atuais e E2 deve produzir o profiling atual. Requisitos
de configuração humana do fluxo (por exemplo, Question ativa) continuam valendo;
não são contornados pelo benchmark.

Depois que os dez Runs de origem estiverem concluídos, gere o manifesto que o
comando A/B já consome:

```sh
uv run python manage.py peerread_ab_manifest
uv run python manage.py peerread_ab_manifest --execute
```

O primeiro comando só valida e não grava. O segundo grava um manifesto novo em
`projects/correction/evals/results/`. O gerador associa cada caso pelo
`external_id` **e** SHA-256 do PDF, exige exatamente um Run de avaliação
concluído por artigo e chama as validações de snapshots, Question, configuração
de avaliação e ModelSpecs do E4. Se houver zero ou mais de um Run compatível, a
geração falha explicitamente para evitar escolher uma execução arbitrária. Use o
caminho gerado nos comandos `ab_evaluation_mode` documentados acima.

Para preparar também as notas numéricas de parecer para `bench_reviews`, passe o
manifesto de Runs e o diretório local dos JSONs de parecer:

```sh
uv run python manage.py peerread_review_manifest caminho/manifesto-runs.json /tmp/metis-peerread/reviews
uv run python manage.py peerread_review_manifest caminho/manifesto-runs.json /tmp/metis-peerread/reviews --execute
```

O preparo confere que as decisões continuam iguais ao catálogo, ignora os textos
de comentários e agrega a mediana inteira por critério, excluindo meta-reviews.
Casos sem nota numérica continuam no manifesto para a medição binária, mas não
entram nas correlações de critério.

O pipeline continua responsável por E1/E2 e pelo módulo de integridade. Nenhum
resultado de `documentos_processados` ou `resultados_extracoes` é tratado como
snapshot atual. A implementação da etapa 3.13 não modifica esses módulos nem o
estágio E3; a execução da amostra fica para a etapa operacional posterior.
