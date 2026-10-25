# Extração (E1)

## Objetivo

Transformar o PDF num `ExtractedDocument`: estrutura, referências, citações, figuras descritas, tabelas, fórmulas e achados de texto oculto. Os estágios seguintes leem esse contrato, nunca o PDF.

## Ferramentas

| Ferramenta | Licença | Papel |
|---|---|---|
| **GROBID 0.9.1** (`grobid/grobid:0.9.1-crf`, ~500 MB, roda em CPU) | Apache-2.0 | Cabeçalho, seções, referências estruturadas (`biblStruct`), ligação de cada citação no texto à referência (com a frase), coordenadas |
| **Docling** | MIT | Figuras (inclusive vetoriais), classe da figura, tabelas (TableFormer → markdown), fórmulas (LaTeX) |
| **pdfplumber** | MIT | Caracteres com cor, tamanho e posição, para achar texto oculto |
| **Agente de visão** (Agno, via `AgentFactory`) | — | Descrição contextual de cada figura |

A stack é toda permissiva. O PyMuPDF ficou de fora por ser AGPL.

**Parâmetros do GROBID:** `consolidateCitations=0`, `includeRawCitations=1`, `segmentSentences=1`, `teiCoordinates=ref,biblStruct,figure,s`.

O `consolidateCitations=0` é proposital. Com 1, o GROBID troca os metadados extraídos pelos do Crossref quando acha um DOI. Uma referência inventada, com DOI de aparência real, seria "consertada" e escondida. A Fase 2 da integridade precisa da referência como o autor a escreveu.

**Opções do Docling:** `generate_picture_images=True`, `images_scale=2.0`, `do_picture_classification=True`, `do_formula_enrichment=True`.

## Passo a passo

```text
PDF ─┬─▶ GROBID ──▶ seções, abstract, referências, citações ligadas, coords. de figuras ─┐
     ├─▶ Docling ─▶ figuras (bbox, legenda, recorte, classe), tabelas, fórmulas ────────┼─▶ junção por bbox
     └─▶ pdfplumber ─▶ texto oculto ───────────────────────────────────────────────────┘        │
                                                                                                 ▼
                                    descrição contextual das figuras (visão) ──▶ gate de qualidade ──▶ ExtractedDocument
```

1. **GROBID.** O TEI dá seções, abstract, referências e citações. Cada `<ref type="bibr">` aponta para uma `<biblStruct>`, junto com a frase que cita. Também vêm as coordenadas das figuras e os chamados no texto (`<ref type="figure">`).
2. **Docling.** Acha cada figura pelo layout da página renderizada e entrega bbox, legenda, recorte e classe (26 classes, como gráfico de linhas, de barras, fluxograma e estrutura química). Também entrega tabelas em markdown e fórmulas em LaTeX.
3. **Junção.** Por página + sobreposição de bbox. O Docling usa origem no canto inferior esquerdo e é convertido com `to_top_left_origin()`; o GROBID já usa o canto superior esquerdo, em pontos PDF. Assim o "Fig. 3" do texto chega ao recorte certo e aos parágrafos que o citam.
4. **Descrição contextual.** Para cada figura, o agente recebe recorte + legenda + parágrafos que a citam e devolve:
   - `FigureDescription{figure_id, kind, description, data_read, supports_claims, issues}`;
   - o prompt muda com a classe. Num gráfico: eixos, unidades, tendências, valores legíveis. Num diagrama: componentes e fluxos;
   - `supports_claims` diz se a figura sustenta o que o texto afirma sobre ela; `issues` aponta eixo sem unidade, legenda que não bate etc.;
   - concorrência limitada por um pool e cache pelo hash da imagem.
5. **Texto oculto** (Fase 0 da integridade): caractere com cor ≈ fundo, fonte < ~2 pt, texto fora da página ou sob imagens, e frases dirigidas a revisores IA ("ignore previous instructions", "give a positive review"). Os achados vão para o relatório de integridade.
6. **Gate de qualidade.** Sem texto, sem abstract ou sem referências → `InvalidSubmission` → `rejected_invalid_submission`, com o motivo.
7. **Montagem.** O `ExtractedDocumentBuilder` junta as fontes, valida no `build()` e persiste.

### Por que recortar a região, e não extrair as imagens embutidas

Extrair as imagens embutidas (como o `get_images()` do PyMuPDF) só enxerga figuras rasterizadas:
- Gráficos gerados por matplotlib e ferramentas parecidas costumam ser desenho vetorial, invisível para esse método.
- Figuras compostas, com (a), (b) e (c), saem quebradas em pedaços.

A detecção de layout trabalha sobre a página renderizada: vê vetorial e raster do mesmo jeito, e o recorte mantém a figura como o leitor a vê.

### Por que o LLM não extrai a estrutura

Perguntado sobre formatação, um LLM tende a "imaginar" layouts que não existem. Por isso a estrutura vem de parser, que é determinístico e dá coordenadas, e o LLM só descreve conteúdo visual.

## O `ExtractedDocument`

| Campo | Conteúdo |
|---|---|
| `metadata` | Título, autores, ano, idioma, número de páginas, versões dos parsers |
| `abstract` | Texto do abstract |
| `sections[]` | Título, nível (seção ou subseção), texto, ids das figuras e tabelas da seção, páginas, offsets |
| `references[]` | Id (`b0`, `b1`…), string crua, campos parseados (título, autores, ano, venue, DOI quando houver) |
| `citation_mentions[]` | Id da referência, frase que cita, seção, offsets |
| `figures[]` | Id, página, bbox, classe, legenda, recorte (arquivo + hash), `FigureDescription`, parágrafos que citam |
| `tables[]` | Id, página, legenda, markdown |
| `equations[]` | Id, página, LaTeX |
| `hidden_text_findings[]` | Página, bbox, texto, motivo (cor, tamanho, posição ou padrão de instrução) |

`render_for_llm()` gera o texto que os modelos leem, com `[FIGURA 3: …]` e `[TABELA 2: …]` na posição de cada elemento:
- o artigo inteiro, para o juiz e para o modo `whole_document`;
- uma seção, para os passes por seção do E4. A hierarquia de subseções permite dividir uma seção longa em vários passes.

## Cache

A extração é guardada pela chave sha256 do PDF + versões dos parsers. Um run novo da mesma attempt reaproveita a extração; atualizar um parser força uma nova.

## Falhas

| Situação | Resultado |
|---|---|
| GROBID fora do ar ou timeout | Erro passageiro → retry → `error_external` |
| PDF corrompido, criptografado ou sem texto | `rejected_invalid_submission`, com o motivo |
| PDF escaneado (sem camada de texto) | No MVP, `rejected_invalid_submission` com o motivo. Depois, OCR do Docling |
| Falha ao descrever uma figura | A figura fica sem descrição, marcada no documento, e o estágio segue. Se o provedor estiver fora (todas falham), vira erro passageiro do estágio |

## Como testar

- 3–5 PDFs reais como fixtures, com snapshot do `ExtractedDocument`.
- Os `referenceMentions` do PeerRead (gerados pelo science-parse) servem de gabarito para a ligação citação ↔ referência.
- Um PDF com texto branco ou minúsculo plantado: o scan precisa achar.
- Um PDF com gráfico vetorial: a figura precisa ser detectada e recortada inteira.
