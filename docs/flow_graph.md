# Grafo do fluxo: entidades e ligações

O fluxo do Metis em grafos: quais entidades existem, como elas se ligam, qual estágio grava e lê cada uma, e o que acontece dentro de cada estágio. Os diagramas são Mermaid: o GitHub os desenha direto, e o VS Code também, com uma extensão de preview de Mermaid.

O detalhe de cada peça está nos documentos próprios: [Modelos de dados](data_models.md), [Orquestração](orchestration.md) e [Agentes e workflows](agents.md).

## Como ler os diagramas

Cada caixa mostra o nome em português na primeira linha e, embaixo, o identificador usado no código (model, passo, agente ou status), que fica em inglês.

| Forma | Significa |
|---|---|
| Cilindro | Entidade: uma tabela no Postgres |
| Retângulo | Passo: código, ou um passo de workflow |
| Hexágono | Agente (chamada de LLM pela `AgentFactory`) |
| Losango | Decisão |
| Pílula (cantos redondos) | Status do Run ao fim do passo |
| Paralelogramo | Serviço externo |
| Seta cheia (`-->`) | Sequência |
| Seta grossa (`==>`) | Grava |
| Linha pontilhada (`-.-`) | Lê ou usa |

## 1. As entidades

| Entidade (código) | Em português | App | O que é | Quem grava | Quem lê |
|---|---|---|---|---|---|
| `Article` | Artigo | `attempts` | O trabalho científico, pelo `external_id` de quem submete | API de submissão | Todos, pela `Attempt` |
| `Attempt` | Versão | `attempts` | Uma versão enviada do artigo (um PDF, com sha256) | API de submissão | E1 |
| `Run` | Execução | `attempts` | Uma execução do pipeline sobre uma versão; o status, o perfil e o snapshot da configuração | API (cria); `RunManagement` (status); E2 (perfil e Question) | Todos os estágios |
| `RunEvent` | Evento da execução | `attempts` | Trilha de auditoria: cada transição, retry, republicação e decisão humana | `RunManagement`, sempre | Admin, API de status |
| `LLMCall` | Chamada de LLM | `attempts` | Uma chamada de modelo, com tokens e custo | `UsageSink` do pipeline, em todo estágio com agente | Admin (custo), evals |
| `ExtractedDocument` | Documento extraído | `extraction` | O artigo estruturado: seções, referências, citações, figuras, tabelas, texto oculto. Compartilhado entre execuções (sha256 + versões dos parsers) | E1 | E2, E3, E4 |
| `Figure` | Figura | `extraction` | Recorte de uma figura, com a descrição | E1 | E4 |
| `TaxonomyNode` | Nó da taxonomia | `questions` | Um nó da taxonomia OpenAlex (domínio → campo → subcampo → tópico) | Comando `load_taxonomy` | E2 |
| `Question` | Question (perfil de avaliação) | `questions` | O perfil de avaliação de uma área | Curadoria no admin | E2 (resolve), E4 (snapshot) |
| `RubricField` | Campo da rubrica | `questions` | Um campo da rubrica da Question, com o `rubric_text` do domínio | Curadoria no admin | E4 |
| `IntegrityReport` | Relatório de integridade | `integrity` | Nível de risco, `coverage` e narrativa | E3 | Gate, E4 (resumo), E5 |
| `IntegrityFinding` | Achado de integridade | `integrity` | Um achado (similaridade, citação, texto oculto), com evidência | E3 | Gate, E5 |
| `SourceDocument` | Obra do corpus | `integrity` | Uma obra do corpus da similaridade (interna ou externa) | E3, `load_peerread` | E3 |
| `SourceChunk` | Trecho do corpus | `integrity` | Um trecho de uma obra, com o vetor do BGE-M3 | E3, `load_peerread` | E3 |
| `ReviewRound` | Rodada de revisão | `evaluation` | O estado da revisão de um avaliador numa rodada (observações, checagens, sínteses) | E4 | E4 (juiz, revisão), E5 |
| `JudgeVerdict` | Veredito | `evaluation` | O veredito de um validador ou do juiz sobre um item | E4 | E4 (loop), E5 |
| `FinalReport` | Relatório final | `evaluation` | O relatório final estruturado | E5 | API (`/report`), admin |

