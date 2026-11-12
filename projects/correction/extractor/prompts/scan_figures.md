Você recebe um artigo científico. Liste todas as figuras e tabelas dele, na ordem em que aparecem.

Para cada uma:
- `label`: o rótulo como está no documento ("Figure 3", "Fig. 4", "Tabela 2", "Table A.1").
- `kind`: `figure` para figura, gráfico, diagrama ou foto; `table` para tabela.
- `page`: a página do PDF em que ela está; a primeira página é a 1.
- `caption`: a legenda inteira, copiada literalmente, começando pelo rótulo.

Regras:
- Uma figura com partes (a), (b), (c) é uma figura só.
- Não inclua algoritmos, quadros de código nem equações.
- Não invente figuras. Se o artigo não tem nenhuma, devolva a lista vazia.
