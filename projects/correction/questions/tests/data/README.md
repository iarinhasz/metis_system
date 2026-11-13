# Resposta gravada do OpenAlex

`openalex_topics.json` foi obtido da API pública em 12/11/2026, sem chave, pela URL:

https://api.openalex.org/topics?per_page=4&page=1&sort=id&select=id,display_name,domain,field,subfield

É a primeira página, sem alterações; `meta.count` descreve a coleção inteira. Nos testes
HTTP, os quatro resultados são repartidos em duas páginas e apenas os metadados de
paginação são ajustados. Nos testes de arquivo, usa-se a lista `results` como recorte
explícito. O comando recusa importar esta página como se fosse a coleção completa.

Os dados do OpenAlex são CC0. Os testes rodam sem acesso à rede externa.

`openalex_catalog.json` reúne os mesmos quatro topics e o subfield Bioengineering
(`subfields/1502`), com os ancestrais devolvidos por
`https://api.openalex.org/subfields?per_page=100&page=1&sort=id&select=id,display_name,domain,field`.
O recorte remove só os metadados da resposta e os demais resultados. Bioengineering
não tem topic associado na coleção consultada; o teste confirma que ele continua na árvore.
