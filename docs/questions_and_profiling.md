# Perfil e Questions (E2)

**Estado de 13/11/2026:** E2, curadoria, catálogo inicial e infraestrutura do
rubric check implementados. A medição disponível é de regras locais, sem LLM;
aprovação especialista das rubricas/rótulos e medição do profiler real continuam
pendentes. [Resultados e metas](status_and_metrics.md).

## O que é uma Question no Metis

Ninguém informa a qual Question um artigo pertence: **o sistema infere a Question pela área do artigo**.

Uma Question é um **perfil de avaliação de uma área**. Ela tem duas partes:
- campos de rubrica (`RubricField`), cujo `rubric_text` traz o contexto do domínio;
- um método de avaliação, com os critérios definidos em código.

## Classificação do artigo

O agente `ArticleProfiler` lê título, abstract e palavras-chave e devolve (`output_schema`):

| Campo | Conteúdo |
|---|---|
| `area_path` | Caminho na taxonomia (domain → field → subfield → topic) |
| `confidence` | Confiança de 0 a 1 |
| `secondary_areas` | Outras áreas plausíveis, para artigos interdisciplinares |
| `paper_type` | `empirical`, `theoretical`, `review`, `methods` ou `case_study` |
| `keywords` | Termos-chave |
| `language` | Idioma identificado do artigo; política de idioma do relatório ainda em Q5 |

A classificação roda em **2 passos**: primeiro o field, depois subfield e topic dentro dele. Cada escolha fica num enum pequeno e fechado, o que reduz erro e impede rótulo inventado.

### Profiler implementado (2.3)

`questions.profiler.profile_article(article, factory=..., taxonomy_version=...)` recebe
o `ExtractedArticle` do E1 e usa somente título, seção `abstract` e palavras-chave
opcionais. Os dois agentes usam o papel `fast`; título e abstract vão no payload
delimitado como dados, fora das instruções. Título ou abstract vazio gera `InvalidSubmission`.

O primeiro schema aceita apenas os fields da versão indicada. Depois da escolha,
`pydantic.create_model` monta o schema com os topics descendentes daquele field,
seus subfields e a relação obrigatória entre eles. Uma combinação de topic e
subfield incoerente é inválida mesmo que os dois códigos existam. Áreas secundárias
são fields da mesma versão e não participam da resolução principal.

A saída `ArticleProfile` traz o caminho completo com códigos e nomes, versão da
taxonomia, tipo do artigo, idioma, palavras-chave, áreas secundárias e as duas
confianças. A confiança final é a menor dos dois passos. O perfil é imutável e
serializa com `model_dump(mode="json")` para `Run.profile["classification"]`.

Cada passo aceita até `METIS_PROFILING_MAX_ATTEMPTS` respostas (padrão: **3**).
Uma resposta inválida provoca outra chamada com os nomes dos campos e os códigos de
erro, sem copiar valores recusados do manuscrito. Esgotado o limite, `InvalidProfile`
é um erro permanente de estágio com status `error_llm`. A indisponibilidade do provedor
continua usando `LLMUnavailable` e o retry do Celery. Cada chamada passa pelo runner
e pelo sink fornecidos à fábrica; não se repete o field quando só o topic é inválido.

A versão é um argumento obrigatório: uma nova carga da taxonomia não altera o
catálogo no meio da classificação. Versão ausente ou field sem topics gera
`SetupRequired`. A etapa 2.5 separa `classify_field()` e `classify_topic()` em passos
do Workflow, com checkpoints independentes no Run; `profile_article()` continua
disponível para chamadas avulsas.

### Workflow e retomada implementados (2.5)

O E2 recebe o id do Run e lê `Run.extraction.article`. A task executa o Workflow
Agno de forma síncrona e só chega a `profiled` depois de persistir a classificação,
a Question, os papéis de todas as seções e o mapa. A transição publica o E3 após
o commit. Falta de taxonomia ou de Question disponível leva a `waiting_setup`.
Depois da configuração, a ação **Reprocessar** no admin retoma os passos pendentes.

