# Estado do módulo e metas medidas

Revisão em **16/11/2026**, durante a etapa **3.10 — workflow E4**. Os dados de
benchmark abaixo continuam históricos. Testes com fakes comprovam a integração do
software, não a qualidade científica das avaliações.

## Implementação e limites

| Parte | Implementado | Limite atual e evidência |
|---|---|---|
| Plataforma | API autenticada, estados, posse da task, retries, gate, reconciliador, Docker e admin | O gate existe, mas E3 ainda não produz achados reais. [Estágios](../projects/correction/pipeline/stages.py), [transições](../projects/correction/queries/attempts/run.py) |
| E1 | `ExtractedArticle`, seções, referências, ligações de citações, figuras e descrições, cache e retomada; contrato `ExtractedDocument` da 1.1 definido | Sem fixtures reais PeerRead para fechar a 1.1, sem conversão do E1 para o contrato (1.11), recorte de imagem ou scan de texto oculto. [Extração](extraction.md) |
| E2 | Profiler field/topic, fallback, papéis de seções, mapa, snapshots e retomada | Exige taxonomia carregada e Question validada/ativa; a genérica não é criada na subida. [Workflow](../projects/correction/questions/workflow.py), [operação](questions_and_profiling.md) |
| Questions | Rascunho por agente, revisão/validação/ativação humanas, catálogo inicial | Genérica, Computação, Física/Quântica e Medicina são propostas inativas após `seed_questions`; aprovação especialista não está demonstrada. [Catálogo](../projects/correction/questions/data/initial_questions.json) |
| E3 | Workflow com coleta/detecção de similaridade, resolução e checagens bibliográficas; `Parallel` entre ramos, checkpoints recuperáveis, relatório, regras v2 e gate humano | Implementação em `integridade/fase4-citacoes-cruzamentos`; `coverage` declara limites de OA/full text. Validação de software com fakes não mede qualidade científica nem fecha I5. [Workflow](../projects/correction/integrity/workflow.py), [relatório](integrity_check.md) |
| E4 | Workflow por modo com três slots, checkpoints, validação, juiz, revisão e finalização | A/B e correlação com avaliação humana ainda pendentes. [Workflow](../projects/correction/evaluation/workflow.py), [Stage](../projects/correction/pipeline/stages.py) |
| E5 | Mediana, dispersão, total, concordância descritiva, meta-revisor, `FinalReport` imutável e JSON/Markdown | Exige as últimas rodadas julgadas e finalizadas de A/B/C. Sem elas, `waiting_setup`; integração do rubric check exercita E2/E4/E5 com agentes falsos. [Workflow](../projects/correction/evaluation/workflow.py), [testes](../projects/correction/questions/tests/test_rubric_check_workflow.py) |
| Rubric check | Lotes de 1–20 attempts em cache, rascunho congelado, E3 pulado com auditoria, comparação no admin | Não altera a Question ativa nem publica runs internos na API. Requer configuração de E4 e provedores. [Operação](questions_and_profiling.md#rubric-check-no-admin-312) |
| Uso e custo | `LLMCall`, tokens/custo por chamada e agregações no admin | Orçamento é alerta visual opcional, sem bloqueio de chamadas. Custo desconhecido deixa totais parciais. [Custo](agents.md#consulta-no-admin-62) |
| Evals | Contrato comum, artefatos sem sobrescrita, `bench_profiling`, `compare_evals` e adaptadores `metis.evals` para `bench_plagiarism` e `bench_integrity_phase2` | Testes validam dry-run e persistência com fakes; execução com fixtures/datasets rotulados e registro dos números ainda pendentes. [Evals](evals.md), [integridade](integrity_check.md) |

Uma submissão pode gerar as rodadas de E4 e o relatório de E5 quando os snapshots
e configurações necessários estão disponíveis. A qualidade das notas dos modelos
ainda precisa ser medida contra avaliações humanas e no conjunto A/B.
O `done` do E2E com stubs do M0 foi uma verificação histórica de infraestrutura.
Não comprova o ponto de integração I3 com avaliadores reais.

## Medições disponíveis

| Medição | Resultado registrado | Alcance |
|---|---|---|
| Ligação citação ↔ referência, 12/11 | Recall **244/263 (92,78%)**, precisão **244/264 (92,42%)**; bruto ≈80%/71% | 10 artigos PeerRead, contra science-parse após exclusão de chamadas inválidas do gabarito. Histórico do E1, não nova execução desta revisão. [Protocolo e limitações](extraction.md#como-testar) |
| Papéis por regras, 13/11 | **119/152 (78,29%)**, F1 micro **0,7884615385** | 30 artigos PLOS ONE, tipo de artigo de referência fornecido. Rótulos provisórios sem revisão humana independente. Não mede field, LLM nem extração de PDF. [Baseline](../projects/correction/evals/data/baseline_rules.json), [amostra/licenças](../projects/correction/evals/data/README.md) |
| Regras por área | Computação **44/61 (72,13%)**; Física **34/40 (85%)**; Medicina **41/51 (80,39%)** | 10 artigos por área; conjuntos de papéis comparados por seção, excluindo abstract e referências |
| Consumo do benchmark de regras | **0 chamadas**, 0 tokens, **USD 0** | Apenas regras locais. Não estima custo de um artigo no pipeline |
| Repetição na base 6.1, 13/11 | Mesmos 119/152; diferença **0** no acerto de papéis | Comando real e comparação com baseline legado, que permaneceu intacto; JSONs gerados ficam fora do Git. [Registro da entrega](../planning/2026-11_november/1_plano_completo/10_etapas_m6_qualidade.md#etapa-61--evals-offline) |

O baseline de regras identifica o dataset `plos-openalex-2026-11-13-v1`, SHA-256
`7f806a0f7af155a47cf894f0bfd827594f467119e11aeb044e5beab588049149`.
Os 50 títulos ambíguos dessa amostra não foram decididos por LLM no modo `rules`.
Ainda falta uma medição LLM de field/topic e papéis com relatório registrado.

Os ensaios históricos de figuras e tempos do E1 estão em [Extração](extraction.md#como-testar).
Foram amostras pequenas, anteriores às mudanças seguintes; não definem SLA,
limite seguro de páginas nem completude das tabelas.

## Metas revistas por marco

As referências medidas viram metas locais de não regressão. Comparações exigem
a mesma amostra, rótulos, modo, política e definição das métricas; mudança de
protocolo exige nova versão e nova referência. Métricas ainda não medidas
permanecem sem piso até a primeira medição.

| Marco | Meta após esta revisão | O que falta para fechar |
|---|---|---|
| M0 | Preservar idempotência, posse, recuperação e gate nos testes; repetir I1 com o compose quando o fluxo mudar | O I1 histórico com stubs não substitui I3; carga e capacidade diária continuam sem medição |
| M1 | No protocolo histórico de citações, não regredir em relação a 244/263 de recall e 244/264 de precisão | Guardar amostra/protocolo para nova execução comparável; fixtures reais PeerRead da 1.1, conversão E1 → `ExtractedDocument` (1.11), texto oculto, recortes e limite de páginas seguem pendentes |
| M2 | Na mesma amostra e modo `rules`, manter ao menos 119/152 e o F1 micro do baseline (≈0,78846); acompanhar os três recortes de área | Revisão humana dos rótulos e rubricas; executar `--mode llm` para estabelecer a primeira meta de field/papéis do profiler real |
| M3 | Validar E4 real + E5 em PDF real; medir A/B, qualidade, custo e tempo antes de escolher modo/produção | Sem Spearman, QWK, recall do juiz, custo médio por artigo ou tempo real de E4 registrados. Escala 1–5, pesos 1 e faixas 4/3/2 do E5 são valores de desenvolvimento |
| M4 | Estabelecer precisão, recall e falso positivo por tipo no plágio sintético antes de fixar N/X/K | Detector, corpus, regras e benchmark implementados; executar em corpus real/sintético versionado e registrar números antes de declarar Q11/I4 |
| M5 | Medir referência inventada, falso positivo, SciCiteVal e Citation Integrity antes de definir pisos | Verificadores, alinhamento, cruzamento, regras v2 e comando implementados; datasets não estão no checkout e nenhum número de baseline foi medido/registrado ainda |
| M6 | Comparar relatórios versionados e manter docs aderentes ao código | Base 6.1 e custo 6.2 presentes; correlação PeerRead, endurecimento/carga 6.3 e retenção completa 6.4 permanecem pendentes |

O `compare_evals` recusa métricas incompatíveis; ele não impõe automaticamente
esses pisos no CI. Um resultado pior exige analisar os casos e registrar a
decisão antes de atualizar a referência. Veja [Evals](evals.md#comparar-relatórios).

## Verificação de software usada como referência

A última validação registrada da base 6.1, em **13/11/2026**, usou Linux,
Python **3.14.10**, PostgreSQL **18** e uv **0.13.8**, no código de `32ff4e6`:

- **654 testes passaram**, **5 testes `llm` excluídos**; somente o aviso de
  depreciação já existente do SDK Google.
- Mypy: **237 arquivos** sem erros. Ruff lint e format: **239 arquivos** formatados.
- `manage.py check` sem problemas e `makemigrations --check --dry-run` sem mudanças.

Fonte: [registro da 6.1](../planning/2026-11_november/1_plano_completo/10_etapas_m6_qualidade.md#etapa-61--evals-offline).
São resultados da entrega anterior, preservados como histórico; a revisão 6.4
altera documentação e verifica links, caminhos e aderência ao código, sem
reexecutar benchmarks pagos ou atribuir sucesso aos testes `llm` excluídos.

## Operação, limites e pendências de retenção

As configurações efetivas estão em [config.py](../projects/correction/metis/config.py)
e [`.env.example`](../.env.example). Upload: **50 MiB** por padrão. A task tem
soft/hard limit de **1.500/1.800 s**; chamadas usam o timeout do spec (E1:
`METIS_LLM_TIMEOUT_SECONDS`, padrão **600 s**). Não há limite de páginas nem
timeout separado do pypdf implementados. [Leitura local](../projects/correction/extractor/pdf_text.py).

O fallback de E2 exige carregar a taxonomia, semear as Questions e **revisar,
validar e ativar** a genérica no admin. A geração de rascunho chama o LLM de forma
síncrona no processo web. A/B é planejado; o enum `purpose=ab_test` não cria um runner.
Hoje a fábrica aceita somente OpenAI/GPT e Google/Gemini; um terceiro provedor
exige ampliar os contratos e a fábrica, além de configurar chave e modelo.

O orçamento `METIS_LLM_RUN_BUDGET_USD` começa desativado e só alerta no admin.
Não há custo médio/limite por artigo aprovado em Q2; os custos congelados de
`LLMCall` permitem a medição futura. O rascunho síncrono de Question usa
`NullUsageSink`, sem Run ou `LLMCall`: seu consumo não entra no painel.
O benchmark usa `MemoryUsageSink` e guarda uso no arquivo. Tarifas e IDs documentados são snapshots
da configuração, sem nova conferência de preços ou disponibilidade nesta revisão.

**Q7 segue aberta:** não há prazo de retenção decidido nem comando de limpeza
com dry-run. PDFs ficam no storage privado, checkpoints de extração podem
permanecer após falhas e relatórios são preservados. JSONs de evals fora do Git
também exigirão política local de guarda. O recorte entregue da 6.4 é a revisão
de docs/metas; a política, permissões específicas e limpeza continuam por definir.
Isso não fecha a etapa 6.4 completa nem o pronto do M6.
