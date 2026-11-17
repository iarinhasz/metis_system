"""Métricas para referências inventadas e baselines de alinhamento de citações."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.alignment import AlignmentLabel

BaselineName = Literal["planted_references", "sciciteval", "citation_integrity"]


class ReferenceBenchmarkCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference: DocumentReference
    expected_exists: bool


class AlignmentBenchmarkCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    expected_label: AlignmentLabel


class Phase2BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset: BaselineName
    cases: int = Field(ge=0)
    metrics: dict[str, float | int | None]
    calibration_status: Literal["measured_not_calibrated"] = "measured_not_calibrated"
    provenance: str


def plant_invented_references(
    references: Sequence[DocumentReference], *, count: int
) -> tuple[ReferenceBenchmarkCase, ...]:
    if count < 0:
        raise ValueError("count não pode ser negativo.")
    cases = [ReferenceBenchmarkCase(reference=item, expected_exists=True) for item in references]
    seed = "|".join(item.raw for item in references) or "metis-reference-planting"
    for index in range(count):
        digest = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()[:20]
        cases.append(
            ReferenceBenchmarkCase(
                reference=DocumentReference(
                    id=f"planted-{digest}",
                    raw=f"Invented bibliographic record {digest}",
                    authors=("Metis Synthetic Author",),
                    title=f"Fabricated reference for benchmark {digest}",
                    year="2099",
                    doi=f"10.5555/metis-synthetic-{digest}",
                ),
                expected_exists=False,
            )
        )
    return tuple(cases)


def evaluate_reference_cases(
    cases: Sequence[ReferenceBenchmarkCase],
    detector: Callable[[DocumentReference], bool],
) -> Phase2BenchmarkReport:
    true_positive = false_positive = false_negative = true_negative = 0
    for case in cases:
        predicted_exists = detector(case.reference)
        if case.expected_exists and predicted_exists:
            true_positive += 1
        elif case.expected_exists:
            false_negative += 1
        elif predicted_exists:
            false_positive += 1
        else:
            true_negative += 1
    predicted_positive = true_positive + false_positive
    expected_positive = true_positive + false_negative
    negative_count = false_positive + true_negative
    return Phase2BenchmarkReport(
        dataset="planted_references",
        cases=len(cases),
        metrics={
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_negative": true_negative,
            "precision": true_positive / predicted_positive if predicted_positive else None,
            "recall": true_positive / expected_positive if expected_positive else None,
            "false_positive_rate": false_positive / negative_count if negative_count else None,
        },
        provenance="Referências negativas sintéticas; resultados não calibram limiares.",
    )


def evaluate_alignment_cases(
    dataset: Literal["sciciteval", "citation_integrity"],
    cases: Sequence[AlignmentBenchmarkCase],
    detector: Callable[[str, str], AlignmentLabel],
) -> Phase2BenchmarkReport:
    labels: tuple[AlignmentLabel, ...] = (
        "SUPPORTS",
        "PARTIAL",
        "CONTRADICTS",
        "UNRELATED",
        "INSUFFICIENT",
    )
    counts = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels}
    correct = 0
    for case in cases:
        predicted = detector(case.claim, case.source_text)
        correct += predicted == case.expected_label
        for label in labels:
            values = counts[label]
            if predicted == label and case.expected_label == label:
                values["tp"] += 1
            elif predicted == label:
                values["fp"] += 1
            elif case.expected_label == label:
                values["fn"] += 1
    per_label_f1: list[float] = []
    for values in counts.values():
        precision_denominator = values["tp"] + values["fp"]
        recall_denominator = values["tp"] + values["fn"]
        precision = values["tp"] / precision_denominator if precision_denominator else 0.0
        recall = values["tp"] / recall_denominator if recall_denominator else 0.0
        per_label_f1.append(
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
    return Phase2BenchmarkReport(
        dataset=dataset,
        cases=len(cases),
        metrics={
            "accuracy": correct / len(cases) if cases else None,
            "macro_f1": sum(per_label_f1) / len(labels) if cases else None,
        },
        provenance=(
            "Arquivo JSONL normalizado fornecido pelo operador; "
            "mapeamentos do dataset original devem ser documentados."
        ),
    )
