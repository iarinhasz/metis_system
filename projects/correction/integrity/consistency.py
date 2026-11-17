"""Consistência entre citações no corpo, bibliografia e autoria."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.resolution import ReferenceResolution


class CitationConsistency(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    uncited_reference_ids: tuple[str, ...]
    citation_without_reference_count: int = Field(ge=0)
    cited_reference_count: int = Field(ge=0)
    self_citation_count: int = Field(ge=0)
    self_citation_rate: float = Field(ge=0, le=1, allow_inf_nan=False)


def check_citation_consistency(
    document: ExtractedDocument,
    resolutions: Sequence[ReferenceResolution],
) -> CitationConsistency:
    known_ids = {reference.id for reference in document.references}
    resolved_ids = {item.reference_id for item in resolutions}
    if known_ids != resolved_ids:
        raise ValueError("As resoluções não correspondem à bibliografia do documento.")
    cited_ids = {
        mention.reference_id
        for mention in document.citation_mentions
        if mention.reference_id is not None
    }
    cited_valid = cited_ids & known_ids
    no_reference = sum(
        mention.reference_id is None or mention.reference_id not in known_ids
        for mention in document.citation_mentions
    )
    author_keys = {_author_key(author) for author in document.authors}
    self_citations = sum(
        bool(author_keys & {_author_key(author) for author in result.authors})
        for result in resolutions
        if result.reference_id in cited_valid and result.authors
    )
    self_citation_denominator = sum(
        bool(result.authors) for result in resolutions if result.reference_id in cited_valid
    )
    return CitationConsistency(
        uncited_reference_ids=tuple(
            reference.id for reference in document.references if reference.id not in cited_ids
        ),
        citation_without_reference_count=no_reference,
        cited_reference_count=len(cited_valid),
        self_citation_count=self_citations,
        self_citation_rate=(
            self_citations / self_citation_denominator if self_citation_denominator else 0.0
        ),
    )


def _author_key(author: str) -> str:
    tokens = re.findall(r"[^\W_]+", author.casefold())
    return tokens[-1] if tokens else ""
