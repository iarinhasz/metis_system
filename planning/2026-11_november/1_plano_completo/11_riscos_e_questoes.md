# Riscos e questões abertas

Revisão de 13/11/2026: as mitigações abaixo são o plano, não controles todos
ativos. [Estado, números e metas](../../../docs/status_and_metrics.md) discriminam
o que já existe. E3/E4, scan de texto oculto e bloqueio por orçamento são pendentes.

Os riscos R1–R12 e as questões Q1–Q14 vêm do [desenho de outubro](../../2026-10_october/1_desenho_inicial/04_riscos_e_questoes_abertas.md). Aqui estão revistos, com os novos.

## Riscos

| # | Risco | Impacto | Mitigação | Etapa |
|---|---|---|---|---|
| R1 | Custo de LLM por artigo acima do esperado | Inviabiliza o volume | `LLMCall` desde a 1.4; orçamento por run; cache do prefixo; validadores antes do juiz; revisão parcial; o A/B mede | 1.4, 3.13, 6.2 |
| R2 | Cobertura limitada da similaridade | Plágio não detectado | `coverage` no relatório; obras citadas como candidatas; corpus cresce a cada submissão | 4.3, 4.4 |
| R3 | Falso positivo de plágio | Acusação injusta | Filtro por citação; regras calibradas; gate humano; nunca rejeição automática | 4.7, 4.10 |
| R4 | Manuscrito inédito enviado a provedores de LLM | Vazamento | Conferir a retenção da OpenAI e do Google antes do primeiro uso real; embeddings locais; telemetria do Agno desligada; logs sem conteúdo | 1.2, 1.3 |
| R5 | Esforço de curadoria das Questions | Poucas áreas | Carga da genérica, revisão e ativação humanas; LLM rascunha; rubric check; 3 áreas propostas. Sem aprovação, fallback vai a `waiting_setup` | 2.6, 2.7, 3.12 |
| R6 | Calibração limitada ao PeerRead | Notas mal calibradas fora de CS | Dados por área; revisão humana por amostragem; concordância | 6.1 |
| R7 | APIs externas mudam preço e limite | Custo e falhas | Clientes isolados em `scholarly/`; cache; orçamento | 4.1 |
| R8 | Agno 3 é recente | Quebra numa atualização | `>=3.1,<4`; spike; uso concentrado em `agents/` e nos `workflow.py`; teste de contrato fora do CI | 1.2, 1.3 |
| R9 | Extração pesada em CPU | Lentidão | Fila própria, concorrência baixa, cache por sha256 | 1.6, 1.9 |
| R10 | Prompt injection evolui | Avaliação manipulada | Scan do E1; delimitação no prompt; conferência das evidências; juiz | 1.7, 3.7, 3.8 |
| R11 | Viés dos modelos (autopreferência, bajulação) | Notas enviesadas | Juiz cruzado (D14); réplica; mediana | 3.8, 3.9 |
| R12 | Complexidade do modo por seção | Custo e erro não detectado | Checagens entre seções; mapa em todo passe; juiz com o artigo inteiro; A/B | 3.4, 3.13 |
| R13 | Duas famílias em três slots podem correlacionar os erros | A mediana e o juiz pegam menos erro | Juiz cruzado; medir concordância A×C no A/B. Hoje C aceita OpenAI/Google por config; terceiro provedor exige ampliar fábrica, enums e testes | 3.1, 3.13 |
| R14 | **Novo.** Threads do `Parallel` e dos pools abrem conexões do Django | Conexões esgotadas no Postgres | `bounded_map` fecha a conexão por thread; `ProviderLimiter`; teste com `transaction=True` (D20) | 1.3 |
| R15 | **Novo.** Agno, Docling ou torch sem suporte a Python 3.14. **Em parte resolvido (11/11):** o Agno 3.1 roda em 3.14; Docling e torch só importam se a 1.6 escolher o Docling | Bloqueia o M1 | Spike 1.2; conferir as wheels na 1.6; plano B: imagem 3.13 só nos workers que precisarem | 1.2, 1.6 |
| R16 | **Novo.** O contrato `ExtractedDocument` muda depois que as fixtures existem | Trilhas A e I quebram | `contract_version`; regenerar as fixtures pelo comando; mudança de contrato avisada no PR | 1.1 |
| R17 | **Novo.** O E4 não cabe no soft limit da task (25 min) | Estágio morto pelo Celery | Medir na 3.10 e no A/B; ajustar a concorrência; se preciso, dividir o E4 em avaliação e juiz, com um checkpoint novo | 3.10, 3.13 |

