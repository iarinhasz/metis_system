# Metis: plano completo do projeto

**Situação revisada em 16/11/2026 (base `13bf6d1`):** plataforma, E1, E2,
curadoria e Questions iniciais, E4 (3.1–3.10), E5, rubric check, custo no admin e base de evals
implementados. O E3 roda enxuto desde 15/11 (texto oculto, regras de risco e gate humano); a trilha de Integridade entregou o `scholarly/` (4.1), o corpus (4.3) e o MinHash (4.5), ainda fora do E3. **Com modelos reais, o pipeline chega ao fim** (ver a 3.10): depois de ajustar as validações do E4 às respostas reais, o ICLR 410 chegou a `done` em 16/11; a qualidade da avaliação ainda precisa ser medida. Recortes, A/B,
benchmarks de avaliação/integridade e as checagens das referências (5.1–5.3) continuam pendentes.
O código fica em `projects/correction/`. O [estado do módulo e as metas revistas](../../../docs/status_and_metrics.md)
registram números, condições e evidências sem declarar os marcos completos.
Conferido em 16/11: a CI inteira (756 testes), os 5 testes com o Gemini e a OpenAI de verdade e, no Docker, um run limpo até o E5 e um PDF com instrução escondida parando no gate e seguindo depois do "continuar".

**Objetivo daqui em diante (15/11):** o pipeline completo, para comparar as nossas avaliações com as reais do PeerRead (notas por critério do ACL 2017, decisão e revisões do ICLR 2017): se a nota acompanha a dos revisores, se a IA é rígida demais e que pontos ela não viu. Para isso, a Plataforma fecha a trilha com as dependências: a 1.7 e o E3 enxuto, sem plágio (feitos em 15/11). A trilha de Avaliação fez o contrato `ExtractedDocument` (1.1 e 1.11) e o E4 (3.1–3.10, em 16/11); falta medir a qualidade contra as revisões reais. A retenção (Q7) saiu do escopo. Os modelos são só `gemini-2.5-flash`, `gpt-5.6-luna` e `gpt-5.4-nano` (Q1).

**Data original:** 05/11/2026
**Base:** o desenho de 25/10 ([1_desenho_inicial](../../2026-10_october/1_desenho_inicial/00_sumario.md)) e os [docs/](../../../docs/README.md)
**Fluxo no Agno:** [docs/agents.md](../../../docs/agents.md); em diagramas, com as entidades e as ligações: [docs/flow_graph.md](../../../docs/flow_graph.md)
**Equipe (07/11):** 4 módulos, um por integrante, com uma branch por etapa e PR para a `dev`: [divisão em módulos](../2_divisao_equipe/divisao_em_modulos.html) (abra no navegador)

---

## O que este plano acrescenta

O desenho de outubro define o sistema e os marcos M0–M6, mas só o M0 tinha etapas. Este plano:

1. **Detalha todos os marcos em etapas** (M0 restante e M1–M6), no formato do M0: o que fazer, por quê, teste, pronto quando, commit.
2. **Desenha o fluxo no Agno de ponta a ponta:** o pacote `agents/`, o catálogo de agentes, um workflow por estágio, o estado, a concorrência, o custo e os fakes ([docs/agents.md](../../../docs/agents.md)).
3. **Organiza o trabalho em 3 trilhas paralelas**, para uma equipe de 3 ou mais pessoas, com pontos de integração e sem datas ([03](03_roteiro_e_trilhas.md)).
4. **Registra as decisões novas** (D14–D21) e as lacunas do desenho que elas resolvem ([01](01_diagnostico.md)).

As decisões D1–D13 continuam valendo, com os ajustes indicados abaixo.

## Decisões (05/11)