## 2. Como as entidades se ligam

```mermaid
erDiagram
    Article ||--o{ Attempt : "tem versões"
    Attempt ||--o{ Run : "é avaliada por"
    Run ||--o{ RunEvent : "registra"
    Run ||--o{ LLMCall : "custa"
    ExtractedDocument |o--o{ Run : "é usado por"
    ExtractedDocument ||--o{ Figure : "contém"
    TaxonomyNode |o--o{ TaxonomyNode : "é pai de"
    TaxonomyNode |o--o{ Question : "é coberto por"
    Question ||--o{ RubricField : "tem"
    Question |o--o{ Run : "é resolvida para"
    Run ||--o| IntegrityReport : "tem (E3)"
    IntegrityReport ||--o{ IntegrityFinding : "reúne"
    IntegrityFinding }o..o| SourceDocument : "aponta para"
    SourceDocument ||--o{ SourceChunk : "é dividido em"
    Attempt |o..o| SourceDocument : "entra no corpus como"
    Run ||--o{ ReviewRound : "tem (E4)"
    ReviewRound ||--o{ JudgeVerdict : "é verificada por"
    Run ||--o| FinalReport : "tem (E5)"

    Article {
        text external_id UK "id no sistema que submete"
        text title "título"
    }
    Attempt {
        int attempt_number "número da versão"
        text sha256 "hash do PDF"
        file file "o PDF"
    }
    Run {
        enum status "status atual"
        enum stage "estágio atual"
        enum purpose "avaliação, rubric check ou A/B"
        json profile "perfil do E2"
        json config_snapshot "modelos, prompts, Question"
    }
    ExtractedDocument {
        text sha256 "hash do PDF"
        json parser_versions "versões dos parsers"
        json content "o documento estruturado"
    }
    Question {
        bool is_generic "é a genérica"
        bool validated "validada"
        bool active "ativa"
        int version "versão"
    }
    IntegrityReport {
        enum risk_level "nível de risco"
        json coverage "o que foi checado"
    }
    ReviewRound {
        text evaluator_slot "avaliador A, B ou C"
        int round_number "rodada"
        enum mode "por seção ou artigo inteiro"
    }
    JudgeVerdict {
        enum item_type "observação, checagem ou critério"
        text item_key "id do item"
        enum verdict "válido ou inválido"
        enum source "validador ou juiz"
    }
    FinalReport {
        enum recommendation "recomendação"
        float total_score "nota total"
        json content "relatório completo"
    }
```

**Como ler**
- **Um artigo tem várias versões** (`Attempt`), e cada versão pode ter várias execuções (`Run`): a avaliação normal, uma reavaliação com outra configuração, um rubric check ou um A/B (`Run.purpose`).
- **A execução é o centro:** tudo o que um estágio produz pendura nela, exceto o documento extraído, que é compartilhado entre execuções do mesmo PDF.
- **A Question não pertence à execução.** A execução aponta para ela e guarda um snapshot no `config_snapshot`, para continuar reproduzível quando a Question mudar de versão.
- **Linhas tracejadas** são referência por valor (DOI, URL), não chave estrangeira.

## 3. O fluxo: estágios e o que cada um grava e lê

### A sequência

```mermaid
flowchart LR
    SUB["Submissão<br/>POST /api/attempts"] --> E1["E1 Extração<br/>extraction"]
    E1 --> E2["E2 Perfil<br/>profiling"]
    E2 --> E3["E3 Integridade<br/>integrity"]
    E3 --> G{"risco<br/>alto?"}
    G -->|"não"| E4["E4 Avaliação<br/>evaluation"]
    G -->|"sim"| H{"Revisão humana<br/>no admin"}
    H -->|"continuar"| E4
    H -->|"encerrar"| CL(["Encerrado pelo revisor<br/>closed_by_reviewer"])
    E4 --> E5["E5 Consolidação<br/>consolidation"]
    E5 --> D(["Concluído<br/>done"])
```

