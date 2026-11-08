# Orquestração

Como o pipeline anda, falha e se recupera. Os estados citados aqui estão definidos em [Modelos de dados](data_models.md#estados-do-run).

## Princípios

- **O banco é a fonte da verdade.** A mensagem Celery leva só o `run_id`; a task lê o que precisa do Postgres e grava o que produz.
- **Um estágio = uma task curta** (minutos, não horas). Uma falha no E4 não refaz a extração.
- **O status só muda pelo `RunManagement`**, que valida a transição e grava o `RunEvent` na mesma transação.
- **O próximo estágio só é publicado depois do commit** (`transaction.on_commit`). Uma task nunca vê um estado que ainda não foi gravado.

## Estágios e checkpoints

| Estágio | Parte de (checkpoint) | Enquanto roda | Termina em | Fila | Task |
|---|---|---|---|---|---|
| E1 extraction | `received` | `extracting` | `extracted` | `extraction` | `pipeline.extract_attempt` |
| E2 profiling | `extracted` | `profiling` | `profiled` | `evaluation` | `pipeline.profile_attempt` |
| E3 integrity | `profiled` | `checking_integrity` | `integrity_checked` ou `waiting_human_review` | `integrity` | `pipeline.check_integrity` |
| E4 evaluation | `integrity_checked` | `evaluating` | `evaluated` | `evaluation` | `pipeline.evaluate_attempt` |
| E5 consolidation | `evaluated` | `consolidating` | `done` | `evaluation` | `pipeline.consolidate_report` |

O E2 roda na fila `evaluation` porque é uma chamada de LLM, não um parse.

A fila e o nome da task de cada estágio ficam no `STAGES` (`attempts/status.py`). As rotas do Celery (`CELERY_TASK_ROUTES`) e a publicação (`pipeline/publishing.py`) são geradas a partir dele.

## Ciclo de uma task de estágio

Todas as tasks seguem a mesma base, `StageTask` (Template Method). Cada estágio implementa só o `execute()`:

```text
claim ──▶ execute() ──▶ complete ──▶ publica o próximo estágio (após o commit)
  │          │
  │          ├─ erro passageiro ──▶ retry com backoff (mesma task) ─ esgotou ─▶ error_llm / error_external
  │          ├─ erro permanente ──▶ rejected_invalid_submission / waiting_setup
  │          └─ erro inesperado ──▶ error_unexpected
  │
  └─ claim negado ──▶ encerra sem efeito (outro worker pegou, ou o run mudou de estado)
```

1. **Claim.** A task trava a linha do run e confere o estado:
   - se o run está no checkpoint do estágio, passa para o status "rodando" e grava `stage`, `current_task_id` e `stage_started_at`;
   - se já está rodando **com o mesmo id de task**, retoma (é um retry ou uma reentrega);
   - em qualquer outro caso, sai sem efeito.
2. **`execute()`.** O trabalho do estágio, em código ou num workflow Agno. Recebe um `StageContext(run_id, attempt_id, task_id, stage)` e devolve um `StageOutcome(payload, halt)`. Cada passo persiste o que produz.
3. **Complete.** Só fecha se a task ainda for a dona: status "rodando" + `current_task_id` igual ao dela. Se perdeu a posse no meio do caminho (chegou uma versão nova do artigo, ou o reconciliador liberou o estágio), encerra sem efeito.
4. **Publicação.** Registra no `on_commit` a task do estágio seguinte, se houver. O E3 pode terminar em `waiting_human_review` (`halt=True` no `StageOutcome`), e aí nada é publicado.

### Por que a posse é pelo id da task

O Celery mantém o mesmo id da task em `retry()` e na reentrega depois da morte do worker (`acks_late` + `task_reject_on_worker_lost`). Assim a própria mensagem retoma o estágio sem voltar ao checkpoint. Qualquer outra mensagem para o mesmo run, como uma republicação duplicada, tem o claim negado, e o trabalho nunca roda em dobro.

## Erros

| Exceção | Exemplo | Retry automático | Status final | Como sai |
|---|---|---|---|---|
| `LLMUnavailable` (passageiro) | 429 ou 5xx do provedor de LLM | sim, com backoff | `error_llm` | "Reprocessar" no admin |
| `TransientStageError` (passageiro) | GROBID fora do ar, timeout no Crossref | sim, com backoff | `error_external` | "Reprocessar" |
| `InvalidSubmission` (permanente) | PDF sem texto, sem abstract, criptografado | não | `rejected_invalid_submission` | Final: o autor envia uma versão nova |
| `SetupRequired` (permanente) | Nenhuma Question disponível, nem a genérica | não | `waiting_setup` | Configurar e "Reprocessar" |
| Qualquer outra | Bug | não | `error_unexpected` | Corrigir e "Reprocessar" |

"Reprocessar" leva o run de volta ao checkpoint do estágio que falhou e publica esse estágio de novo. Os estágios anteriores não são refeitos.

### Retries

- **Backoff:** exponencial com jitter completo, calculado pelo próprio Celery (`get_exponential_backoff_interval`). Valores iniciais: 3 retries, base de 60 s, teto de 15 min.
- **Registro:** cada retry gera um `RunEvent` `retry_scheduled` com o erro e o tempo de espera.
- **Dentro do Agno:** `Step(max_retries=0)`, porque o retry de step do Agno não tem backoff. O retry de uma chamada fica no modelo (`retries` + `exponential_backoff=True`, só para 429/5xx), e o do estágio inteiro fica no Celery.

## Reconciliador

Uma task do beat (`pipeline.reconcile_runs`, a cada 5 min) cobre duas situações que o fluxo normal não cobre:

| Situação | Como detecta | O que faz | Limite |
|---|---|---|---|
| Checkpoint sem task: commitou, mas a publicação falhou | Run num checkpoint sem mudança há mais de 15 min | Republica o estágio e grava um evento `republished` | 3 republicações → `error_unexpected` |
| Estágio travado: o worker morreu e a mensagem não voltou | Run "rodando" com `stage_started_at` mais antigo que 45 min | Volta ao checkpoint e republica | 8 claims no estágio → `error_unexpected` |

Por que é seguro:
- O claim e a posse impedem processamento duplo, mesmo que a mensagem antiga ainda esteja na fila.
- 45 min é mais que o hard limit da task (30 min). Quando o reconciliador libera um estágio, a task antiga já foi morta.

## Tempos e validação na subida

| Configuração | Valor inicial |
|---|---|
| Soft / hard time limit da task | 25 min / 30 min |
| Visibility timeout do Redis | 2 h |
| Backoff do retry (base / teto) | 60 s / 15 min |
| Reconciliador: intervalo / republicar após / estágio travado após | 5 min / 15 min / 45 min |

O `metis/config.py` recusa subir com valores contraditórios:
- soft < hard < visibility timeout;
- teto do backoff < visibility timeout. O retry espera no worker como ETA, e se passar do visibility timeout o Redis reentrega a mensagem;
- estágio travado após > hard limit;
- máximo de claims > retries + 1, porque os retries também contam como claims.

## Filas e workers

| Fila | Worker | Concorrência inicial | Por quê |
|---|---|---|---|
| `extraction` | `worker-extraction` | baixa (1–2), com limite de memória | GROBID e Docling são pesados em CPU e memória |
| `integrity` | `worker-integrity` | 2 | Rede (APIs acadêmicas com rate limit) + embeddings locais |
| `evaluation` | `worker-evaluation` | 4 | Chamadas de LLM, limitadas por I/O |
| `default` | `worker-evaluation` | — | Manutenção (reconciliador) |

Todos usam a mesma imagem, com `prefetch_multiplier=1` e `acks_late`.

## Agno dentro dos estágios

O `execute()` de cada estágio monta o Workflow Agno do estágio e chama `workflow.run()`. O desenho completo (fronteiras, `agents/`, catálogo de agentes, workflow por estágio, estado, concorrência, custo e testes) está em [Agentes e workflows](agents.md). As regras que tocam a orquestração:

- **Construção por task.** O workflow e os agentes são criados dentro de cada task, nunca como singletons de módulo: o cliente HTTP do modelo fica preso ao event loop em que nasceu. Cada ramo de um `Parallel` recebe uma instância própria de Agent.
- **Execução síncrona.** `workflow.run()` nos workers prefork. O `background=True` do Agno não é usado: o Celery já é a camada de background.
- **Configuração:** `Workflow(..., telemetry=False)`, `store_media=False`, `run_id` = id da task Celery.
- **Retomada pelo banco.** Um retry do estágio executa o workflow inteiro de novo, e cada passo pula o que já tem saída persistida.
- **Concorrência com limite.** `Parallel` e os pools rodam em threads; os pools usam `bounded_map`, que fecha a conexão do Django em cada thread, e o `ProviderLimiter` limita as chamadas por provedor.
- **Workflow, não Team.** O fluxo é determinístico; num Team, o líder LLM decide o que fazer.
- **O gate fica na máquina de estados**, não no `HumanReview` do Agno: ele atravessa estágios Celery e precisa sobreviver a restart de worker.
- **O `PostgresDb` do Agno fica desligado.** Se um dia for usado, fica num schema `agno` no mesmo Postgres, só para inspecionar execuções.

## Idempotência, camada por camada

| Camada | Mecanismo |
|---|---|
| API | Unicidade de (artigo, sha256): o reenvio idêntico devolve 200 com a attempt existente |
| Publicação | `on_commit` + reconciliador para a janela "commitou, mas não publicou" |
| Claim | Lock da linha + checkpoint ou posse pelo id da task |
| Passos de um estágio | Cada passo persiste e pula o que já existe (ex.: um passe por seção que já tem observações na rodada não é chamado de novo) |
| Eventos | `event_key` único: `{run}:{version}` nas transições, `{run}:retry:{task}:{n}` nos retries |

## Auditoria e custo

- **`RunEvent`:** toda transição (de, para, estágio, task, ator, payload), cada retry e cada republicação.
- **`LLMCall`** (a partir do M1): cada chamada de modelo, com modelo, tokens, custo, latência e versão do prompt.
- **Flower:** filas e workers em tempo real.
