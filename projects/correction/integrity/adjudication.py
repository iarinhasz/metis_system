"""Detecção de sobreposição e adjudicação contextual limitada aos pares de topo."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.agents.factory import AgentFactory
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.candidates import Candidate
from projects.correction.integrity.citation_filter import (
    CitationAssessment,
    SimilarityPair,
    assess_pair,
)
from projects.correction.integrity.lexical import find_lexical_overlaps
from projects.correction.metis.concurrency import bounded_map


class AdjudicatorOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    verdict: Literal[
        "verbatim_copy",
        "paraphrase_without_attribution",
        "properly_cited",
        "common_knowledge",
        "same_work",
        "false_positive",
    ]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    justification: str = Field(min_length=1, max_length=4000)


class AdjudicationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pair: SimilarityPair
    verdict: AdjudicatorOutput


class AdjudicationBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assessments: tuple[CitationAssessment, ...]
    adjudicated: tuple[AdjudicationResult, ...]
    excluded_from_review: int


def lexical_pairs(
    document: ExtractedDocument,
    candidates: Sequence[Candidate],
    *,
    minimum_words: int = 8,
) -> list[SimilarityPair]:
    """Map exact lexical spans back to the original section and candidate texts."""
    if minimum_words < 1:
        raise ValueError("minimum_words deve ser positivo.")
    pairs: list[SimilarityPair] = []
    for section in document.sections:
        for candidate in candidates:
            for overlap in find_lexical_overlaps(section.text, candidate.text):
                target_excerpt = section.text[overlap.source_start : overlap.source_end]
                source_excerpt = candidate.text[overlap.target_start : overlap.target_end]
                if len(target_excerpt.split()) < minimum_words:
                    continue
                pairs.append(
                    SimilarityPair(
                        section_id=section.id,
                        target_start=overlap.source_start,
                        target_end=overlap.source_end,
                        source_start=overlap.target_start,
                        source_end=overlap.target_end,
                        target_excerpt=target_excerpt,
                        source_excerpt=source_excerpt,
                        candidate_source=candidate.source,
                        candidate_id=candidate.source_id,
                        candidate_title=candidate.title,
                        candidate_doi=candidate.doi,
                        reference_id=candidate.reference_id,
                        similarity=1.0,
                        method="lexical",
                    )
                )
    return pairs


def adjudicate_pairs(
    document: ExtractedDocument,
    candidates: Sequence[Candidate],
    pairs: Sequence[SimilarityPair],
    *,
    factory: AgentFactory,
    top_n: int,
    max_workers: int = 2,
) -> AdjudicationBatch:
    if top_n < 0:
        raise ValueError("top_n não pode ser negativo.")
    if max_workers < 1:
        raise ValueError("max_workers deve ser positivo.")
    by_id = {(candidate.source, candidate.source_id): candidate for candidate in candidates}
    assessments = tuple(
        assess_pair(
            pair,
            document,
            by_id[(pair.candidate_source, pair.candidate_id)],
        )
        for pair in pairs
    )
    review = sorted(
        (assessment for assessment in assessments if assessment.disposition == "review"),
        key=lambda assessment: (-assessment.pair.similarity, assessment.pair.section_id),
    )[:top_n]

    def judge(assessment: CitationAssessment) -> AdjudicationResult:
        runner = factory.plagiarism_adjudicator(output_schema=AdjudicatorOutput)
        pair = assessment.pair
        result = runner.run(
            "Classifique o par em um veredito permitido. "
            f"Contexto da citação: {assessment.rationale}\n"
            f"Trecho do manuscrito: {pair.target_excerpt}\n"
            f"Trecho da fonte {pair.candidate_title!r}: {pair.source_excerpt}\n"
            f"Fonte citada no trecho: {assessment.cited_in_passage}; "
            f"trecho entre aspas: {assessment.quoted}."
        )
        if not result.valid or not isinstance(result.content, AdjudicatorOutput):
            raise RuntimeError("O adjudicador de integridade devolveu saída inválida.")
        return AdjudicationResult(pair=pair, verdict=result.content)

    judged = bounded_map(judge, review, max_workers=max_workers) if review else []
    return AdjudicationBatch(
        assessments=assessments,
        adjudicated=tuple(judged),
        excluded_from_review=sum(assessment.disposition != "review" for assessment in assessments),
    )