Cada estágio (E1–E5) é uma task Celery que executa um Workflow Agno. Entre dois estágios, a execução fica parada num checkpoint no banco (`extracted`, `profiled`…), e é dali que ela retoma depois de uma falha.

### O que cada estágio cria

Cada faixa é um momento do fluxo, de cima para baixo, com as entidades que ele cria.

```mermaid
flowchart TB
    subgraph PRE["Antes do fluxo: admin e comandos"]
        direction LR
        TAX[("Taxonomia<br/>TaxonomyNode")]
        QST[("Question e rubrica<br/>Question + RubricField")]
        SEED[("Corpus inicial (PeerRead)<br/>SourceDocument + SourceChunk")]
        TAX ~~~ QST ~~~ SEED
    end
    subgraph SUB["Submissão (API)"]
        direction LR
        ART[("Artigo<br/>Article")]
        ATT[("Versão<br/>Attempt")]
        RUN[("Execução<br/>Run")]
        ART ~~~ ATT ~~~ RUN
    end
    subgraph E1["E1 Extração"]
        direction LR
        ED[("Documento extraído<br/>ExtractedDocument")]
        FIG[("Figura<br/>Figure")]
        ED ~~~ FIG
    end
    subgraph E2["E2 Perfil"]
        direction LR
        PRF[("Perfil e Question na execução<br/>Run.profile · Run.question")]
    end
    subgraph E3["E3 Integridade"]
        direction LR
        IR[("Relatório de integridade<br/>IntegrityReport + IntegrityFinding")]
        SRC[("Corpus ampliado<br/>SourceDocument + SourceChunk")]
        IR ~~~ SRC
    end
    subgraph E4["E4 Avaliação"]
        direction LR
        RR[("Rodada de revisão<br/>ReviewRound")]
        JV[("Veredito<br/>JudgeVerdict")]
        RR ~~~ JV
    end
    subgraph E5["E5 Consolidação"]
        direction LR
        FR[("Relatório final<br/>FinalReport")]
    end
    PRE --> SUB --> E1 --> E2 --> E3 --> E4 --> E5
```

Em todo estágio, a mudança de status gera um evento (`RunEvent`) e cada chamada de modelo gera uma chamada de LLM (`LLMCall`).

### Quem lê e quem grava cada entidade

"Status" quer dizer que o estágio só muda o status da execução, pelo `RunManagement`.

| Entidade | Submissão | E1 | E2 | E3 | E4 | E5 | Admin e comandos |
|---|---|---|---|---|---|---|---|
| Artigo (`Article`) | grava | — | — | — | — | — | — |
| Versão (`Attempt`) | grava | lê | — | — | — | — | — |
| Execução (`Run`) | grava | status | lê e grava (perfil) | status | lê (perfil) | status | grava (gate, reprocessar) |
| Evento (`RunEvent`) | grava | grava | grava | grava | grava | grava | grava (decisões) |
| Chamada de LLM (`LLMCall`) | — | grava | grava | grava | grava | grava | grava (rascunho de Question) |
| Documento extraído (`ExtractedDocument`) | — | grava | lê | lê | lê | — | — |
| Figura (`Figure`) | — | grava | — | — | lê | — | — |
| Taxonomia (`TaxonomyNode`) | — | — | lê | — | — | — | grava |
| Question e rubrica (`Question`, `RubricField`) | — | — | lê | — | lê | — | grava |
| Corpus (`SourceDocument`, `SourceChunk`) | — | — | — | lê e grava | — | — | grava (semente) |
| Relatório de integridade (`IntegrityReport`, `IntegrityFinding`) | — | — | — | grava | lê (resumo) | lê | lê (gate) |
| Rodada de revisão (`ReviewRound`) | — | — | — | — | lê e grava | lê | — |
| Veredito (`JudgeVerdict`) | — | — | — | — | lê e grava | lê | — |
| Relatório final (`FinalReport`) | — | — | — | — | — | grava | lê |

