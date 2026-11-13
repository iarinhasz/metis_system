# M2 — Perfil e Questions

**Objetivo:** cada artigo ganha uma área, uma Question resolvida com o contexto do domínio, papéis das seções e o mapa do documento.
**Trilha:** A (começa sobre as fixtures da 1.1, em paralelo à extração real)
**Referência:** [Perfil e Questions](../../../docs/questions_and_profiling.md), [Agentes e workflows](../../../docs/agents.md#e2--perfil-questionsworkflowpy)
**Fora daqui:** rubric check (vai para a 3.12, porque depende do E4 real)

Caminhos relativos a `projects/correction/`.

---

## Etapa 2.1 — App questions e taxonomia

**O que fazer**
- App `questions`: `TaxonomyNode`, `Question`, `RubricField`, com os campos de [Modelos de dados](../../../docs/data_models.md#questions).
- Comando `load_taxonomy`: lê a taxonomia do OpenAlex (domain → field → subfield → topic), dry-run por padrão, grava com `--execute`, registra a `taxonomy_version`.
- Admin de leitura da taxonomia.

**Teste** (`questions/tests/test_load_taxonomy.py`, resposta gravada)
- Dry-run não grava; `--execute` grava a árvore com os níveis certos.
- Rodar duas vezes não duplica nós.

**Commit sugerido:** `feat: add questions app and OpenAlex taxonomy loader`

**Situação (12/11/2026):** implementada. App registrado, três models e migração inicial;
Managements em `queries/questions/`; cliente paginado em `scholarly/openalex.py`.
`load_taxonomy` valida a árvore inteira, mostra o SHA-256 da versão e só grava com
`--execute`, numa transação. Aceita JSON local com `--file`, preserva versões anteriores
e não duplica nós na repetição. Admin da taxonomia somente de leitura. Testes com resposta
real gravada cobrem níveis, repetição, versões, falhas HTTP, dados incompletos e permissões.
Uso e fontes em [Perfil e Questions](../../../docs/questions_and_profiling.md#carga-implementada-21).

---

## Etapa 2.2 — Critérios em código

**O que fazer**
- `questions/criteria.py`: `EvaluationConfig` (pydantic congelado, validado no import) com os 7 critérios do núcleo, notas discretas e pesos.
- Regras por `paper_type`: quais critérios valem (ex.: sem `replicability` em teórico) e quais papéis de seção existem.
- Tabela papel de seção → critérios do passe (de [Avaliadores e juiz](../../../docs/evaluators_and_judge.md#papéis-e-critérios)).
- Registro de métodos: `method` → `EvaluationConfig`.

**Teste** (`questions/tests/test_criteria.py`)
- Config com nota fora da escala ou peso negativo não importa.
- Todo papel de cada `paper_type` tem pelo menos um critério; todo critério ativo aparece em algum papel.

**Commit sugerido:** `feat: define evaluation criteria and method registry`

**Situação (13/11/2026):** implementada como dependência da curadoria 2.6.
Método `standard` congelado com sete critérios, escala discreta 1–5, pesos
uniformes de desenvolvimento e cobertura por papel e tipo de artigo. Validação
no import recusa escalas, pesos e coberturas inválidos. Valores aguardam calibração
no M3; o agente da curadoria recebe essa configuração em código.

---

## Etapa 2.3 — Profiler e resolução da Question

**O que fazer**
- Agentes `profiler_field()` e `profiler_topic(field)`, papel `fast`. O enum do segundo é montado com `create_model` a partir dos filhos do field escolhido.
- `questions/resolver.py`: cadeia topic → subfield → field → genérica (Chain of Responsibility), só Questions `validated` e `active`.
  - Confiança abaixo do limiar → genérica, com a flag "classificação incerta".
  - Nem a genérica → `SetupRequired`.
- O caminho percorrido e o snapshot da Question (id, versão, textos) saem prontos para o Run.

**Teste**
- `test_profiler.py` (fakes): o segundo passo só aceita topics do field escolhido; saída inválida → nova tentativa com o motivo; tentativas esgotadas → o estágio termina em `error_llm`.
- `test_resolver.py`: cada degrau do fallback; confiança baixa → genérica com a flag; sem genérica → `SetupRequired`.

**Commit sugerido:** `feat: classify articles and resolve the evaluation question`

**Situação (13/11/2026):** implementada. Profiler em dois passos com schemas dinâmicos,
validação de parentesco, confiança conservadora e tentativas limitadas; resolver por
método e versão, somente Questions validadas e ativas, com fallback e snapshot
imutável de todos os textos da rubrica. Limite de tentativas e limiar configuráveis
em `metis/config.py`. Testes com fakes, SDKs contra HTTP local e PostgreSQL real.
O teste de estágio cobre o status `error_llm` ao esgotar as respostas inválidas;
a integração com o workflow e o Run continua na 2.5.

**Verificação (13/11):** 509 testes passaram com PostgreSQL 18 e Python 3.14.10,
com 5 casos `llm` excluídos. Ruff (172 arquivos), mypy (170 arquivos),
`manage.py check` e `makemigrations --check --dry-run` passaram. Os contratos dos
dois provedores usam HTTP local; não exigem chaves nem chamadas a LLMs externos.

---

## Etapa 2.4 — Papéis das seções e mapa do documento

**O que fazer**
- `questions/section_roles.py`: dicionário de títulos em PT e EN por `paper_type`; seção com mais de um papel; `other` para o resto.
- Agente `section_role_classifier()`, só para os títulos ambíguos.
- `questions/document_map.py`: abstract, seções (papel + primeira frase), legendas de figuras e tabelas, montado em código.

**Teste**
- `test_section_roles.py`: "Materiais e métodos", "Methods" e "Approach" viram método; "Experimentos e resultados" ganha dois papéis; título desconhecido vai para o agente; agente ambíguo → `other`.
- `test_document_map.py`: snapshot do mapa de uma fixture.

**Commit sugerido:** `feat: assign section roles and build the document map`

**Situação (13/11/2026):** implementada como dependência da 2.5, com regras PT/EN
por tipo de artigo, classificação apenas dos títulos ambíguos, fallback `other`
e mapa determinístico. Testes cobrem títulos compostos, papéis incompatíveis,
baixa confiança e o conteúdo do mapa.

---

## Etapa 2.5 — Workflow do E2 e o Run

**O que fazer**
- `questions/workflow.py`: o workflow do E2 de [docs/agents.md](../../../docs/agents.md#e2--perfil-questionsworkflowpy).
- Campos no `Run`: `question` (FK), `profile` (JSON: área, confiança, `paper_type`, idioma, papéis, mapa), `config_snapshot` (specs, versões de prompt, versão da taxonomia, snapshot da Question) e `purpose` (`evaluation`, `rubric_check`, `ab_test`; padrão `evaluation`). Migration.
- Runs com `purpose` diferente de `evaluation` não tornam outros runs `superseded` e não aparecem no `GET /api/runs/{id}` de quem submete.
- O stub do E2 no `StageTask` vira o workflow real.

**Teste** (`questions/tests/test_workflow.py`, eager, fakes, fixtures da 1.1)
- Fixture → `profiled`, com `profile`, `question` e `config_snapshot` gravados.
- Sem Question disponível → `waiting_setup`; depois de criar a genérica, "Reprocessar" → `profiled`.
- Retry no meio → a classificação já gravada não chama o agente de novo.

**Commit sugerido:** `feat: run profiling stage and store the run profile`

**Situação (13/11/2026):** implementada. Workflow Agno com política explícita de
propagação de erros; checkpoints de field, classificação, Question, papéis e mapa
no Run. Migration dos quatro campos, snapshot de configuração sem credenciais,
retomada com posse conferida e isolamento dos propósitos internos nas rotas públicas
e na substituição de avaliações. Testes eager com fakes e PostgreSQL real.

Validação: suíte com **533 testes aprovados** (5 testes `llm` fora da execução),
Ruff, mypy, checks do Django e migrations no PostgreSQL 18.

---

## Etapa 2.6 — Curadoria no admin

**O que fazer**
- Agente `question_drafter()`: rascunha a Question a partir do nó da taxonomia e dos critérios, **nunca** de um artigo.
- Admin da Question: ação "Rascunhar Question" (grava com `validated=False`), edição dos `RubricField`, ação "Validar" (incrementa a `version`), "Ativar/Desativar".
- Os runs antigos ficam com o snapshot da versão que usaram.

**Teste** (`questions/tests/test_curation.py`)
- O rascunho nasce com `validated=False` e não entra na resolução.
- Validar incrementa a versão; um run anterior continua com o snapshot antigo.

**Commit sugerido:** `feat: add question curation in the admin`

**Situação (13/11/2026):** implementada. Formulário e ação de rascunho por nó ou
genérica, sem manuscrito como entrada; rubricas em linha; ações de validar,
ativar e desativar, com permissões e histórico do admin. Rascunhos começam
desativados e não validados. Edições exigem nova aprovação, e a validação aumenta
a versão. Gravações atômicas, conflito de escopo tratado, proteção contra edições
obsoletas e leitura consistente do resolver. Runs antigos preservam os snapshots.
Testes com fakes, POSTs reais do admin e PostgreSQL 18. Sem migration nova.

**Verificação:** 564 testes aprovados, com 5 testes `llm` fora da execução;
Ruff, formatação, mypy (187 arquivos) e checks do Django aprovados. O teste de concorrência usa duas
conexões reais para verificar que o resolver não mistura versões das rubricas.

---

## Etapa 2.7 — Questions iniciais e amostra rotulada

**O que fazer**
- A Question genérica + 2–3 áreas (proposta: Computação, Física/Quântica e Saúde; questão aberta Q4), curadas no admin.
- Amostra rotulada: ~10 artigos por área, com o field certo e os papéis das seções, em `evals/data/`.
- Comando `bench_profiling`: acerto do field e dos papéis.

**Pronto quando:** o primeiro número está registrado e vira a meta.

**Implementação (13/11/2026):** catálogo versionado com genérica + Computação,
Física/Quântica e Medicina. `seed_questions` faz dry-run por padrão e cria quatro
rascunhos inativos/não validados com `--execute`, preservando qualquer curadoria
existente no mesmo escopo/método. A revisão, validação e ativação continuam no admin.

`bench_profiling` mede regras locais ou o profiler real (field, topic e papéis
ambíguos), com relatório JSON de métricas, uso, modelos, versões e falhas. A amostra
inclui 30 artigos abertos PLOS ONE, 10 por área, com DOI, atribuição, licença e hash
de origem, em `projects/correction/evals/data/`. Fields vêm do OpenAlex e papéis
foram anotados pelo Codex; são **rótulos provisórios, sem revisão humana independente**.

Primeira referência local registrada: **119/152 papéis (78,29%)**, **F1 micro 0,7885**,
zero falhas e zero chamadas pagas. Esse modo usa o tipo de artigo de referência
e não mede o field. O resultado está em `baseline_rules.json`; não é baseline
de LLM. A rodada com LLM foi autorizada para até 30 artigos e aguarda a credencial
do provedor no clone. A aprovação das rubricas e dos rótulos continua pendente.

Validação: **575 testes passaram**, com 5 contratos ao vivo excluídos; Ruff,
formatação (197 arquivos), mypy (195 arquivos), checks do Django e conferência
de migrações aprovados. Inclui carga concorrente/idempotente, rollback atômico,
preservação de curadoria, métricas multilabel e profiler com fakes sem rótulos
no payload. A taxonomia completa de 4.798 nós foi carregada no banco isolado.

**Commit sugerido:** `feat: seed initial questions and measure profiling`

---

## Pronto do M2

- A amostra rotulada é classificada no field certo (meta da primeira medição).
- O fallback está coberto por testes.
- A curadoria funciona ponta a ponta no admin.
- Os papéis das seções batem com a amostra rotulada.
