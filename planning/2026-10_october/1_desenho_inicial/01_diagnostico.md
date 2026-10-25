# Diagnóstico: o ponto de partida

## O repositório hoje

Só `dataset_project/`, com o loader do PeerRead para a biblioteca `datasets` do Hugging Face (`peer_read.py`, `dataset_infos.json`, README, `gitattributes`). Ainda não há commits.

## Padrões adotados

- **Vocabulário:** attempt (versão submetida), question (perfil de avaliação de uma área), campos de rubrica com texto de contexto.
- **Critérios em código**, num config pydantic congelado e validado no import, com notas discretas (o modelo só pode escolher valores de uma lista).
- **Estágios com checkpoint no banco**, com claim atômico; a mensagem da task leva só o id.
- **Publicação de task só após o commit**, com um reconciliador periódico para o que ficou para trás.
- **Categorias explícitas de erro:** passageiro (com retry), permanente, erro de quem submeteu, falta de configuração.
- **Log de eventos append-only**, sem duplicatas.
- **Prompts com marcadores `<<nome>>`**, em que um marcador que sobra é erro.
- **Registro de tokens e custo** por chamada de LLM.
- **Fakes de LLM** que respondem conforme o schema de saída, inclusive com respostas inválidas.
- **API com token de serviço** e bloqueio por padrão.
- **Imagem Docker** com uv, usuário não-root e checagem de `.env` vazado.

## Princípios de desenho

| Problema a evitar | No Metis |
|---|---|
| Artigo inteiro e todos os critérios numa chamada diluem a atenção do modelo: justificativas genéricas, "faltou" que não faltou, nota instável | Passes por seção + checagens entre seções + síntese por critério, com o juiz vendo o artigo inteiro; o A/B do M3 confirma (D13) |
| Task longa com todos os estágios exige limites de horas e muito código próprio de lease e retry | Uma task curta por estágio, com as opções nativas do Celery |
| Status cujo significado depende do nome guardado no banco é difícil de manter | Enum + tabela de transições em código |
| Reavaliar criando uma attempt auxiliar espalha casos especiais pelo código | Um novo `Run` na mesma attempt |
| Testar um rascunho de rubrica não pode alterar a question em uso | O rubric check recebe o rascunho como argumento |
| Pedir de novo ao LLM sem dizer o erro tende a repetir o erro | Toda nova tentativa leva o motivo (validador ou juiz) |
| LLM perguntado sobre layout "imagina" estrutura | Estrutura vem de parser; o LLM só descreve o visual |
| Limiar de similaridade fixo no código não acompanha a calibração | Limiares configuráveis, testados e calibrados |
| Configuração lida de vários lugares diverge | `metis/config.py` como único leitor, com regra no ruff |
| Feedback guardado como texto formatado precisa ser parseado de volta | Saídas estruturadas em JSON |
| Responder erro a um reenvio idempotente gera loop de retry no cliente | Reenvio idêntico → 200 com a attempt existente |

## O PeerRead (`dataset_project/`)

- **O que é:** um dataset de reviews de artigos (Kang et al., NAACL 2018; https://github.com/allenai/PeerRead). Tem mais de 14 mil rascunhos de artigos de ACL, NIPS, ICLR e seções do arXiv, com decisões de aceite e mais de 10 mil reviews.
- **Configuração `parsed_pdfs`:** artigos já parseados (science-parse), com seções, referências e `referenceMentions` (citação → referência, com contexto e offsets). Divisão: 11.090 treino, 637 teste e 637 validação.
- **Configuração `reviews`:** reviews com notas por aspecto (`originality`, `soundness_correctness`, `substance`, `clarity`, `meaningful_comparison`, `impact`, `replicability`, `appropriateness`, `recommendation`, `reviewer_confidence`).
- **Download:** ~1,2 GB (o zip do repositório no GitHub).
- **Problema:** o `peer_read.py` é um *script* de dataset, e o `datasets` a partir da versão 4 não executa mais scripts. O caminho é um comando `load_peerread` que lê os JSONs do zip direto; o script já documenta o schema.

Usos no Metis:
1. Semente do corpus interno da similaridade.
2. Calibração das notas: aspectos dos reviews humanos vs. critérios do Metis.
3. Conjunto do A/B do modo de avaliação (D13).
4. Gabarito da ligação citação ↔ referência do GROBID (`referenceMentions`).
5. Base para plágio sintético: trechos literais, parafraseados e traduzidos para PT.
6. Base para erros plantados nas saídas dos avaliadores, para testar o juiz.

Limites:
- Só computação, IA e PLN; nada de física ou saúde.
- Artigos de 2013–2017, que os LLMs provavelmente já viram (contaminação).

## Pesquisa de ferramentas (25/10/2026)

**Agno** (https://docs.agno.com/)
- **Versão:** a atual é a 3.1.10; a 3.0 saiu em 24/08/2026. Fixar `agno>=3.1,<4`.
- **API de workflow:** `Workflow` (construtor só com argumentos nomeados), `Step`, `Steps`, `Parallel`, `Loop(max_iterations, end_condition)`, `Condition`, `StepInput`, `StepOutput`. `output_schema` substituiu o `response_model` da 1.x.
- **Sem execução durável fora do AgentOS:** `continue_run` só retoma runs pausadas, e o `background=True` morre com o event loop.
- **Retries:** o `Step` tem `max_retries=3` por padrão, sem backoff. Os modelos têm `retries` + `exponential_backoff`, só para 429/5xx.
- **`Parallel`:** um thread por ramo, sem limite de concorrência. O `session_state` é compartilhado entre os ramos.
- **Ferramentas prontas:** não há para Crossref, OpenAlex ou Semantic Scholar. Os clientes ficam no nosso pacote `scholarly/`.

**PDF**
- **GROBID 0.9.1** (Apache-2.0): o único que liga cada citação do texto à referência. Imagem `grobid/grobid:0.9.1-crf` (~500 MB, CPU) ou `-full` (~8 GB, GPU recomendada).
- **Docling** (MIT): detecção de layout na página renderizada (acha gráficos vetoriais), 26 classes de figura, TableFormer, fórmulas em LaTeX.
- **PyMuPDF 2.0:** AGPL; descartado.

**APIs acadêmicas** (preços e limites mudam):

| API | O que mudou ou importa |
|---|---|
| Crossref | Limites desde 1/12/2025: no pool *polite*, consultas a 3 req/s e 3 simultâneas; retratações com fonte Retraction Watch |
| OpenAlex | Chave obrigatória desde 13/02/2026. Consulta por DOI grátis; busca US$ 1 por mil; a chave grátis dá US$ 1/dia (https://help.openalex.org/access/pricing/) |
| Semantic Scholar | Chave dá 1 req/s; exige atribuição e proíbe revenda |
| arXiv | 1 requisição a cada 3 s |

**Similaridade**
- **`datasketch` 2.0** (MIT) para MinHash-LSH.
- **BGE-M3** (MIT, multilíngue, 8 mil tokens) para cópia traduzida.
- **SPECTER2** só funciona em inglês.
- Não existe benchmark público PT↔EN para modelos atuais; calibrar com abstracts bilíngues do SciELO.

**Referências inventadas e alinhamento de citação**
- `RefChecker` e `halref` (MIT): verificação em cascata em várias bases.
- SciCiteVal e Citation Integrity: datasets para medir o alinhamento.

**Avaliação por partes**
- MARG (*Multi-Agent Review Generation for Scientific Papers*, 2024) divide o artigo entre agentes e relata comentários menos genéricos. Leitura recomendada antes do M3.