`METIS_EVALUATION_METHOD` seleciona o método, com padrão `standard`.
`METIS_PROFILING_TAXONOMY_VERSION` permite escolher uma carga específica; vazio
seleciona a versão carregada mais recentemente. Essa escolha fica fixa no Run
antes da primeira chamada. Também ficam fixos specs, templates, orçamento local
e limiar de confiança. Nenhuma chave de API entra no snapshot.

`Run.profile` guarda `field_choice`, `classification`, `resolution`, `section_roles`
e `document_map`. `complete=True` marca o fim do E2. Cada resposta bem-sucedida
é gravada antes do passo seguinte: uma falha no topic não repete o field, e uma
falha numa seção ambígua não repete outras seções. Toda escrita confere se a task
ainda tem a posse do Run. Os eventos levam apenas ids e metadados de conclusão.

`Run.config_snapshot["question"]` preserva id, versão e textos da rubrica usada.
Runs `rubric_check` recebem esse snapshot de rascunho ao serem criados e dispensam
o fallback por Questions ativas. Runs `ab_test` usam a resolução normal. Os dois
propósitos internos ficam fora das rotas públicas de consulta e decisão, não
substituem a avaliação retornada no reenvio do PDF e não são invalidados por uma
nova submissão de avaliação.

### Rubric check no admin (3.12)

Salve uma Question **inativa**, com ao menos um campo de rubrica preenchido. Na sua
página, use **Rodar rubric check**, ou selecione uma Question na lista e use a ação
de mesmo nome. Selecione de 1 a 20 attempts: a seleção mostra somente PDFs com
extração em cache na versão atual do E1. O teste cria um run interno por attempt;
os arquivos não são reabertos nem enviados novamente ao extrator.

O formulário exige permissão de alterar a Question, criar Run, ver Attempt, ver Run
e ver FinalReport (`questions.change_question`, `attempts.add_run`,
`attempts.view_attempt`, `attempts.view_run`, `evaluation.view_finalreport`). A tela
de resultados exige as permissões de leitura desses dados. As views pertencem ao
admin, exigem autenticação de staff e protegem o POST com CSRF.

O lote congela id, versão, método, campos e textos do rascunho em cada
`Run.config_snapshot["question"]`; também fixa o método de avaliação, a revisão
do rascunho, a versão da extração e um identificador de lote. A criação é atômica
e a publicação das tasks ocorre somente após o commit. Reenviar o mesmo formulário
devolve o lote já criado, sem agendar novas chamadas. Editar o rascunho depois não
muda os snapshots existentes; enviar uma nova amostra exige um novo formulário.

E1 reaproveita a extração ligada ao run; E2 classifica e monta o mapa, usando a
Question congelada sem consultar o fallback por Questions ativas. A passagem de
`profiled` para `integrity_checked` registra um evento com `skipped=true` e motivo
`rubric_check`; não executa E3. O reconciliador usa o mesmo desvio. Avaliações
normais continuam passando pelo E3. E4 e E5 seguem os estágios já configurados.

A página do lote compara os FinalReports lado a lado, com nota, concordância e
texto do relatório. Ela mostra também os estados pendentes e erros de cada run,
sem expor os resultados internos nas rotas públicas. Question ativa, validação,
versão e runs de avaliação anteriores permanecem intactos.

E4 agora produz as rodadas julgadas de A, B e C consumidas pelo E5. O fluxo ainda
depende de credenciais, taxonomia e Question válidas; os testes usam fakes e não
medem a qualidade científica das avaliações geradas por provedores reais.

Para operar: aplique `uv run python manage.py migrate`, carregue a taxonomia e
configure uma Question validada e ativa do método selecionado. Sem essa Question,
o comportamento esperado é `waiting_setup`, preservando a classificação.

## Taxonomia

- **Origem:** a taxonomia do OpenAlex (CC0), em quatro níveis: domain, field, subfield e topic.
- **Carga:** um comando de gestão grava a taxonomia como `TaxonomyNode`. Por padrão ele só mostra o que faria (dry-run); grava com `--execute`.
- **Versão:** fica registrada, e cada Run guarda com qual versão foi classificado.

### Carga implementada (2.1)

```bash
uv run python manage.py migrate
uv run python manage.py load_taxonomy            # confere e mostra a versão, sem gravar
uv run python manage.py load_taxonomy --execute  # grava a árvore numa única transação
```