- O E2 grava na própria execução: o perfil (área, tipo de artigo, papéis das seções, mapa do documento), a Question resolvida e o `config_snapshot`.
- O E3 lê o corpus e também o amplia: cada versão nova e cada fonte em acesso aberto viram uma obra do corpus.
- O admin e os comandos (`load_taxonomy`, curadoria, `load_peerread`) preparam o que os estágios leem.

## 4. Dentro de cada estágio

### Celery por fora, Agno por dentro

```mermaid
flowchart LR
    T["Task Celery<br/>fila, retry, posse"] --> ST["Base dos estágios<br/>StageTask: claim → execute → complete"]
    ST --> WF["Workflow Agno do estágio<br/>app/workflow.py"]
    WF --> STP["Passos do workflow<br/>Step · Parallel · Loop · Condition"]
    STP --> EX["Executor<br/>classe do app"]
    EX --> CODE["Código puro<br/>parser, regra, agregação"]
    EX --> AF["Fábrica de agentes<br/>AgentFactory em agents/"]
    AF --> AG{{"Agente<br/>Agent"}}
    AG --> PROV[/"Provedores de LLM<br/>OpenAI · Gemini"/]
    EX ==> DB[("Banco<br/>Postgres")]
    ST ==> DB
```

A base dos estágios muda o status da execução; os executors gravam as saídas. Num retry, o workflow roda de novo, e cada passo pula o que já está no banco.

### E1 — Extração

```mermaid
flowchart TD
    ATT[("Versão (PDF)<br/>Attempt")] --> CACHE{"Já existe extração para<br/>sha256 + versões dos parsers?"}
    CACHE -->|"sim"| LINK["Liga a extração à execução"]
    CACHE -->|"não"| PARSE
    subgraph PARSE["Em paralelo: leitura do PDF (Parallel)"]
        direction LR
        GRO["Estrutura e citações<br/>grobid"]
        DOC["Figuras, tabelas, fórmulas<br/>docling"]
        HID["Texto oculto<br/>hidden_text"]
    end
    GROBID[/"Serviço GROBID"/] -.- GRO
    PARSE --> MERGE["Junta GROBID e Docling por posição<br/>merge_by_bbox"]
    MERGE --> QG{"Tem texto, abstract e referências?<br/>quality_gate"}
    QG -->|"não"| REJ(["Rejeitado<br/>rejected_invalid_submission"])
    QG -->|"sim"| DESC["Descreve as figuras<br/>describe_figures"]
    AGF{{"Descritor de figuras<br/>figure_describer"}} -.- DESC
    DESC --> BUILD["Monta e grava<br/>build_and_persist"]
    BUILD ==> ED[("Documento extraído<br/>ExtractedDocument")]
    BUILD ==> FIG[("Figura<br/>Figure")]
    BUILD --> OK(["Extraído<br/>extracted"])
    LINK --> OK
```

### E2 — Perfil

