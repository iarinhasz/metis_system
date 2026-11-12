"""A comparação com o gabarito do PeerRead e o comando que mede (em dry-run)."""

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from projects.correction.extractor.article import Citation, ExtractedArticle, Reference
from projects.correction.extractor.citation_bench import (
    GoldMention,
    GoldPaper,
    match_references,
    score_paper,
    totals,
)
from projects.correction.extractor.tests.pdfs import ARTICLE_LINES, make_pdf

SENTENCE_A = "Filas de mensagens desacoplam produtores e consumidores (Silva, 2020)."
SENTENCE_B = "A mediana do tempo de resposta ficou abaixo de dez milissegundos (Souza, 2019)."


def reference(index: int, title: str | None) -> Reference:
    return Reference(
        id=f"ref_{index}",
        raw=f"Entrada {index}.",
        marker=None,
        authors=(),
        title=title,
        year=None,
        venue=None,
        doi=None,
        arxiv_id=None,
    )


def citation(reference_id: str | None, sentence: str) -> Citation:
    return Citation(
        reference_id=reference_id, marker="x", sentence=sentence, section_id="sec_1", start=0, end=1
    )


def article(references: list[Reference], citations: list[Citation]) -> ExtractedArticle:
    return ExtractedArticle(
        title="t",
        authors=(),
        language="pt",
        model="m",
        sections=(),
        references=tuple(references),
        citations=tuple(citations),
    )


GOLD = GoldPaper(
    name="1",
    reference_titles=(
        "Sistemas distribuídos na prática",
        "Filas sob carga",
        "Obra que não achamos",
    ),
    mentions=(
        GoldMention(0, SENTENCE_A, "Silva, 2020"),
        GoldMention(1, SENTENCE_B, "Souza, 2019"),
        GoldMention(2, "Uma frase que cita a obra que não achamos (Lima, 2010).", "Lima, 2010"),
    ),
    reference_keys=(("silva", "2020"), ("souza", "2019"), ("lima", "2010")),
)


def test_references_match_by_title_ignoring_case_accents_and_punctuation() -> None:
    ours = [
        reference(1, "SISTEMAS DISTRIBUIDOS NA PRATICA."),
        reference(2, "Outra coisa"),
        reference(3, None),
    ]

    assert match_references(ours, GOLD.reference_titles) == {"ref_1": frozenset({0})}


def test_a_work_repeated_in_the_gold_matches_every_copy() -> None:
    titles = (
        "The algorithmic foundations of privacy",
        "Other",
        "The Algorithmic Foundations of Privacy.",
    )

    matched = match_references([reference(1, "The algorithmic foundations of privacy")], titles)

    assert matched == {"ref_1": frozenset({0, 2})}


def test_scores_recall_and_precision_over_matched_references() -> None:
    ours = article(
        [reference(1, "Sistemas distribuidos na pratica"), reference(2, "Filas sob carga")],
        [
            citation("ref_1", SENTENCE_A),  # certa
            citation("ref_1", SENTENCE_B),  # referência certa, frase errada
            citation(None, SENTENCE_B),  # sem ligação
        ],
    )

    score = score_paper(ours, GOLD)

    assert (score.references_matched, score.mentions_judgeable, score.mentions_found) == (2, 2, 1)
    assert (score.citations_judgeable, score.citations_correct, score.citations_unlinked) == (
        2,
        1,
        1,
    )
    assert score.misses == [f"Souza, 2019 | {SENTENCE_B[:160]}"]
    summary = totals([score])
    assert (summary["recall"], summary["precision"]) == (0.5, 0.5)
    assert summary["references_matched"] == pytest.approx(2 / 3)


