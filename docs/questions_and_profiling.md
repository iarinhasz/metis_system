# Perfil e Questions (E2)

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
| `language` | Idioma do artigo; também define o idioma do relatório (ver questões abertas) |

A classificação roda em **2 passos**: primeiro o field, depois subfield e topic dentro dele. Cada escolha fica num enum pequeno e fechado, o que reduz erro e impede rótulo inventado.

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
exclusão e ações em lote ficam bloqueadas. A ligação com o Run vem na etapa 2.5.

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

Exemplo, com nomes ilustrativos: um artigo sobre correção de erros em qubits supercondutores cai num topic de computação quântica. Se esse topic não tem Question própria, o resolver sobe para o subfield e o field de física. Se também não houver Question ali, usa a genérica.

## Papéis das seções e mapa do documento

Depois de resolver a Question, o E2 dá a cada seção do `ExtractedDocument` um **papel**. No E4, é o papel que define o prompt, o checklist e os critérios de cada passe por seção (ver [Avaliadores e juiz](evaluators_and_judge.md#papéis-e-critérios)).

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

## Estrutura de uma Question

| Campo | Conteúdo |
|---|---|
| `taxonomy_node` | Nó da taxonomia que a Question cobre |
| `method` | Método de avaliação (critérios em código) |
| `rubric_fields` | Campos com `rubric_text`: o contexto do domínio, com quebras de linha preservadas |
| `validated`, `active` | Só Questions validadas e ativas entram na resolução |
| `version` | Incrementa a cada edição; os runs antigos ficam com o snapshot da versão que usaram |

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

## Curadoria

```text
admin: "rascunhar Question" ──▶ rascunho (validated=False) ──▶ pessoa revisa e edita ──▶ rubric check ──▶ validar
```

- **Rascunho.** O LLM rascunha a partir do conhecimento da área, **nunca a partir de um artigo específico**. Se cada artigo gerasse a própria Question, ele moldaria o critério que vai avaliá-lo, e as notas deixariam de ser comparáveis.
- **Rubric check.** Roda o E4 em artigos de amostra com o rascunho **passado como argumento**. A Question ativa não é tocada: testar não pode mudar o que está em uso.
- **Validação.** Validar incrementa a `version`. Os runs seguintes usam a versão nova, e os antigos ficam com o snapshot.
- **Conjunto inicial (M2):** a genérica + 2–3 áreas (ex.: Computação, Física/Quântica, Saúde). Quem faz a curadoria é uma questão aberta.

## Falhas

| Situação | Resultado |
|---|---|
| Provedor de LLM fora | Retry → `error_llm` |
| Saída fora do schema (área que não existe) | O enum fechado recusa. Nova tentativa com o motivo do erro; esgotou → `error_llm` |
| Nenhuma Question disponível, nem a genérica | `waiting_setup` → configurar → "Reprocessar" |
| Título de seção que nenhuma regra reconhece | O LLM decide; se continuar ambíguo, a seção fica `other` e o run segue |
