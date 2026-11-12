# Extração (E1)

## Objetivo

Dividir o PDF em seções, com título, nível e texto literal, e guardar o resultado (`Extraction`) que os estágios seguintes leem, sem voltar ao PDF. A estrutura vem de chamadas a um modelo de linguagem, e o texto devolvido é conferido contra o texto do próprio PDF.

O código fica em `extractor/` (caminhos relativos a `projects/correction/`).

## Ferramentas

| Ferramenta | Papel |
|---|---|
| **Gemini 2.5 Flash**, pelo Agno (`session.py`) | Lê o PDF: mapeia as seções (chamada 1) e copia o texto de cada uma (chamada 2) |
| **pypdf** (Python puro) | Lê o texto do PDF aqui: é a referência para conferir as respostas e o texto enviado na estratégia `text` |

Nenhum serviço à parte. O GROBID chegou a ser implementado na 1.5 e foi descartado em 11/11/2026: a imagem tem 1,7 GB, ele ocupa 3,6 GB de RAM, e a divisão por chamada ao modelo bastou. O Docling, previsto para figuras, tabelas e fórmulas, está em aberto pelo mesmo motivo (usa modelos do torch).

## Passo a passo

```text
PDF ─▶ chamada 1: mapa das seções ─▶ gate: tem abstract e referências?
                                       └─ não ─▶ rejected_invalid_submission
          │
          ▼
       uma chamada 2 por seção do mapa, em paralelo (até max_parallel_calls)
          │
          ▼
       conferência contra o texto local do PDF: cobertura e fidelidade
          ├─ passou ─▶ aceita
          └─ não ────▶ refaz só aquela seção, com uma dica do que deu errado (até check_retries)
          │            e fica com a melhor resposta
          ▼
       lista de referências separada em campos (uma chamada, só com o texto da seção)
          │
          ▼
       chamadas no texto ([3], "Silva et al. (2020)") achadas e ligadas às referências (código)
          │
          ▼
       lista de figuras e tabelas (uma chamada), com as legendas conferidas contra o PDF
          │
          ▼
       chamadas às figuras no texto ("Fig. 3", "Tabela 2") achadas e ligadas (código)
          │
          ▼
       uma descrição por figura e tabela, em paralelo, conferida pelo começo da legenda
          │
          ▼
       ExtractedArticle ─▶ Extraction (banco) ─▶ Run.extraction
```

1. **Chamada 1, o mapa** (`prompts/scan_headings.md`). O modelo devolve título, autores (sem marcas de nota e de afiliação), idioma e os títulos das seções com o nível. Só conta o título em linha própria: título de parágrafo ("Quicksort. The algorithm…") e rótulo de algoritmo, lista ou código ficam no texto da seção em que estão. Com essa regra, três rodadas seguidas no mesmo artigo deram o mesmo mapa.
2. **O dict das seções** (`section_map.py`). Cada título vira `sec_1`, `sec_2`…, com o nível, o pai (a seção anterior de nível menor) e a chave das seções que a config procura pelo nome (`abstract`, `references`), comparando sem numeração, acento e caixa.
3. **Gate.** Sem abstract ou sem referências, o artigo é rejeitado (`MissingRequiredSections` → `rejected_invalid_submission`) antes das chamadas por seção, que são as mais caras.
4. **Chamada 2, uma por seção** (`prompts/extract_section.md`). O prompt nomeia a seção e diz onde ela termina: `Seção: "1.1 Contexto", dentro da seção "1 Introdução" … termina no título "Referências"`. A seção-mãe desfaz a dúvida entre títulos repetidos. O modelo copia o texto literalmente, sem pular parágrafos, deixando de fora cabeçalho e rodapé de página, figuras, tabelas e legendas, com cada referência num parágrafo. As notas de rodapé seguem a config (`ignore_footnotes`).
5. **Conferência** (`coverage.py`), contra o texto do PDF lido pelo pypdf, sem as linhas repetidas em metade das páginas (cabeçalho e rodapé):
   - o código acha no texto local, em ordem, o título de cada seção do mapa (preferindo a ocorrência que começa uma linha); o trecho até o título seguinte é a versão local da seção;
   - **cobertura:** fração da prosa desse trecho que veio na resposta (o modelo pulou texto?). Legenda, tabela e fórmula não contam;
   - **fidelidade:** fração da resposta que está nesse trecho (o modelo trouxe texto de outra seção ou inventou?);
   - a comparação usa trechos de 20 caracteres do texto só com letras e dígitos, sem acento e sem caixa. Espaço, hifenização e palavra grudada não contam como diferença, e uma nota que o pypdf colou no meio de uma frase só derruba os trechos em volta dela;
   - título não achado no texto local deixa a seção sem verificação (`None`).
