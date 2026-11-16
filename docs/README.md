# Documentação do Metis

Revisados contra o código em **16/11/2026** (etapa 3.10, workflow E4).
E1, E2, E4 e E5 têm implementação; E3 permanece stub. As partes ainda
planejadas estão identificadas nos documentos. O código é a fonte de verdade;
o [estado do módulo e as metas medidas](status_and_metrics.md) distinguem
implementação, testes com fakes, resultados históricos e verificações pendentes.

O plano de construção (decisões, marcos, riscos) está em [planning/2026-10_october/1_desenho_inicial](../planning/2026-10_october/1_desenho_inicial/00_sumario.md). O plano completo, com as etapas de todos os marcos e as trilhas da equipe, está em [planning/2026-11_november/1_plano_completo](../planning/2026-11_november/1_plano_completo/00_sumario.md).

Os caminhos de código citados nos docs (`metis/config.py`, `attempts/`, `agents/`…) são relativos a `projects/correction/`.

## Ordem recomendada

1. [Estado e métricas](status_and_metrics.md): o que funciona, medições e metas revistas por marco.
2. [Arquitetura](architecture.md): componentes, responsabilidades e limites.
3. [Fluxo de uma avaliação](evaluation_flow.md): o que acontece com um artigo, da submissão ao relatório. Em diagramas: [Grafo do fluxo](flow_graph.md), com as entidades e as ligações entre elas.
4. [Orquestração](orchestration.md): como Celery e Agno dividem o trabalho, retries e recuperação.
5. [Agentes e workflows](agents.md): o pacote `agents/`, o catálogo de agentes e os fluxos implementados e planejados.
6. Os estágios, na ordem do pipeline:
   1. [Extração](extraction.md)
   2. [Perfil e Questions](questions_and_profiling.md)
   3. [Checagem de integridade](integrity_check.md)
   4. [Avaliadores, juiz e consolidação](evaluators_and_judge.md)
7. [Modelos de dados](data_models.md): entidades e máquina de estados.
8. [Infraestrutura](infrastructure.md): serviços do Docker, configuração e chaves.
9. [Convenções](conventions.md): organização do código, padrões, prompts e testes.

## Índice

| Documento | Conteúdo |
|---|---|
| [Estado e métricas](status_and_metrics.md) | Implementação atual, referências medidas, metas revistas e pendências |
| [Evals offline](evals.md) | Executar benchmarks, guardar e comparar relatórios por prompt e ModelSpec |
| [Arquitetura](architecture.md) | Componentes, divisão Celery × Agno, apps e regras de dependência, segurança, limites conhecidos |
| [Fluxo de uma avaliação](evaluation_flow.md) | Submissão, estágios E1–E5, gate humano, versões, reprocessamento, endpoints da API |
| [Orquestração](orchestration.md) | Estágios e checkpoints, ciclo de uma task, posse do estágio, erros, retries, reconciliador, regras do Agno |
| [Grafo do fluxo](flow_graph.md) | Diagramas: entidades e como se ligam, o que cada estágio grava e lê, os passos e agentes de cada estágio, estados da execução |
| [Agentes e workflows](agents.md) | Fronteiras do Agno, pacote `agents/`, modelos e juiz cruzado, catálogo de agentes, workflow por estágio, estado, concorrência, custo, testes |
| [Extração](extraction.md) | Divisão do artigo por chamadas ao modelo, `DocumentConfig`, conferência contra o PDF, `Extraction` |
| [Perfil e Questions](questions_and_profiling.md) | Taxonomia, classificação do artigo, resolução da Question, papéis das seções e mapa do documento, critérios, curadoria |
| [Checagem de integridade](integrity_check.md) | Fases 0, 1 e 2, regras de risco, relatório, gate, APIs acadêmicas |
| [Avaliadores, juiz e consolidação](evaluators_and_judge.md) | Passes por seção, checagens entre seções, síntese, validadores, juiz, revisão parcial, A/B do modo de avaliação, relatório final |
| [Modelos de dados](data_models.md) | Models por app, estados do Run e transições |
| [Infraestrutura](infrastructure.md) | docker-compose, variáveis de ambiente, portas, chaves externas, CI |
| [Convenções](conventions.md) | Regras do código, padrões de projeto, prompts, testes, commits |

## Vocabulário

| Termo | Significado |
|---|---|
| Artigo (`Article`) | O trabalho científico, identificado pela chave de quem o submete |
| Attempt | Uma versão enviada do artigo (um PDF). Reenviar o artigo corrigido cria a attempt seguinte |
| Run | Uma execução do pipeline sobre uma attempt. Reavaliar com outra configuração cria outro Run |
| Estágio | Uma das cinco etapas do pipeline (E1 extração … E5 consolidação). Cada uma roda numa task Celery |
| Checkpoint | Status estável entre dois estágios (ex.: `extracted`). É dele que um estágio parte, e é para ele que se volta numa falha recuperável |
| Question | O perfil de avaliação de uma área (ex.: computação quântica): rubricas com o contexto do domínio + método de avaliação |
| RubricField | Um campo da rubrica de uma Question, com o texto de contexto do domínio (`rubric_text`) |
| Critério | O que é pontuado (ex.: originalidade, solidez). Definido em código, com notas discretas |
| Avaliador | Um dos 3 slots: A = GPT, B = Gemini, C = outro modelo de uma das duas famílias (E4 planejado) |
| Papel da seção | A função de uma seção no artigo (introdução, método, resultados…). Define o prompt e os critérios do passe |
| Mapa do documento | Abstract, seções com papel e primeira frase, legendas de figuras e tabelas. Montado em código; vai em todo passe |
| Passe por seção | Uma chamada de um avaliador sobre uma seção. Produz observações, sem nota |
| Observação | Ponto forte, ponto fraco, ausência ou inconsistência numa seção, com trecho literal como evidência |
| Checagem entre seções | Verificação do que cruza partes do artigo (promessa × resultado, método × pergunta, figura × texto) |
| Síntese | A nota e a justificativa de um critério, construídas a partir das observações e checagens |
| Juiz | O modelo que verifica, com o artigo inteiro, se observações e sínteses estão aterradas e coerentes. Não dá nota |
| Rodada | Uma passagem avaliador → juiz. Só o que foi invalidado volta numa rodada nova (no máximo 2 revisões) |
| Item `unresolved` | Observação ou critério que continuou inválido após as rodadas: sai da nota e vai para revisão humana |
| Relatório de integridade | Achados de similaridade, citações e texto oculto, com evidências e o nível de risco |
| Gate | O ponto depois da integridade em que risco alto pausa o run para revisão humana |

Tokens, senhas e chaves de API não devem ser copiados para estes documentos.