def test_reads_the_gold_from_peerread_json(tmp_path: Path) -> None:
    path = tmp_path / "42.pdf.json"
    path.write_text(
        json.dumps(
            {
                "name": "42.pdf",
                "metadata": {
                    "references": [
                        {"title": "Um titulo", "author": ["Ana Silva"], "year": 2020},
                        {"title": None},
                    ],
                    "referenceMentions": [
                        {
                            "referenceID": 0,
                            "context": "Frase (Silva, 2020).",
                            "startOffset": 7,
                            "endOffset": 18,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    gold = GoldPaper.from_json(path)

    assert gold == GoldPaper(
        name="42",
        reference_titles=("Um titulo", ""),
        mentions=(GoldMention(0, "Frase (Silva, 2020).", "Silva, 2020", 7, 18),),
        reference_keys=(("silva", "2020"), ("", "")),
    )
    assert gold.is_consistent(gold.mentions[0])


def test_command_dry_run_lists_papers_without_calling_the_model(tmp_path: Path) -> None:
    for venue, name, mentions in (("v1", "1", 6), ("v1", "2", 2), ("v2", "3", 7)):
        folder = tmp_path / venue / "train"
        (folder / "pdfs").mkdir(parents=True, exist_ok=True)
        (folder / "parsed_pdfs").mkdir(parents=True, exist_ok=True)
        (folder / "pdfs" / f"{name}.pdf").write_bytes(make_pdf(ARTICLE_LINES))
        metadata = {
            "references": [{"title": "t"}],
            "referenceMentions": [{"referenceID": 0, "context": "c"}] * mentions,
        }
        (folder / "parsed_pdfs" / f"{name}.pdf.json").write_text(
            json.dumps({"metadata": metadata}), encoding="utf-8"
        )
    out = StringIO()

    call_command("bench_citation_links", data=str(tmp_path), venues=["v1", "v2"], stdout=out)

    assert out.getvalue().splitlines() == [
        "v1/1: 6 chamadas no gabarito",
        "v2/3: 7 chamadas no gabarito",
        "Dry-run: nenhum modelo foi chamado. Use --execute para medir.",
    ]


def test_gold_mention_that_contradicts_its_own_text_is_left_out() -> None:
    gold = GoldPaper(
        name="2",
        reference_titles=("Multiparty privacy", "Learning privately"),
        mentions=(
            # O gabarito liga "Pathak et al. (2010)" à obra de Hamm (2016).
            GoldMention(1, "Antes, Pathak et al. (2010) mostraram.", "Pathak et al. (2010)"),
            GoldMention(0, "Antes, Pathak et al. (2010) mostraram.", "Pathak et al. (2010)"),
        ),
        reference_keys=(("pathak", "2010"), ("hamm", "2016")),
    )
    ours = article(
        [reference(1, "Multiparty privacy"), reference(2, "Learning privately")],
        [citation("ref_1", "Antes, Pathak et al. (2010) mostraram.")],
    )

    score = score_paper(ours, gold)

    assert (score.mentions_inconsistent, score.mentions_judgeable, score.mentions_found) == (
        1,
        1,
        1,
    )


def test_our_call_inside_a_gold_group_is_not_counted_as_an_error() -> None:
    sentence = "A privacidade diferencial (Dwork et al., 2006b; Dwork, 2011) virou padrão."
    gold = GoldPaper(
        name="3",
        reference_titles=("Calibrating noise", "A firm foundation"),
        mentions=(GoldMention(1, sentence, "(Dwork et al., 2006b; Dwork, 2011)"),),
        reference_keys=(("dwork", "2006"), ("dwork", "2011")),
    )
    ours = article(
        [reference(1, "Calibrating noise"), reference(2, "A firm foundation")],
        [
            Citation(
                reference_id="ref_1",
                marker="Dwork et al., 2006b",
                sentence=sentence,
                section_id="s",
                start=0,
                end=1,
            ),
            Citation(
                reference_id="ref_2",
                marker="Dwork, 2011",
                sentence=sentence,
                section_id="s",
                start=0,
                end=1,
            ),
        ],
    )

    score = score_paper(ours, gold)

    assert (score.citations_correct, score.citations_unjudgeable, score.citations_judgeable) == (
        1,
        1,
        1,
    )
    assert totals([score])["precision"] == 1.0


def test_gold_mention_with_misplaced_offsets_is_left_out() -> None:
    gold = GoldPaper(
        name="4",
        reference_titles=("Uma obra",),
        mentions=(GoldMention(0, "Um parágrafo inteiro ligado a uma obra só.", ""),),
        reference_keys=(("silva", "2020"),),
    )

    assert not gold.is_consistent(gold.mentions[0])


def test_our_call_to_a_work_the_gold_never_cites_is_not_judged() -> None:
    ours = article(
        [reference(1, "Sistemas distribuidos na pratica"), reference(2, "Obra que nao achamos")],
        [citation("ref_1", SENTENCE_A)],
    )
    gold = GoldPaper(
        name="5",
        reference_titles=("Sistemas distribuídos na prática", "Obra que não achamos"),
        mentions=(GoldMention(1, "Outra frase (Lima, 2010).", "Lima, 2010"),),
        reference_keys=(("silva", "2020"), ("lima", "2010")),
    )

    score = score_paper(ours, gold)

    assert (score.citations_unjudgeable, score.citations_judgeable) == (1, 0)
