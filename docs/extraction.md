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
6. **Nova tentativa** (`section_answer.py`). Abaixo de `min_coverage` ou de `min_fidelity`, a chamada daquela seção é refeita com uma dica: as frases do PDF que faltaram ou o começo do texto que não é da seção. Repetir o mesmo pedido com temperatura 0 dá a mesma resposta, por isso a dica. Fica a melhor resposta. Uma seção sem prosa no PDF que, mesmo assim, recebe texto de fora fica vazia: o texto é de outra seção e estaria duplicado.
7. **Resultado.** Seção obrigatória vazia é resposta inválida (`InvalidModelAnswer`, o estágio tenta de novo). O resto vira um `ExtractedArticle`, guardado como `Extraction` e ligado ao run.

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
| `check_retries` | Novas tentativas de uma seção reprovada | 1 |

Os papéis das seções (introdução, método, resultados…) não ficam aqui: são do E2.

## O resultado

`ExtractedArticle` (`article.py`): `title`, `authors`, `language`, `model` (provedor/modelo) e `sections[]`. Cada `ExtractedSection` tem `id`, `title`, `level`, `parent_id`, `key`, `text`, `has_footnotes`, `coverage` e `fidelity`. Uma seção que só tem subseções vem com o texto vazio.

O contrato `ExtractedDocument` da 1.1 (módulo Avaliação) ainda não existe; quando existir, é montado a partir deste resultado.

## Cache e ligação ao run

- **`Extraction`** (`models.py`): o `ExtractedArticle` em JSON, único por (sha256 do PDF, versão). A versão é o hash da config inteira e de todos os prompts: mudar o modelo, um limite ou um prompt força uma extração nova. Um run novo do mesmo PDF reaproveita a guardada, sem chamar o modelo.
- **`Run.extraction`**: o E1 liga a extração ao run pelo `RunManagement.attach_extraction`, só se o estágio ainda é da task (posse).
- **Evento do E1:** o `RunEvent` de `extracted` traz `extraction_id`, `reused`, `model`, o número de seções e as seções abaixo dos limites (`below_check`). Nunca texto do manuscrito.

## Falhas

| Situação | Resultado |
|---|---|
| Falta a `GEMINI_KEY` | `MissingModelKey` → `waiting_setup` |
| Chamada ao modelo falhou (fora do ar, cota, timeout de `METIS_LLM_TIMEOUT_SECONDS`) | `ModelUnavailable` → retry do estágio → `error_llm` |
| Resposta vazia, cortada, fora do schema ou seção obrigatória vazia | `InvalidModelAnswer` → retry do estágio → `error_llm` |
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
- **Custo:** o PDF vai em cada chamada. O Agno manda o texto do prompt antes do PDF, então o cache implícito do Gemini não reaproveita o PDF entre as chamadas.
- **Ainda não feito:** descrição de figuras, tabelas e fórmulas (1.6 e 1.8, em aberto), texto oculto (1.7, Integridade) e a ligação de cada citação no texto à sua referência, que o GROBID faria (as etapas 4.4 e 4.7 da Integridade dependiam dela).

## Como testar

- `extractor/tests/`: a config, o mapa, a conferência, a nova tentativa e o caso de uso, com uma sessão falsa e PDFs gerados no teste; a sessão do Agno contra um servidor HTTP local no lugar do Google; o E1 por attempt com banco real e PDF no storage.
- `pytest -m llm`: divide um artigo inventado com o Gemini de verdade (usa a `GEMINI_KEY` do `.env`; fica fora do `pytest` padrão e do CI).
- Calibração (11/11): dois artigos do ICLR 2017 (PeerRead) divididos de ponta a ponta. No 410 (13 páginas), 18 de 19 seções passaram nas duas medidas, com 21 chamadas em 30 s; no 304 (20 páginas), as 3 reprovadas eram de pseudocódigo, com 39 chamadas em 68 s.