```mermaid
flowchart TD
    ED[("Documento extraído<br/>ExtractedDocument")] -.- CF
    TAX[("Taxonomia<br/>TaxonomyNode")] -.- CF
    CF["Classifica o campo<br/>classify_field"] --> CT["Classifica subcampo e tópico,<br/>só entre os filhos do campo<br/>classify_topic"]
    AGP{{"Classificador de área<br/>profiler_field · profiler_topic"}} -.- CF
    AGP -.- CT
    CT --> RQ["Escolhe a Question: tópico → subcampo<br/>→ campo → genérica<br/>resolve_question"]
    QST[("Question e rubrica<br/>Question + RubricField")] -.- RQ
    RQ -->|"nenhuma Question"| WS(["Aguardando configuração<br/>waiting_setup"])
    RQ --> RL["Papéis das seções por regra PT/EN<br/>section_roles"]
    RL --> AMB{"Há títulos<br/>ambíguos?"}
    AMB -->|"sim"| CR["Classifica os ambíguos<br/>classify_roles"]
    AGR{{"Classificador de papéis<br/>section_role_classifier"}} -.- CR
    CR --> MAP
    AMB -->|"não"| MAP["Monta o mapa do documento, em código<br/>document_map"]
    MAP --> PER["Grava o perfil<br/>persist"]
    PER ==> RUN[("Execução: perfil, Question, snapshot<br/>Run.profile · question · config_snapshot")]
    PER --> OK(["Perfil pronto<br/>profiled"])
```

### E3 — Integridade

Até o M3, o E3 é um passo só (*pass-through*). A forma final, com as duas fases:

```mermaid
flowchart TD
    ED[("Documento extraído<br/>ExtractedDocument")] -.- HT
    HT["Fase 0: texto oculto<br/>hidden_text"] --> RR["Resolve as referências<br/>resolve_references"]
    SCH[/"APIs acadêmicas<br/>Crossref · OpenAlex · S2 · arXiv"/] -.- RR
    RR --> PH
    subgraph PH["Em paralelo: as duas fases (Parallel)"]
        direction LR
        subgraph F1["Fase 1: similaridade (M4)"]
            direction TB
            C1["Busca candidatos<br/>candidates"] --> L1["Cópia literal<br/>lexical"] --> S1["Paráfrase e tradução<br/>semantic"] --> CI["Confere se a fonte foi citada<br/>citation_filter"] --> AD["Julga os pares suspeitos<br/>adjudicate"]
        end
        subgraph F2["Fase 2: citações (M5)"]
            direction TB
            EX["A referência existe?<br/>existence"] --> RT["Foi retratada?<br/>retraction"] --> CO["Citações e lista batem?<br/>consistency"] --> AL["A fonte sustenta a frase?<br/>alignment"]
        end
    end
    SRC[("Corpus<br/>SourceDocument + SourceChunk")] -.- S1
    AGA{{"Juiz de plágio<br/>plagiarism_adjudicator"}} -.- AD
    AGE{{"Juiz de referências<br/>reference_adjudicator"}} -.- EX
    AGC{{"Juiz de alinhamento<br/>citation_alignment_judge"}} -.- AL
    PH --> XP["Cruza as fases<br/>cross_phases"]
    XP --> RU["Regras decidem o nível de risco<br/>risk_rules"]
    RU --> NA["Redige a narrativa<br/>narrative"]
    AGN{{"Narrador<br/>integrity_narrator"}} -.- NA
    NA --> PE["Grava o relatório<br/>persist"]
    PE ==> IR[("Relatório de integridade<br/>IntegrityReport + IntegrityFinding")]
    PE --> RK{"Risco<br/>alto?"}
    RK -->|"não"| OK(["Integridade ok<br/>integrity_checked"])
    RK -->|"sim"| WH(["Aguardando revisão humana<br/>waiting_human_review"])
```

### E4 — Avaliação

