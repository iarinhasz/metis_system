"""Métricas de precisão e recall em pares sintéticos derivados do PeerRead."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.extractor.contract import ExtractedDocument

BenchmarkType = Literal["literal", "paraphrase", "translated", "negative"]
_TYPES: tuple[BenchmarkType, ...] = ("literal", "paraphrase", "translated", "negative")


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    plagiarism_type: BenchmarkType
    source_text: str = Field(min_length=1)
    target_text: str = Field(min_length=1)
    expected_match: bool


class TypeMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plagiarism_type: BenchmarkType
    cases: int = Field(ge=0)
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: tuple[TypeMetrics, ...]
    calibration_status: Literal["measured_not_calibrated"] = "measured_not_calibrated"
    calibration_values: dict[str, int | float]


TextRewriter = Callable[[str, Literal["paraphrase", "translated"]], str]


def build_peerread_cases(
    documents: Sequence[ExtractedDocument],
    *,
    rewrite: TextRewriter | None = None,
    max_documents: int = 10,
    max_passages: int = 3,
    minimum_words: int = 12,
) -> tuple[BenchmarkCase, ...]:
    if max_documents < 1:
        raise ValueError("max_documents deve ser positivo.")
    if max_passages < 1:
        raise ValueError("max_passages deve ser positivo.")
    if minimum_words < 1:
        raise ValueError("minimum_words deve ser positivo.")
    selected = documents[:max_documents]
    passages: list[tuple[int, str]] = []
    for index, document in enumerate(selected):
        passage = next(
            (text for text in _passages(document) if len(text.split()) >= minimum_words),
            None,
        )
        if passage is not None:
            passages.append((index, passage))
        if len(passages) >= max_passages:
            break
    cases: list[BenchmarkCase] = []
    for index, (document_index, passage) in enumerate(passages):
        context = (
            f"An unrelated introduction precedes the passage. {passage} The discussion follows."
        )
        cases.append(
            BenchmarkCase(
                case_id=f"literal-{index}",
                plagiarism_type="literal",
                source_text=passage,
                target_text=context,
                expected_match=True,
            )
        )
        if rewrite is not None:
            for kind in ("paraphrase", "translated"):
                replacement = rewrite(passage, kind)
                cases.append(
                    BenchmarkCase(
                        case_id=f"{kind}-{index}",
                        plagiarism_type=kind,
                        source_text=passage,
                        target_text=replacement,
                        expected_match=True,
                    )
                )
        different = next(
            (other for other_index, other in passages if other_index != document_index),
            None,
        )
        if different is not None:
            cases.append(
                BenchmarkCase(
                    case_id=f"negative-{index}",
                    plagiarism_type="negative",
                    source_text=different,
                    target_text=context,
                    expected_match=False,
                )
            )
    return tuple(cases)


def evaluate_cases(
    cases: Iterable[BenchmarkCase],
    detector: Callable[[str, str], bool],
    *,
    calibration_values: dict[str, int | float] | None = None,
) -> BenchmarkReport:
    counters = {
        kind: {"cases": 0, "true_positive": 0, "false_positive": 0, "false_negative": 0}
        for kind in _TYPES
    }
    for case in cases:
        predicted = detector(case.source_text, case.target_text)
        values = counters[case.plagiarism_type]
        values["cases"] += 1
        if case.expected_match and predicted:
            values["true_positive"] += 1
        elif case.expected_match:
            values["false_negative"] += 1
        elif predicted:
            values["false_positive"] += 1
    metrics: list[TypeMetrics] = []
    for kind, values in counters.items():
        precision_denominator = values["true_positive"] + values["false_positive"]
        recall_denominator = values["true_positive"] + values["false_negative"]
        metrics.append(
            TypeMetrics(
                plagiarism_type=kind,
                cases=values["cases"],
                true_positive=values["true_positive"],
                false_positive=values["false_positive"],
                false_negative=values["false_negative"],
                precision=(
                    values["true_positive"] / precision_denominator
                    if precision_denominator
                    else None
                ),
                recall=(
                    values["true_positive"] / recall_denominator if recall_denominator else None
                ),
            )
        )
    return BenchmarkReport(
        metrics=tuple(metrics),
        calibration_values=calibration_values or {},
    )


def _passages(document: ExtractedDocument) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys((document.abstract, *(section.text for section in document.sections)))
    )
