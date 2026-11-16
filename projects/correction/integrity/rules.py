"""Regras versionadas que decidem o risco sem delegar a decisão ao LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.metis.config import settings

RULES_VERSION = "1.0"
type ArticleText = str | dict[str, str]


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


type FindingSeverity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class FindingRecord:
    finding_type: str
    severity: FindingSeverity
    verdict: str = ""
    section_id: str = ""
    target_start: int | None = None
    target_end: int | None = None
    source_start: int | None = None
    source_end: int | None = None
    target_excerpt: str = ""
    source_excerpt: str = ""
    source_title: str = ""
    source_id: str = ""
    source_doi: str | None = None
    confidence: float | None = None
    rationale: str = ""


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    level: RiskLevel
    rules_version: str
    reasons: tuple[str, ...] = ()


class RiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    high_verbatim_sentences: int = Field(ge=1)
    high_paraphrase_fraction: float = Field(gt=0, le=1, allow_inf_nan=False)
    high_nonexistent_references: int = Field(ge=1)

    @classmethod
    def from_settings(cls) -> RiskPolicy:
        return cls(
            high_verbatim_sentences=settings.integrity_high_verbatim_sentences,
            high_paraphrase_fraction=settings.integrity_high_paraphrase_fraction,
            high_nonexistent_references=settings.integrity_high_nonexistent_references,
        )


def decide_risk(
    findings: tuple[FindingRecord, ...] | list[FindingRecord],
    *,
    article_text: ArticleText,
    nonexistent_references: int | None = None,
    policy: RiskPolicy | None = None,
) -> RiskDecision:
    policy = policy or RiskPolicy.from_settings()
    high_reasons: list[str] = []
    medium_reasons: list[str] = []

    hidden = [item for item in findings if item.finding_type == "hidden_ai_instruction"]
    if hidden:
        high_reasons.append("hidden_ai_instruction")

    literal_spans = [
        item for item in findings if item.verdict == "verbatim_copy" and item.severity == "high"
    ]
    if any(
        _sentence_count(item.target_excerpt) >= policy.high_verbatim_sentences
        for item in literal_spans
    ):
        high_reasons.append("long_unattributed_verbatim_copy")
    elif literal_spans:
        medium_reasons.append("unattributed_verbatim_copy")

    paraphrases = [
        item
        for item in findings
        if item.verdict == "paraphrase_without_attribution" and item.severity != "low"
    ]
    paraphrase_intervals: dict[str, list[tuple[int, int]]] = {}
    for item in paraphrases:
        if item.target_start is not None and item.target_end is not None:
            paraphrase_intervals.setdefault(item.section_id, []).append(
                (item.target_start, item.target_end)
            )
    if isinstance(article_text, str):
        fraction = _union_fraction(
            paraphrase_intervals.get("", [])
            + [interval for items in paraphrase_intervals.values() for interval in items],
            len(article_text),
        )
    else:
        suspicious_length = sum(
            _union_fraction(intervals, len(article_text.get(section_id, "")))
            * len(article_text.get(section_id, ""))
            for section_id, intervals in paraphrase_intervals.items()
        )
        total_length = sum(map(len, article_text.values()))
        fraction = suspicious_length / total_length if total_length else 0.0
    if paraphrases and fraction >= policy.high_paraphrase_fraction:
        high_reasons.append("widespread_unattributed_paraphrase")
    elif paraphrases:
        medium_reasons.append("unattributed_paraphrase")

    if (
        nonexistent_references is not None
        and nonexistent_references >= policy.high_nonexistent_references
    ):
        high_reasons.append("multiple_nonexistent_references")
    elif any(
        item.finding_type in {"metadata_mismatch", "retracted_source", "hidden_text"}
        for item in findings
    ):
        medium_reasons.append("reference_integrity_issue")

    if high_reasons:
        return RiskDecision(
            level=RiskLevel.HIGH,
            rules_version=RULES_VERSION,
            reasons=tuple(high_reasons),
        )
    if medium_reasons:
        return RiskDecision(
            level=RiskLevel.MEDIUM,
            rules_version=RULES_VERSION,
            reasons=tuple(medium_reasons),
        )
    return RiskDecision(level=RiskLevel.LOW, rules_version=RULES_VERSION)


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?]+(?:[.!?]+|$)", text.strip()))


def _union_fraction(intervals: list[tuple[int, int]], total_length: int) -> float:
    if total_length <= 0 or not intervals:
        return 0.0
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if start < 0 or end < start or end > total_length:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged) / total_length
