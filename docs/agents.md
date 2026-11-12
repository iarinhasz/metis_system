# Agentes e workflows (Agno)

Como o Metis usa o Agno 3 dentro dos estágios: o pacote `agents/`, o catálogo de agentes, o workflow de cada estágio, o estado, a concorrência, o custo e os fakes. A divisão com o Celery (durabilidade, filas, retries) está em [Orquestração](orchestration.md).

Os caminhos de código são relativos a `projects/correction/`. A versão em diagramas, com as entidades que cada passo lê e grava, está em [Grafo do fluxo](flow_graph.md).

> **Spike 1.2, verificação local em 12/11/2026:** Agno **3.1.12**, Python **3.14.5**, `openai` **3.49.0** e `google-genai` **1.75.0** instalados. Workflows e clientes dos dois provedores foram exercitados com executors sintéticos e HTTP local. A validação de respostas dos provedores com chaves válidas continua **pendente**, por decisão de seguir com os testes locais. O resultado e as correções dos esboços estão abaixo.

## Resultado do spike 1.2

O lock fixa as versões verificadas; a dependência do Agno fica em `>=3.1.12,<4`. Não foi necessário usar Python 3.13. Os testes ficam em `projects/correction/agents/tests/`: `test_workflow_contract.py` (sem rede externa), `test_provider_contract.py` (HTTP local, com SDKs reais) e `test_agno_contract.py` (provedores reais, marcado com `llm`). Só usam entradas sintéticas.

| Item | Comportamento observado em 3.1.12 | Consequência para a implementação |
|---|---|---|
| Executor de `Step` | Instância chamável recebe `StepInput` e devolve `StepOutput`; o `content` preserva o objeto pydantic | Executors por classe continuam válidos |
| Retry e erro de `Step` | `max_retries` é **3** por padrão. `Step.execute()` com 0 propaga a exceção, mas o `Workflow` usa **`HumanReview.on_error=skip`** por padrão e pode terminar `completed` após pular a falha | Todo `Step` e `Condition` de estágio precisa de `human_review=HumanReview(on_error=OnError.fail)`; com essa política, o workflow propaga a exceção original ao chamador |
| `Parallel` | Os ramos rodam em threads; a saída guarda `steps[]` na ordem declarada. Um ramo que falha **não cancela os irmãos**; o container volta com `success=False`, mas o workflow pode continuar e terminar `completed` | O executor que recebe o container deve conferir seus ramos e levantar o erro do estágio antes de continuar. `on_error=fail` nos filhos não basta |
| Saídas do paralelo | `get_step_output("ramo").content` preserva o pydantic; a busca pelo nome é recursiva | Usar `get_step_output`, com conferência de `None` e de `success`; não usar o texto agregado como contrato |
| `Condition` | `evaluator(step_input: StepInput) -> bool`; pode conter um `Loop` | Sem pendência, nenhuma revisão roda; configurar a política de erro também na condição |
| `Loop` | `end_condition(outputs: list[StepOutput]) -> bool` recebe **só a iteração atual**, depois de todos os seus passos; `max_iterations=2` limita a duas revisões | A forma `revise → validate → judge` continua correta. A condição consulta os dados persistidos; não depende de efeitos somente em memória |
| `output_schema` | Ambos os clientes enviam o schema aninhado com `Literal` e devolvem o pydantic. JSON cortado ou enum inválido pode voltar como **`str`, com status `completed`** | Conferir o tipo de `content` mesmo quando o status indica sucesso; saída fora do schema vira `valid=False` |
| Métricas | `run.metrics.input_tokens`, `output_tokens`, **`cache_read_tokens`**, `cache_write_tokens` e **`duration` em segundos** | `LLMCall.cached_tokens` vem de `cache_read_tokens`; converter duração para milissegundos. O teste local confere 20/5 tokens e 4 de cache em cada SDK |
| Erros dos provedores | `model.invoke()` levanta `agno.exceptions.ModelProviderError`, com `status_code` e causa da SDK. Já **`Agent.run()` captura a falha e devolve `RunOutput(status=RunStatus.error)`** | O runner precisa conferir `run.status` antes do schema. Apenas `except ModelProviderError` ao redor de `Agent.run()` não trata a indisponibilidade |
| Retries do modelo | Com SDK sem retry, 429/503 são retentados e 401 não é. O modelo também pode retentar timeout/conexão, não apenas HTTP 429/5xx | OpenAI: `max_retries=0` na SDK; Google: `http_options.retry_options.attempts=1`. Configurar um único retry do modelo, além do retry do estágio |
| Timeout | `timeout` do modelo é em segundos; o Gemini converte para milissegundos na SDK. Se `client_params.http_options` for passado, ele substitui as opções montadas pelo modelo | Ao fornecer opções explícitas do Google, incluir também `timeout` em ms e as opções de retry |
| `run_id` e telemetria | Agent e Workflow preservam o `run_id` recebido. `telemetry=False` funciona nos dois; `AGNO_TELEMETRY=false` é aplicado **na execução**, não ao construir o objeto. `store_media=False` é aceito no Agent | Passar o id da task a `.run(run_id=...)`, desligar telemetria nos construtores e no ambiente; banco Agno desligado |

