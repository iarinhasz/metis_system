# Metis

Avaliador de artigos científicos com IA. O Metis recebe o PDF de um artigo e:

1. extrai o conteúdo: seções, referências, citações, figuras e tabelas descritas, e texto escondido no PDF;
2. identifica a área do artigo e escolhe a rubrica de avaliação (Question);
3. checa a integridade e, com risco alto, para o processo para uma pessoa decidir;
4. faz três avaliações independentes, seção por seção, com modelos de duas famílias (GPT e Gemini), conferidas por um juiz;
5. consolida as notas num relatório com uma recomendação: aceitar, revisão menor, revisão maior ou rejeitar.

O sistema recomenda; não decide sozinho. Risco alto e pontos sem consenso vão para revisão humana.

> **Situação (16/11/2026):** a plataforma, o E1 (extração), o E2 (perfil e Question), o E3 enxuto (texto oculto, regras de risco e gate humano), o E4 (avaliadores, juiz e revisão), o E5 (consolidação), a curadoria das Questions, o rubric check e o custo no admin estão implementados. **Um PDF real já chega ao relatório final** (ICLR 410, 16/11, cerca de 15 min e US$ 1,07). A qualidade da avaliação ainda está sendo medida: muitas citações dos avaliadores não batem com o texto e são descartadas, e a comparação com as revisões reais do PeerRead está em andamento. As checagens das referências no E3 (existência, retratação e consistência) também estão em andamento. Detalhes em [estado e métricas](docs/status_and_metrics.md) e na [divisão em módulos](planning/2026-11_november/2_divisao_equipe/divisao_em_modulos.html) (abra no navegador).

## Como funciona

```text
PDF ─▶ E1 Extração ─▶ E2 Perfil ─▶ E3 Integridade ─┬─▶ E4 Avaliação ─▶ E5 Consolidação ─▶ relatório
       seções, refs,  área, tópico  texto oculto,   │   3 avaliadores    mediana,
       citações,      e Question    regras de risco │   e juiz cruzado   meta-revisão
       figuras                                      └─▶ risco alto: gate humano
```

| Estágio | O que faz | Situação |
|---|---|---|
| E1 Extração | Divide o artigo com o Gemini e confere cada seção contra o texto do PDF; separa as referências e liga as citações; lista e descreve figuras e tabelas; procura texto escondido | Implementado |
| E2 Perfil | Classifica área e tópico pela taxonomia do OpenAlex, escolhe a Question e o papel de cada seção | Implementado |
| E3 Integridade | Transforma o texto escondido em achados, aplica as regras de risco e, com risco alto, para no gate humano | Implementado (enxuto); checagens das referências em andamento |
| E4 Avaliação | Avaliadores A, B e C por seção e por critério; juiz cruzado; até 2 rodadas de revisão | Em andamento |
| E5 Consolidação | Mediana e concordância das notas, meta-revisão e o relatório final em JSON e Markdown | Implementado |

Cada estágio roda numa task Celery, com checkpoint no banco: se um estágio cai, só ele é refeito, e o E1 retoma das respostas do modelo que já tinha guardado. O passo a passo está em [Fluxo de uma avaliação](docs/evaluation_flow.md).

## Requisitos

