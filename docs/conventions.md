# Convenções

## Princípios

- **Prioridade:** correção > clareza > simplicidade > manutenibilidade.
- **Nada de abstração especulativa** nem de camadas hexagonais mecânicas. Uma interface entra quando há duas implementações reais ou quando o teste precisa de um fake.
- **Uma função longa e coesa é melhor** que a lógica espalhada em pedaços.
- **Atenção a consultas:** N+1, transações curtas.

## Organização

O código é organizado por domínio (apps Django). Cada app tem `models.py`, `api/`, `admin.py` e `tests/`. Em `api/`, o `schemas.py` tem os contratos de entrada e saída e o `routes.py` tem as rotas. Os casos de uso ficam em `services/` do app, ou em `pipeline/services.py` quando iniciam ou retomam um run, e as consultas ao banco em `queries/<app>/`. As regras de dependência entre módulos estão em [Arquitetura](architecture.md#apps-e-regras-de-dependência).

## Regras do código

| Regra | Por quê |
|---|---|
| O status de um Run só muda por `RunManagement` (valida + grava evento na mesma transação) | Um único dono da máquina de estados |
| Tasks são publicadas só depois do commit (`transaction.on_commit`) | A task nunca lê estado que ainda não foi gravado |
| A mensagem Celery leva só ids | O banco é a fonte da verdade |
| Cada arquivo tem uma responsabilidade. A rota só recebe, chama o caso de uso e responde; schemas, regra de negócio e helpers ficam nos módulos próprios | A regra fica testável sem HTTP, e o arquivo de rotas mostra a API de relance |
| Variáveis de ambiente só em `metis/config.py` (o ruff TID251 bloqueia o resto) | Nada de `os.getenv` espalhado, com nomes divergentes |
| O Agno só é instanciado pela `AgentFactory` | Um ponto para modelos, retries, telemetria e fakes |
| APIs acadêmicas só por `scholarly/` | Rate limit, cache e chaves num lugar |
| Status, estágios, vereditos e categorias são enums, nunca strings soltas | Erro de digitação vira erro de import |
| Todo acesso ao banco (consultar ou criar) fica em `projects/correction/queries/<app>/`, num Management por model (`RunManagement`, `RunEventManagement`…). O model herda o Management, e o código chama o método na classe: `Run.get_with_events(run_id)`, nunca `Run.objects…`. Vale para API, pipeline, services e testes | Consultas num lugar só: reaproveitáveis, testáveis e fáceis de revisar (N+1, locks) |
| Saídas são estruturadas (pydantic/JSON); nunca uma string que outra parte do código parseia | Parsear texto livre quebra quando o formato muda |
| Nada de texto do manuscrito, dado pessoal ou segredo em log | Os manuscritos são inéditos e confidenciais |
| Comandos de gestão rodam em dry-run por padrão e só gravam com `--execute` | Operação segura |

## Padrões de projeto

| Padrão | Onde | Por que se paga |
|---|---|---|
| Factory | `ModelFactory(ModelSpec)` → modelo Agno; `AgentFactory` → profiler, describer, evaluator, judge, meta-revisor, adjudicadores | Único ponto que instancia o Agno; nos testes devolve fakes |
| Registry + Factory | Método de avaliação → `EvaluationConfig` | Um método novo entra registrando o config, sem mexer no pipeline |
| Builder | `EvaluationContextBuilder`, `RevisionPromptBuilder` | Objetos montados de várias fontes, validados no `build()` |
| Strategy | `CandidateSource` (interno, citadas, S2, arXiv, OpenAlex), `SimilarityDetector` (léxico, semântico), modo de avaliação (`sectioned`, `whole_document`) | Várias implementações reais desde o início; os dois modos de avaliação são necessários para o A/B |
| Chain of Responsibility | Validadores antes do juiz; fallback da Question | Ordem explícita, cada elo testável |
| Template Method | `StageTask` | Claim, persistência e eventos iguais em todo estágio |
| Repository (Managements em `queries/<app>/`, herdados pelo model) | `ArticleManagement`, `AttemptManagement`, `RunManagement`, `RunEventManagement` | Status só via `RunManagement` + evento; consultas fora de `queries/` não existem |

## Prompts

- **Onde e como:** arquivos `.md` em `agents/prompts/`, com marcadores `<<nome>>`.
  - O render falha se sobrar marcador.
  - `str.format` é proibido, porque os prompts têm exemplos em JSON.
- **Versão:** é o hash do conteúdo, gravado em cada `LLMCall`.
- **Exemplos JSON:** gerados a partir do `output_schema`. Assim prompt e schema não divergem (um campo com um nome no exemplo e outro no schema).
- **Ordem:** o artigo vem primeiro (prefixo estável para o cache), entre delimitadores, marcado como dado.
- **Por papel de seção:** um prompt por papel (`agents/prompts/sections/<papel>.md`), com o checklist daquele papel.

## Testes

- **Banco real:** pytest + pytest-django, com o Postgres do compose. Sem mock nem patch.
- **LLM:** a `AgentFactory` devolve fakes que respondem conforme o `output_schema`, inclusive "inválido N vezes" e "quote inexistente".
- **APIs externas:** respostas HTTP reais gravadas (cassetes).
- **Celery:** modo eager nos testes; o E2E roda com `docker compose`.
- **Todo bug corrigido ganha teste de regressão.**
- **Arquivos de teste pequenos**, um por módulo.
- **Evals offline** (`evals/`) ficam fora do CI e são acompanhados por versão de prompt e por `ModelSpec`.

## Qualidade

- **ruff** (lint + format, com `banned-api`) e **mypy** (django-stubs + plugin do pydantic; funções sem tipo só nos testes), rodando no CI desde o M0.
- O PR atualiza os docs que descrevem o que ele mudou.

## Git e planejamento

- **Commits:** Conventional Commits em inglês (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`), um commit por etapa.
- **Idioma:** docs, comentários e docstrings em português; identificadores em inglês.
- **Planejamento:** uma pasta por tema em `planning/<ano-mês>/<n>_<tema>/`, com `00_sumario`, `01_diagnostico`, uma `0N_etapa…` por etapa e `NN_testes_e_verificacao`.