As causas observadas em `model.invoke()` foram `AuthenticationError` (OpenAI 401), `RateLimitError` (429), `InternalServerError` (503), `ClientError` (Google 4xx), `ServerError` (Google 5xx), `APITimeoutError` (OpenAI) e `ReadTimeout` (Google). São contratos exercitados pela rede local, não uma medição de disponibilidade dos serviços. A anotação de `Parallel.__init__(*args)` nesta versão declara listas onde a execução espera passos variádicos; os testes usam `type: ignore[arg-type]` pontual, com a construção real coberta pelo contrato.

### Configuração dos esboços

Nos workflows abaixo, `stage_step` representa esta configuração explícita do `Step`:

```python
from agno.workflow import Step
from agno.workflow.types import HumanReview, OnError

def stage_step(name, executor):
    return Step(name=name, executor=executor, max_retries=0,
                human_review=HumanReview(on_error=OnError.fail))
```

`HumanReview` aqui só configura a política de erro, sem habilitar pausa ou confirmação humana. O gate continua no banco e no Celery. Toda `Condition` usa a mesma política. Depois de um `Parallel`, o passo seguinte confere `success` e os resultados de cada ramo; uma falha é levantada antes de validar, agregar ou persistir o checkpoint.

### Reprodução e pendência dos provedores

```bash
uv sync --locked --group dev
uv run pytest projects/correction/agents/tests -m "not llm"
uv run pytest projects/correction/agents/tests/test_agno_contract.py -m llm -rs
```

O último comando fica fora do CI. Com `METIS_OPENAI_API_KEY` e `GEMINI_KEY` no `.env`, ele confere respostas reais com schema aninhado, enums e métricas. Sem uma chave, o teste daquele provedor é pulado explicitamente; isso **não** conta como validação bem-sucedida. Os modelos do spike são configuráveis por `METIS_AGNO_CONTRACT_OPENAI_MODEL` e `METIS_AGNO_CONTRACT_GOOGLE_MODEL`; não definem os slots da etapa 1.3. O arquivo também oferece testes de chave deliberadamente inválida, sem exigir segredo válido.

**Verificação desta entrega (12/11):** `pytest projects/correction -m "not django_db and not llm"` passou com **227 testes**, incluindo os contratos novos; 78 casos com banco ou provedores foram excluídos. `ruff check`, `ruff format --check`, `mypy projects/correction` (113 arquivos) e `python manage.py check` passaram. A suíte com PostgreSQL não foi executada: o Docker Desktop estava parado. Os dois testes de chave deliberadamente inválida também passaram; os dois de resposta com chave válida foram pulados e continuam pendentes.

Referência para o schema do cliente OpenAI: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). O comportamento do Agno descrito nesta seção vem dos testes contra o pacote instalado, não de uma suposição sobre a SDK.

## Visão geral

```text
Celery (durável)                    Agno (dentro do estágio)                       Provedores
────────────────                    ─────────────────────────                      ──────────
task do estágio                      <app>/workflow.py monta o Workflow
  └─ StageTask                         Step / Steps / Parallel / Loop / Condition
       claim                             └─ executor (classe chamável do app)
       execute() ──────────────────────▶      ├─ código puro (parser, regra, agregação)
       complete                               └─ AgentFactory.<papel>() ──▶ Agent ──▶ OpenAI / Gemini
       publica o próximo                             (agents/: único lugar com Agent e Model)
```

