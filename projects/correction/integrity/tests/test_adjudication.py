from __future__ import annotations

from types import SimpleNamespace

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)
from projects.correction.integrity.adjudication import (
    AdjudicatorOutput,
    adjudicate_pairs,
    lexical_pairs,
)
from projects.correction.integrity.candidates import Candidate

PASSAGE = "The authors measured outcomes across several independent clinical groups."


def _document(text: str, *, cited: bool = False) -> ExtractedDocument:
    return ExtractedDocument(
        title="Submitted paper",
        authors=("Jane Author",),
        language="en",
        abstract="A short abstract.",
        sections=(
            DocumentSection(
                id="sec_1",
                title="Results",
                level=1,
                text=text,
            ),
        ),
        references=(
            (DocumentReference(id="ref_1", raw="Reference", authors=("Other Person",)),)
            if cited
            else ()
        ),
        citation_mentions=(
            (
                CitationMention(
                    reference_id="ref_1",
                    marker="[1]",
                    sentence=text,
                    section_id="sec_1",
                    start_offset=0,
                    end_offset=len(text),
                ),
            )
            if cited
            else ()
        ),
    )


class _Factory:
    def __init__(self) -> None:
        self.calls = 0

    def plagiarism_adjudicator(self, *, output_schema: type[AdjudicatorOutput]) -> _Runner:
        assert output_schema is AdjudicatorOutput
        self.calls += 1
        return _Runner()


class _Runner:
    def run(self, payload: str) -> SimpleNamespace:
        assert "Trecho do manuscrito" in payload
        return SimpleNamespace(
            valid=True,
            content=AdjudicatorOutput(
                verdict="verbatim_copy",
                confidence=0.98,
                justification="The wording is identical.",
            ),
        )


def test_cited_quoted_passage_skips_adjudicator() -> None:
    text = f"“{PASSAGE}.” [1]"
    document = _document(text, cited=True)
    candidate = Candidate(
        source="cited_works",
        source_id="doi:10.1/example",
        title="A related work",
        text=PASSAGE,
        reference_id="ref_1",
    )
    factory = _Factory()

    batch = adjudicate_pairs(
        document,
        (candidate,),
        lexical_pairs(document, (candidate,)),
        factory=factory,  # type: ignore[arg-type]
        top_n=5,
        max_workers=1,
    )

    assert factory.calls == 0
    assert batch.adjudicated == ()
    assert batch.assessments[0].disposition == "properly_cited"
    assert batch.assessments[0].quoted


def test_only_top_n_unquoted_pairs_are_sent_to_the_adjudicator() -> None:
    document = ExtractedDocument(
        title="Submitted paper",
        authors=("Jane Author",),
        language="en",
        abstract="A short abstract.",
        sections=(
            DocumentSection(id="sec_1", title="First", level=1, text=PASSAGE),
            DocumentSection(id="sec_2", title="Second", level=1, text=PASSAGE),
        ),
    )
    candidate = Candidate(
        source="internal_corpus",
        source_id="source-1",
        title="A different work",
        text=PASSAGE,
    )
    pairs = lexical_pairs(document, (candidate,))
    factory = _Factory()

    batch = adjudicate_pairs(
        document,
        (candidate,),
        pairs,
        factory=factory,  # type: ignore[arg-type]
        top_n=1,
        max_workers=1,
    )

    assert len(batch.assessments) >= 2
    assert factory.calls == 1
    assert len(batch.adjudicated) == 1
