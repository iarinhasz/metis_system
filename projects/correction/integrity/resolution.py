"""Resolu??o de refer?ncias bibliogr?ficas com os clientes scholarly compartilhados."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from projects.correction.extractor.contract import DocumentReference
from projects.correction.scholarly.cache import normalize_doi
from projects.correction.scholarly.crossref import CrossrefClient, CrossrefWork, CrossrefWorks
from projects.correction.scholarly.openalex import OpenAlexWork, OpenAlexWorksClient
from projects.correction.scholarly.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarPaper,
)

_YEAR = re.compile(r"\b(?:18|19|20)\d{2}\b")
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_Provider = Literal["crossref", "openalex", "semantic_scholar"]


class ReferenceResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_id: str
    status: Literal["ok", "metadata_mismatch", "not_found"]
    provider: Literal["crossref", "openalex", "semantic_scholar"] | None = None
    doi: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    arxiv_id: str | None = None
    title: str | None = None
    authors: tuple[str, ...] = ()
    abstract: str | None = None
    open_access_url: str | None = None
    is_retracted: bool | None = None
    crossref_update_to: tuple[dict[str, object], ...] = ()
    crossref_updated_by: tuple[dict[str, object], ...] = ()


class _CrossrefClient(Protocol):
    def by_doi(self, doi: str) -> CrossrefWork | None: ...

    def search(self, query: str, *, rows: int = 10) -> CrossrefWorks: ...


class _OpenAlexClient(Protocol):
    def by_doi(self, doi: str) -> OpenAlexWork | None: ...


class _SemanticScholarClient(Protocol):
    def by_doi(self, doi: str) -> SemanticScholarPaper | None: ...

    def match(self, query: str) -> SemanticScholarPaper | None: ...


def resolve_references(
    references: tuple[DocumentReference, ...],
    *,
    crossref: _CrossrefClient | None = None,
    openalex: _OpenAlexClient | None = None,
    semantic_scholar: _SemanticScholarClient | None = None,
) -> tuple[ReferenceResolution, ...]:
    """Resolve todas as refer?ncias sem ocultar falhas transit?rias dos provedores."""
    crossref_client = crossref or CrossrefClient()
    openalex_client = openalex or OpenAlexWorksClient()
    semantic_client = semantic_scholar or SemanticScholarClient()
    return tuple(
        _resolve_one(
            reference,
            crossref_client,
            openalex_client,
            semantic_client,
        )
        for reference in references
    )


def _resolve_one(
    reference: DocumentReference,
    crossref: _CrossrefClient,
    openalex: _OpenAlexClient,
    semantic_scholar: _SemanticScholarClient,
) -> ReferenceResolution:
    requested_doi = _normalize_optional_doi(reference.doi)
    crossref_work: CrossrefWork | None = None
    if requested_doi:
        crossref_work = crossref.by_doi(requested_doi)
    else:
        results = crossref.search(reference.raw)
        items = getattr(results, "items", ())
        crossref_work = _best_crossref_match(reference, items)

    candidate_doi = _normalize_optional_doi(crossref_work.doi) if crossref_work else None
    doi = requested_doi or candidate_doi
    openalex_work = openalex.by_doi(doi) if doi else None
    if crossref_work is not None and _is_accepted(
        reference, crossref_work, doi_match=requested_doi is not None
    ):
        return _resolution(
            reference.id, "crossref", crossref_work, crossref_work, openalex_work, None
        )
    if openalex_work is not None and _is_accepted(
        reference, openalex_work, doi_match=requested_doi is not None
    ):
        return _resolution(
            reference.id, "openalex", openalex_work, crossref_work, openalex_work, None
        )

    semantic_paper = semantic_scholar.by_doi(doi) if doi else semantic_scholar.match(reference.raw)
    if semantic_paper is not None and _is_accepted(
        reference, semantic_paper, doi_match=requested_doi is not None
    ):
        return _resolution(
            reference.id,
            "semantic_scholar",
            semantic_paper,
            crossref_work,
            openalex_work,
            semantic_paper,
        )

    candidates: list[tuple[_Provider, object]] = []
    if crossref_work is not None:
        candidates.append(("crossref", crossref_work))
    if openalex_work is not None:
        candidates.append(("openalex", openalex_work))
    if semantic_paper is not None:
        candidates.append(("semantic_scholar", semantic_paper))
    if candidates:
        provider, candidate = candidates[0]
        result = _resolution(
            reference.id, provider, candidate, crossref_work, openalex_work, semantic_paper
        )
        return result.model_copy(update={"status": "metadata_mismatch"})
    return ReferenceResolution(reference_id=reference.id, status="not_found")


def _best_crossref_match(reference: DocumentReference, items: object) -> CrossrefWork | None:
    if not isinstance(items, (tuple, list)):
        return None
    matches = [
        item
        for item in items
        if isinstance(item, CrossrefWork) and _is_accepted(reference, item, doi_match=False)
    ]
    return max(
        matches,
        key=lambda item: _title_similarity(reference.title, _crossref_title(item)),
        default=None,
    )


def _is_accepted(reference: DocumentReference, candidate: object, *, doi_match: bool) -> bool:
    if doi_match:
        return True
    title = _candidate_title(candidate)
    expected_title = _normalize_title(reference.title or "")
    actual_title = _normalize_title(title or "")
    if not expected_title or not actual_title:
        return False
    if SequenceMatcher(None, expected_title, actual_title).ratio() < 0.9:
        return False
    expected_surname = _reference_surname(reference)
    candidate_surname = _candidate_surname(candidate)
    if not expected_surname or expected_surname != candidate_surname:
        return False
    expected_year = _reference_year(reference)
    candidate_year = _candidate_year(candidate)
    return (
        expected_year is not None
        and candidate_year is not None
        and abs(expected_year - candidate_year) <= 1
    )


def _candidate_title(candidate: object) -> str | None:
    if isinstance(candidate, CrossrefWork):
        return _crossref_title(candidate)
    return getattr(candidate, "title", None)


def _crossref_title(candidate: CrossrefWork) -> str | None:
    return candidate.title[0] if candidate.title else None


def _candidate_surname(candidate: object) -> str | None:
    if isinstance(candidate, CrossrefWork):
        authors: tuple[object, ...] = candidate.author
        first = authors[0] if authors else None
        if isinstance(first, dict):
            return _normalize_surname(str(first.get("family", "")))
    elif isinstance(candidate, OpenAlexWork):
        authorships = getattr(candidate, "authorships", ())
        if authorships and isinstance(authorships[0], dict):
            author = authorships[0].get("author")
            if isinstance(author, dict):
                return _normalize_surname(str(author.get("display_name", "")))
    elif isinstance(candidate, SemanticScholarPaper) and candidate.authors:
        return _normalize_surname(str(candidate.authors[0].get("name", "")))
    return None


def _reference_surname(reference: DocumentReference) -> str | None:
    if not reference.authors:
        return None
    return _normalize_surname(reference.authors[0])


def _normalize_surname(author: str) -> str | None:
    surname = author.partition(",")[0] if "," in author else author.split()[-1]
    normalized = _NON_WORD.sub(" ", surname).strip().casefold()
    return normalized or None


def _reference_year(reference: DocumentReference) -> int | None:
    match = _YEAR.search(reference.year or reference.raw)
    return int(match.group()) if match else None


def _candidate_year(candidate: object) -> int | None:
    if isinstance(candidate, CrossrefWork):
        published = candidate.published or {}
        date_parts = published.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
            year = date_parts[0][0]
            return year if isinstance(year, int) else None
    year = getattr(candidate, "publication_year", None) or getattr(candidate, "year", None)
    return year if isinstance(year, int) else None


def _normalize_title(title: str) -> str:
    return " ".join(_NON_WORD.sub(" ", title).casefold().split())


def _title_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _normalize_title(left), _normalize_title(right)).ratio()


def _normalize_optional_doi(doi: str | None) -> str | None:
    if doi is None or not doi.strip():
        return None
    return normalize_doi(doi)


def _resolution(
    reference_id: str,
    provider: _Provider,
    candidate: object,
    crossref: CrossrefWork | None,
    openalex: OpenAlexWork | None,
    semantic_scholar: SemanticScholarPaper | None,
) -> ReferenceResolution:
    doi = _normalize_optional_doi(crossref.doi) if crossref is not None else None
    if doi is None and openalex is not None:
        doi = _normalize_optional_doi(openalex.doi)
    if doi is None and semantic_scholar is not None:
        semantic_doi = semantic_scholar.external_ids.get("DOI")
        doi = _normalize_optional_doi(str(semantic_doi)) if semantic_doi else None
    title = _candidate_title(candidate)
    abstract = getattr(candidate, "abstract", None) or (
        _openalex_work_abstract(openalex) if openalex else None
    )
    open_access_url = _open_access_url(openalex, semantic_scholar)
    crossref_relations = (*crossref.update_to, *crossref.updated_by) if crossref else ()
    crossref_retracted = any(_is_retraction_relation(item) for item in crossref_relations)
    if crossref_retracted or (openalex is not None and openalex.is_retracted):
        retracted: bool | None = True
    elif openalex is not None:
        retracted = False
    elif semantic_scholar is not None:
        retracted = semantic_scholar.is_retracted
    else:
        retracted = None
    authors = _candidate_authors(candidate)
    openalex_id = openalex.id if openalex else None
    semantic_id = semantic_scholar.paper_id if semantic_scholar else None
    external_ids = semantic_scholar.external_ids if semantic_scholar else {}
    arxiv_id = str(external_ids["ArXiv"]) if external_ids.get("ArXiv") else None
    return ReferenceResolution(
        reference_id=reference_id,
        status="ok",
        provider=provider,
        doi=doi,
        openalex_id=openalex_id,
        semantic_scholar_id=semantic_id,
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        abstract=abstract,
        open_access_url=open_access_url,
        is_retracted=retracted,
        crossref_update_to=crossref.update_to if crossref else (),
        crossref_updated_by=crossref.updated_by if crossref else (),
    )


def _candidate_authors(candidate: object) -> tuple[str, ...]:
    if isinstance(candidate, CrossrefWork):
        return tuple(
            " ".join(
                item
                for item in (str(author.get("given", "")), str(author.get("family", "")))
                if item
            )
            for author in candidate.author
        )
    if isinstance(candidate, OpenAlexWork):
        names: list[str] = []
        for authorship in candidate.authorships:
            author = authorship.get("author")
            if isinstance(author, dict) and author.get("display_name"):
                names.append(str(author["display_name"]))
        return tuple(names)
    if isinstance(candidate, SemanticScholarPaper):
        return tuple(str(author["name"]) for author in candidate.authors if author.get("name"))
    return ()


def _is_retraction_relation(relation: dict[str, object]) -> bool:
    relation_type = str(relation.get("type", "")).casefold().replace("_", "-")
    return relation_type in {"retraction", "retracted"}


def _openalex_work_abstract(work: OpenAlexWork) -> str | None:
    inverted = work.abstract_inverted_index
    if not inverted:
        return None
    words: list[tuple[int, str]] = [
        (position, word) for word, positions in inverted.items() for position in positions
    ]
    return " ".join(word for _, word in sorted(words))


def _open_access_url(
    openalex: OpenAlexWork | None, semantic_scholar: SemanticScholarPaper | None
) -> str | None:
    if openalex is not None and openalex.best_oa_location is not None:
        location = openalex.best_oa_location
        if location.pdf_url or location.landing_page_url:
            return location.pdf_url or location.landing_page_url
    if semantic_scholar is not None and semantic_scholar.open_access_pdf is not None:
        url = semantic_scholar.open_access_pdf.get("url")
        return str(url) if url else None
    return None
