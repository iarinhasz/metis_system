# Arquitetura do Metis

## Visão geral

O Metis recebe o PDF de um artigo científico e devolve um relatório de avaliação. Ele roda num único projeto Django, com workers Celery separados por tipo de trabalho:

```text
          sistema que submete (ou uma pessoa)
                       │ POST /api/attempts (PDF)
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ web: Django + Ninja + admin                                    │
│ API de submissão e status · curadoria de Questions ·           │
│ revisão humana do gate · reprocessamento · auditoria           │
└──────────────┬─────────────────────────────────────────────────┘
               │ grava Article/Attempt/Run e, após o commit,
               │ publica a task do primeiro estágio
               ▼
┌──────────────────────────┐   Redis    ┌──────────────────────────────┐
│ PostgreSQL 18 + pgvector │◀──────────▶│ workers Celery, um por fila  │
│ fonte da verdade         │  (broker)  │ extraction · integrity ·     │
│ (status, saídas, eventos)│            │ evaluation (+ default)       │
└──────────────────────────┘            └──┬──────────┬──────────┬─────┘
               ▲                           │          │          │
               │                           ▼          ▼          ▼
     beat: reconciliador              GROBID e     APIs        provedores
     de runs parados                  Docling      acadêmicas  de LLM
                                      (local)      (Crossref,  (GPT, Gemini)
                                                   OpenAlex,
                                                   S2, arXiv)
```

O pipeline tem cinco estágios, cada um numa task Celery curta:

```text
E1 Extração      texto, referências, citações, figuras descritas, texto oculto  → ExtractedDocument
E2 Perfil        área (taxonomia OpenAlex), tipo de artigo, papéis das seções   → Question + mapa do documento
E3 Integridade   similaridade + citações + texto oculto                         → IntegrityReport → GATE
E4 Avaliação     3 avaliadores por seção + síntese → juiz → revisão (máx. 2)    → rodadas e vereditos
E5 Consolidação  mediana, concordância, meta-review                            → FinalReport
```

O detalhe de cada estágio está nos documentos próprios; o caminho completo de um artigo está em [Fluxo de uma avaliação](evaluation_flow.md).

## Responsabilidades

| Componente | Faz | Não faz |
|---|---|---|
| `web` | Recebe submissões, valida o PDF, responde status, serve o admin | Não chama LLM nem API externa; não processa PDF |
| Admin do Django | Curadoria de Questions, decisão do gate, reprocessamento, leitura da trilha de auditoria | Não edita notas nem saídas dos estágios |
| `worker-extraction` | E1: GROBID, Docling, recorte e descrição das figuras | Trabalho de rede pesado ou longo de LLM |
| `worker-integrity` | E3: busca de candidatos, MinHash, embeddings locais, consultas acadêmicas | Avaliação |
| `worker-evaluation` | E2, E4 e E5 (chamadas de LLM) e a fila `default` (manutenção) | Parse de PDF |
| `beat` | Agenda o reconciliador | Lógica de negócio |
| PostgreSQL + pgvector | Estado dos runs, saídas estruturadas, eventos, vetores do corpus | — |
| Redis | Broker do Celery | Guardar estado de negócio |
| GROBID | Estrutura do artigo, referências e ligação citação ↔ referência | — |

## Celery × Agno

Os dois orquestram, mas em níveis diferentes:

| | Celery | Agno |
|---|---|---|
| Papel | Durabilidade, filas, retries, escala, retomada | Agentes com saída estruturada, `Parallel`, `Loop`, `Condition` |
| Unidade | Um estágio; a mensagem leva só o `run_id` | Os passos dentro de um estágio |
| Estado | Postgres é a fonte da verdade | Só durante a execução; cada passo persiste o que produz |

**Por quê:**
- O Agno 3 não tem execução durável fora do AgentOS: `continue_run` só retoma runs *pausadas*, e reexecutar cria um `run_id` novo. A durabilidade fica com o Celery e com os checkpoints no banco.
- Tasks curtas, uma por estágio, deixam a configuração do Celery simples e o reprocessamento barato: uma falha no E4 não refaz a extração.

O detalhe (ciclo da task, retries, reconciliador) está em [Orquestração](orchestration.md), e o uso do Agno (agentes, workflow de cada estágio, estado, concorrência) em [Agentes e workflows](agents.md).

## Apps e regras de dependência

O código fica em `projects/correction/` (monorepo), e os caminhos abaixo são relativos a essa pasta. Os imports usam o caminho completo (`projects.correction.attempts…`). O `dataset_project/` (PeerRead) fica à parte.