- **Uma task Celery por estágio, um Workflow Agno por estágio.** O `execute()` do `StageTask` monta o workflow do estágio e chama `workflow.run()`, de forma síncrona. A decisão é a D5, e o detalhe está em [Orquestração](orchestration.md#agno-dentro-dos-estágios).
- **O banco é a fonte da verdade.** O workflow recebe só ids. Cada passo grava o que produz e, quando o estágio é retentado, pula o que já existe.
- **O Agno não decide o fluxo.** É `Workflow`, não `Team`: a ordem dos passos é fixa em código, e os agentes só preenchem saídas tipadas.

## Fronteiras

| O quê | Onde | Por quê |
|---|---|---|
| `Agent` e modelos do Agno (`agno.agent`, `agno.models.*`) | só em `agents/` | Um ponto para modelos, chaves, retries, telemetria, custo e fakes |
| `Workflow`, `Step`, `Steps`, `Parallel`, `Loop`, `Condition` | no `workflow.py` de cada app (`questions/`, `integrity/`, `evaluation/`; o E1 não usa Workflow) | O fluxo de um estágio fica junto do domínio que ele implementa |
| Executors dos passos | no app do estágio (`<app>/steps/`) | Usam os Managements de `queries/<app>/` e os services do próprio app |
| Chamada do workflow | `pipeline/stages.py` (`StageTask.execute()`) | O pipeline orquestra; o domínio não importa `pipeline` |

- `agents/` não importa nenhum app de domínio. O registro de custo entra por injeção (`UsageSink`, abaixo).
- **Exceção provisória:** o E1 (`extractor/session.py`) cria o `Agent` e o modelo Gemini direto, porque o `agents/` ainda não existe. Quando a 1.3 entrar, a sessão passa a pedir o agente à `AgentFactory`.
- **Teste de fronteira** (`agents/tests/test_import_boundaries.py`): falha se `agno.agent` ou `agno.models` for importado fora de `agents/`, ou se `agents/` importar um app de domínio.

## O pacote `agents/`

| Módulo | Conteúdo |
|---|---|
| `specs.py` | `ModelSpec(provider, model_id, family, params, timeout_seconds)`, pydantic congelado. `Role` (enum dos papéis de modelo) e o mapa papel → spec, lido do `MetisSettings` |
| `models.py` | `ModelFactory.build(spec)`: devolve o modelo Agno do provedor, com a chave passada explicitamente, `retries` e `exponential_backoff=True` (só para 429/5xx) e o timeout do spec. `judge_for(spec)` escolhe o juiz |
| `factory.py` | `AgentFactory(run_id, stage, usage_sink, limiter)`: um método por papel do catálogo. Cria um `Agent` novo por chamada, com instruções renderizadas, `output_schema`, `telemetry=False` e `store_media=False` |
| `runner.py` | Protocolo `AgentRunner` (`run(payload) -> AgentResult`). A implementação real envolve o `Agent`: pega o limiter, roda, mede e chama o `UsageSink`, inclusive nas falhas. Confere primeiro `run.status`: em `error`, levanta `LLMUnavailable`. Em sucesso, se `content` não for o schema pedido, devolve `AgentResult(valid=False, raw=...)`. O `Agent.run()` não propaga normalmente o `ModelProviderError` |
| `prompts/` | Arquivos `.md` com marcadores `<<nome>>`. O `render()` falha se sobrar marcador, a versão é o hash do conteúdo renderizado sem o artigo, e o exemplo JSON é gerado do `output_schema`. Um prompt por papel de seção em `prompts/sections/<papel>.md` |
| `schemas/` | Os `output_schema` de cada papel (pydantic). Os enums fechados (vereditos, categorias, notas) vêm de código compartilhado, nunca de strings soltas |
| `usage.py` | Protocolo `UsageSink.record(call: LLMUsage)`. `LLMUsage` traz papel, provedor, modelo, versão do prompt, tokens (entrada, saída, cache), latência, sucesso e erro |
| `pricing.py` | Tabela de preços por (provedor, modelo). Um modelo sem preço grava o custo vazio e gera um alerta no log |
| `limits.py` | `ProviderLimiter`: um semáforo por provedor (`METIS_LLM_MAX_CONCURRENCY`), compartilhado no processo do worker. Limita a concorrência somada de `Parallel` + pools |
| `errors.py` | `LLMUnavailable` (a mesma do `pipeline/errors.py`, reexportada para quem está fora do pipeline) |
| `fakes.py` | `FakeAgentFactory`: mesma interface, com roteiro por papel. Respostas válidas geradas do schema; "inválido N vezes"; quote inexistente; `missing` de algo que está em outra seção; `LLMUnavailable` |

O `UsageSink` real fica no pipeline (`pipeline/usage.py`) e grava um `LLMCall` por chamada, ligado ao run e ao estágio.

## Modelos e papéis

Hoje a equipe tem chave da **OpenAI** e do **Google**. A decisão é a D14.

| Papel (`Role`) | Família | Uso |
|---|---|---|
| `evaluator_a` | OpenAI (GPT), modelo forte | Avaliador A |
| `evaluator_b` | Google (Gemini), modelo forte | Avaliador B |
| `evaluator_c` | Uma das duas, com outro tamanho ou geração | Avaliador C. Muda de provedor só por config (ex.: OpenRouter ou Ollama), quando houver chave |
| `judge_openai` | OpenAI, modelo forte | Juiz das revisões feitas pelo Gemini |
| `judge_google` | Google, modelo forte | Juiz das revisões feitas pelo GPT |
| `meta_reviewer` | Forte, de qualquer família | Meta-revisor do E5 |
| `vision` | Barato, com visão | Descrição de figuras |
| `fast` | Barato | Profiler, papéis das seções, narrativa, adjudicação de referências |
| `adjudicator` | Médio ou forte | Veredito de plágio e alinhamento citação ↔ afirmação |

- **Juiz cruzado.** `judge_for(spec)` devolve o juiz da **outra** família: GPT é julgado pelo Gemini, e Gemini pelo GPT. O slot C segue a regra da família dele. Assim nenhum avaliador é julgado por um modelo da mesma família (viés de autopreferência).
- **Ids exatos dos modelos** ficam no `.env` (questão aberta Q1). O Run grava um snapshot dos specs usados.
- **Com duas famílias, os erros ficam mais correlacionados** (risco R13). O A/B do M3 mede a concordância, e um 3º provedor entra no slot C sem mudar código.

## Catálogo de agentes

| Agente (método da `AgentFactory`) | Estágio | Entrada | `output_schema` | Papel de modelo |
|---|---|---|---|---|
| `figure_describer(kind)` | E1 | Recorte + legenda + parágrafos que citam a figura; prompt muda com a classe. Hoje (1.8): o PDF inteiro + rótulo, página, legenda e frases que citam a figura, num prompt só, pela sessão do `extractor/` | `FigureDescription` (hoje `DescribedFigure`) | `vision` (hoje o modelo da config do extractor) |
| `profiler_field()` | E2 | Título, abstract, palavras-chave + enum dos fields | `FieldChoice` (field, `paper_type`, idioma, palavras-chave, confiança) | `fast` |
| `profiler_topic(field)` | E2 | Os mesmos dados + enum dos subfields e topics daquele field | `TopicChoice` (subfield, topic, áreas secundárias, confiança) | `fast` |
| `section_role_classifier()` | E2 | Títulos ambíguos + primeira frase + `paper_type` | `SectionRoles` | `fast` |
| `section_reviewer(slot, role)` | E4 | Mapa do documento + seção + checklist do papel + critérios do papel com `rubric_text` | `SectionObservations` | `evaluator_<slot>` |
| `cross_checker(slot, kind)` | E4 | Só as seções envolvidas + figuras com `supports_claims` | `CrossCheckResult` | `evaluator_<slot>` |
| `synthesizer(slot)` | E4 | Observações + checagens do avaliador + critérios + resumo da integridade + obras relacionadas | `CriteriaSynthesis` | `evaluator_<slot>` |
| `whole_document_reviewer(slot)` | E4 (modo `whole_document`) | Artigo inteiro + critérios | `CriteriaSynthesis` com `evidence[]` | `evaluator_<slot>` |
| `reviser(slot, level)` | E4 | Item anterior + trecho apontado + motivo | `RevisionResponse` (`accept` ou `rebut`, item novo ou nova evidência) | `evaluator_<slot>` |
| `judge(for_spec)` | E4 | Artigo inteiro (prefixo) + revisão do avaliador + dicas de divergência | `JudgeReport` (um veredito por item) | `judge_for(spec)` |
| `meta_reviewer()` | E5 | Sínteses e observações dos 3 avaliadores, já agregadas | `MetaReview` (fortes, fracos, sugestões, com ids citados) | `meta_reviewer` |
| `plagiarism_adjudicator()` | E3, Fase 1 | Par de trechos + contexto de citação + scores | `SimilarityVerdict` | `adjudicator` |
| `reference_adjudicator()` | E3, Fase 2 | String crua da referência + candidatos das bases | `ReferenceMatch` | `fast` |
| `citation_alignment_judge()` | E3, Fase 2 | Frase que cita + abstract (ou trecho) da obra | `AlignmentLabel` | `adjudicator` |
| `integrity_narrator()` | E3 | Achados + nível de risco já decidido pelas regras | `IntegrityNarrative` | `fast` |
| `question_drafter()` | Curadoria (admin) | Nó da taxonomia + critérios do método; **nunca** um artigo | `QuestionDraft` (campos com `rubric_text`) | `meta_reviewer` |

Regras comuns a todos os prompts:
- **Artigo primeiro, entre delimitadores**, marcado como dado e não como instrução. É prefixo estável para o caching de prompt.
- **Toda nova tentativa leva o motivo** (validador ou juiz).
- **Saídas com enum fechado** sempre que a resposta é uma escolha (área, veredito, nota, categoria).

## Workflow por estágio

Os esboços abaixo mostram a forma; os nomes finais saem da implementação. `stage_step` usa `max_retries=0` e `on_error=fail`, como em [Configuração dos esboços](#configuração-dos-esboços).

### E1 — Extração (`extractor/`)

O E1 não usa `Workflow`. O `ExtractionStage` chama `extract_attempt()`, que reaproveita a `Extraction` guardada para o mesmo PDF e a mesma versão do extractor ou divide o artigo agora:

```python
scan = session.ask(config.scan_prompt, HeadingScan)          # chamada 1: o mapa das seções
section_map = build_section_map(scan, config)                 # dict sec_1, sec_2…; gate: abstract e referências
answers = {sid: ask_section(session, config, prompt(sid), local_text[sid])   # chamada 2, uma por seção,
           for sid in section_map}                            # em paralelo (ThreadPoolExecutor), conferida
                                                              # contra o PDF e refeita com dica se reprovada
```

- **Uma chamada por seção, em paralelo** (até `max_parallel_calls`): respostas curtas, e o modelo pula menos texto que numa resposta com o artigo inteiro.
- **Depois das seções:** uma chamada separa as referências em campos, uma lista as figuras e tabelas e uma por figura, em paralelo, descreve cada uma (`describe_figures`). As citações e as chamadas às figuras são achadas em código.
- **Sem retry no Agno** (`retries=0`): uma falha vira `ModelUnavailable`, e quem tenta de novo é o Celery. A sessão guarda cada resposta (`ResumableSession`), e o retry só chama o modelo a partir de onde parou.
- O detalhe (config, conferência, cache, falhas) está em [Extração](extraction.md).

### E2 — Perfil (`questions/workflow.py`)

```python
Workflow(name="profiling", telemetry=False, steps=[
    stage_step(name="classify_field", executor=ClassifyFieldStep(deps)),     # profiler_field
    stage_step(name="classify_topic", executor=ClassifyTopicStep(deps)),     # profiler_topic, enum dos filhos do field
    stage_step(name="resolve_question", executor=ResolveQuestionStep(deps)), # cadeia de fallback; SetupRequired
    stage_step(name="section_roles", executor=RuleBasedRolesStep(deps)),     # dicionário PT/EN
    Condition(name="ambiguous_roles", human_review=HumanReview(on_error=OnError.fail), evaluator=has_ambiguous_sections(ctx),
              steps=[stage_step(name="classify_roles", executor=ClassifyRolesStep(deps))]),
    stage_step(name="document_map", executor=DocumentMapStep(deps)),         # código, sem LLM
    stage_step(name="persist", executor=PersistProfileStep(deps)),           # Run.profile, Run.question, snapshot
])
```

- O enum do segundo passo é montado em tempo de execução (`pydantic.create_model` com `Literal` dos filhos do field escolhido). Assim o modelo não consegue devolver um topic de outro field.
- Num Run de rubric check (`purpose=rubric_check`), o `resolve_question` usa a Question rascunho do `config_snapshot` em vez de resolver pela árvore.

### E3 — Integridade (`integrity/workflow.py`)

Do M0 ao M3, o E3 é um passo só, *pass-through*: risco baixo, relatório vazio e `coverage` = "não checado". A forma final (M5):

```python
Workflow(name="integrity", telemetry=False, steps=[
    stage_step(name="hidden_text", executor=HiddenTextFindingsStep(deps)),   # Fase 0, achados do E1
    stage_step(name="resolve_references", executor=ResolveReferencesStep(deps)),  # scholarly/, cache por DOI
    Parallel(
        Steps(name="phase1", steps=[                                   # entra no M4
            stage_step(name="candidates", executor=CandidatesStep(deps)),    # Strategy + orçamento
            stage_step(name="lexical", executor=LexicalStep(deps)),          # MinHash-LSH + winnowing
            stage_step(name="semantic", executor=SemanticStep(deps)),        # BGE-M3 local + PT↔EN
            stage_step(name="citation_filter", executor=CitationFilterStep(deps)),
            stage_step(name="adjudicate", executor=AdjudicatePairsStep(deps)),  # plagiarism_adjudicator, top-N
        ]),
        Steps(name="phase2", steps=[                                   # entra no M5
            stage_step(name="existence", executor=ExistenceStep(deps)),      # reference_adjudicator nos duvidosos
            stage_step(name="retraction", executor=RetractionStep(deps)),
            stage_step(name="consistency", executor=ConsistencyStep(deps)),
            stage_step(name="alignment", executor=AlignmentStep(deps)),      # citation_alignment_judge, amostra de K
        ]),
        name="phases"),
    stage_step(name="check_phases", executor=CheckParallelStep("phases", deps)),  # não ignorar ramo falho
    stage_step(name="cross_phases", executor=CrossPhasesStep(deps)),
    stage_step(name="risk_rules", executor=RiskRulesStep(deps)),             # integrity/rules.py, código
    stage_step(name="narrative", executor=NarrativeStep(deps)),              # integrity_narrator
    stage_step(name="persist", executor=PersistReportStep(deps)),            # IntegrityReport → StageOutcome(halt=risco alto)
])
```

- **O nível de risco sai das regras**, nunca do LLM. O narrador recebe o nível já decidido.
- **As duas fases escrevem no banco**, cada uma nos próprios achados. Nenhuma lê o `session_state` da outra, que é compartilhado entre os ramos do `Parallel`.
- **O gate não é do Agno.** O `StageOutcome(halt=True)` leva o run a `waiting_human_review` pela máquina de estados.

### E4 — Avaliação (`evaluation/workflow.py`)

```python
def evaluator_steps(slot, mode):                 # Strategy escolhida na montagem
    if mode is Mode.SECTIONED:
        return Steps(name=f"evaluator_{slot}", steps=[
            stage_step(name=f"sections_{slot}", executor=SectionPassStep(slot, deps)),   # pool com limite
            stage_step(name=f"cross_checks_{slot}", executor=CrossCheckStep(slot, deps)),
            stage_step(name=f"synthesis_{slot}", executor=SynthesisStep(slot, deps)),
        ])
    return Steps(name=f"evaluator_{slot}", steps=[
        stage_step(name=f"whole_{slot}", executor=WholeDocumentStep(slot, deps)),
    ])

Workflow(name="evaluation", telemetry=False, steps=[
    Parallel(*[evaluator_steps(s, ctx.mode) for s in ctx.slots], name="evaluators"),
    stage_step(name="check_evaluators", executor=CheckParallelStep("evaluators", deps)),
    stage_step(name="validate_1", executor=ValidateStep(deps)),              # validadores em cadeia, sem LLM
    stage_step(name="judge_1", executor=JudgeStep(deps)),                    # uma chamada por avaliador
    Condition(name="needs_revision", human_review=HumanReview(on_error=OnError.fail), evaluator=has_pending_items(ctx), steps=[
        Loop(name="revision_loop",
             max_iterations=settings.max_revision_rounds,              # 2
             end_condition=no_pending_items(ctx),                      # consulta o banco, não os outputs
             steps=[
                 stage_step(name="revise", executor=RevisionStep(deps)),     # só os itens inválidos
                 stage_step(name="validate", executor=ValidateStep(deps)),
                 stage_step(name="judge", executor=JudgeStep(deps)),         # só os itens revisados
             ]),
    ]),
    stage_step(name="mark_unresolved", executor=MarkUnresolvedStep(deps)),
])
```

**Por que esta forma (D17):**
- A rodada 1 é validada e julgada **fora** do loop. Cada iteração do loop é "revisar → validar → julgar", então **a última revisão sempre passa pelo juiz**. Num loop `[judge, revise]`, a revisão da última iteração sairia sem verificação.
- O `Condition` evita entrar no loop quando a rodada 1 já sai sem pendências.
- O `end_condition` consulta o estado persistido (há `JudgeVerdict` inválido sem revisão?), não a lista de outputs, porque a documentação não garante que ela cubra só a iteração atual.
- O que continuar inválido depois das 2 revisões vira `unresolved` no `mark_unresolved`.

**Rodadas e persistência**

| Passo | Lê | Grava | Pula quando |
|---|---|---|---|
| `sections_<slot>` | `ExtractedDocument`, mapa, Question | Observações em `ReviewRound(round=1)` | A seção já tem observações na rodada |
| `cross_checks_<slot>` | Seções envolvidas, figuras | Checagens na mesma `ReviewRound` | A checagem já existe |
| `synthesis_<slot>` | Observações e checagens do slot | Sínteses por critério | O critério já tem síntese |
| `validate` | A `ReviewRound` atual de cada slot | `JudgeVerdict` com `source=validator` | O item já tem veredito na rodada |
| `judge` | Artigo inteiro + itens ainda sem veredito | `JudgeVerdict` com `source=judge` | O item já tem veredito na rodada |
| `revise` | Itens inválidos da rodada anterior | `ReviewRound(round=n+1)`: cópia da anterior com os itens revisados (`accept`/`rebut`) | O item já foi revisado nessa rodada |

- A revisão de uma observação roda de novo o passe daquela seção só para aquela observação e, depois, a síntese dos critérios que a citam. A de uma síntese roda só aquele critério. A regra completa está em [Avaliadores e juiz](evaluators_and_judge.md#revisão-parcial-e-réplica).
- O item recusado por um validador vai direto para a revisão, com o motivo, sem passar pelo juiz.

### E5 — Consolidação (`evaluation/workflow.py`)

```python
Workflow(name="consolidation", telemetry=False, steps=[
    stage_step(name="aggregate", executor=AggregateStep(deps)),             # mediana, dispersão, total, faixa → recomendação
    stage_step(name="meta_review", executor=MetaReviewStep(deps)),          # meta_reviewer; não altera notas
    stage_step(name="validate_meta_review", executor=ValidateMetaReviewStep(deps)),  # só cita ids que existem
    stage_step(name="build_report", executor=BuildFinalReportStep(deps)),   # FinalReport (JSON) + render Markdown
])
```

- Uma meta-revisão que cita um id inexistente volta ao `meta_reviewer` uma vez, com o motivo. Se persistir, o item citado é removido e o fato é registrado no relatório.

### Curadoria, rubric check e A/B (D18)

| Fluxo | Como roda |
|---|---|
| Rascunhar Question | Ação no admin: uma chamada direta do `question_drafter`, que grava a Question com `validated=False`. Não é um Run |
| Rubric check | Um **Run** com `purpose=rubric_check` sobre uma attempt de amostra. O `config_snapshot` leva a Question rascunho. A extração vem do cache, o E3 é pulado e o E4/E5 rodam normalmente. A Question ativa não é tocada |
| A/B do modo de avaliação | Runs com `purpose=ab_test` e o modo (`sectioned` ou `whole_document`) no `config_snapshot`, criados pelo comando do A/B |

- Os três fluxos reaproveitam o pipeline e os workflows; não existe um workflow paralelo para teste.
- Runs que não são `purpose=evaluation` não aparecem para o sistema que submete e não tornam outros runs `superseded`.

## Estado e idempotência

- **Entrada do workflow:** `StageContext(run_id, attempt_id, task_id, stage)`, só com ids. Cada executor lê do banco o que precisa.
- **`session_state` não carrega dado de negócio.** No `Parallel`, ele é compartilhado entre os ramos, e uma escrita de um ramo apareceria no outro.
- **Saídas tipadas entre passos** só para valores pequenos (ex.: o field escolhido no E2), lidas com `step_input.get_step_output("<passo>").content`. O `get_step_content` de um `Parallel` devolve strings, então não serve para saída tipada. O que importa para auditoria vai para o banco.
- **Executors são classes chamáveis**, com as dependências no construtor (`AgentFactory`, Managements de `queries/<app>/`, clientes). Nos testes, a `FakeAgentFactory` entra no lugar da real.
- **Retomada.** Um retry do estágio pelo Celery executa o workflow inteiro de novo; cada passo pula o que já tem saída persistida (tabela acima). Por isso nenhum passo pode depender de um efeito que não esteja no banco.
- **`run_id` do workflow** = id da task Celery, para cruzar os logs do Agno com o `RunEvent`.
- **`PostgresDb` do Agno:** desligado. Se um dia for usado para inspecionar execuções, fica num schema `agno` próprio.

## Concorrência

- **Onde há threads:**
  - os ramos de um `Parallel` (um thread por ramo, sem limite);
  - os pools dentro de um passo (N figuras, N passes por seção, N pares de plágio).
- **Pools com limite.** `metis/concurrency.py` expõe `bounded_map(fn, items, max_workers)`, que roda num `ThreadPoolExecutor` e fecha a conexão do Django ao fim de cada tarefa (`close_old_connections()`), para não vazar conexões do Postgres (D20).
- **Limite por provedor.** O `ProviderLimiter` segura a concorrência somada: 3 avaliadores em `Parallel`, cada um com um pool de passes, não passam de `METIS_LLM_MAX_CONCURRENCY` chamadas simultâneas por provedor.
- **Agentes por thread.** Cada ramo e cada tarefa do pool pede o próprio `Agent` à fábrica; o Agno não copia agentes entre ramos.
- **Testes com threads** usam `pytest.mark.django_db(transaction=True)`, porque uma thread não enxerga a transação do teste.

## Tempo

- **Por chamada:** `timeout_seconds` no `ModelSpec`, aplicado no cliente do modelo.
- **Por estágio:** o soft limit da task (25 min) vale para o workflow inteiro. A estimativa do E4 (avaliadores em paralelo + até 3 rodadas de juiz) precisa caber nele; o A/B do M3 mede. Se não couber, o primeiro ajuste é a concorrência do pool, e o segundo é dividir o E4 em duas tasks (avaliação e juiz), com um checkpoint novo.

## Erros e retries

| Nível | Quem faz | Como |
|---|---|---|
| Uma chamada de modelo | O modelo Agno | `retries` + `exponential_backoff=True` para falhas transitórias, inclusive timeout; o retry da SDK fica desligado |
| Um passo do workflow | Ninguém | `Step(max_retries=0, human_review=HumanReview(on_error=OnError.fail))`: sem a política explícita, o workflow pode pular a falha |
| O estágio inteiro | O Celery | `LLMUnavailable` ou `TransientStageError` → retry com backoff e jitter; esgotou → `error_llm` ou `error_external` |
| Saída fora do schema | O validador do passo | `AgentResult(valid=False)` → nova tentativa com o motivo, até o limite do passo; depois, o item fica inválido (E4) ou o estágio falha (E2) |

- O `runner.py` trata o `RunStatus.error` devolvido pelo Agent e levanta `LLMUnavailable`, além de tratar exceções de provedor que escaparem. Erros de programação que forem efetivamente levantados sobem como estão e terminam em `error_unexpected`. Depois de um `Parallel`, o executor de junção também confere os ramos: o status global `completed` não comprova que todos deram certo.

## Custo

- Cada chamada passa pelo `AgentRunner`, que mede e chama o `UsageSink`. O sink do pipeline grava o `LLMCall` com run, estágio, papel, provedor, modelo, versão do prompt, tokens, custo e latência.
- Tokens vêm das métricas da resposta do Agno, incluindo os tokens de cache.
- Um orçamento por run (M3–M4) é conferido antes de cada chamada; estourou → o estágio falha com um erro próprio, registrado no `RunEvent`.

## Testes

| O quê | Como |
|---|---|
| Executors e workflows | `FakeAgentFactory` com roteiro por papel; banco real; Celery eager |
| Loop do juiz | Fakes que invalidam N vezes, quote inexistente, `missing` falso, `rebut`; o loop para em 2 revisões e marca `unresolved` |
| Idempotência | Rodar o mesmo workflow duas vezes: a segunda não chama nenhum agente |
| Concorrência | `bounded_map` com `transaction=True`: nenhuma conexão sobra aberta; o limiter nunca passa do limite |
| Fronteira | `test_import_boundaries.py` |
| Prompts | Render sem marcador sobrando; exemplo JSON bate com o schema; hash muda quando o texto muda |
| Agno real | Um teste de contrato por provedor, fora do CI, que roda um agente mínimo com `output_schema` e confere métricas e erros |