```mermaid
flowchart TD
    IN[("Documento extraído · perfil<br/>Question · relatório de integridade")] -.- CTX
    CTX["Monta o contexto<br/>EvaluationContextBuilder"] --> EV
    subgraph EV["Em paralelo: avaliadores independentes (Parallel)"]
        direction LR
        A["Avaliador A: GPT<br/>seções → checagens → síntese"]
        B["Avaliador B: Gemini<br/>seções → checagens → síntese"]
        C["Avaliador C: 2º modelo<br/>seções → checagens → síntese"]
    end
    AGS{{"Avaliador por seção, checador, sintetizador<br/>section_reviewer · cross_checker · synthesizer"}} -.- EV
    EV ==> R1[("Rodada de revisão 1<br/>ReviewRound")]
    EV --> V1["Validadores em código<br/>validate"]
    V1 --> J1["Juiz da rodada 1<br/>judge"]
    AGJ{{"Juiz da outra família<br/>judge"}} -.- J1
    J1 ==> JV[("Veredito<br/>JudgeVerdict")]
    J1 --> PD{"Há item<br/>inválido?"}
    PD -->|"não"| MU["Marca o que ficou sem consenso<br/>mark_unresolved"]
    PD -->|"sim"| LP
    subgraph LP["Repetição: no máximo 2 revisões (Loop)"]
        direction LR
        RV["Revisa só os inválidos<br/>revise"] --> V["Valida<br/>validate"] --> J["Julga<br/>judge"]
        J -.->|"ainda inválido"| RV
    end
    AGR{{"Revisor: corrige ou defende<br/>reviser: accept ou rebut"}} -.- RV
    LP ==> RN[("Rodada de revisão n+1<br/>ReviewRound")]
    LP --> MU
    MU --> OK(["Avaliado<br/>evaluated"])
```

- O juiz é sempre da outra família: o GPT julga o Gemini, e o Gemini julga o GPT.
- Cada volta da repetição termina no juiz, então a última revisão também é verificada. O que continuar inválido fica sem consenso (`unresolved`) e sai da nota.

### E5 — Consolidação

```mermaid
flowchart TD
    IN[("Rodadas · vereditos<br/>relatório de integridade")] -.- AGG
    AGG["Agrega as notas: mediana, dispersão,<br/>total e recomendação<br/>aggregate"] --> MR["Meta-revisão<br/>meta_review"]
    AGM{{"Meta-revisor<br/>meta_reviewer"}} -.- MR
    MR --> VM["Confere se só cita itens que existem<br/>validate_meta_review"]
    VM --> BR["Monta o relatório<br/>build_report"]
    BR ==> FR[("Relatório final<br/>FinalReport")]
    BR --> OK(["Concluído<br/>done"])
```

## 5. Estados da execução (Run)

Cada estado mostra o identificador do código e, embaixo, o nome em português.

```mermaid
stateDiagram-v2
    direction LR
    received: recebido
    extracting: extraindo
    extracted: extraído
    profiling: classificando
    profiled: perfil pronto
    checking_integrity: checando integridade
    integrity_checked: integridade ok
    waiting_human_review: aguardando revisão humana
    closed_by_reviewer: encerrado pelo revisor
    evaluating: avaliando
    evaluated: avaliado
    consolidating: consolidando
    done: concluído

    [*] --> received
    received --> extracting: E1
    extracting --> extracted
    extracted --> profiling: E2
    profiling --> profiled
    profiled --> checking_integrity: E3
    checking_integrity --> integrity_checked: risco baixo ou médio
    checking_integrity --> waiting_human_review: risco alto
    waiting_human_review --> integrity_checked: continuar
    waiting_human_review --> closed_by_reviewer: encerrar
    integrity_checked --> evaluating: E4
    evaluating --> evaluated
    evaluated --> consolidating: E5
    consolidating --> done
    done --> [*]
    closed_by_reviewer --> [*]
```

Fora do caminho principal (a tabela completa está em [Modelos de dados](data_models.md#transições-permitidas)):
- **Falhas.** Um estágio em andamento pode terminar em `rejected_invalid_submission` (rejeitado, final), `waiting_setup` (aguardando configuração), `error_llm` (erro do provedor de LLM), `error_external` (erro de serviço externo) ou `error_unexpected` (erro inesperado). "Reprocessar" leva esses quatro últimos de volta ao checkpoint do estágio que falhou.
- **Versão nova.** Qualquer status não final vai para `superseded` (substituído) quando chega uma versão nova do artigo.
- **Reconciliador.** Um estágio travado volta ao checkpoint de onde partiu.