- Docker com o Compose v2.
- Uma chave da API do Google Gemini, usada no E1 e no E2.
- Uma chave da API da OpenAI, usada no E4 e no E5. Só é necessária quando o E4 estiver pronto.
- Para desenvolver e rodar os testes fora do Docker: Python 3.14 e [`uv`](https://docs.astral.sh/uv/).

## Como executar

### 1. Configurar o `.env`

```bash
cp .env.example .env
```

Preencha no `.env`:

| Variável | Para quê |
|---|---|
| `METIS_SECRET_KEY` | Chave do Django. Use um valor aleatório |
| `METIS_API_TOKEN` | Token que quem envia os artigos usa na API. Vazio, a API recusa tudo |
| `GEMINI_KEY` | Chave do Google Gemini (E1, E2 e avaliador B) |
| `METIS_OPENAI_API_KEY` | Chave da OpenAI (avaliadores A e C, juiz e meta-revisor) |

Para gerar valores aleatórios para os dois primeiros:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

As outras variáveis já vêm com valores que funcionam. Entre elas estão o limite de upload (`METIS_MAX_UPLOAD_MB`, 50 MB), as portas (`METIS_WEB_PORT`, 8100) e os modelos de cada papel. O projeto usa só três modelos: `gemini-2.5-flash`, `gpt-5.6-luna` e `gpt-5.4-nano`.

### 2. Subir os serviços

```bash
docker compose up -d --build
curl http://localhost:8100/health/          # {"status": "ok"}
```

O compose sobe a API (`web`), três workers Celery (extração, integridade e avaliação), o beat, o Flower, o Postgres e o Redis. As migrações rodam sozinhas na subida da API ([Infraestrutura](docs/infrastructure.md)).

### 3. Criar o usuário do admin

```bash
docker compose exec web python manage.py createsuperuser
```

O admin fica em http://localhost:8100/admin/.

### 4. Preparar o perfil (uma vez só)

O E2 precisa da taxonomia do OpenAlex e de uma Question ativa. Os comandos rodam em dry-run e só gravam com `--execute`:

```bash
docker compose exec web python manage.py load_taxonomy --execute    # 4.798 áreas e tópicos
docker compose exec web python manage.py seed_questions --execute   # 4 Questions em rascunho
```

Depois, no admin, em **Questions**, revise a Question **Genérica — avaliação científica**, selecione-a e aplique a ação **Validar** e depois a ação **Ativar**. As de Computação, Física e Medicina são opcionais.

Sem taxonomia ou sem Question ativa, o run para no E2 em `waiting_setup` ([Configuração e curadoria](docs/questions_and_profiling.md#questions-iniciais-e-benchmark-27)).

### 5. Pronto

- API: http://localhost:8100/api/ (com `METIS_DEBUG=true`, a documentação interativa fica em http://localhost:8100/docs)
- Admin: http://localhost:8100/admin/
- Flower (filas do Celery): http://127.0.0.1:5556

## Como enviar um artigo para avaliar

Os artigos entram pela API, com o token do `.env` no cabeçalho `Authorization: Bearer`. Cada envio cria (ou reaproveita) uma versão do artigo e um run, e o run percorre os estágios sozinho.

### O arquivo

| Requisito | Detalhe |
|---|---|
| Formato | PDF de verdade (o arquivo precisa começar com `%PDF-`); outro formato volta com `400` |
| Tamanho | Até 50 MB (`METIS_MAX_UPLOAD_MB`). Acima de 18 MB, o PDF vai ao modelo como texto, sem as figuras |
| Conteúdo | Um artigo científico com **resumo** e **referências**. Sem um deles, o run termina em `rejected_invalid_submission` logo depois do mapa das seções |
| Idioma | Português, inglês ou espanhol: o resumo e as referências são achados por esses nomes ("Resumo", "Abstract", "Resumen", "Referências", "References"…) |
| PDF com texto | O ideal. Num PDF escaneado (só imagem), o modelo ainda lê as páginas, mas a extração fica sem a conferência contra o texto, e a busca de texto escondido não tem o que achar |

Junto do PDF vai o **`external_id`**, o identificador do artigo no sistema de quem envia (até 255 caracteres). Ele liga as versões de um mesmo artigo.

### Enviar um PDF

```bash
TOKEN=...   # o METIS_API_TOKEN do .env

curl -H "Authorization: Bearer $TOKEN" \
  --form-string external_id=artigo-1 \
  -F file=@artigo.pdf \
  http://localhost:8100/api/attempts
```

| Resposta | Quando |
|---|---|
| `202` | Versão nova: o run foi criado e o E1 já está na fila |
| `200` | O mesmo arquivo para o mesmo `external_id`: devolve a versão e o run que já existem, sem refazer nada |
| `400` | PDF inválido, vazio ou acima do limite, ou `external_id` em branco (a mensagem diz o motivo) |
| `422` | Falta o campo `file` ou o campo `external_id` |
| `401` | Token ausente ou errado (ou `METIS_API_TOKEN` vazio) |

O corpo traz `attempt_id`, `run_id`, `attempt_number`, `status` e `created`. Guarde o `run_id`.

### Vários PDFs de uma vez

Um envio por arquivo, usando o nome do arquivo como `external_id`:

```bash
for pdf in artigos/*.pdf; do
  curl -s -H "Authorization: Bearer $TOKEN" \
    --form-string "external_id=$(basename "$pdf" .pdf)" \
    -F "file=@$pdf" \
    http://localhost:8100/api/attempts
  echo
done
```

Os runs rodam em paralelo, nos limites de cada fila. Se o mesmo PDF for enviado com outro `external_id`, o E1 reaproveita a extração já feita e não chama o modelo de novo.

### Nova versão do mesmo artigo

Envie o arquivo novo com o **mesmo `external_id`**. Ele vira a versão seguinte (`attempt_number` 2, 3…), com um run novo. Os runs ainda em andamento das versões anteriores passam para `superseded`.

### Acompanhar o run

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/api/runs/<run_id>
```

A resposta traz o `status`, o estágio atual, o último erro e todos os eventos do run (só contagens e ids, nunca texto do artigo). O caminho normal é:

```text
received → extracting → extracted → profiling → profiled → checking_integrity
→ integrity_checked → evaluating → evaluated → consolidating → done
```

| Status | O que significa | O que fazer |
|---|---|---|
| `waiting_human_review` | O E3 achou risco alto (por exemplo, uma instrução escondida para revisores de IA) | Decidir no gate (abaixo) |
| `waiting_setup` | Falta configuração: chave do modelo, taxonomia, Question ativa ou as rodadas completas do E4 | Completar a configuração e usar *Reprocessar* na página do run, no admin |
| `rejected_invalid_submission` | O PDF não tem resumo ou referências | Enviar outro arquivo |
| `error_llm` | O modelo ficou fora do ar depois de todas as tentativas | *Reprocessar* no admin: o estágio recomeça, e o E1 aproveita as respostas já guardadas |
| `closed_by_reviewer` | Alguém encerrou o run no gate | — |
| `superseded` | Chegou uma versão nova do artigo | Acompanhar o run da versão nova |

### Gate humano

Com risco alto, o run espera uma decisão. Ela pode ser tomada:
- **no admin**, na página do run: os achados aparecem com o trecho do artigo, e há os botões *Continuar avaliação* e *Encerrar*, com um campo para a nota;
- **pela API:**

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"decision": "continue", "note": "Achado conferido no PDF."}' \
  http://localhost:8100/api/runs/<run_id>/decision
```

`continue` segue para o E4; `close` encerra o run. A nota vai para o histórico do run.

Para alguém decidir no gate sem ser administrador, crie um usuário com acesso ao admin (`is_staff`) e ponha-o no grupo **revisores**: ele vê o run e os achados e decide no gate, sem poder mexer no resto.

### Resultados

```bash
# Achados da integridade (409 enquanto o E3 não rodou)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/api/runs/<run_id>/integrity

# Relatório final em JSON ou Markdown (409 até o run chegar a done)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/api/runs/<run_id>/report
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8100/api/runs/<run_id>/report?format=markdown"
```

No admin também ficam:
- a trilha de eventos de cada run;
- os relatórios de integridade;
- o custo de cada chamada aos modelos, por run, estágio, papel e modelo;
- a curadoria das Questions e o rubric check, que roda uma Question em rascunho numa amostra de artigos.

### Testar com artigos do PeerRead

O [PeerRead](https://github.com/allenai/PeerRead) tem artigos de computação com as avaliações reais. Baixe o repositório em `dataset_project/raw/` (essa pasta fica fora do git) e envie, por exemplo, um artigo do ICLR 2017:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  --form-string external_id=iclr2017-410 \
  -F file=@dataset_project/raw/PeerRead-master/data/iclr_2017/train/pdfs/410.pdf \
  http://localhost:8100/api/attempts
```

Hoje esse run passa pelo E1 (cerca de 1 min 40 s e US$ 0,12 para as 13 páginas), pelo E2 (cerca de 1 min) e pelo E3, e pelo E4 (cerca de 12 min, três avaliadores, juízes e revisão) e o E5, e termina em `done`, com o relatório em `GET /api/runs/<run_id>/report`. Se o E4 falhar, a mensagem do erro, na página do run, diz que passo falhou e por quê.

## Desenvolvimento

Para preparar o ambiente fora do Docker:

```bash
uv sync --group dev --group analysis
cp .env.example .env
uv run python manage.py check
```

Os testes usam o Postgres do compose, publicado em `127.0.0.1:5440`:

```bash
docker compose up -d postgres
uv run ruff check && uv run ruff format --check
uv run python manage.py makemigrations --check --dry-run
uv run mypy projects/correction
uv run pytest
```

São os mesmos passos da CI. O `pytest` padrão não chama nenhum modelo. Os testes contra os modelos de verdade usam as chaves do `.env` e rodam à parte:

```bash
uv run pytest -m llm
```

Comandos de manutenção e medição (todos em dry-run por padrão; rodam de verdade com `--execute`):

| Comando | Para quê |
|---|---|
| `load_taxonomy` | Carrega a taxonomia do OpenAlex |
| `seed_questions` | Cria as Questions iniciais em rascunho |
| `bench_citation_links` | Mede a ligação citação ↔ referência contra o gabarito do PeerRead |
| `bench_profiling` | Mede o perfil (área e papéis das seções) numa amostra rotulada |
| `compare_evals` | Compara dois relatórios de medição |

O código Django fica em `projects/correction/`. São eles: `metis/` (configuração); os apps de domínio `attempts`, `pipeline`, `extractor`, `questions`, `integrity`, `evaluation` e `evals`; `agents/`, o pacote dos agentes; e `queries/`, todo o acesso ao banco. As convenções estão em [docs/conventions.md](docs/conventions.md).

## Modelos de IA e custo

| Modelo | Onde |
|---|---|
| `gemini-2.5-flash` | E1, E2, avaliador B, juiz do Google, adjudicador e descrição de figuras |
| `gpt-5.6-luna` | Avaliador A, juiz da OpenAI e meta-revisor |
| `gpt-5.4-nano` | Avaliador C |

Cada chamada fica registrada com tokens e custo (`LLMCall`), e o admin soma por run, estágio, papel e modelo. Um orçamento de alerta por run pode ser ligado com `METIS_LLM_RUN_BUDGET_USD`.

## Stack

Django 6 + Django Ninja · Celery + Redis · PostgreSQL 18 + pgvector · Agno 3 com Gemini e OpenAI · pypdf e pdfplumber · Docker Compose

## Documentação

- [docs/](docs/README.md): como o sistema funciona. Cobre a arquitetura, o fluxo, a orquestração, cada estágio, os modelos de dados, a infraestrutura e as convenções.
- [planning/](planning/2026-11_november/1_plano_completo/00_sumario.md): o plano completo (M0–M6), com as decisões, os riscos e os testes de cada marco.

## Dados

`dataset_project/` tem o loader e a análise do PeerRead (artigos de computação com avaliações e notas por aspecto), usados nas medições do E1. A amostra rotulada do perfil (30 artigos PLOS ONE) está em `projects/correction/evals/data/`. Resultados e limites estão em [estado e métricas](docs/status_and_metrics.md#medições-disponíveis).