6. **Nova tentativa** (`section_answer.py`). Abaixo de `min_coverage` ou de `min_fidelity`, a chamada daquela seção é refeita com uma dica: as frases do PDF que faltaram ou o começo do texto que não é da seção. Repetir o mesmo pedido com temperatura 0 dá a mesma resposta, por isso a dica. Fica a melhor resposta. Uma resposta vazia ou fora do schema conta como tentativa falha daquela seção, sem derrubar a extração inteira. Uma seção sem prosa no PDF que, mesmo assim, recebe texto de fora fica vazia: o texto é de outra seção e estaria duplicado.
7. **Referências em campos** (`references.py`, `prompts/parse_references.md`). Uma chamada só com o texto da seção de referências, sem o PDF. O modelo devolve cada entrada com o texto cru (`raw`), a marca da lista (`[3]`, `3.`), autores, título, ano (com o sufixo, `2020a`), venue, DOI e arXiv. O código confere: entrada cujo `raw` não está no texto é descartada, e o conjunto precisa cobrir o texto; reprovada, a chamada é refeita com uma dica (as entradas que não estão na lista ou as que faltaram). Ids `ref_1`, `ref_2`… na ordem.
8. **Chamadas no texto** (`citations.py`, só código), em todas as seções menos a de referências:
   - **numérico:** `[3]`, `[1, 4]`, `[2–5]` (o intervalo é expandido); a ligação é pela marca da entrada ou, se a lista não é numerada, pela posição;
   - **autor-ano:** "Silva (2020)", "Silva et al. (2020a)", "Silva e Souza (2020)" e, entre parênteses, "(e.g., Silva, 2020; Souza et al., 2019)"; a ligação é pelo sobrenome do primeiro autor (sem acento e caixa) e pelo ano. Duas entradas com o mesmo primeiro autor e ano são desempatadas pelo segundo autor ("Agić e Ljubešić (2015)"), pelo "et al." (três ou mais autores) ou, sem nenhum dos dois, pela entrada de autor único;
   - o estilo é decidido uma vez por artigo: numérico se a lista é numerada ou se as chamadas numéricas válidas são maioria. Assim um intervalo "[0, 1]" num artigo autor-ano não vira citação, e colchete com 0 nunca é citação;
   - sem entrada correspondente, ou com mais de uma, a citação fica com `reference_id` nulo (a 5.3 usa: citação sem entrada na lista). "Palavra (2020)" sem entrada é descartada, porque pode não ser citação; "(Silva, 2020)" e "Silva et al. (2020)" ficam.
