# Fixtures do PeerRead

Doze artigos do ACL 2017 convertidos para o contrato `ExtractedDocument`, a partir dos `parsed_pdfs` (science-parse) do [PeerRead](https://github.com/allenai/PeerRead). São para testar a avaliação (E2–E5) sem pagar o E1.

Geradas com `python manage.py make_peerread_fixtures --limit 12 --execute` em 16/11/2026, a partir de `dataset_project/raw/PeerRead-master/data/acl_2017/{dev,test}/parsed_pdfs/`. A origem de cada arquivo:

| Fixture | Origem | Título |
|---|---|---|
| `peerread-01.json` | ACL 2017 `dev`, `173.pdf` | Determining Gains Acquired from Word Embedding Quantitatively using Discrete Distribution Clustering |
| `peerread-02.json` | ACL 2017 `dev`, `352.pdf` | 352.pdf |
| `peerread-03.json` | ACL 2017 `dev`, `37.pdf` | Sequential Matching Network: A New Architecture for Multi-turn Response Selection in Retrieval-based Chatbots |
| `peerread-04.json` | ACL 2017 `dev`, `371.pdf` | 371.pdf |
| `peerread-05.json` | ACL 2017 `dev`, `489.pdf` | Combining distributional and referential information for naming objects through cross-modal mapping and direct word prediction |
| `peerread-06.json` | ACL 2017 `dev`, `660.pdf` | Automatically Generating Rhythmic Verse with Neural Networks |
| `peerread-07.json` | ACL 2017 `dev`, `94.pdf` | A Full Non-Monotonic Transition System for Unrestricted Non-Projective Parsing |
| `peerread-08.json` | ACL 2017 `test`, `148.pdf` | Evaluation Metrics for Reading Comprehension: Prerequisite Skills and Readability |
| `peerread-09.json` | ACL 2017 `test`, `323.pdf` | A Neural Local Coherence Model |
| `peerread-10.json` | ACL 2017 `test`, `355.pdf` | Neural Modeling of Multi-Predicate Interactions for Japanese Predicate Argument Structure Analysis |
| `peerread-11.json` | ACL 2017 `test`, `435.pdf` | Neural Disambiguation of Causal Lexical Markers based on Context |
| `peerread-12.json` | ACL 2017 `test`, `49.pdf` | Chunk-based Decoder for Neural Machine Translation |

Os artigos são da ACL Anthology, sob a licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); os direitos são dos autores. O PeerRead é da Allen Institute for AI (Apache 2.0).

Limites: o science-parse não traz figuras com descrição, e em dois artigos (ACL 352 e 371) não achou o título, que ficou com o nome do arquivo.
