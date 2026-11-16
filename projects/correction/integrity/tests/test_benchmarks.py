from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.management import call_command

from projects.correction.extractor.contract import DocumentSection, ExtractedDocument
from projects.correction.integrity.benchmarks import build_peerread_cases, evaluate_cases

if TYPE_CHECKING:
    import pytest


def _document(title: str, passage: str) -> ExtractedDocument:
    return ExtractedDocument(
        title=title,
        language="en",
        abstract=passage,
        sections=(
            DocumentSection(
                id="s1",
                title="Section",
                level=1,
                text=passage,
            ),
        ),
    )


def test_peerread_cases_generate_literal_rewrite_and_negative_examples() -> None:
    first = _document(
        "First",
        "The investigators carefully compared treatment outcomes across four independent patient "
        "groups during the randomized clinical study.",
    )
    second = _document(
        "Second",
        "Researchers systematically examined seasonal rainfall patterns over multiple geographic "
        "regions during a decade-long environmental monitoring program.",
    )
    cases = build_peerread_cases(
        (first, second),
        rewrite=lambda text, kind: f"{kind}: {text}",
        max_passages=2,
    )

    assert {case.plagiarism_type for case in cases} == {
        "literal",
        "paraphrase",
        "translated",
        "negative",
    }


def test_precision_and_recall_are_reported_by_synthetic_type() -> None:
    cases = build_peerread_cases(
        (
            _document(
                "First",
                "The investigators carefully compared treatment outcomes across four independent "
                "patient groups during the randomized clinical study.",
            ),
            _document(
                "Second",
                "Researchers systematically examined seasonal rainfall patterns over multiple "
                "geographic regions during a decade-long environmental monitoring program.",
            ),
        ),
        max_passages=2,
    )
    report = evaluate_cases(
        cases,
        detector=lambda source, target: source in target,
        calibration_values={"semantic_similarity_threshold": 0.88},
    )
    literal = next(item for item in report.metrics if item.plagiarism_type == "literal")
    negative = next(item for item in report.metrics if item.plagiarism_type == "negative")

    assert literal.precision == 1
    assert literal.recall == 1
    assert negative.false_positive == 0
    assert report.calibration_status == "measured_not_calibrated"
    assert report.calibration_values == {"semantic_similarity_threshold": 0.88}


def test_management_command_emits_metrics_without_external_rewrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = tmp_path / "peerread"
    source_dir.mkdir()
    for index in range(2):
        passage = (
            "The investigators carefully compared treatment outcomes across four independent "
            "patient groups during the randomized clinical study."
            if index == 0
            else "Researchers systematically examined seasonal rainfall patterns over multiple "
            "geographic regions during a decade-long environmental monitoring program."
        )
        (source_dir / f"peerread-{index}.json").write_text(
            _document(f"Document {index}", passage).model_dump_json(),
            encoding="utf-8",
        )
    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.bench_plagiarism.embed_documents",
        lambda texts: [[1.0, 0.0] for _ in texts],
    )
    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.bench_plagiarism.embed_query",
        lambda text: [1.0, 0.0],
    )
    output = StringIO()

    call_command("bench_plagiarism", source_dir=source_dir, limit=2, stdout=output)
    report = json.loads(output.getvalue())

    assert report["calibration_status"] == "measured_not_calibrated"
    assert report["metrics"][0]["plagiarism_type"] == "literal"