9. **Figuras e tabelas** (`figures.py`, `prompts/scan_figures.md`). Uma chamada com o PDF lista cada figura e tabela: rótulo ("Figure 3", "Tabela 2"), tipo (`figure` ou `table`), página e legenda literal, sem algoritmos, quadros de código e equações. O código confere contra o texto do PDF: legenda que não está nele é descartada (fidelidade), e as linhas que começam como legenda ("Figure 3:", "Table 2.") mostram quais rótulos existem; o que faltar volta como dica numa nova tentativa. Os ids (`fig_1`, `fig_2`…) seguem a ordem das páginas. Uma resposta inválida aqui não derruba a extração: a lista fica vazia.
10. **Chamadas às figuras** (`figure_mentions.py`, só código): "Fig. 3", "Figure 3a", "Figura 2", "Figures 2 and 3", "Figs. 2–4", "Table 1", "Tabela A.1", ligadas pelo tipo e pelo número do rótulo; rótulo fora da lista fica com `figure_id` nulo.
11. **Descrição de cada figura e tabela** (`figure_descriptions.py`, `prompts/describe_figure.md`). Uma chamada por figura, em paralelo, com o PDF, o rótulo, a página, a legenda e até 5 frases do artigo que citam a figura (do passo 10). O modelo devolve a classe (gráfico de linhas, diagrama, tabela…), o que a figura mostra, o que dá para ler nela (eixos, valores, tendências), se ela sustenta o que as frases afirmam (nulo quando elas não afirmam nada), o porquê, os problemas que vê (eixo sem unidade, legenda que não bate com o desenho) e, para tabela, o conteúdo em markdown. Duas conferências no código, cada uma com nova tentativa e dica:
    - **a figura certa:** o modelo devolve também o começo da legenda da figura que descreveu; se não bate com a legenda pedida (comparando sem o rótulo, acento, caixa e pontuação), ele olhou outra figura. Aconteceu no ICLR 304: a "Figure 1" saiu com o conteúdo da "Table 1". Se continuar trocada, a figura fica sem descrição;
    - **tabela com as linhas:** markdown só com o cabeçalho é refeito. Aconteceu no ICLR 410, na Table 5. Se continuar assim, a descrição fica e o markdown sai.

    Uma figura cuja resposta continua inválida fica sem descrição e o resto segue. O modelo fora do ar sobe, como nos outros passos, e o retry do estágio refaz só as figuras que faltaram (ver [Retomada](#retomada)). Com `describe_figures` desligado na config, o passo não roda.
12. **Resultado.** Seção obrigatória vazia é resposta inválida (`InvalidModelAnswer`, o estágio tenta de novo), e também uma lista de referências sem nenhuma entrada conferida. O resto vira um `ExtractedArticle`, guardado como `Extraction` e ligado ao run.

## A config (`DocumentConfig`)

Tipagem congelada em `config.py`; a do artigo científico é a `ARTICLE_CONFIG` (`configs.py`). Os passos só leem a config, e uma config inválida falha já no import.

| Campo | Para quê | Artigo |
|---|---|---|
| `strategy` | `pdf`: o PDF vai ao modelo; `text`: só o texto lido pelo pypdf | `pdf` (artigo em duas colunas, com tabelas, se perde no texto puro) |
| `provider`, `model` | Quem atende as chamadas | `google`, `gemini-2.5-flash` |
| `scan_prompt`, `extraction_prompt` | Prompts das chamadas 1 e 2 (o 2 com os marcadores `<<title>>`, `<<end>>`, `<<footnotes>>`) | arquivos em `prompts/` |
| `required_sections`, `optional_sections` | Seções procuradas pelo nome (`SectionDefinition(key, labels)`); sem uma obrigatória, o artigo é rejeitado | `abstract` e `references`, com grafias em PT e EN |
| `ignore_footnotes` | `true`: o texto das notas e as marcas de chamada ficam fora, e cada seção só diz se tinha nota; `false`: as notas vêm no fim da seção que as chama | `true` |
| `max_parallel_calls` | Chamadas por seção ao mesmo tempo | 4 |
| `min_coverage`, `min_fidelity` | Limites da conferência | 0,8 e 0,8 |
| `check_retries` | Novas tentativas de uma seção (ou da lista de referências) reprovada | 1 |
| `references_prompt` | Prompt da chamada que separa as referências em campos (com o marcador `<<references>>`) | `prompts/parse_references.md` |
| `figures_prompt` | Prompt da chamada que lista as figuras e as tabelas | `prompts/scan_figures.md` |
| `describe_figure_prompt` | Prompt da chamada que descreve uma figura (marcadores `<<label>>`, `<<page>>`, `<<caption>>`, `<<mentions>>`) | `prompts/describe_figure.md` |
| `describe_figures` | Descrever cada figura e tabela (uma chamada por figura) | `true` |

Os papéis das seções (introdução, método, resultados…) não ficam aqui: são do E2.

## O resultado

`ExtractedArticle` (`article.py`): `title`, `authors`, `language`, `model` (provedor/modelo) e `sections[]`. Cada `ExtractedSection` tem `id`, `title`, `level`, `parent_id`, `key`, `text`, `has_footnotes`, `coverage` e `fidelity`. Uma seção que só tem subseções vem com o texto vazio.

Desde a 1.10, também `references[]` (cada `Reference` com `id`, `raw`, `marker`, `authors`, `title`, `year`, `venue`, `doi`, `arxiv_id`) e `citations[]` (cada `Citation` com `reference_id` ou nulo, `marker`, `sentence`, `section_id` e `start`/`end`, offsets do `marker` no texto da seção). As extrações anteriores continuam válidas, com as duas listas vazias.

Desde a 1.6, também `figures[]` (cada `Figure` com `id`, `kind`, `label`, `number`, `page`, `caption` e `fidelity` da legenda) e `figure_mentions[]` (cada `FigureMention` com `figure_id` ou nulo, `marker`, `sentence`, `section_id` e `start`/`end`).

Desde a 1.8, cada `Figure` traz `description`, nula quando a chamada falhou: um `FigureDescription` com `figure_class`, `description`, `data_read[]`, `supports_claims` (sim, não ou nulo), `support_rationale`, `issues[]` e `table_markdown` (nulo para figura).

O contrato `ExtractedDocument` da 1.1 (módulo Avaliação) ainda não existe; quando existir, é montado a partir deste resultado.

## Cache e ligação ao run

- **`Extraction`** (`models.py`): o `ExtractedArticle` em JSON, único por (sha256 do PDF, versão). A versão é o hash da config inteira e de todos os prompts: mudar o modelo, um limite ou um prompt força uma extração nova. Um run novo do mesmo PDF reaproveita a guardada, sem chamar o modelo.
- **`Run.extraction`**: o E1 liga a extração ao run pelo `RunManagement.attach_extraction`, só se o estágio ainda é da task (posse).
- **Passos guardados:** enquanto a extração não termina, cada resposta do modelo fica no banco (`ExtractionStep`), para o retry do estágio retomar delas (ver [Retomada](#retomada)).
- **Evento do E1:** o `RunEvent` de `extracted` traz `extraction_id`, `reused`, `model`, o número de seções, as seções abaixo dos limites (`below_check`) o número de referências, de citações e de citações sem ligação, o número de figuras e tabelas e quantas foram descritas (`figures_described`). Nunca texto do manuscrito.

## Retomada

Se o modelo cai no meio (fora do ar, cota, timeout), o Celery tenta o estágio de novo. Sem a retomada, o retry refaria todas as chamadas: umas 37 no ICLR 410 e 48 no 304, cada uma com o PDF.

- **`ResumableSession`** (`resumable_session.py`) envolve a sessão do Agno, com a mesma interface `ask`. Cada resposta válida é guardada assim que chega, inclusive as das tentativas com dica e as das chamadas em paralelo que terminaram depois de outra cair. No retry, as guardadas voltam sem chamar o modelo.
- **Por que o retry segue o mesmo caminho:** cada prompt depende só das respostas anteriores. O mapa dá os prompts das seções, os textos dão o das referências, a lista dá os das descrições. O retry passa pelas respostas guardadas e só chama o modelo a partir de onde parou.
- **Chave:** o hash do prompt, do schema pedido e de `with_document`, junto do sha256 do PDF e da versão do extractor. Mudar um prompt, a config ou um schema não reaproveita a resposta antiga.
- **`ExtractionStep`** (`sha256`, `version`, `key`, `answer`), único pelos três primeiros. As respostas guardadas são lidas uma vez, na thread principal; cada thread das chamadas em paralelo grava a sua e fecha a própria conexão (o Django abre uma conexão por thread e não a fecha sozinho).
- **Quando os passos são apagados:** quando a `Extraction` é guardada, e quando o estágio falha com `InvalidModelAnswer` (seção obrigatória vazia, referências sem entrada). Neste caso, as respostas guardadas levariam à mesma falha no retry.
- **Quando ficam:** num run que terminou em `error_llm` depois de todas as tentativas. Reprocessar no gate retoma deles. A limpeza das sobras entra no comando de retenção da 6.4.
- Dois runs do mesmo PDF ao mesmo tempo podem chamar o modelo para o mesmo passo; fica a primeira resposta gravada.

## Falhas

| Situação | Resultado |
|---|---|
| Falta a `GEMINI_KEY` | `MissingModelKey` → `waiting_setup` |
| Chamada ao modelo falhou (fora do ar, cota, timeout de `METIS_LLM_TIMEOUT_SECONDS`) | `ModelUnavailable` → retry do estágio, que retoma das respostas guardadas → `error_llm` |
| Resposta vazia, cortada, fora do schema ou seção obrigatória vazia | `InvalidModelAnswer` → as respostas guardadas são apagadas → retry do estágio, do zero → `error_llm` |
| Sem abstract ou sem referências no mapa | `MissingRequiredSections` → `rejected_invalid_submission`, sem as chamadas por seção |
| PDF sem texto para o pypdf (escaneado) | O modelo ainda lê o PDF; as seções ficam sem verificação |
| PDF acima de 18 MB (o Gemini aceita 20 MB por pedido) | Vai como texto, lido pelo pypdf |

O Agno não refaz chamadas (`retries=0`): quem tenta de novo, com backoff, é o Celery.

## Confidencialidade

- O PDF vai ao Google em cada chamada. A política de retenção do provedor precisa ser conferida, porque os manuscritos são inéditos.
- O Agno registra em warning a resposta que não bateu com o schema, com texto do manuscrito. Um filtro no logger `agno` deixa passar só os erros.

## Limitações conhecidas

- **Algoritmos:** uma seção só com pseudocódigo pode ficar vazia, porque a transcrição do modelo não bate com o texto do pypdf e conta como texto de fora.
- **Símbolos:** letras gregas podem mudar ("α" virou "a" num teste), e fórmulas vêm como texto corrido.
- **Ruído na conferência:** tabelas e notas que o pypdf cola no meio do texto baixam a cobertura de seções que vieram certas (a 3.1 do ICLR 410 fica em 76%). Por isso os limites ficam em 0,8.
- **Custo:** o PDF vai em cada chamada, inclusive uma por figura na descrição. O Agno manda o texto do prompt antes do PDF, então o cache implícito do Gemini não reaproveita o PDF entre as chamadas.
- **Citações:** chamada em número sobrescrito ("…doença¹⁻³", comum na área da saúde) não é reconhecida; num artigo numérico, um intervalo como "[1, 2]" no meio de uma fórmula vira citação; no autor-ano, "Silva (2020)" com duas entradas de Silva 2020 que nem o segundo autor nem o "et al." desempatam fica sem ligação.
- **Tabela cortada no meio:** a conferência só pega a tabela que vem só com o cabeçalho. A Table 11 do ICLR 410 veio com 67 números numa rodada e 181 na seguinte. Os números que vêm estão no PDF (100% nas 16 tabelas conferidas), mas pode faltar linha.
- **Julgamento brando:** nas 19 figuras e tabelas da calibração, o modelo disse sempre que a figura sustenta as frases e não apontou nenhum problema. Serve de ponto de partida para o E2, não de veredito.
- **Ainda não feito:** o recorte da imagem (adiado), o texto oculto (1.7, Integridade) e o `ExtractedDocument` da 1.1, montado a partir deste resultado (1.11).

## Como testar

- `extractor/tests/`: a config, o mapa, a conferência, a nova tentativa, as referências (`test_references.py`), as citações (`test_citations.py`), as figuras (`test_figures.py`, `test_figure_mentions.py`, `test_figure_descriptions.py`), a retomada (`test_resumable_session.py` e o retry no meio em `test_attempt_extraction.py`), a medição (`test_citation_bench.py`) e o caso de uso, com uma sessão falsa e PDFs gerados no teste; a sessão do Agno contra um servidor HTTP local no lugar do Google; o E1 por attempt com banco real e PDF no storage.
- `pytest -m llm`: divide um artigo inventado com o Gemini de verdade (usa a `GEMINI_KEY` do `.env`; fica fora do `pytest` padrão e do CI).
- Calibração (11/11): dois artigos do ICLR 2017 (PeerRead) divididos de ponta a ponta. No 410 (13 páginas), 18 de 19 seções passaram nas duas medidas, com 21 chamadas em 30 s; no 304 (20 páginas), as 3 reprovadas eram de pseudocódigo, com 39 chamadas em 68 s.
- **Medição da ligação citação ↔ referência (12/11)**, com `python manage.py bench_citation_links --execute` (em dry-run só lista os artigos; `--rescore <pasta>` recalcula a partir dos artigos salvos, sem o modelo): 10 artigos do PeerRead (ICLR 2017, ACL 2017, CoNLL 2016), comparados com o gabarito do science-parse. Contra o gabarito bruto, recall de 80% e precisão de 71%. O gabarito erra muito: 134 das 406 chamadas dele não batem com o próprio texto (o sobrenome e o ano da chamada não são os da referência ligada) ou têm os offsets fora do lugar; sem elas, **recall de 93% (244 de 263) e precisão de 92% (244 de 264)**, com 98% das referências casadas pelo título. Na conferência manual, as 20 citações contadas como erradas estavam certas (o gabarito não as tinha naquela frase); das 19 chamadas não achadas, 7 estão em tabelas, legendas ou notas (fora do texto por desenho), 3 em frases que o modelo pulou na cópia e o resto é desacordo de recorte do gabarito. Os relatórios ficam em `dataset_project/processed/bench_citation_links/`.
- **Figuras (12/11):** no ICLR 410, 12 tabelas e 1 figura, todas com a legenda idêntica à do PDF e as 17 chamadas no texto ligadas; no ICLR 304, 2 figuras e 4 tabelas (os algoritmos ficam de fora).
- **Descrições (12/11):** as 19 figuras e tabelas do ICLR 304 e do 410 descritas, cerca de 80 s por artigo. As 16 tabelas vieram em markdown, com todos os números presentes no texto do PDF. Os dois casos que viraram conferência (figura trocada no 304, tabela só com o cabeçalho no 410) saíram certos na rodada seguinte.
