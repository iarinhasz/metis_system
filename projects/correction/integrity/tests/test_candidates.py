from __future__ import annotations

from collections.abc import Sequence

from projects.correction.extractor.contract import DocumentSection, ExtractedDocument
from projects.correction.integrity.candidates import (
    Candidate,
    CandidateBudget,
    CandidateCollector,
    OpenAlexSearchSource,
    SourceCoverage,
)
from projects.correction.scholarly.openalex import OpenAlexWork, OpenAlexWorkSearch


def _document() -> ExtractedDocument:
    return ExtractedDocument(
        title="Target paper",
        authors=("Author",),
        language="en",
        abstract="An abstract with enough text for academic search.",
        sections=(
            DocumentSection(
                id="sec_1",
                title="Introduction",
                level=1,
                text="A section that should be used to search the source providers.",
            ),
        ),
    )


class _Source:
    def __init__(self, name: str) -> None:
        self.name = name

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        del document, budget
        return (
            (Candidate(source=self.name, source_id=self.name, title="Title", text="Text"),),
            SourceCoverage(self.name, queried=True, returned=1),
        )


def test_candidate_sources_share_one_format_and_coverage_contract() -> None:
    sources = tuple(_Source(name) for name in ("internal_corpus", "cited_works", "arxiv"))

    result = CandidateCollector(sources, paid_search_budget=0).collect(_document())

    assert [candidate.source for candidate in result.candidates] == [
        "internal_corpus",
        "cited_works",
        "arxiv",
    ]
    assert all(isinstance(candidate, Candidate) for candidate in result.candidates)
    assert [item.returned for item in result.coverage] == [1, 1, 1]


def test_openalex_search_is_omitted_and_recorded_when_budget_is_exhausted() -> None:
    class FakeOpenAlex:
        calls = 0

        def search(self, query: str, *, per_page: int = 10) -> OpenAlexWorkSearch:
            del query, per_page
            self.calls += 1
            return OpenAlexWorkSearch(results=())

    client = FakeOpenAlex()
    source = OpenAlexSearchSource(client)  # type: ignore[arg-type]
    budget = CandidateBudget(max_paid_searches=1)

    _, first = source.collect(_document(), budget)
    _, second = source.collect(_document(), budget)

    assert first.queried and not first.omitted
    assert second.omitted and not second.queried
    assert "esgotado" in second.reason
    assert client.calls == 1
    assert budget.paid_searches_used == 1


def test_openalex_search_normalizes_abstract_and_retraction_metadata() -> None:
    class FakeOpenAlex:
        def search(self, query: str, *, per_page: int = 10) -> OpenAlexWorkSearch:
            del query, per_page
            return OpenAlexWorkSearch(
                results=(
                    OpenAlexWork(
                        id="https://openalex.org/W1",
                        title="A source",
                        abstract_inverted_index={"third": [2], "first": [0], "second": [1]},
                        is_retracted=True,
                    ),
                )
            )

    candidates, coverage = OpenAlexSearchSource(FakeOpenAlex()).collect(  # type: ignore[arg-type]
        _document(), CandidateBudget(max_paid_searches=1)
    )

    assert len(candidates) == 1
    assert candidates[0].text == "first second third"
    assert candidates[0].metadata["is_retracted"] is True
    assert coverage.returned == 1