## Questões abertas

| # | Pergunta | Situação | Decidir antes de |
|---|---|---|---|
| Q1 | Quais modelos em cada papel? | **Parcialmente decidido (D14):** OpenAI e Google; A = GPT, B = Gemini, C = outro modelo de uma das duas; juiz cruzado. Na 1.3 (12/11), a equipe escolheu padrões de desenvolvimento substituíveis pelo ambiente, documentados em `docs/agents.md`. Os ids e a calibração de produção continuam abertos | 1.3 (papéis), 1.8 (`vision`), 3.1 (avaliadores e juízes) |
| Q2 | Orçamento por artigo | Aberta; custo real de avaliação ainda sem medição. `LLMCall` e painel 6.2 implementados; alerta opcional não bloqueia chamadas | 3.13 |
| Q3 | Identificação do artigo entre versões | **Decidido:** `external_id` obrigatório | — |
| Q4 | Curadoria e áreas iniciais | Catálogo 2.7 implementado: genérica + Computação, Física/Quântica e Medicina. São rascunhos; responsável e revisão especialista continuam pendentes | 2.7 |
| Q5 | Idioma do relatório | Aberta; proposta: idioma do artigo, com opção na submissão | 3.11 |
| Q6 | Aviso de relatório pronto | Aberta; polling no início | Depois do M3 |
| Q7 | Retenção de dados (LGPD) | Aberta; recorte 6.4 revisou docs/metas, sem decidir prazos ou implementar limpeza/dry-run | Antes de qualquer uso real; 6.4 |
| Q8 | Revisores humanos no admin | Aberta; proposta: grupo "revisores" | 4.9 |
| Q9 | Limites de upload e de páginas | Upload 50 MiB por padrão; sem limite de páginas nem timeout separado do pypdf. Tasks têm soft/hard limit 25/30 min. Medição de páginas/carga pendente | 6.3 |
| Q10 | Volume esperado por dia | Aberta | Antes de dimensionar workers |
| Q11 | Metas numéricas | Referências locais: citações E1 244/263 recall, 244/264 precisão; regras E2 119/152, F1 micro 0,7885. [Condições e pisos de comparação](../../../docs/status_and_metrics.md#metas-revistas-por-marco). LLM, notas/juiz e integridade ainda sem número | 4.10, 5.6, 6.1 |
| Q12 | Modo de avaliação padrão | Aberta; decidida pelo A/B | 3.13 |
| Q13 | Checagens entre seções da primeira versão | Aberta; proposta: promessas × resultados, método × pergunta, figuras × texto | 3.4 |
| Q14 | Papéis por `paper_type` cobrem os artigos reais? | Primeira referência condicional: 78,29% nas regras, tipo de referência fornecido e rótulos provisórios; revisão humana e LLM ainda pendentes | 2.4, 2.7 |
| Q15 | **Nova.** Quem fica em cada trilha (P, A, I)? | **Parcialmente decidido (07/11):** as trilhas viraram 4 módulos ([divisão em módulos](../2_divisao_equipe/divisao_em_modulos.html)); Plataforma e Extração fica com Iara Yasmin. Faltam os nomes de Agentes, Perfil e Relatório, de Avaliação e de Integridade | Início da fase 1 |
| Q16 | **Nova (11/11).** Figuras, tabelas e fórmulas: Docling (pesado) ou chamada de visão do modelo sobre as páginas? | **Decidido (12/11):** o Gemini, como na 1.5 (lista conferida + uma chamada por figura); recorte adiado; a 1.8 foi incorporada à 1.6 | — |
| Q17 | **Nova (11/11).** Sem o GROBID, como ligar cada citação no texto à sua referência: código sobre o texto das seções ou chamada ao modelo? | **Decidido (12/11):** híbrido; o modelo separa as referências em campos, e o código acha e liga as chamadas (1.10, antes da 1.6) | — |