O cliente fica em `scholarly/openalex.py`. Ele lê `/domains`, `/fields`, `/subfields`
e `/topics`, em páginas de até 100 itens e no máximo uma requisição por segundo.
Ler os quatro endpoints preserva também os subfields que não têm topics associados.
Recusa contagens divergentes, páginas repetidas ou incompletas e parentescos
inconsistentes antes de escrever. Em falha HTTP, encerra sem gravar; basta repetir o
comando. A chave opcional vem de `METIS_OPENALEX_API_KEY`, em `metis/config.py`.

Também é possível carregar sem rede:

```bash
uv run python manage.py load_taxonomy --file /caminho/topics.json
uv run python manage.py load_taxonomy --file /caminho/topics.json --execute
```

Para preservar a árvore inteira, o JSON deve ter as chaves `domains`, `fields`,
`subfields` e `topics`, cada uma com a lista de objetos OpenAlex daquele nível.
Também aceita uma lista de topics com `id`, `display_name`, `domain`, `field` e
`subfield`, útil para recortes de desenvolvimento. Uma resposta da API é aceita se
`meta.count` corresponder a todos os resultados no arquivo; uma página isolada da
coleção é recusada. Listas permitem importar um recorte explícito para desenvolvimento.

`taxonomy_version` é o SHA-256 dos códigos, nomes, níveis e pais normalizados; a ordem
da resposta e os metadados da API não mudam a versão. Repetir a carga preserva os UUIDs.
Conteúdo diferente cria outra versão, sem apagar a árvore anterior nem suas Questions.
O admin oferece busca, filtros por nível e versão e leitura dos pais; criação, edição,
exclusão e ações em lote ficam bloqueadas. A ligação com o Run está implementada na 2.5.