| # | Pergunta | Decisão | Alternativas descartadas |
|---|---|---|---|
| D14 | Como ter 3 avaliadores com chave só da OpenAI e do Google? | A = GPT, B = Gemini, C = outro modelo de uma das duas famílias (tamanho ou geração diferente). O C troca de provedor só por config. O juiz é sempre da **outra** família (juiz cruzado). Ajusta a D3 e a D10 | 3ª família via OpenRouter ou Ollama agora; só 2 avaliadores |
| D15 | Onde fica o código? | Monorepo: `projects/correction/` (`metis/` + apps), com imports `projects.correction.*`; `dataset_project/` fica à parte. Já aplicado | Apps na raiz do repositório |
| D16 | Onde o Agno pode ser usado? | Todo estágio executa um Workflow Agno, montado no `workflow.py` do app. `Agent` e modelos só em `agents/`. Um teste de fronteira de imports garante isso. Refina a regra "só `agents/` instancia o Agno" | Workflows dentro de `agents/` (que passaria a depender dos apps); Agno só nos estágios com LLM |
| D17 | Como o loop do juiz garante que a última revisão é verificada? | A rodada 1 é validada e julgada fora do loop; depois, `Condition(há pendências)` → `Loop([revisar, validar, julgar], máx. 2)`; o que sobra vira `unresolved`. Corrige o esboço `[judge, revise]` | Loop `[judge, revise]` (a última revisão sairia sem juiz) |
| D18 | Como rodar rubric check e A/B sem tocar a Question ativa? | Como **Runs** com `purpose` (`evaluation`, `rubric_check`, `ab_test`) e `config_snapshot` próprios, reaproveitando o pipeline | Workflow de teste à parte; avaliação direta no admin, fora do pipeline |
| D19 | Como M2 e M3 começam antes do M1 terminar? | O contrato `ExtractedDocument` (pydantic) vem primeiro, junto com um conversor PeerRead → fixtures | Esperar a extração real |
| D20 | Como controlar a concorrência das threads do Agno? | `ProviderLimiter` por provedor + `bounded_map` com limite, fechando a conexão do Django em cada thread | `Parallel` sem limite; um pool por passo sem limite global |
| D21 | Em que ordem roda o gate de qualidade do E1? | Antes da descrição das figuras, para não pagar visão por um PDF que vai ser rejeitado | Depois da descrição (ordem do desenho inicial) |

O detalhe de cada uma está em [docs/agents.md](../../../docs/agents.md) e nos docs ajustados.

**Aplicação atual da D16:** E2 e E5 têm Workflow Agno; E1 usa sessão e
`bounded_map` sem Workflow. E3/E4 permanecem stubs. A fronteira de `Agent` e
modelos em `agents/` está implementada e testada; os esboços não comprovam
implementação de todos os workflows.

## Visão do caminho

```text
            ┌─ Trilha P: M0 0.4–0.7 ──▶ extração real (M1) ──▶ E5 + relatório ──▶ M5 ─┐
I0 (hoje) ──┼─ Trilha A: contrato + spike + agents/ ──▶ M2 ──▶ E4 (M3) ──▶ A/B ───────┼──▶ M6
            └─ Trilha I: scholarly/ + corpus + léxico ──▶ referências + semântico ──▶ M4 ──▶ M5 ─┘
```

Pontos de integração: I1 (M0), I2 (E1 real + `agents/`), I3 (M3), I4 (M4), I5 (M5), I6 (M6). O detalhe está em [03](03_roteiro_e_trilhas.md).

## Fora daqui

Continua o que estava fora no desenho inicial: detector de texto gerado por IA, interface própria além do admin, acordos com editoras e webhook (Q6).

## Arquivos deste plano

| Arquivo | Conteúdo |
|---|---|
| [01_diagnostico.md](01_diagnostico.md) | Estado do código, o que se reaproveita, lacunas do desenho, o que confirmar no Agno 3 |
| [02_fluxo_agno.md](02_fluxo_agno.md) | O fluxo no Agno do ponto de vista da construção: qual etapa cria cada peça, e em que ordem |
| [03_roteiro_e_trilhas.md](03_roteiro_e_trilhas.md) | Marcos M0–M6, dependências, 3 trilhas e pontos de integração |
| [04_etapas_m0_restante.md](04_etapas_m0_restante.md) | Pendências da 0.3 e etapas 0.4–0.7 |
| [05_etapas_m1_extracao.md](05_etapas_m1_extracao.md) | M1: contrato, spike do Agno, `agents/`, `LLMCall`, divisão do artigo pelo modelo (1.5, feita), figuras, E1 |
| [06_etapas_m2_perfil.md](06_etapas_m2_perfil.md) | M2: taxonomia, critérios, profiler, papéis das seções, curadoria |
| [07_etapas_m3_avaliacao.md](07_etapas_m3_avaliacao.md) | M3: avaliadores, validadores, juiz, revisão, E5, rubric check, A/B |
| [08_etapas_m4_integridade_fase1.md](08_etapas_m4_integridade_fase1.md) | M4: `scholarly/`, referências, corpus, funil de similaridade, regras, gate |
| [09_etapas_m5_integridade_fase2.md](09_etapas_m5_integridade_fase2.md) | M5: existência, retratação, consistência, alinhamento, regras v2 |
| [10_etapas_m6_qualidade.md](10_etapas_m6_qualidade.md) | M6: evals, custo, endurecimento, retenção, docs |
| [11_riscos_e_questoes.md](11_riscos_e_questoes.md) | Riscos R1–R17 e questões Q1–Q15 |
| [12_testes_e_verificacao.md](12_testes_e_verificacao.md) | Testes por marco e verificação manual por ponto de integração |
