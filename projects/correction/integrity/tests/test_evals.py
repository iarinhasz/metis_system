from __future__ import annotations

from pathlib import Path

import pytest

from projects.correction.agents.specs import Role, development_spec
from projects.correction.agents.usage import LLMUsage
from projects.correction.integrity.benchmarks import (
    BenchmarkReport,
    TypeMetrics,
)
from projects.correction.integrity.benchmarks_phase2 import Phase2BenchmarkReport
from projects.correction.integrity.evals import (
    adapt_phase2_report,
    adapt_plagiarism_report,
)


def test_plagiarism_adapter_emits_versioned_shared_eval_report(tmp_path: Path) -> None:
    source = tmp_path / "bench.py"
    source.write_text("benchmark implementation", encoding="utf-8")
    report = BenchmarkReport(
        metrics=(
            TypeMetrics(
                plagiarism_type="literal",
                cases=2,
                true_positive=1,
                false_positive=0,
                false_negative=1,
                precision=1,
                recall=0.5,
            ),
            TypeMetrics(
                plagiarism_type="paraphrase",
                cases=0,
                true_positive=0,
                false_positive=0,
                false_negative=0,
            ),
            TypeMetrics(
                plagiarism_type="translated",
                cases=0,
                true_positive=0,
                false_positive=0,
                false_negative=0,
            ),
            TypeMetrics(
                plagiarism_type="negative",
                cases=1,
                true_positive=0,
                false_positive=0,
                false_negative=0,
            ),
        ),
        calibration_values={"similarity_threshold": 0.88},
    )

    normalized = adapt_plagiarism_report(
        report,
        dataset_version="peerread-v1",
        dataset_sha256="a" * 64,
        case_ids=("literal-0", "negative-0"),
        parameters={"mode": "rules"},
        source_files=(source,),
        model_specs={Role.FAST: development_spec(Role.FAST)},
    )

    assert normalized.benchmark == "bench_plagiarism"
    assert normalized.benchmark_version == "plagiarism-1"
    assert normalized.dataset.case_ids == ("literal-0", "negative-0")
    assert normalized.metrics["literal.precision"].value == 1
    assert normalized.metrics["literal.recall"].value == 0.5
    assert normalized.model_specs[Role.FAST] == development_spec(Role.FAST)
    assert normalized.source_sha256["bench.py"]


def test_phase2_adapter_records_model_prompt_hashes_and_usage(tmp_path: Path) -> None:
    source = tmp_path / "phase2.py"
    source.write_text("alignment implementation", encoding="utf-8")
    call = LLMUsage(
        run_id="bench",
        stage="integrity_benchmark",
        role=Role.ADJUDICATOR,
        agent="citation_alignment_judge",
        provider=development_spec(Role.ADJUDICATOR).provider,
        model_id=development_spec(Role.ADJUDICATOR).model_id,
        prompt_version="b" * 64,
        input_tokens=12,
        output_tokens=3,
        cached_tokens=0,
        latency_ms=20,
        success=True,
    )
    report = Phase2BenchmarkReport(
        dataset="sciciteval",
        cases=1,
        metrics={"accuracy": 1.0, "macro_f1": 1.0},
        provenance="normalized fixture",
    )

    normalized = adapt_phase2_report(
        report,
        dataset_version="sciciteval-v1",
        dataset_sha256="c" * 64,
        case_ids=("case-1",),
        parameters={"limit": 1},
        source_files=(source,),
        model_specs={Role.ADJUDICATOR: development_spec(Role.ADJUDICATOR)},
        prompt_versions={"citation_alignment_judge": (call.prompt_version,)},
        calls=(call,),
    )

    assert normalized.benchmark == "sciciteval"
    assert normalized.metrics["accuracy"].value == 1
    assert normalized.usage.calls == 1
    assert normalized.prompt_versions["citation_alignment_judge"] == ("b" * 64,)
    assert normalized.model_specs[Role.ADJUDICATOR].model_id == call.model_id


def test_plagiarism_adapter_rejects_empty_case_identity(tmp_path: Path) -> None:
    source = tmp_path / "bench.py"
    source.write_text("source", encoding="utf-8")
    report = BenchmarkReport(metrics=(), calibration_values={})

    with pytest.raises(ValueError, match="pelo menos um caso"):
        adapt_plagiarism_report(
            report,
            dataset_version="peerread-v1",
            dataset_sha256="a" * 64,
            case_ids=(),
            parameters={},
            source_files=(source,),
        )
