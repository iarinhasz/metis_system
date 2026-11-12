Você recebe um artigo científico. A tarefa é mapear a estrutura dele, sem extrair o conteúdo.

Devolva:
- o título do artigo e os nomes dos autores, como estão no documento, sem as marcas de nota ou de afiliação (`*`, `†`, números sobrescritos);
- o idioma do texto principal, em código ISO 639-1 (`pt`, `en`, `es`…);
- os títulos das seções, na ordem em que aparecem, cada um com o nível: 1 para seção, 2 para subseção, 3 para a subseção dela, e assim por diante.

Regras para os títulos:
- Copie cada título exatamente como está no documento, com a numeração quando houver (ex.: "2.1 Coleta de dados").
- Inclua o resumo (abstract), os agradecimentos, as referências e os apêndices quando existirem, mesmo sem numeração.
- Só conta como seção o título que ocupa uma linha própria. Um título de parágrafo, isto é, palavras em destaque no começo de um parágrafo, seguidas do texto na mesma linha (ex.: "Quicksort. The algorithm…"), não é seção: o texto dele fica na seção em que está.
- Não inclua o título do artigo, legendas de figuras e tabelas, cabeçalhos e rodapés de página, nem títulos ou rótulos de dentro de tabelas, algoritmos, listas, quadros ou código (ex.: "Algorithm 2", "WRITE.", "Argument Sets").
- Não invente títulos. Se o documento não tem seções, devolva a lista vazia.
