# Agentes e workflows (Agno)

Como o Metis usa o Agno 3 dentro dos estágios: o pacote `agents/`, o catálogo de agentes, o workflow de cada estágio, o estado, a concorrência, o custo e os fakes. A divisão com o Celery (durabilidade, filas, retries) está em [Orquestração](orchestration.md).

Os caminhos de código são relativos a `projects/correction/`. A versão em diagramas, com as entidades que cada passo lê e grava, está em [Grafo do fluxo](flow_graph.md).

**Estado revisto em 16/11/2026:** fábrica, limites, uso/custo, E1 sem Workflow,
E2, E4 e E5 reais. E3 segue stub; o A/B ainda é planejado e não há correlação
com avaliação humana. [Medições, metas e validação atual](status_and_metrics.md).
As verificações de 1.2/1.3/1.4 nesta página são registros históricos de cada entrega.

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

- **Uma task Celery por estágio.** E2, E4 e E5 chamam `workflow.run()` de forma síncrona. E1 usa sessão e `bounded_map`, sem Workflow; E3 segue stub. Essa aplicação atual ajusta o alvo D16 de um Workflow por estágio. [Orquestração](orchestration.md#agno-dentro-dos-estágios).
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
- O E1 (`extractor/session.py`) pede o runner à `AgentFactory`, preservando o modelo da `DocumentConfig`, o envio do PDF/texto e `retries=0`. Os pools de seções e figuras usam `bounded_map`.
- **Teste de fronteira** (`agents/tests/test_import_boundaries.py`): falha se `agno.agent` ou `agno.models` for importado fora de `agents/`, ou se `agents/` importar um app de domínio.

## O pacote `agents/`

| Módulo | Conteúdo |
|---|---|
| `specs.py` | `ModelSpec(provider, model_id, family, params, timeout_seconds)`, pydantic congelado. `Role` (enum dos papéis de modelo) e o mapa papel → spec, lido do `MetisSettings` |
| `models.py` | `ModelFactory.build(spec)`: modelo Agno com chave explícita, timeout e retry de falhas transitórias (incluindo timeout/conexão), sem multiplicar retry da SDK. `judge_for(spec)` escolhe o juiz |
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

Na curadoria (2.6), `questions/curation.py` chama `question_drafter()` com
`agents/schemas/curation.py`. A entrada contém somente a taxonomia e os critérios
registrados em código. O agente usa `meta_reviewer`; o rascunho exige revisão e
ativação humanas no admin. A geração usa runner e limiter da mesma fábrica,
com até três tentativas de resposta inválida. O formulário mostra falhas do
provedor e preserva a Question ativa. O fluxo de uso está em
[Curadoria](questions_and_profiling.md#curadoria-implementada-26).

Essa chamada do admin não tem Run nem `DatabaseUsageSink`: a fábrica padrão usa
`NullUsageSink`. Portanto rascunhos não geram `LLMCall` persistente e seu custo
não aparece no painel por run. Benchmarks usam `MemoryUsageSink` no próprio relatório.

### Implementação da etapa 1.3

`MetisSettings` traz os nove specs com padrões de desenvolvimento, conforme a decisão da equipe. Todos podem ser substituídos pelo ambiente; o catálogo é validado na subida, inclusive famílias dos avaliadores A/B e dos juízes, parâmetros de geração, concorrência e timeout menor que o soft limit. Uma configuração explícita nula ou inválida falha antes de construir clientes. As chaves são exigidas somente quando um cliente real é construído.

| Papéis | Modelo padrão de desenvolvimento |
|---|---|
| `evaluator_a`, `judge_openai`, `meta_reviewer` | `gpt-5.6-terra` |
| `evaluator_c` | `gpt-5.6-luna` |
| `evaluator_b`, `judge_google`, `adjudicator` | `gemini-3.8-flash` |
| `vision`, `fast` | `gemini-3.5-flash-lite` |

Os IDs e o suporte a saídas estruturadas foram conferidos na documentação oficial de [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Gemini 3.8 Flash](https://aistudio.google.com/docs/models/gemini-3.8-flash) e [Gemini 3.5 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite). São padrões configuráveis, sem calibração ou chamada real nesta etapa; o acesso depende da conta. A escolha de produção continua na Q1. O E1 mantém o modelo já configurado na `DocumentConfig`.

Exemplos de substituição no `.env`:

```dotenv
METIS_EVALUATOR_A__MODEL_ID=gpt-5.6-terra
METIS_FAST__TIMEOUT_SECONDS=60
METIS_EVALUATOR_C={"provider":"google","family":"gemini","model_id":"gemini-3.5-flash-lite"}
METIS_LLM_MAX_CONCURRENCY=4
METIS_EVALUATION_MODE=whole_document
```

`METIS_EVALUATION_MODE` aceita `sectioned` (padrão) ou `whole_document`; o Run
salva a escolha no snapshot antes da avaliação.

`METIS_OPENAI_API_KEY` e `METIS_GOOGLE_API_KEY` são passadas explicitamente aos clientes. `GEMINI_KEY` continua aceita pelo E1 e como alternativa para o Google. A fábrica desliga o retry das SDKs e permite um retry do modelo; o E1 mantém zero. Cada execução cria seu próprio agente e modelo, sem banco Agno, histórico compartilhado, mídia persistida ou telemetria. Erros de provedor e respostas inválidas são registrados sem texto do manuscrito no log.

Os métodos do catálogo aceitam `output_schema=MeuSchema`. Enquanto o contrato do domínio não entra em sua etapa, usam `PendingOutput(summary)`, o mínimo para testar o catálogo. `build(nome_do_prompt, Role.FAST, MeuSchema)` preserva o tipo no `AgentRunner[MeuSchema]`. Os prompts por seção estão em `prompts/sections/`; são bases com checklist, a serem completadas pelos critérios de M2/M3. `render()` gera e valida o exemplo a partir do schema e calcula o SHA-256 das instruções; o artigo fica em `AgentPayload`, fora desse hash e no início da mensagem de entrada.

`FakeAgentFactory` herda a mesma interface e aceita `scripts` por nome de prompt ou por `Role`: `InvalidFor(n)` devolve conteúdo fora do schema N vezes, uma exceção `LLMUnavailable` simula indisponibilidade, e respostas pydantic ou dicts fornecem casos específicos. `QuoteNotInDocument(path=...)` e `MissingElsewhere(path=...)` alteram um campo de um exemplo válido para exercitar validadores semânticos. Depois do roteiro, o fake volta a gerar respostas do schema. `MemoryUsageSink` guarda uma medição por execução, inclusive nas falhas.

`pricing.py` calcula o custo com tarifas Standard por padrão ou com uma tabela injetada; modelo sem preço produz `cost_usd=None` e alerta. O E1 recebe o sink persistente do pipeline. A reexportação de `pipeline.errors.LLMUnavailable` em `agents/errors.py` é a única dependência permitida do pacote no pipeline: preserva a classe que o Celery já reconhece.

**Verificação da 1.3 (12/11):** em Linux com Python 3.14.10 e PostgreSQL 18, **412 testes passaram em 88,75 s**, com 5 casos `llm` excluídos. Passaram `uv lock --check`, `uv sync --locked --all-groups`, Ruff (137 arquivos), mypy (135 arquivos) e `manage.py check`. O lock permaneceu idêntico. A suíte cobre os dois SDKs por HTTP local, timeout e retry sem multiplicação, uso nas falhas, todos os métodos da fábrica falsa, o slot C nas duas famílias, a fronteira de imports e conexões reais fechadas nas threads, em sucesso e falha. O catálogo não recebeu chamadas externas nem calibração de produção nesta etapa.

## Modelos e papéis

Hoje a equipe tem chave da **OpenAI** e do **Google**. A decisão é a D14.

| Papel (`Role`) | Família | Uso |
|---|---|---|
| `evaluator_a` | OpenAI (GPT), modelo forte | Avaliador A |
| `evaluator_b` | Google (Gemini), modelo forte | Avaliador B |
| `evaluator_c` | Uma das duas, com outro tamanho ou geração | Avaliador C. Troca entre OpenAI e Google por config; terceiro provedor requer ampliar a fábrica e os enums |
| `judge_openai` | OpenAI, modelo forte | Juiz das revisões feitas pelo Gemini |
| `judge_google` | Google, modelo forte | Juiz das revisões feitas pelo GPT |
| `meta_reviewer` | Forte, de qualquer família | Meta-revisor do E5 |
| `vision` | Barato, com visão | Descrição de figuras |
| `fast` | Barato | Profiler, papéis das seções, narrativa, adjudicação de referências |
| `adjudicator` | Médio ou forte | Veredito de plágio e alinhamento citação ↔ afirmação |

- **Juiz cruzado.** `judge_for(spec)` devolve o juiz da **outra** família: GPT é julgado pelo Gemini, e Gemini pelo GPT. O slot C segue a regra da família dele. Assim nenhum avaliador é julgado por um modelo da mesma família (viés de autopreferência).
- **Specs por papel** têm padrões de desenvolvimento e aceitam substituição no `.env`; a escolha de produção continua na Q1. O snapshot dos specs usados integra o `config_snapshot` do Run nas etapas seguintes.
- **Duas famílias em três slots deixam risco de correlação** (R13). O A/B ainda precisa medi-la. A fábrica atual aceita somente `openai`/`google` e famílias `gpt`/`gemini`; um terceiro provedor exige código, contratos e testes novos.

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

Na etapa 2.3, `questions/profiler.py` executa `profiler_field()` e `profiler_topic(field)`
pela fábrica, com schemas de `agents/schemas/profiling.py` fechados em uma versão da
taxonomia. O schema do topic valida também o par topic/subfield. Respostas inválidas
voltam com motivo sanitizado até o orçamento local; o esgotamento termina em `error_llm`.
`questions/resolver.py` produz a Question e seu snapshot pela cadeia de fallback.
A composição abaixo e a persistência no Run estão implementadas na etapa 2.5.

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

O `ProfilingStage` chama `run_profiling()` com a fábrica e o `DatabaseUsageSink`.
Os executors são classes chamáveis em `questions/workflow.py`; cada passo consulta
o Run, reaproveita seu checkpoint e confere a posse antes de gravar. Field, topic,
resolução e cada seção ambígua concluída sobrevivem ao retry da task. O Celery
continua sendo o único responsável pelo retry de indisponibilidade do provedor.

Antes da primeira chamada, o Run fixa os specs, os templates de prompt, o método,
a versão da taxonomia, o limite de tentativas e o limiar de confiança. Os hashes
dos prompts renderizados são registrados junto dos checkpoints e correspondem aos
`LLMCall`s. Um retry usa essa configuração, mesmo que o ambiente ou os prompts
tenham mudado. As credenciais ficam fora do snapshot.

### E3 — Integridade (`integrity/workflow.py`)

Hoje E3 é um `StageOutcome(payload={"risk": "low"})`, sem Workflow ou
`IntegrityReport`. O E5 declara `not_checked`, risco desconhecido e cobertura
indisponível. O esboço a seguir é a forma planejada para M5:

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

**Estado:** E4 e E5 estão conectados em `evaluation/workflow.py`. `run_evaluation`
congela o contexto do Run, executa o workflow E4 e finaliza a rodada mais recente
dos slots A, B e C. E5 permanece no mesmo módulo, sem compartilhar checkpoints de
avaliação.

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
    Parallel(*[evaluator_steps(slot, ctx.mode) for slot in ctx.slots], name="evaluators"),
    Parallel(*[ValidateStep(slot, round=1) for slot in ctx.slots], name="validate"),
    Parallel(*[JudgeStep(slot, round=1) for slot in ctx.slots], name="judge"),
    Condition(evaluator=has_pending_items_from_database, steps=[
        Loop(max_iterations=settings.max_revision_rounds,
             end_condition=no_revision_work_from_database,
             steps=[Parallel(*[revision_cycle(slot) for slot in ctx.slots])]),
    ]),
    Parallel(*[MarkUnresolvedStep(slot) for slot in ctx.slots]),
    Parallel(*[FinalizeRoundStep(slot) for slot in ctx.slots]),
])
```

Os executors retomam pelos checkpoints persistidos. Em uma reentrega, passos já
concluídos são ignorados; uma rodada parcial de revisão é completada antes de
abrir outra. O workflow fecha as conexões de banco abertas pelos executors paralelos.

**Por que esta forma (D17):**
- A rodada 1 é validada e julgada **fora** do loop. Cada iteração do loop é "revisar → validar → julgar", então **a última revisão sempre passa pelo juiz**. Num loop `[judge, revise]`, a revisão da última iteração sairia sem verificação.
- O `Condition` evita entrar no loop quando a rodada 1 já sai sem pendências.
- O `end_condition` consulta o estado persistido (há `JudgeVerdict` inválido sem revisão?). O spike observou que a lista de outputs cobre só a iteração atual.
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

Implementado na etapa 3.11: quatro executors em `evaluation/workflow.py`, com
checkpoints em `Run.consolidation` e `FinalReport` imutável. A retomada respeita
o modelo/template congelado e o orçamento de respostas inválidas. Cada ponto
cita critérios ativos e ids qualificados do catálogo de evidências, que também
fica no relatório. A agregação e os números não são saída do meta-revisor.
O E4 usa os executors das etapas 3.3–3.9 e finaliza rodadas antes de publicar o
E5. Sem as entradas necessárias para montar o contexto, o estágio vai para
`waiting_setup`; o A/B e a medição de custo por artigo ainda estão pendentes.

### Curadoria, rubric check e A/B (D18)

| Fluxo | Como roda |
|---|---|
| Rascunhar Question | Ação no admin: uma chamada direta do `question_drafter`, que grava a Question com `validated=False`. Não é um Run |
| Rubric check | Um **Run** com `purpose=rubric_check` sobre uma attempt de amostra. O `config_snapshot` leva a Question rascunho. A extração vem do cache, o E3 é pulado e o E4/E5 rodam normalmente. A Question ativa não é tocada |
| A/B do modo de avaliação (planejado) | `purpose=ab_test` já existe no enum; comando e comparação de modos ainda dependem da 3.13 |

- Rubric check reaproveita o pipeline; rascunho é chamada síncrona no web, sem Run. A/B ainda não tem runner.
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
- **Pools com limite.** `metis/concurrency.py` expõe `bounded_map(fn, items, max_workers)`, com fila limitada pelo `buffersize` do Python 3.14. Preserva a ordem, cancela tarefas ainda não iniciadas numa falha e espera a limpeza das que já começaram. Chama `close_old_connections()` no início e `connections.close_all()` no fim de cada tarefa: somente `close_old_connections()` manteria conexões saudáveis abertas (D20).
- **Limite por provedor e processo.** `ProviderLimiter` limita as chamadas simultâneas no processo em `METIS_LLM_MAX_CONCURRENCY` (padrão 4). Cada processo prefork tem seu limite; ele não é uma cota global entre workers. Pools de três avaliadores em `Parallel` são ainda o desenho de E4.
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

## Implementação da etapa 1.4

`attempts.LLMCall` registra run, estágio, papel, agente, provedor, modelo, hash do prompt, tokens, custo, latência, sucesso e classe do erro. `pipeline.usage.DatabaseUsageSink` delega a gravação a `LLMCall.record_usage()`, em `queries/attempts/llm_call.py`. Cada execução do runner gera uma linha; uma resposta inválida e uma nova tentativa contam como execuções distintas. O admin permite consulta e filtros, sem criar, alterar ou excluir registros.

`ExtractionStage` passa o run, o id da task e o sink para `AgnoSession`. As chamadas de mapa, seções, referências e figuras usam a mesma fábrica e persistem o uso. Respostas recuperadas por `ResumableSession` e uma `Extraction` reaproveitada não executam o runner nem criam cobrança duplicada. Sessões avulsas sem run continuam com o sink nulo. A persistência não grava prompt, resposta, PDF nem credenciais; erros são os códigos sanitizados do runner.

### Tarifas iniciais

Tarifas **Standard pagas**, USD por milhão de tokens, conferidas em **12/11/2026**, para os modelos do catálogo e da extração:

| Provedor/modelo | Entrada | Saída | Leitura de cache |
|---|---:|---:|---:|
| OpenAI `gpt-5.6-terra` | 2,00 | 12,00 | 0,20 |
| OpenAI `gpt-5.6-luna` | 0,20 | 1,20 | 0,02 |
| Google `gemini-3.8-flash`, até 31/12/2026 | 0,75 | 3,75 | 0,075 |
| Google `gemini-3.8-flash`, a partir de 01/01/2027 | 1,50 | 7,50 | 0,15 |
| Google `gemini-3.6-flash`, até 31/12/2026 | 0,75 | 3,75 | 0,075 |
| Google `gemini-3.6-flash`, a partir de 01/01/2027 | 1,50 | 7,50 | 0,15 |
| Google `gemini-3.5-flash-lite` | 0,30 | 2,50 | 0,03 |
| Google `gemini-2.5-flash` (histórico) | 0,30 | 2,50 | 0,03 |

Fontes: [OpenAI Docs — GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [OpenAI Docs — GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) e [preços oficiais da Gemini API](https://ai.google.dev/gemini-api/docs/pricing).

Nos dois modelos OpenAI, acima de 272.000 tokens de entrada, aplicam-se 2× à entrada e 1,5× à saída do pedido inteiro; escritas de cache custam 1,25× a entrada comum. As tarifas promocionais dos modelos Gemini 3.8 e 3.6 são escolhidas pela data UTC da chamada e mudam em janeiro, inclusive num processo já em execução. O preço de `gemini-2.5-flash` fica cadastrado para calcular chamadas históricas.

O cálculo subtrai da entrada comum os tokens lidos e escritos no cache, sem cobrá-los duas vezes. O Agno 3.1.12 separa `thoughts_token_count` da saída do Gemini: o runner soma o raciocínio à saída faturável e o guarda também em `reasoning_tokens`. No OpenAI, o raciocínio já faz parte da saída e não é somado de novo. O valor final usa `Decimal` e 12 casas, com arredondamento `ROUND_HALF_UP`, e fica congelado no registro.

Trocar o modelo pelo ambiente exige cadastrar sua tarifa por `(Provider, model_id)`; um id desconhecido mantém os tokens, custo nulo e aviso no log. A tabela cobre tokens de texto e imagem/PDF em chamadas Standard. Não estima taxas de ferramentas, armazenamento de cache, áudio, descontos de conta ou Batch/Flex/Priority; essas modalidades não são usadas pelo pipeline atual. Em falhas sem métricas, registram-se as contagens disponíveis (zero quando ausentes), sem inferir consumo que o provedor não informou.

Os testes usam PostgreSQL 18 e HTTP local, sem chamadas a provedores externos: gravação por run, falha e resposta inválida, modelo sem tarifa, tentativas distintas, concorrência, cache e raciocínio, admin somente leitura e integração do E1. Os testes de preços cobrem também o fim da promoção e o limite de contexto longo.

**Verificação da 1.4 (12/11):** a suíte completa passou com **437 testes**, 5 casos `llm` excluídos e um aviso de depreciação do SDK Google, em Linux com Python 3.14.10 e PostgreSQL 18. Passaram também Ruff (143 arquivos), mypy (141 arquivos), `manage.py check`, aplicação de `attempts.0003_llmcall` e conferência de migrações pendentes. A validação com chaves válidas da 1.2 continua pendente.

## Custo

- Cada chamada passa pelo `AgentRunner`, que mede e chama o `UsageSink`. O sink do pipeline grava o `LLMCall` com run, estágio, papel, provedor, modelo, versão do prompt, tokens, custo e latência.
- Tokens vêm das métricas da resposta do Agno, incluindo os tokens de cache.
- O admin compara o custo histórico do run com o orçamento de alerta configurado. Esse alerta não interrompe chamadas nem muda o estado do pipeline; bloqueio preventivo por orçamento ainda não está implementado.

### Consulta no admin (6.2)

Em **Attempts → LLM calls**, o painel **Custos de LLM** soma todas as chamadas que atendem
à busca e aos filtros, inclusive as de outras páginas da lista. Os desdobramentos são por
run, estágio, papel, provedor/modelo e dia. O filtro de criação e a hierarquia de datas
permitem selecionar o período; os dias usam o fuso ativo do Django (`America/Recife` por
padrão). Cada tabela mostra até 100 grupos em ordem de identificação, com aviso quando
há mais; o resumo geral continua incluindo todos os grupos. Refine os filtros para
consultar os demais.

O detalhe de cada **Run** mostra os mesmos totais e desdobramentos para todo o histórico
da execução. Esses painéis exigem `attempts.view_llmcall`; ter somente `view_run` não dá
acesso aos custos. Os registros continuam somente leitura.

Defina, por exemplo, `METIS_LLM_RUN_BUDGET_USD=1.00` no ambiente dos processos web para
ativar o alerta **Orçamento excedido** quando a soma conhecida for maior que USD 1.00.
Sem a variável, aparece **Orçamento não configurado**. O limite deve ser positivo e
finito; é um limite global de alerta por run, aplicado também a runs anteriores. Na lista
filtrada, a coluna de custo mostra o recorte e o alerta compara separadamente o **custo
histórico completo do run**, evitando ocultar um excesso ao filtrar por período ou modelo.

As somas usam `Decimal` e os custos congelados de `LLMCall`, sem consultar a tabela de
preços atual. Chamadas com falha e retries também entram na conta. Custo nulo sinaliza
**total parcial**, com a contagem de chamadas sem preço; abaixo do limite, o orçamento
fica **indeterminado**, em vez de afirmar que foi respeitado. Se a parcela conhecida já
exceder o limite, o alerta aparece mesmo com chamadas sem preço. Valores pequenos
preservam as casas decimais necessárias, até as 12 registradas.

## Testes

| O quê | Como |
|---|---|
| Executors e workflows | `FakeAgentFactory` com roteiro por papel; banco real; Celery eager |
| Loop do juiz (planejado) | Fakes já oferecem roteiros; integração do loop depende de E4/3.9–3.10 |
| Idempotência | Rodar o mesmo workflow duas vezes: a segunda não chama nenhum agente |
| Concorrência | `bounded_map` com `transaction=True`: nenhuma conexão sobra aberta; o limiter nunca passa do limite |
| Fronteira | `test_import_boundaries.py` |
| Prompts | Render sem marcador sobrando; exemplo JSON bate com o schema; hash muda quando o texto muda |
| Agno real | Um teste de contrato por provedor, fora do CI, que roda um agente mínimo com `output_schema` e confere métricas e erros |
