# Checagem de integridade (E3)

**Desenho revisto em 13/11/2026; implementação atualizada para as etapas M4.** O E3
usa o corpus vetorial, detectores léxico e semântico, resolução bibliográfica,
coleta de candidatos, filtro por citação, adjudicação limitada e regras versionadas.
Risco alto pausa o run para revisão humana; o LLM não decide o nível de risco.
O relatório mantém no `coverage` as fontes e limitações efetivamente observadas.

## Objetivo e princípios

O E3 procura sinais de plágio, de citações problemáticas e de manipulação, e guarda evidência para cada achado.

- **Regras explícitas decidem o nível de risco.** O LLM julga casos ambíguos e redige a explicação, mas não escolhe o nível.
- **Risco alto vai para uma pessoa.** O sistema nunca rejeita sozinho: falso positivo de plágio tem custo alto (descrição padrão de método, preprint do próprio autor).
- **O relatório declara o que não conseguiu checar** (campo `coverage`).

## Visão geral

```text
                     resolver referências (Fase 2, passo 1)
                                   │
                  ┌────────────────┴────────────────┐
                  ▼                                 ▼
     Fase 1: similaridade (funil)       Fase 2: retratação, consistência,
                  │                     alinhamento citação ↔ afirmação
                  └────────────────┬────────────────┘
                                   ▼
          cruzamento ──▶ regras de risco ──▶ IntegrityReport ──▶ gate
                   + Fase 0: texto oculto (achado no E1)
```

A resolução das referências roda **primeiro**, porque as duas fases dependem dela: a Fase 1 usa as obras citadas como candidatas. Depois as duas fases rodam em `Parallel` num workflow Agno. O cruzamento e as regras são código.

## Fase 0 — Texto oculto e prompt injection

O E1 encontra o texto oculto (ver [Extração](extraction.md)), e aqui ele vira achado. Instrução escondida dirigida a revisores IA tem severidade alta, porque é uma tentativa de manipular a avaliação.

## Fase 1 — Similaridade, em funil

Do mais barato ao mais caro:

1. **Candidatos.**

   | Fonte | O que traz | Limite e custo |
   |---|---|---|
   | Corpus interno (pgvector) | Attempts anteriores + semente do PeerRead | — |
   | Obras citadas | Abstract e, quando houver, full text em acesso aberto | — |
   | Semantic Scholar `/paper/search` | Artigos relacionados | 1 req/s com chave |
   | arXiv | Busca e PDF | 1 requisição a cada 3 s |
   | OpenAlex (busca) | Artigos relacionados | **Paga desde 2026**: US$ 1 por mil buscas; a chave grátis dá US$ 1/dia → orçamento por run |

   O texto integral em acesso aberto ainda não é baixado nem extraído nesta implementação: os links OA são registrados e os abstracts são candidatos; `coverage.full_text` declara essa limitação. O corpus PeerRead e os artigos submetidos são divididos em chunks e ganham embeddings locais.
2. **Léxico, sem LLM.**
   - MinHash-LSH (`datasketch` 2.0, MIT), sobre shingles de palavras, acha os parágrafos candidatos.
   - *Winnowing* localiza os trechos idênticos, com offsets: guarda o menor hash de cada janela de k-gramas, com hash estável (blake2b). Qualquer trecho comum com pelo menos `w + k − 1` palavras é detectado.
3. **Semântico.**
   - O modelo é o **multilingual-E5-large** via FastEmbed/ONNX (mais de 100 idiomas, limite de 512 tokens, vetores de 1024 dimensões), rodando **localmente**: o manuscrito não sai da infraestrutura. Chunks de até 300 palavras reduzem o risco de truncamento; cada chunk recebe os k vizinhos mais próximos (índice HNSW do pgvector). O BGE-M3 previsto inicialmente não está disponível no FastEmbed compatível com Python 3.14.
   - A carga inicial usa as fixtures `ExtractedDocument` do PeerRead: `make_peerread_fixtures --execute` prepara pelo menos 10 artigos em `projects/correction/extractor/tests/fixtures/peerread`; `load_peerread` valida cinco por padrão em dry-run. Para gravar documentos e vetores, rode `load_peerread --execute`.
   - **Cópia traduzida** (PT↔EN) aparece como uma sequência de frases alinhadas na mesma ordem (cosseno + vizinho mais próximo nos dois sentidos).
   - O **SPECTER2** não serve aqui: só funciona em inglês e compara artigos inteiros.
   - Os limiares são calibrados com abstracts bilíngues do SciELO e com o plágio sintético do PeerRead. Não existe benchmark público PT↔EN para modelos atuais.
