# Exemplo de extração (E1)

A saída real do E1 para um artigo do PeerRead, para ver o formato sem rodar o pipeline.

| Arquivo | O que é |
|---|---|
| `iclr2017_410_extracted_article.json` | O `ExtractedArticle`, como o E1 grava em `Extraction.content`: seções com cobertura e fidelidade, referências, citações ligadas, figuras e tabelas descritas e achados de texto oculto |
| `iclr2017_410_extracted_document.json` | O mesmo artigo no contrato `ExtractedDocument` (`extractor/document_adapter.py`), que o E2, o E3 e o E4 recebem |

**Origem:** ICLR 2017, artigo 410 do PeerRead (*A Baseline for Detecting Misclassified and
Out-of-Distribution Examples in Neural Networks*, Hendrycks e Gimpel),
`dataset_project/raw/PeerRead-master/data/iclr_2017/train/pdfs/410.pdf`
(SHA-256 `75573b15211a067090692d56e4b0977b8d3f7659486827f70158c22db914f53d`).

**Como foi gerado:** enviado pela API ao Docker em 16/11/2026, com o `gemini-2.5-flash`
(versão da extração `2a9b3bd344b6070b`). O resultado tem 19 seções, 42 referências,
44 citações ligadas e 13 figuras e tabelas, com as descrições em inglês, o idioma do artigo.

Limite conhecido, visível no arquivo: a extração das seções preserva bem o texto corrido,
mas fórmulas podem sair corrompidas (expoentes e índices perdidos); ver a comparação em
`../resultados/comparacao_peerread_2026-11-17/`.
