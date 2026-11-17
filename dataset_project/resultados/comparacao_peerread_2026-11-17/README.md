# Metis × revisores humanos (PeerRead), 17/11/2026

Nove artigos do PeerRead passaram pelo pipeline completo no Docker (E1 → E5), e a nota do
Metis foi comparada com a dos revisores reais. O resultado está em
[`metis_vs_humanos.pdf`](metis_vs_humanos.pdf).

## Resumo

| | Humanos | IA (Metis) |
|---|---|---|
| Média geral (1–5) | 3,0 | 2,7 |
| Faixa das médias por artigo | 2,2 a 4,0 | 2,2 a 3,2 |
| Decisão no ICLR (6 artigos com decisão real) | — | acertou 2 de 6 |

- As notas da IA quase não variam (correlação com as humanas: −0,07): ela é dura com os artigos
  bons e generosa com os fracos.
- **Limitação do processamento:** a extração (E1) corrompe fórmulas (letras gregas e expoentes),
  e os avaliadores reclamaram de "notação corrompida" em 8 dos 9 artigos.
- No conteúdo, as críticas da IA costumam coincidir com as dos revisores; ela perde o argumento
  decisivo de especialista.
- Tempo de processamento: de 10 a 27 min por artigo (154 min no total). Custo: de US$ 0,76 a
  1,64 por artigo (US$ 10,15 no total).

## Artigos

| Rótulo | Origem no PeerRead | Decisão real |
|---|---|---|
| 410 | `iclr_2017/train/pdfs/410.pdf` | aceito |
| 457, 358 | `iclr_2017/test/pdfs/` | aceitos |
| 554, 518, 611 | `iclr_2017/test/pdfs/` | recusados |
| 768, 355, 435 | `acl_2017/test/pdfs/` | não informada (há notas por critério) |

Os do ICLR `test` usaram o `external_id` `peerread:iclr_2017:test:<id>` da amostra do A/B
(`projects/correction/evals/data/peerread_iclr2017_test_candidates.json`).

## Como foi feito

- Código da `dev` de 17/11 (`002c3e2`), com a correção do adaptador para citações no resumo.
- Modelos: avaliador A `gpt-5.6-luna`, B `gemini-2.5-flash`, C `gpt-5.4-nano`; E1 e E2 com o
  `gemini-2.5-flash`.
- **Média humana:** média das recomendações dos revisores (o ICLR, de 1 a 10, foi convertido
  para 1 a 5). **Média da IA:** média das notas dos três avaliadores em todos os critérios, lidas
  da última rodada de cada um (antes do filtro de evidência do relatório oficial).
- **Tempo:** soma do processamento de cada estágio, sem o tempo parado com erro. **Custo:** soma
  das chamadas registradas em `LLMCall`.
- A leitura qualitativa de cada artigo (`dados/analysis.json`) foi escrita comparando o
  relatório do Metis com o texto das revisões humanas.

## Depois da correção das fórmulas (LaTeX)

Os dois artigos mais punidos por "notação corrompida" rodaram de novo com a extração das
fórmulas em LaTeX (pastas `artigos/*_latex/`):

| | ICLR 457 antes | depois | ICLR 358 antes | depois |
|---|---|---|---|---|
| Críticas de "notação corrompida" | 16 | **0** | 29 | **0** |
| Clareza (IA) | 2,0 | 3,0 | 2,0 | 2,3 |
| Média da IA (humanos: 3,8) | 2,71 | 2,81 | 2,52 | 2,38 |

O LaTeX eliminou a crítica falsa, mas a nota da IA não se aproximou da humana: a distância que
sobra é a rigidez dos avaliadores (solidez 2,0 e reprodutibilidade 1,3 nos dois). O tempo do run
do 358 com LaTeX não serve de medida: o computador ficou suspenso com o E4 em andamento.

## Resultado completo de cada artigo (`artigos/`)

Uma pasta por run, com a saída de cada estágio do pipeline:

| Arquivo | Estágio | O que é |
|---|---|---|
| `1_extracao.json` | E1 | O `ExtractedArticle`: seções com cobertura e fidelidade, referências, citações ligadas, figuras e tabelas descritas, texto oculto |
| `2_perfil.json` | E2 | Área e tema na taxonomia, tipo do artigo, a Question (rubrica) usada, papel de cada seção e o mapa do documento |
| `3_integridade.json` | E3 | O relatório de integridade (`GET /api/runs/<id>/integrity`): risco, regras e achados |
| `4_relatorio_final.json` e `.md` | E4 e E5 | O relatório final (`GET /api/runs/<id>/report`): notas por critério com os votos de cada avaliador, evidências, observações por seção, pontos fortes e fracos, sugestões e recomendação |

## Arquivos

| Caminho | O que é |
|---|---|
| `metis_vs_humanos.pdf` | O relatório da comparação |
| `artigos/<artigo>/` | O resultado completo de cada run, estágio por estágio (acima) |
| `dados/report_<rótulo>.json` | O relatório final do Metis (`GET /api/runs/<id>/report`) |
| `dados/collected.json` | Por run: notas de cada avaliador, tempo e custo por estágio |
| `dados/articles.json` | Os artigos e onde estão no PeerRead |
| `dados/analysis.json` | A leitura de cada artigo e a conclusão |
| `scripts/collect.py` | Gera o `collected.json` a partir do banco (roda no container) |
| `scripts/render.py` | Gera o PDF a partir de `dados/` e das revisões do PeerRead |

Para regenerar o PDF (precisa do PeerRead em `dataset_project/raw/` e do `google-chrome`):

```bash
cd dataset_project/resultados/comparacao_peerread_2026-11-17
python3 scripts/render.py dados metis_vs_humanos.pdf
```
