from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.resolution import resolve_references
from projects.correction.scholarly.crossref import CrossrefWork, CrossrefWorks
from projects.correction.scholarly.openalex import OpenAlexLocation, OpenAlexWork
from projects.correction.scholarly.semantic_scholar import SemanticScholarPaper


class FakeCrossref:
    def __init__(self, work: CrossrefWork | None = None) -> None:
        self.work = work
        self.calls: list[tuple[str, str]] = []

    def by_doi(self, doi: str) -> CrossrefWork | None:
        self.calls.append(("by_doi", doi))
        return self.work

    def search(self, query: str, *, rows: int = 10) -> CrossrefWorks:
        self.calls.append(("search", query))
        return CrossrefWorks(
            items=(self.work,) if self.work is not None else (),
            total_results=1 if self.work is not None else 0,
        )


class FakeOpenAlex:
    def __init__(self, work: OpenAlexWork | None = None) -> None:
        self.work = work
        self.calls: list[str] = []

    def by_doi(self, doi: str) -> OpenAlexWork | None:
        self.calls.append(doi)
        return self.work


class FakeSemanticScholar:
    def __init__(
        self,
        paper: SemanticScholarPaper | None = None,
    ) -> None:
        self.paper = paper
        self.calls: list[tuple[str, str]] = []

    def by_doi(self, doi: str) -> SemanticScholarPaper | None:
        self.calls.append(("by_doi", doi))
        return self.paper

    def match(self, query: str) -> SemanticScholarPaper | None:
        self.calls.append(("match", query))
        return self.paper


def test_resolves_doi_through_ordered_providers_and_collects_metadata() -> None:
    reference = DocumentReference(
        id="ref-1",
        raw="Smith, A. Sample work. 2024.",
        authors=("Smith, Alice",),
        title="A Sample Work",
        year="2024",
        doi="https://doi.org/10.1000/example",
    )
    crossref_work = CrossrefWork.model_validate(
        {
            "DOI": "10.1000/example",
            "title": ["A Sample Work"],
            "author": [{"family": "Smith", "given": "Alice"}],
            "published": {"date-parts": [[2024]]},
        }
    )
    crossref = FakeCrossref(crossref_work)
    openalex = FakeOpenAlex(
        OpenAlexWork(
            id="https://openalex.org/W123",
            doi="https://doi.org/10.1000/example",
            title="A Sample Work",
            publication_year=2024,
            authorships=({"author": {"display_name": "Alice Smith"}},),
            abstract_inverted_index={"Abstract": [0], "found.": [1]},
            is_retracted=True,
            best_oa_location=OpenAlexLocation(pdf_url="https://example.org/paper.pdf"),
        )
    )
    semantic = FakeSemanticScholar(
        SemanticScholarPaper(
            paper_id="paper-123",
            external_ids={"DOI": "10.1000/example", "ArXiv": "2401.00001"},
            title="A Sample Work",
            year=2024,
            authors=({"name": "Alice Smith"},),
        )
    )

    result = resolve_references(
        (reference,),
        crossref=crossref,
        openalex=openalex,
        semantic_scholar=semantic,
    )[0]

    assert result.status == "ok"
    assert result.provider == "crossref"
    assert result.doi == "10.1000/example"
    assert result.openalex_id == "https://openalex.org/W123"
    assert result.semantic_scholar_id is None
    assert result.arxiv_id is None
    assert result.abstract == "Abstract found."
    assert result.open_access_url == "https://example.org/paper.pdf"
    assert result.is_retracted is True
    assert crossref.calls == [("by_doi", "10.1000/example")]
    assert openalex.calls == ["10.1000/example"]
    assert semantic.calls == []


def test_falls_back_to_semantic_scholar_and_rejects_bad_year_match() -> None:
    reference = DocumentReference(
        id="ref-2",
        raw="Smith, A. Sample work. 2024.",
        authors=("Smith, Alice",),
        title="A Sample Work",
        year="2024",
    )
    crossref_work = CrossrefWork.model_validate(
        {
            "DOI": "10.1000/old",
            "title": ["A Sample Work"],
            "author": [{"family": "Smith"}],
            "published": {"date-parts": [[2010]]},
        }
    )
    crossref = FakeCrossref(crossref_work)
    openalex = FakeOpenAlex()
    semantic = FakeSemanticScholar(
        SemanticScholarPaper(
            paper_id="paper-456",
            title="A Sample Work",
            year=2010,
            authors=({"name": "Alice Smith"},),
        )
    )

    result = resolve_references(
        (reference,),
        crossref=crossref,
        openalex=openalex,
        semantic_scholar=semantic,
    )[0]

    assert result.status == "metadata_mismatch"
    assert result.provider == "semantic_scholar"
    assert crossref.calls == [("search", reference.raw)]
    assert openalex.calls == []
    assert semantic.calls == [("match", reference.raw)]


def test_resolves_without_doi_when_semantic_match_meets_all_criteria() -> None:
    reference = DocumentReference(
        id="ref-3",
        raw="Smith, A. Sample work. 2024.",
        authors=("Smith, Alice",),
        title="A Sample Work",
        year="2024",
    )
    crossref = FakeCrossref()
    semantic = FakeSemanticScholar(
        SemanticScholarPaper(
            paper_id="paper-789",
            title="A Sample Work",
            year=2024,
            authors=({"name": "Alice Smith"},),
        )
    )

    result = resolve_references(
        (reference,),
        crossref=crossref,
        openalex=FakeOpenAlex(),
        semantic_scholar=semantic,
    )[0]

    assert result.status == "ok"
    assert result.provider == "semantic_scholar"


def test_uses_semantic_scholar_after_crossref_and_openalex_miss() -> None:
    reference = DocumentReference(
        id="ref-4",
        raw="Smith, A. Sample work. 2024.",
        authors=("Smith, Alice",),
        title="A Sample Work",
        year="2024",
        doi="10.1000/example",
    )
    crossref = FakeCrossref()
    openalex = FakeOpenAlex()
    semantic = FakeSemanticScholar(
        SemanticScholarPaper(
            paper_id="paper-123",
            external_ids={"DOI": "10.1000/example"},
            title="A Sample Work",
            year=2024,
            authors=({"name": "Alice Smith"},),
        )
    )

    result = resolve_references(
        (reference,),
        crossref=crossref,
        openalex=openalex,
        semantic_scholar=semantic,
    )[0]

    assert result.status == "ok"
    assert result.provider == "semantic_scholar"
    assert result.doi == "10.1000/example"
    assert semantic.calls == [("by_doi", "10.1000/example")]
