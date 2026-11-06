# Metis: desenho inicial e roteiro

**Situação:** desenho aprovado em 25/10/2026, incluindo a avaliação por seção (D13). Em 05/11, o [plano completo](../../2026-11_november/1_plano_completo/00_sumario.md) detalhou todos os marcos e acrescentou as decisões D14–D21; este arquivo fica como registro do desenho inicial
**Data:** 25/10/2026
**Base:** repositório vazio, exceto `dataset_project/` (loader do PeerRead)
**Como o sistema funciona:** [docs/](../../../docs/README.md)

---

## O problema

Avaliar um artigo científico pede três coisas:

1. **Saber de que área o artigo é.** Ninguém informa a qual question a submissão pertence: ela depende do abstract e precisa trazer o contexto daquele domínio (ex.: computação quântica).
2. **Checar a integridade além da cópia entre submissões.** A comparação inclui fontes externas, confere se as citações existem e sustentam o que o texto afirma, e detecta tentativas de manipular o avaliador.
3. **Avaliar com confiabilidade.** Uma única chamada de LLM sobre o artigo inteiro erra sem que ninguém perceba, e a nota varia de uma execução para outra. É preciso dividir o trabalho, ter avaliações independentes e verificar se cada uma está aterrada no artigo.

## A solução em uma página

| # | O quê | Como |
|---|---|---|
| 1 | Submissão | A API recebe o PDF. Versão nova = attempt nova; reenvio idêntico = 200 com a existente |
| 2 | Extração | GROBID + Docling + descrição contextual das figuras + scan de texto oculto → `ExtractedDocument` |
| 3 | Perfil | Classifica a área na taxonomia OpenAlex, resolve a Question (fallback até a genérica), dá papel às seções e monta o mapa do documento |
| 4 | Integridade | Similaridade em funil + verificação de citações + texto oculto → regras de risco → gate humano |
| 5 | Avaliação | 3 avaliadores independentes, de famílias de modelo diferentes. Cada um analisa o artigo seção por seção (observações com trechos literais), faz checagens entre seções e sintetiza a nota por critério |
| 6 | Juiz | Validadores em código + juiz com o artigo inteiro. Só o inválido volta (o passe da seção ou a síntese do critério), com trecho + motivo e direito a réplica; no máximo 2 rodadas |
| 7 | Consolidação | Mediana + concordância + meta-review → relatório final estruturado, por critério e por seção |
| 8 | Orquestração | Uma task Celery curta por estágio, com checkpoint no banco; Agno dentro dos estágios |

## Decisões (25/10)

| # | Pergunta | Decisão | Alternativas descartadas |
|---|---|---|---|
| D1 | Stack web e persistência | Django 6 + Ninja + ORM e migrations do Django; o admin já serve para curadoria e revisão humana | FastAPI + SQLAlchemy |
| D2 | O que fazer com risco alto de plágio | Pausar em `waiting_human_review`; uma pessoa decide no admin. Risco médio ou baixo segue, com o resumo no contexto | Seguir sempre, com flag; rejeitar automaticamente |
| D3 | Como diferenciar os 3 avaliadores | Modelos de famílias diferentes, com o mesmo contexto e os mesmos critérios | O mesmo modelo 3 vezes; personas com focos diferentes |
| D4 | Como criar as Questions | Curadas por nó da taxonomia, com fallback até a genérica; o LLM só rascunha e uma pessoa valida | Geradas por LLM sem curadoria; geradas por artigo a partir do abstract |
| D5 | Celery × Agno | Uma task Celery curta por estágio; o Agno roda dentro do estágio | Um workflow Agno inteiro numa task longa |
| D6 | Parsers | GROBID + Docling + pdfplumber, todos com licença permissiva | PyMuPDF (AGPL); Marker e MinerU (licenças com restrições); LLM lendo o PDF direto |
| D7 | Taxonomia das áreas | OpenAlex (4 níveis, CC0) | Tabela CAPES/CNPq (nacional e sem ligação com as bases da integridade; pode ser mapeada depois); categorias do arXiv (só exatas e computação) |
| D8 | Embeddings da similaridade | BGE-M3 local (multilíngue) | SPECTER2 (só inglês); APIs pagas (o manuscrito sairia da infraestrutura) |
| D9 | Quem decide o nível de risco | Regras explícitas e configuráveis; o LLM só redige a narrativa | O LLM decide |
| D10 | Papel do juiz | Verificador com o artigo inteiro, uma chamada por avaliador; juiz alternativo quando o avaliador é da mesma família | Juiz como 4º avaliador; uma chamada por critério |
| D11 | Como revisar | Só o que foi invalidado (observação, checagem ou síntese), com trecho + motivo e direito a réplica; no máximo 2 rodadas | Reavaliar tudo; sem limite de rodadas |
| D12 | Reavaliar a mesma versão | Novo Run na mesma attempt | Attempt auxiliar criada só para reavaliar |
| D13 | Como o avaliador lê o artigo | Por seção (`sectioned`): passes por papel da seção geram observações sem nota; checagens entre seções; síntese por critério; o mapa do documento vai em todo passe; o juiz vê o artigo inteiro. O A/B do M3 contra o artigo inteiro confirma o padrão | Artigo inteiro numa chamada (fica como linha de base do A/B); seção por seção sem visão global |

Detalhes e justificativas em [docs/](../../../docs/README.md). A D13 está em [Avaliadores, juiz e consolidação](../../../docs/evaluators_and_judge.md). O que ainda falta decidir está em [04](04_riscos_e_questoes_abertas.md).

## Fora daqui

- Detector de texto gerado por IA: pouco confiável, e não serve de evidência.
- Interface própria além do admin do Django, por enquanto.
- Acordos com editoras para comparar com full text fechado.
- Notificação por webhook (questão aberta Q6).

## Arquivos deste plano

| Arquivo | Conteúdo |
|---|---|
| [01_diagnostico.md](01_diagnostico.md) | Ponto de partida: o repositório, padrões e princípios de desenho, o PeerRead e a pesquisa de ferramentas |
| [02_roteiro.md](02_roteiro.md) | Marcos M0–M6: objetivo, entregas, dependências, critério de pronto |
| [03_etapa_m0_fundacao.md](03_etapa_m0_fundacao.md) | O M0 em etapas, com testes e commits |
| [04_riscos_e_questoes_abertas.md](04_riscos_e_questoes_abertas.md) | Riscos com mitigação e o que ainda falta decidir |
| [05_testes_e_verificacao.md](05_testes_e_verificacao.md) | Testes por marco e verificação manual |
