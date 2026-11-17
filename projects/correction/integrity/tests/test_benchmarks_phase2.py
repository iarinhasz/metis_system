from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from django.core.management import call_command

from projects.correction.evals.reports import read_report
from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.alignment import AlignmentJudgment
from projects.correction.integrity.resolution import ReferenceResolution

if TYPE_CHECKING:
    import pytest
from projects.correction.integrity.benchmarks_phase2 import (
    AlignmentBenchmarkCase,
    evaluate_alignment_cases,
    evaluate_reference_cases,
    plant_invented_references,
)


def test_invented_reference_cases_are_deterministic_and_metrics_are_measured() -> None:
    real = DocumentReference(id="r1", raw="A known title", title="A known title")
    cases = plant_invented_references((real,), count=2)
    repeated = plant_invented_references((real,), count=2)
    assert cases == repeated
    assert len(cases) == 3

    report = evaluate_reference_cases(
        cases,
        detector=lambda reference: reference.id == "r1",
    )

    assert report.metrics["recall"] == 1
    assert report.metrics["false_positive_rate"] == 0
    assert report.calibration_status == "measured_not_calibrated"


def test_alignment_baseline_reports_accuracy_and_macro_f1() -> None:
    cases = (
        AlignmentBenchmarkCase(
            claim="Claim",
            source_text="Evidence",
            expected_label="SUPPORTS",
        ),
        AlignmentBenchmarkCase(
            claim="Claim",
            source_text="Evidence",
            expected_label="CONTRADICTS",
        ),
    )
    report = evaluate_alignment_cases(
        "sciciteval",
        cases,
        detector=lambda claim, source: "SUPPORTS",
    )

    assert report.metrics["accuracy"] == 0.5
    assert report.dataset == "sciciteval"


def test_phase_two_command_reports_planted_reference_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = DocumentReference(id="r1", raw="A known title", title="A known title")
    source = tmp_path / "references.jsonl"
    source.write_text(reference.model_dump_json() + "\n", encoding="utf-8")
    output = StringIO()

    def resolve(references: tuple[DocumentReference, ...]) -> tuple[object, ...]:
        return tuple(
            ReferenceResolution(
                reference_id=item.id,
                status="ok" if item.id == "r1" else "not_found",
            )
            for item in references
        )

    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.bench_integrity_phase2.resolve_references",
        resolve,
    )
    call_command(
        "bench_integrity_phase2",
        dataset="planted_references",
        input=source,
        plant_count=1,
        stdout=output,
    )

    report = json.loads(output.getvalue())
    assert report["metrics"]["recall"] == 1
    assert report["metrics"]["false_positive_rate"] == 0

    artifact_path = tmp_path / "references-eval.json"
    call_command(
        "bench_integrity_phase2",
        dataset="planted_references",
        input=source,
        plant_count=1,
        execute=True,
        output=artifact_path,
    )

    normalized = read_report(artifact_path)
    assert normalized.benchmark == "planted_references"
    assert normalized.benchmark_version == "integrity-phase2-1"
    assert normalized.dataset.case_ids == tuple(
        case.reference.id for case in plant_invented_references((reference,), count=1)
    )


def test_phase_two_command_runs_alignment_baseline_with_fake_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "alignment.jsonl"
    source.write_text(
        json.dumps({"claim": "Claim", "source_text": "Evidence", "expected_label": "SUPPORTS"})
        + "\n",
        encoding="utf-8",
    )
    output = StringIO()

    class Runner:
        def run(self, payload: str) -> SimpleNamespace:
            assert "Claim" in payload and "Evidence" in payload
            return SimpleNamespace(
                valid=True,
                content=AlignmentJudgment(
                    label="SUPPORTS",
                    confidence=1,
                    rationale="Evidence supports the claim.",
                ),
            )

    class Factory:
        def __init__(self, run_id: str, stage: str, *, usage_sink: object) -> None:
            assert run_id == "phase2-benchmark" and stage == "integrity_benchmark"
            assert usage_sink is not None

        def citation_alignment_judge(self, *, output_schema: type[AlignmentJudgment]) -> Runner:
            assert output_schema is AlignmentJudgment
            return Runner()

    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.bench_integrity_phase2.AgentFactory",
        Factory,
    )
    call_command(
        "bench_integrity_phase2",
        dataset="citation_integrity",
        input=source,
        stdout=output,
    )

    report = json.loads(output.getvalue())
    assert report["metrics"]["accuracy"] == 1
