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

---

## Etapa 2.7 — Questions iniciais e amostra rotulada

**O que fazer**
- A Question genérica + 2–3 áreas (proposta: Computação, Física/Quântica e Saúde; questão aberta Q4), curadas no admin.
- Amostra rotulada: ~10 artigos por área, com o field certo e os papéis das seções, em `evals/data/`.
- Comando `bench_profiling`: acerto do field e dos papéis.

**Pronto quando:** o primeiro número está registrado e vira a meta.

**Commit sugerido:** `feat: seed initial questions and measure profiling`

---

## Pronto do M2

- A amostra rotulada é classificada no field certo (meta da primeira medição).
- O fallback está coberto por testes.
- A curadoria funciona ponta a ponta no admin.
- Os papéis das seções batem com a amostra rotulada.
