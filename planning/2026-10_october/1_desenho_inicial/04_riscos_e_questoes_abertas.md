# Riscos e questões abertas

## Riscos

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| R1 | Custo de LLM por artigo acima do esperado (3 avaliadores com passes por seção + juiz + revisões + figuras) | Inviabiliza o volume | `LLMCall` desde o M1; orçamento por run; caching do prefixo do artigo; validadores antes do juiz; revisão parcial; o A/B do M3 mede o custo dos dois modos antes de escalar |
| R2 | Cobertura limitada da similaridade (sem full text fechado) | Plágio não detectado | `coverage` declarado no relatório; obras citadas como candidatas; o corpus interno cresce a cada submissão |
| R3 | Falso positivo de plágio | Acusação injusta | Filtro por citação, boilerplate e mesmo trabalho; regras calibradas; gate humano; nunca rejeição automática |
| R4 | Manuscrito inédito enviado a provedores de LLM | Vazamento de trabalho não publicado | Provedores com retenção zero ou contrato; embeddings locais; telemetria do Agno desligada; logs sem conteúdo; avaliar modelos locais (Ollama) depois |
| R5 | Esforço de curadoria das Questions | Poucas áreas cobertas | Genérica sempre disponível; LLM rascunha; rubric check; começar com 2–3 áreas |
| R6 | Calibração limitada: o PeerRead só cobre CS/IA/PLN (2013–2017), com provável contaminação | Notas mal calibradas em outras áreas | Dados por área (a definir); revisão humana por amostragem; acompanhar a concordância entre avaliadores |
| R7 | APIs externas mudam preço e limite (o OpenAlex mudou em 2026) | Custo e falhas | Clientes isolados em `scholarly/`; cache; orçamento; ordem de consulta com alternativa |
| R8 | Agno 3 é recente (3.0 em agosto/2026) | Quebra numa atualização | Fixar `>=3.1,<4`; uso concentrado na `AgentFactory` e nos executors; testes com fakes |
| R9 | Extração pesada em CPU (Docling, BGE-M3) | Lentidão | Fila própria com concorrência baixa; cache por sha256; GPU depois, se necessário |
| R10 | Técnicas de prompt injection evoluem | Avaliação manipulada | Scan do E1 + delimitação no prompt + conferência das evidências + juiz |
| R11 | Viés dos modelos (autopreferência, bajulação) | Notas enviesadas | Famílias diferentes; juiz alternativo para a mesma família; direito a réplica; mediana |
| R12 | Modo por seção: mais chamadas e orquestração mais complexa; uma inconsistência global pode escapar das checagens entre seções | Custo e erro não detectado | Checagens entre seções explícitas; mapa do documento em todo passe; juiz com o artigo inteiro; A/B contra o artigo inteiro antes de fixar o padrão |

## Questões abertas

| # | Pergunta | Decidir antes de | Proposta |
|---|---|---|---|
| Q1 | Quais modelos exatos em cada papel, e de quais provedores a equipe tem chave? | M1 (descrição de figuras); M3 (avaliadores e juiz) | 3 famílias (ex.: Gemini, GPT, Claude) e um juiz forte fixo |
| Q2 | Qual o orçamento por artigo (tokens + buscas pagas)? | M3 | Medir em 10 artigos no M3 e decidir com o número |
| Q3 | Como identificar o artigo entre versões? | M0 (etapa 0.3) | **Decidido:** `external_id` obrigatório, enviado por quem submete |
| Q4 | Quem faz a curadoria das Questions, e quais áreas entram no M2? | M2 | A genérica + Computação, Física/Quântica e Saúde |
| Q5 | Em que idioma sai o relatório? | M3 | No idioma do artigo, com opção de escolher na submissão |
| Q6 | Como avisar quem submeteu que o relatório ficou pronto? | M3 | Consulta periódica (polling) no início; webhook com `Idempotency-Key` depois |
| Q7 | Retenção de dados (LGPD): por quanto tempo guardar PDFs e relatórios, e quem pode ver? | Antes de qualquer uso real | Definir com quem for usar o sistema |
| Q8 | Quem são os revisores humanos, e como entram no admin? | M4 | Usuários do Django num grupo "revisores", com permissão só para o gate |
| Q9 | Limites de upload: tamanho e páginas | M0 (tamanho), M1 (páginas) | 50 MB; o limite de páginas sai das medições do M1 |
| Q10 | Qual o volume esperado de artigos por dia? | Antes de dimensionar workers e custo | — |
| Q11 | Quais as metas numéricas (precisão/recall da Fase 1, correlação com o PeerRead, recall do juiz)? | M4 e M6 | Definir depois da primeira medição de cada uma |
| Q12 | Qual modo de avaliação vira padrão? | Fim do M3 | Decidir com o A/B; a proposta é `sectioned` |
| Q13 | Quais checagens entre seções entram na primeira versão? | M3 | Promessas (abstract, introdução) × resultados e conclusão; método × pergunta; figuras e tabelas × afirmações do texto |
| Q14 | A tabela de papéis por `paper_type` cobre os artigos reais? | M2 | Começar com `empirical` e `theoretical`; revisar com a amostra rotulada |
