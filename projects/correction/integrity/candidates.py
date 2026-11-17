"""Coleta de candidatos de similaridade com orçamento explícito por execução."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from projects.correction.extractor.contract import DocumentReference, ExtractedDocument
from projects.correction.integrity.embeddings import embed_query
from projects.correction.integrity.models import SourceChunk
from projects.correction.scholarly.arxiv import ArxivClient
from projects.correction.scholarly.crossref import CrossrefClient, CrossrefWork
from projects.correction.scholarly.openalex import OpenAlexWork, OpenAlexWorksClient
from projects.correction.scholarly.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarPaper,
)


@dataclass(frozen=True)
class Candidate:
    source: str
    source_id: str
    title: str
    text: str
    doi: str | None = None
    authors: tuple[str, ...] = ()
    reference_id: str | None = None
    similarity: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceCoverage:
    source: str
    queried: bool
    returned: int
    omitted: bool = False
    reason: str = ""


@dataclass(frozen=True)
class CandidateCollection:
    candidates: tuple[Candidate, ...]
    coverage: tuple[SourceCoverage, ...]
    paid_searches_used: int
    paid_search_budget: int


@dataclass
class CandidateBudget:
    """Run-local counter for metered OpenAlex search requests."""

    max_paid_searches: int
    paid_searches_used: int = 0

    def __post_init__(self) -> None:
        if self.max_paid_searches < 0:
            raise ValueError("max_paid_searches não pode ser negativo.")

    def consume_paid_search(self) -> bool:
        if self.paid_searches_used >= self.max_paid_searches:
            return False
        self.paid_searches_used += 1
        return True


class CandidateSource(Protocol):
    name: str

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]: ...


class InternalCorpusSource:
    name = "internal_corpus"

    def __init__(self, *, neighbors_per_section: int = 10) -> None:
        if neighbors_per_section < 1:
            raise ValueError("neighbors_per_section deve ser positivo.")
        self.neighbors_per_section = neighbors_per_section

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        del budget
        candidates: dict[tuple[str, str], Candidate] = {}
        for section in document.sections:
            if not section.text.strip():
                continue
            embedding = embed_query(section.text)
            for chunk in SourceChunk.nearest_by_embedding(
                embedding, limit=self.neighbors_per_section
            ):
                key = (str(chunk.document_id), str(chunk.chunk_index))
                distance = getattr(chunk, "cosine_distance", None)
                if not isinstance(distance, (int, float)):
                    raise RuntimeError("A consulta vetorial não retornou cosine_distance.")
                candidates.setdefault(
                    key,
                    Candidate(
                        source=chunk.document.source,
                        source_id=f"{chunk.document_id}:{chunk.chunk_index}",
                        title=chunk.document.title,
                        text=chunk.text,
                        doi=chunk.document.doi,
                        authors=tuple(chunk.document.authors),
                        similarity=1.0 - float(distance),
                        metadata={
                            "section_id": chunk.section_id,
                            "section_title": chunk.section_title,
                            "section_key": chunk.section_key,
                            "chunk_index": chunk.chunk_index,
                        },
                    ),
                )
        return tuple(candidates.values()), SourceCoverage(
            self.name, queried=True, returned=len(candidates)
        )


class CitedWorksSource:
    """Candidate abstracts from cited works; OA full-text retrieval is reported separately."""

    name = "cited_works"

    def __init__(
        self,
        *,
        crossref: CrossrefClient | None = None,
        openalex: OpenAlexWorksClient | None = None,
    ) -> None:
        self.crossref = crossref or CrossrefClient()
        self.openalex = openalex or OpenAlexWorksClient()

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        del budget
        candidates: dict[str, Candidate] = {}
        for reference in document.references:
            work = self._lookup(reference)
            if work is not None and work.text:
                candidates[work.source_id] = Candidate(
                    source=work.source,
                    source_id=work.source_id,
                    title=work.title,
                    text=work.text,
                    doi=work.doi,
                    authors=work.authors,
                    reference_id=reference.id,
                    metadata={"open_access_pdf": work.open_access_pdf},
                )
        return tuple(candidates.values()), SourceCoverage(
            self.name,
            queried=True,
            returned=len(candidates),
            reason="Abstracts consultados; full texts OA não recuperados nesta etapa.",
        )

    def _lookup(self, reference: DocumentReference) -> _WorkText | None:
        crossref_work: CrossrefWork | None = None
        if reference.doi:
            crossref_work = self.crossref.by_doi(reference.doi)
        if crossref_work is None:
            search = self.crossref.search(reference.raw, rows=1)
            crossref_work = search.items[0] if search.items else None
        if crossref_work is None:
            return None

        doi = crossref_work.doi
        openalex_work = self.openalex.by_doi(doi) if doi else None
        title = _first(crossref_work.title) or reference.title or reference.raw
        abstract = _first(crossref_work.abstract)
        if openalex_work is not None:
            title = openalex_work.title or title
            abstract = _decode_openalex_abstract(openalex_work) or abstract
        if not abstract:
            return None
        authors = tuple(
            " ".join(
                value
                for value in (str(author.get("given", "")), str(author.get("family", "")))
                if value
            )
            for author in crossref_work.author
        )
        return _WorkText(
            source="cited_works",
            source_id=f"doi:{doi}" if doi else f"reference:{reference.id}",
            title=title,
            text=abstract,
            doi=doi,
            authors=authors,
            open_access_pdf=(
                openalex_work.best_oa_location.pdf_url
                if openalex_work and openalex_work.best_oa_location
                else None
            ),
        )


@dataclass(frozen=True)
class _WorkText:
    source: str
    source_id: str
    title: str
    text: str
    doi: str | None
    authors: tuple[str, ...]
    open_access_pdf: str | None = None


class SemanticScholarSearchSource:
    name = "semantic_scholar"

    def __init__(self, client: SemanticScholarClient | None = None, *, limit: int = 10) -> None:
        self.client = client or SemanticScholarClient()
        self.limit = limit

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        del budget
        query = _search_query(document)
        results = self.client.search(query, limit=self.limit)
        candidates = tuple(
            _semantic_scholar_candidate(paper)
            for paper in results.data
            if paper.title and paper.abstract
        )
        return candidates, SourceCoverage(self.name, queried=True, returned=len(candidates))


class ArxivSearchSource:
    name = "arxiv"

    def __init__(self, client: ArxivClient | None = None, *, max_results: int = 10) -> None:
        self.client = client or ArxivClient()
        self.max_results = max_results

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        del budget
        results = self.client.search(_search_query(document), max_results=self.max_results)
        candidates = tuple(
            Candidate(
                source=self.name,
                source_id=entry.id,
                title=entry.title,
                text=entry.summary,
                doi=entry.doi,
                authors=tuple(author.name for author in entry.authors),
            )
            for entry in results.entries
        )
        return candidates, SourceCoverage(self.name, queried=True, returned=len(candidates))


class OpenAlexSearchSource:
    name = "openalex_search"

    def __init__(self, client: OpenAlexWorksClient | None = None, *, per_page: int = 10) -> None:
        self.client = client or OpenAlexWorksClient()
        self.per_page = per_page

    def collect(
        self, document: ExtractedDocument, budget: CandidateBudget
    ) -> tuple[Sequence[Candidate], SourceCoverage]:
        if not budget.consume_paid_search():
            return (), SourceCoverage(
                self.name,
                queried=False,
                returned=0,
                omitted=True,
                reason="Orçamento de buscas pagas OpenAlex por run esgotado.",
            )
        results = self.client.search(_search_query(document), per_page=self.per_page)
        candidates = tuple(
            candidate
            for work in results.results
            if (candidate := _openalex_candidate(work)) is not None
        )
        return candidates, SourceCoverage(self.name, queried=True, returned=len(candidates))


class CandidateCollector:
    def __init__(
        self,
        sources: Sequence[CandidateSource] | None = None,
        *,
        paid_search_budget: int = 0,
    ) -> None:
        if paid_search_budget < 0:
            raise ValueError("paid_search_budget não pode ser negativo.")
        self.sources = tuple(
            sources
            or (
                InternalCorpusSource(),
                CitedWorksSource(),
                SemanticScholarSearchSource(),
                ArxivSearchSource(),
                OpenAlexSearchSource(),
            )
        )
        self.paid_search_budget = paid_search_budget

    def collect(self, document: ExtractedDocument) -> CandidateCollection:
        budget = CandidateBudget(self.paid_search_budget)
        candidates: dict[tuple[str, str], Candidate] = {}
        coverage: list[SourceCoverage] = []
        for source in self.sources:
            found, source_coverage = source.collect(document, budget)
            coverage.append(source_coverage)
            for candidate in found:
                candidates.setdefault((candidate.source, candidate.source_id), candidate)
        return CandidateCollection(
            candidates=tuple(candidates.values()),
            coverage=tuple(coverage),
            paid_searches_used=budget.paid_searches_used,
            paid_search_budget=budget.max_paid_searches,
        )


def _search_query(document: ExtractedDocument) -> str:
    return f"{document.title} {document.abstract[:600]}".strip()


def _semantic_scholar_candidate(paper: SemanticScholarPaper) -> Candidate:
    external_ids = paper.external_ids
    return Candidate(
        source="semantic_scholar",
        source_id=paper.paper_id or str(external_ids.get("DOI") or paper.title),
        title=paper.title or "",
        text=paper.abstract or "",
        doi=str(external_ids["DOI"]) if external_ids.get("DOI") else None,
        authors=tuple(
            str(author["name"]) for author in paper.authors if author.get("name") is not None
        ),
        metadata={
            "open_access_pdf": (
                paper.open_access_pdf.get("url") if paper.open_access_pdf else None
            ),
            "is_retracted": paper.is_retracted,
        },
    )


def _openalex_candidate(work: OpenAlexWork) -> Candidate | None:
    text = _decode_openalex_abstract(work)
    if not text or not work.title:
        return None
    return Candidate(
        source="openalex_search",
        source_id=work.id,
        title=work.title,
        text=text,
        doi=work.doi,
        metadata={
            "is_retracted": work.is_retracted,
            "open_access_pdf": (work.best_oa_location.pdf_url if work.best_oa_location else None),
        },
    )


def _decode_openalex_abstract(work: OpenAlexWork) -> str | None:
    if not work.abstract_inverted_index:
        return None
    indexed = sorted(
        (
            position,
            word,
        )
        for word, positions in work.abstract_inverted_index.items()
        for position in positions
    )
    return " ".join(word for _, word in indexed)


def _first(values: Sequence[str] | str | None) -> str | None:
    if isinstance(values, str):
        return values
    return values[0] if values else None