| Módulo | Tipo | Responsabilidade |
|---|---|---|
| `metis/` | projeto Django | settings, URLs, API Ninja, app Celery, `config.py` (único leitor de variáveis de ambiente) |
| `attempts/` | app | `Article`, `Attempt`, `Run`, `RunEvent`, `LLMCall`; máquina de estados; API de submissão e status |
| `questions/` | app | Taxonomia, `Question`, `RubricField`, critérios em código, profiler, resolução da Question |
| `extraction/` | app | E1 e o `ExtractedDocument` |
| `integrity/` | app | E3, relatório, corpus (`SourceDocument`, `SourceChunk`), regras de risco |
| `evaluation/` | app | E4 e E5: contexto, avaliadores, validadores, juiz, rodadas, relatório final |
| `pipeline/` | app sem models | `StageTask`, tasks Celery, publicação, reconciliador, casos de uso que iniciam ou retomam runs |
| `queries/` | pacote | Todo acesso ao banco: uma pasta por app (`queries/attempts/`…) e um Management por model, que o model herda (`Run.claim_stage(...)`) |
| `agents/` | pacote | `ModelSpec`, `ModelFactory`, `AgentFactory`, schemas de saída, prompts, limites de concorrência, registro de uso, fakes |
| `scholarly/` | pacote | Clientes de Crossref, OpenAlex, Semantic Scholar, arXiv e Unpaywall, com rate limit e cache |
| `evals/` | pacote | Comandos de avaliação offline (PeerRead) |

Regras:
- `pipeline` depende dos apps de domínio; os apps de domínio não importam `pipeline`, exceto a API e o admin, que são a borda.
- **`Agent` e modelos do Agno só em `agents/`.** O resto pede agentes à `AgentFactory`, e os testes trocam a fábrica por fakes. O `Workflow` de cada estágio (com `Step`, `Parallel`, `Loop`, `Condition`) é montado no `workflow.py` do app do estágio. `agents/` não importa apps de domínio. Um teste de fronteira de imports garante as três regras (ver [Agentes e workflows](agents.md#fronteiras)).
- **Só `scholarly/` chama APIs acadêmicas.** Rate limit, cache e chaves ficam num lugar só.
- **Só `queries/` fala com o banco.** Fora de `queries/<app>/`, ninguém usa `Model.objects` nem `cursor`: o código chama o método do Management na classe do model (`Run.get_with_events(run_id)`).
- **Só `metis/config.py` lê variáveis de ambiente.** O ruff bloqueia `os.getenv`/`os.environ` fora dele.

## Decisões principais

As decisões e as alternativas descartadas estão em [planning/…/1_desenho_inicial/00_sumario.md](../planning/2026-10_october/1_desenho_inicial/00_sumario.md) (D1–D13) e em [planning/…/1_plano_completo/00_sumario.md](../planning/2026-11_november/1_plano_completo/00_sumario.md) (D14–D21). Em resumo:

| Tema | Decisão |
|---|---|
| Stack | Django 6 + Ninja, Celery + Redis, Postgres 18 + pgvector, Agno 3.x |
| Parsers | GROBID (estrutura e citações) + Docling (figuras, tabelas, fórmulas) + pdfplumber (texto oculto); tudo com licença permissiva |
| Questions | Curadas por área da taxonomia OpenAlex, com fallback até uma Question genérica |
| Avaliadores | 3 slots com mesmo contexto e mesmos critérios: A = GPT, B = Gemini, C = outro modelo de uma das duas famílias, trocável por config. Juiz sempre da outra família |
| Leitura do artigo | Por seção: passes por papel da seção geram observações, checagens entre seções e síntese por critério; o A/B do M3 contra o artigo inteiro confirma |
| Juiz | Verificador com checklist; revisão parcial com direito a réplica |
| Integridade | Regras explícitas decidem o risco; risco alto pausa para revisão humana |
| Embeddings | BGE-M3 local (multilíngue; o manuscrito não sai da infraestrutura) |

## Segurança e confidencialidade

- **O PDF é entrada não confiável.** Há limite de tamanho e de páginas, timeout no parse, e o worker de extração fica isolado.
- **Prompt injection.** O E1 procura texto oculto dirigido a revisores IA. Nos prompts, o artigo vai entre delimitadores, com a regra explícita de que o conteúdo do artigo não é instrução.
- **Manuscritos inéditos.** O texto vai para APIs de LLM: é preciso conferir a política de retenção de cada provedor. Os embeddings rodam localmente, e a telemetria do Agno fica desligada.
- **Arquivos.** Os PDFs e recortes ficam no storage do Django e nunca são servidos por URL pública.
- **Acesso.** A API exige token de serviço e nega por padrão o que não tiver política explícita. O admin usa os usuários do Django.

## Limites conhecidos

- **O sistema recomenda, não decide.** Risco alto de plágio e itens sem consenso vão para uma pessoa.
- **Cobertura da similaridade.** Sem acordo com editoras, a comparação usa o corpus interno, abstracts e textos em acesso aberto. Os textos fechados ficam de fora, e o relatório declara isso.
- **Detecção de texto gerado por IA está fora do escopo**, por ser pouco confiável. Referência inventada e citação desalinhada são sinais objetivos e entram na checagem.
- **Calibração.** O PeerRead cobre só computação, IA e PLN (2013–2017). As outras áreas precisam de dados próprios para calibrar.