Fontes do contrato: [objeto topic e hierarquia](https://help.openalex.org/data/topics/)
e [paginação do OpenAlex](https://help.openalex.org/api/paging/), conferidas em 12/11/2026.
As respostas gravadas e os testes ficam em `questions/tests/`; o CI usa PostgreSQL real
e não consulta APIs externas.

## Resolução da Question

```text
topic ──▶ subfield ──▶ field ──▶ genérica
  a primeira Question "validated" e "active" encontrada, subindo a árvore
```

- **Confiança abaixo do limiar** → genérica, com a flag "classificação incerta".
- **Nem a genérica disponível** → `waiting_setup`. A equipe configura e reprocessa.
- **O Run grava** `area_path`, confiança, o caminho percorrido e o snapshot da Question (id + versão + textos).

### Resolver implementado (2.3)

`questions.resolver.resolve_question(profile, method=...)` verifica o caminho na
mesma versão da taxonomia e consulta apenas Questions `validated=True`, `active=True`
e do método solicitado. O método é explícito, sem depender do registro de critérios
da etapa 2.2. A cadeia procura topic, subfield, field e genérica; domain não entra
no fallback. Questions de outras versões, métodos ou áreas não são candidatas.

Com confiança abaixo de `METIS_PROFILING_CONFIDENCE_THRESHOLD` (padrão: **0.7**),
vai direto à genérica e marca `uncertain=True`. Confiança igual ao limiar já pode
usar a área. Sem candidata válida, levanta `SetupRequired` (`waiting_setup`).

`ResolvedQuestion` contém a versão da taxonomia, a flag de incerteza, todos os
degraus tentados e um `QuestionSnapshot` imutável. O snapshot leva id, versão, nome,
método, nó de origem e todos os campos da rubrica em ordem, preservando quebras de
linha. `model_dump(mode="json")` produz o conteúdo para o `config_snapshot` do Run.
As consultas ficam nos Managements de `queries/questions/`; as rubricas são
carregadas em lote para não fazer uma consulta por campo.

Exemplo, com nomes ilustrativos: um artigo sobre correção de erros em qubits supercondutores cai num topic de computação quântica. Se esse topic não tem Question própria, o resolver sobe para o subfield e o field de física. Se também não houver Question ali, usa a genérica.

## Papéis das seções e mapa do documento

Depois de resolver a Question, o E2 dá a cada seção do `ExtractedArticle` um
**papel**. A entrada atual é o contrato do E1; `ExtractedDocument` permanece
pendente na 1.1/1.11. No E4 planejado, o papel definirá prompt, checklist e critérios
do passe (ver [Avaliadores e juiz](evaluators_and_judge.md#papéis-e-critérios)).

| `paper_type` | Papéis |
|---|---|
| `empirical`, `methods` | Introdução, trabalhos relacionados, método, resultados, discussão e limitações, conclusão |
| `theoretical` | Introdução, trabalhos relacionados, definições e problema, resultados principais (teoremas), provas, discussão, conclusão |
| `review` | Introdução e escopo, protocolo de busca, seções temáticas, síntese e discussão, conclusão |
| `case_study` | Contexto, descrição do caso, análise, lições, conclusão |

- **Como classifica:** primeiro por regra, com um dicionário de títulos em português e inglês ("Metodologia", "Materiais e métodos", "Methods", "Approach"…). O LLM só decide os títulos ambíguos.
- **Casos especiais:** uma seção pode ter mais de um papel ("Experimentos e resultados"). O que não se encaixa fica como `other` e aparece só no mapa.
- **Mapa do documento:** montado em código, sem LLM, com o abstract, a lista de seções (com papel e primeira frase) e as legendas de figuras e tabelas. Vai em todo passe por seção do E4. Por ser extraído, e não interpretado, pode ser compartilhado pelos 3 avaliadores sem comprometer a independência deles.
- **O Run guarda** os papéis e o mapa junto com o perfil do artigo.

Implementados como dependência do E2 em `section_roles.py` e `document_map.py`.
Os papéis aceitos vêm de `agents/schemas/section_roles.py` e são limitados pelo
`paper_type`. O classificador recebe somente títulos ambíguos e um trecho limitado
da seção como dados. Resposta inválida, confiança baixa ou papel incompatível
vira `other`; indisponibilidade do provedor sobe para o retry do estágio.
Abstract e referências ficam no mapa com `other`, sem chamada de classificação.
O mapa guarda o abstract, títulos, papéis, primeira frase de cada seção e legendas
das figuras e tabelas; não incorpora descrições interpretativas das imagens.

## Estrutura de uma Question

| Campo | Conteúdo |
|---|---|
| `taxonomy_node` | Nó da taxonomia que a Question cobre |
| `method` | Método de avaliação (critérios em código) |
| `rubric_fields` | Campos com `rubric_text`: o contexto do domínio, com quebras de linha preservadas |
| `validated`, `active` | Só Questions validadas e ativas entram na resolução |
| `version` | Incrementa na validação humana; editar remove aprovação e ativação. Runs antigos preservam o snapshot usado |

Exemplo de `rubric_text` (computação quântica):
- modelo de ruído e decoerência: qual, e se é realista para o hardware citado;
- métricas de fidelidade reportadas e como foram medidas;
- resultados em hardware real ou em simulador, e o que isso limita;
- comparação com baseline clássico;
- escalabilidade com o número de qubits.

Na saúde, o `rubric_text` traz as checklists de relato da área: CONSORT para ensaios clínicos, PRISMA para revisões sistemáticas, STROBE para estudos observacionais.

## Critérios em código

Os critérios ficam num `EvaluationConfig` em pydantic congelado, validado no import, com notas discretas (o modelo só pode responder um valor da lista) e peso por critério. O mesmo config diz quais critérios cada papel de seção avalia.

O núcleo vale para todas as áreas e foi semeado pelos aspectos dos reviews do PeerRead:

| Critério | Pergunta central |
|---|---|
| `originality` | O que é novo em relação ao estado da arte? |
| `soundness` | Os métodos e as conclusões se sustentam? |
| `substance` | Há trabalho suficiente: experimentos, provas, análise? |
| `clarity` | O texto é claro e bem organizado? |
| `meaningful_comparison` | Compara com os trabalhos relevantes? |
| `impact` | Qual a relevância para a área? |
| `replicability` | Dá para reproduzir (dados, código, parâmetros)? |

- O `paper_type` liga ou desliga critérios. Por exemplo, `replicability` não se aplica a um artigo teórico.
- A Question não muda os critérios: o `rubric_text` dá a lente do domínio. "Solidez" em quântica inclui o modelo de ruído; em saúde, o desenho do estudo.

### Registro implementado como dependência da curadoria (2.2)

`questions/criteria.py` registra o método `standard` como `EvaluationConfig` congelado.
As sete definições, a escala discreta, os pesos e a cobertura de critérios por papel
são validados no import. As estruturas internas também são tuplas de objetos
congelados. Um critério ativo sem passe, um papel sem critérios, uma nota fora da
escala ou um peso negativo impede a configuração de carregar.

O padrão inicial usa notas de **1 a 5** e pesos uniformes **1**; esses valores são
de desenvolvimento e aguardam a calibração do M3. `replicability` fica inativo em
artigos teóricos. Os demais tipos cobrem os sete critérios; `clarity` participa de
todos os passes. `other` pertence apenas ao mapa e não define um passe de avaliação.

## Curadoria

```text
admin: "rascunhar Question" ──▶ rascunho (validated=False) ──▶ pessoa revisa e edita ──▶ rubric check ──▶ validar
```

- **Rascunho.** O LLM rascunha a partir do conhecimento da área, **nunca a partir de um artigo específico**. Se cada artigo gerasse a própria Question, ele moldaria o critério que vai avaliá-lo, e as notas deixariam de ser comparáveis.
- **Rubric check.** Roda o E4 em artigos de amostra com o rascunho **passado como argumento**. A Question ativa não é tocada: testar não pode mudar o que está em uso.
- **Validação.** Validar incrementa a `version`. Os runs seguintes usam a versão nova, e os antigos ficam com o snapshot.
- **Conjunto inicial (M2):** a genérica + 2–3 áreas (ex.: Computação, Física/Quântica, Saúde). Quem faz a curadoria é uma questão aberta.

### Curadoria implementada (2.6)

No admin, abra **Questions → Rascunhar Question**, selecione o método e o nó da
taxonomia. Deixe o nó vazio para a genérica. A ação de lista **Rascunhar Question**
também cria outra proposta no escopo da única Question selecionada.

`question_drafter()` usa o papel `meta_reviewer` e recebe apenas a árvore da área e
o `EvaluationConfig`; a função não recebe artigo, PDF nem Run. O schema exige uma
rubrica de domínio para cada um dos sete critérios. São permitidas até três
tentativas de saída inválida. Resposta inválida ou indisponibilidade não deixa uma
Question parcial: Question e campos são gravados juntos, após uma resposta válida.
A geração é síncrona; os modelos e as chaves vêm da configuração central.

O rascunho do admin começa em `version=1`, `validated=False`, `active=False`.
Revise os textos na edição da Question, nos campos de rubrica em linha, e então:

1. Selecione a Question na lista e use **Validar**. A versão aumenta e a aprovação
   fica registrada; é necessário pelo menos um campo de rubrica não vazio.
2. Use **Ativar** para disponibilizar a versão aprovada ao resolver.
3. Use **Desativar** para retirar uma Question de uso.

Uma segunda Question aprovada e ativa do mesmo escopo e método é recusada;
desative a anterior antes de ativar a substituta. Editar metadados, adicionar,
alterar ou excluir um campo remove a aprovação e desativa a Question até nova
revisão. Os estados e a versão não são editáveis diretamente pelo formulário.
Uma edição baseada numa página desatualizada é recusada, preservando o trabalho
do outro curador. Operações de aprovação e edição são serializadas por Question.

O resolver trava as Questions candidatas enquanto lê suas rubricas, evitando
misturar metadados aprovados com textos que acabam de ser editados. A configuração
dos Runs já produzidos permanece intacta: a próxima validação muda a versão da
Question, e cada novo Run captura seu próprio snapshot. O histórico de ações do
admin identifica a pessoa que rascunhou, editou, validou ou ativou.

Rascunhar exige a permissão de adicionar Question. Editar, validar e ativar exigem
a permissão de alterar; os campos em linha respeitam suas permissões do Django.
A taxonomia continua somente de leitura. O rubric check da 3.12 já agenda lotes e
compara relatórios no admin. Seus runs passam pelo E4 e continuam sujeitos às
mesmas configurações necessárias de provedores e Question.

### Questions iniciais e benchmark (2.7)

O catálogo `questions/data/initial_questions.json` propõe quatro Questions para o
método `standard`: genérica, Computação (field 17), Física/Astronomia com foco
quântico (31) e Medicina (27). Cada uma contém as sete rubricas de domínio; não
muda a escala, os pesos nem os critérios ativos do método.

Carregue uma versão completa da taxonomia OpenAlex e prepare os rascunhos:

```sh
uv run python manage.py load_taxonomy
uv run python manage.py load_taxonomy --execute
uv run python manage.py seed_questions
uv run python manage.py seed_questions --execute
```

`seed_questions` também aceita `--taxonomy-version HASH` e `--file CAMINHO`.
Sem versão explícita, respeita `METIS_PROFILING_TAXONOMY_VERSION` e depois usa a
última versão carregada. A falta de qualquer field do catálogo aborta a carga
inteira. Ela é atômica e serializada, inclusive quando ainda não existe a Question
genérica. Repetir o comando preserva qualquer Question já existente no mesmo
escopo/método, incluindo rascunhos, nomes e textos editados por pessoas.

As novas Questions começam **não validadas e inativas**. Os textos são propostas
para revisão, não rubricas já aprovadas por especialistas. A pessoa responsável
deve revisar, validar e ativar no admin antes de usar a genérica como fallback
ou as específicas no E2. O comando não aprova conteúdo nem modifica Runs.

O pacote `projects/correction/evals/` inclui uma amostra aberta de 30 artigos
(10 por área), com 152 seções, e o comando `bench_profiling`:

```sh
# Confere a amostra, sem consultar LLM nem escrever relatório.
uv run python manage.py bench_profiling

# Medição local condicional ao tipo de artigo de referência; sem chamadas pagas.
uv run python manage.py bench_profiling --execute --mode rules --output regras.json

# Profiler real: field, topic e LLM nas seções ambíguas. Usa o papel fast.
uv run python manage.py bench_profiling --execute --mode llm --limit 30 --max-attempts 1 --output llm.json
```

O modo LLM precisa da taxonomia carregada e da chave do provedor configurado para
`fast` (`GEMINI_KEY`/`METIS_GOOGLE_API_KEY` ou `METIS_OPENAI_API_KEY`, conforme o
ModelSpec). `--max-attempts` limita respostas inválidas por passo; o retry de
transporte da fábrica continua valendo. Para outra rodada, use um novo arquivo.
As entradas e os rótulos são separados. A medição não depende de uma Question
ativa nem cria Runs: a finalidade é medir a classificação do E2.

A primeira medição real das **regras locais** em 13/11/2026 foi **119/152 (78,29%)**
de acerto exato dos papéis e **F1 micro 0,7885**, sem falhas nem chamadas de LLM.
Computação: 44/61; Física: 34/40; Medicina: 41/51. O field não é medido nesse modo.
O relatório `evals/data/baseline_rules.json` registra os resultados e os hashes.

Na base da 6.1, `bench_profiling --execute` passou a gravar sempre no
[formato compartilhado das evals](evals.md), com destino padrão em
`projects/correction/evals/results/`. `--output` continua escolhendo um arquivo novo.
O relatório preserva a amostra selecionada, os specs, os prompts utilizados e os
contadores de consumo. `compare_evals` aceita também o baseline da 2.7 sem alterá-lo.

Os rótulos são provisórios: fields do OpenAlex e papéis anotados pelo Codex,
ainda sem revisão humana independente. O número é a referência de desenvolvimento
para este conjunto e este modo, não uma estimativa geral ou uma validação do LLM.
Consulte [a origem, as licenças e a convenção de anotação](../projects/correction/evals/data/README.md).
Evals de desempenho ficam fora do CI; os testes regulares conferem o contrato da
amostra, as métricas e a integração com fakes sem fazer chamadas externas.

## Falhas

| Situação | Resultado |
|---|---|
| Provedor de LLM fora | Retry → `error_llm` |
| Saída fora do schema (área que não existe) | O enum fechado recusa. Nova tentativa com o motivo do erro; esgotou → `error_llm` |
| Nenhuma Question disponível, nem a genérica | `waiting_setup` → configurar → "Reprocessar" |
| Título de seção que nenhuma regra reconhece | O LLM decide; se continuar ambíguo, a seção fica `other` e o run segue |