4. **Filtro por citação.** Para cada par suspeito:
   - a fonte está citada nesse trecho? Pela ligação de cada citação à sua referência, que o E1 entrega em `citations[]` (ver [Extração](extraction.md#passo-a-passo));
   - o trecho está entre aspas?
   - é boilerplate (descrição padrão de método, definição)?
   - é o mesmo trabalho, como o preprint do próprio autor (título e autores batem)?
5. **LLM só nos top-N pares.** Veredito: `verbatim_copy | paraphrase_without_attribution | properly_cited | common_knowledge | same_work | false_positive`, com confiança e justificativa.

## Fase 2 — Citações

1. **Existência, em cascata.**
   - Com DOI → Crossref (404 é alerta) + OpenAlex por DOI (consulta grátis; traz `is_retracted`, abstract e link de acesso aberto).
   - Sem DOI → Crossref `query.bibliographic` com a string crua + Semantic Scholar `paper/search/match`.
   - Aceite: título com similaridade ≥ ~0,9, mesmo sobrenome do primeiro autor e diferença de ano ≤ 1.
   - Caso duvidoso → LLM, medindo a taxa de falso positivo.
   - Heurísticas de referência: `halref` e `RefChecker` (MIT).
   - Resultado por referência: `ok | metadata_mismatch | not_found`.

   Referência inventada é um sinal objetivo, mais confiável que qualquer "detector de texto gerado por IA".
2. **Retratação.** Crossref (`update-to`/`updated-by`, com fonte Retraction Watch) + `is_retracted` do OpenAlex.
3. **Consistência.** Referência nunca citada no texto, citação sem entrada na lista, taxa de autocitação.
4. **Alinhamento citação ↔ afirmação**, numa amostra de K frases.
   - Compara primeiro com o abstract da obra citada e só busca o full text se o resultado for `INSUFFICIENT`.
   - Frase em português contra fonte em inglês → juiz LLM, porque os modelos de inferência textual disponíveis são só em inglês.
   - Rótulos: `SUPPORTS | PARTIAL | CONTRADICTS | UNRELATED | INSUFFICIENT`.

## Cruzamento das fases

| Situação | Leitura |
|---|---|
| Fonte muito similar (Fase 1) que **não está nas referências** (Fase 2) | Citação faltante: o sinal mais forte de plágio |
| Fonte similar, citada no trecho e entre aspas | `properly_cited`; o achado desce de severidade |
| Trecho similar a um trabalho retratado | Registrado à parte, junto com o achado de retratação |

## Regras de risco

**Proposta inicial.** Os limiares N, X e K ficam em `integrity/rules.py`, configuráveis, e são calibrados no M4/M5.

| Nível | Quando (basta uma condição) |
|---|---|
| Alto | Instrução oculta dirigida a IA; trecho literal ou quase literal (≥ N frases seguidas) de fonte não citada; paráfrase sem atribuição cobrindo ≥ X% do texto; ≥ K referências inexistentes |
| Médio | Paráfrase sem atribuição pontual; referências com metadados divergentes; trabalho retratado citado como suporte; vários alinhamentos `CONTRADICTS` |
| Baixo | Só achados de baixa severidade ou boilerplate |

Limiar fixo no código não acompanha a calibração. Aqui os limiares são configuração, com teste.

## O relatório

`IntegrityReport`:

| Campo | Conteúdo |
|---|---|
| `risk_level` | `low`, `medium` ou `high`, pelas regras |
| `findings[]` | Os achados (abaixo) |
| `coverage` | O que foi checado e os limites: fontes consultadas, referências resolvidas, orçamento usado, o que ficou de fora |
| `narrative` | Resumo em texto, redigido pelo LLM a partir dos achados |

Exemplo ilustrativo de achado:

```json
{
  "type": "missing_citation",
  "severity": "high",
  "excerpt": {"page": 3, "section": "2. Trabalhos relacionados", "text": "…"},
  "source": {"doi": "10.xxxx/…", "title": "…", "excerpt": "…"},
  "lexical_score": 0.71,
  "semantic_score": 0.93,
  "cited": false,
  "verdict": "paraphrase_without_attribution",
  "rationale": "Mesma sequência de argumentos e exemplos da fonte, reescrita, sem citá-la."
}
```

## Gate e revisão humana

- **Risco alto** → `waiting_human_review`. O admin mostra os achados com o trecho do artigo e o da fonte lado a lado. A pessoa escolhe *continuar* ou *encerrar* e deixa uma nota; a decisão vira `RunEvent`.
- **Risco médio ou baixo** → o run segue. O resumo entra no contexto dos avaliadores, que podem considerá-lo em originalidade, por exemplo.

## APIs externas

Verificado em outubro de 2026. Preços e limites mudam; o OpenAlex, por exemplo, mudou em 2026.

| API | Uso | Autenticação | Limite e custo |
|---|---|---|---|
| Crossref | DOI, `query.bibliographic`, retratação | `mailto` (pool *polite*) | Consultas: 3 req/s e 3 simultâneas; por DOI: 10 req/s |
| OpenAlex | Por DOI (grátis): abstract, `is_retracted`, acesso aberto. Busca (paga) | Chave obrigatória desde fev/2026 | Por DOI grátis; busca US$ 1/mil; chave grátis = US$ 1/dia; 30 req/s |
| Semantic Scholar | `search/match`, busca, referências com contexto | Chave (`x-api-key`) | 1 req/s; exige atribuição; proíbe revenda |
| arXiv | Busca e PDF | — | 1 requisição a cada 3 s |
| Unpaywall | PDF em acesso aberto por DOI | E-mail real | ~100 mil chamadas/dia |

- **Ordem de consulta:** Crossref → OpenAlex por DOI → Semantic Scholar → arXiv.
- **Rate limit:** por provedor, com token bucket no Redis.
- **Cache:** por DOI, porque as mesmas referências se repetem entre artigos.
- Os clientes compartilhados de `scholarly/` usam `urllib`, timeout por cliente e retries limitados para 429/5xx; esgotadas as tentativas, a falha transitória propaga para o retry do estágio. O cache armazena somente respostas bem-sucedidas.
- **Tempo estimado** para um artigo com ~40 referências: ~15 s no Crossref e ~40 s no Semantic Scholar.

## Limitações declaradas no `coverage`

- **Full texts fechados ficam de fora.** O iThenticate (Crossref Similarity Check) tem acordos com editoras que não temos.
- **Muitas fontes só têm abstract**, o que limita a detecção de paráfrase.
- **O alinhamento começa pelo abstract**, então `INSUFFICIENT` é comum, e não é acusação.
- **O orçamento** (buscas pagas no OpenAlex) pode encerrar a busca de candidatos antes do fim; isso fica registrado.

## Como avaliar a checagem

| O quê | Como |
|---|---|
| Fase 1 | `python manage.py bench_plagiarism`; por padrão mede trechos literais. `--with-llm` gera, com chamadas externas explícitas, exemplos parafraseados e traduzidos para PT. |
| Limiares cross-lingual | Abstracts bilíngues do SciELO |
| Alinhamento citação ↔ afirmação | SciCiteVal e Citation Integrity |
| Existência de referências | Referências inventadas plantadas, medindo também a taxa de falso positivo |
| Fase 0 | PDFs com texto oculto plantado |

O benchmark registra as métricas por tipo e os limiares usados; a execução, por si
só, não declara os limiares calibrados nem que a meta Q11 foi atingida.
