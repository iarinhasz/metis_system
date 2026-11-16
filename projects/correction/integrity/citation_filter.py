"""Regras determinísticas para contextualizar pares de similaridade."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict

from projects.correction.extractor.contract import CitationMention, ExtractedDocument
from projects.correction.integrity.candidates import Candidate

_BOILERPLATE = re.compile(
    r"\b("
    r"written informed consent was obtained|"
    r"all participants provided informed consent|"
    r"the study was approved by the institutional review board|"
    r"this study was conducted in accordance with the declaration of helsinki"
    r")\b",
    re.IGNORECASE,
)
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"), ("«", "»"))


class SimilarityPair(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    target_start: int
    target_end: int
    source_start: int
    source_end: int
    target_excerpt: str
    source_excerpt: str
    candidate_source: str
    candidate_id: str
    candidate_title: str
    candidate_doi: str | None = None
    reference_id: str | None = None
    similarity: float
    method: Literal["lexical", "semantic"] = "lexical"


class CitationAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pair: SimilarityPair
    disposition: Literal["review", "properly_cited", "common_knowledge", "same_work"]
    cited_in_passage: bool
    quoted: bool
    rationale: str


def assess_pair(
    pair: SimilarityPair,
    document: ExtractedDocument,
    candidate: Candidate,
) -> CitationAssessment:
    """Mark safe explanations for known, deterministic exclusions from adjudication."""
    if pair.section_id == "abstract":
        section_text = document.abstract
    else:
        section = next(section for section in document.sections if section.id == pair.section_id)
        section_text = section.text
    citations = [
        mention
        for mention in document.citation_mentions
        if mention.section_id == pair.section_id and _citation_matches(mention, pair)
    ]
    cited = any(
        _citation_overlaps(
            mention.start_offset,
            mention.end_offset,
            mention.sentence,
            pair.target_start,
            pair.target_end,
            section_text,
        )
        for mention in citations
    )
    quoted = _is_quoted(section_text, pair.target_start, pair.target_end)
    if cited and quoted:
        disposition: Literal["review", "properly_cited", "common_knowledge", "same_work"] = (
            "properly_cited"
        )
        rationale = "Trecho entre aspas e ligado a uma referência citada."
    elif _same_work(document.title, document.authors, candidate):
        disposition = "same_work"
        rationale = "A fonte corresponde ao mesmo trabalho submetido."
    elif _BOILERPLATE.search(pair.target_excerpt):
        disposition = "common_knowledge"
        rationale = "Trecho corresponde a uma expressão de boilerplate conhecida."
    else:
        disposition = "review"
        rationale = "O par requer adjudicação contextual."
    return CitationAssessment(
        pair=pair,
        disposition=disposition,
        cited_in_passage=cited,
        quoted=quoted,
        rationale=rationale,
    )


def _citation_matches(mention: CitationMention, pair: SimilarityPair) -> bool:
    return (
        pair.reference_id is not None
        and mention.reference_id == pair.reference_id
        or pair.candidate_doi is not None
        and pair.candidate_doi.casefold() in mention.sentence.casefold()
    )


def _citation_overlaps(
    start: int | None,
    end: int | None,
    sentence: str,
    target_start: int,
    target_end: int,
    section_text: str,
) -> bool:
    if start is not None and end is not None:
        return start < target_end and target_start < end
    sentence_start = section_text.find(sentence)
    return (
        sentence_start >= 0
        and sentence_start < target_end
        and sentence_start + len(sentence) > target_start
    )


def _is_quoted(text: str, start: int, end: int) -> bool:
    excerpt = text[start:end].strip()
    for opening, closing in _QUOTE_PAIRS:
        left_quoted = re.search(re.escape(opening) + r"\s*$", text[:start]) is not None
        right_quoted = re.match(r"[\s.,;:!?]*" + re.escape(closing), text[end:]) is not None
        if (
            excerpt.startswith(opening)
            and excerpt.endswith(closing)
            or left_quoted
            and right_quoted
        ):
            return True
    return False


def _same_work(title: str, authors: tuple[str, ...], candidate: Candidate) -> bool:
    normalized_title = _normalize(title)
    candidate_title = _normalize(candidate.title)
    title_matches = bool(normalized_title and candidate_title) and (
        SequenceMatcher(None, normalized_title, candidate_title).ratio() >= 0.9
    )
    normalized_authors = {_normalize(author) for author in authors}
    candidate_authors = {_normalize(author) for author in candidate.authors}
    authors_match = bool(normalized_authors and candidate_authors & normalized_authors)
    return title_matches and authors_match


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))
