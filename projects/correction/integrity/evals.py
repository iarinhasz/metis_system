"""Adaptadores dos benchmarks de integridade ao contrato compartilhado de evals."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import JsonValue

from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import LLMUsage
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    Metric,
    UsageSummary,
)
from projects.correction.integrity.benchmarks import BenchmarkReport as PlagiarismReport
from projects.correction.integrity.benchmarks_phase2 import Phase2BenchmarkReport

PLAGIARISM_BENCHMARK_VERSION = "plagiarism-1"
PHASE2_BENCHMARK_VERSION = "integrity-phase2-1"


def adapt_plagiarism_report(
    report: PlagiarismReport,
    *,
    dataset_version: str,
    dataset_sha256: str,
    case_ids: Sequence[str],
    parameters: Mapping[str, JsonValue],
    source_files: Sequence[Path],
    model_specs: Mapping[Role, ModelSpec] | None = None,
    prompt_versions: Mapping[str, Sequence[str]] | None = None,
    calls: Sequence[LLMUsage] = (),
) -> EvaluationReport:
    metrics: dict[str, Metric] = {}
    for item in report.metrics:
        prefix = item.plagiarism_type
        metrics[f"{prefix}.cases"] = Metric(value=item.cases, unit="count")
        metrics[f"{prefix}.true_positive"] = Metric(value=item.true_positive, unit="count")
        metrics[f"{prefix}.false_positive"] = Metric(
            value=item.false_positive, unit="count", direction="lower"
        )
        metrics[f"{prefix}.false_negative"] = Metric(
            value=item.false_negative, unit="count", direction="lower"
        )
        metrics[f"{prefix}.precision"] = Metric(
            value=item.precision, unit="fraction", direction="higher"
        )
        metrics[f"{prefix}.recall"] = Metric(value=item.recall, unit="fraction", direction="higher")
    calibration_values: dict[str, JsonValue] = {
        key: value for key, value in report.calibration_values.items()
    }
    return _evaluation_report(
        benchmark="bench_plagiarism",
        benchmark_version=PLAGIARISM_BENCHMARK_VERSION,
        dataset_name="peerread_synthetic_plagiarism",
        dataset_version=dataset_version,
        dataset_sha256=dataset_sha256,
        case_ids=case_ids,
        metrics=metrics,
        parameters=parameters,
        details={
            "calibration_status": report.calibration_status,
            "calibration_values": calibration_values,
        },
        source_files=source_files,
        model_specs=model_specs,
        prompt_versions=prompt_versions,
        calls=calls,
    )


def adapt_phase2_report(
    report: Phase2BenchmarkReport,
    *,
    dataset_version: str,
    dataset_sha256: str,
    case_ids: Sequence[str],
    parameters: Mapping[str, JsonValue],
    source_files: Sequence[Path],
    model_specs: Mapping[Role, ModelSpec] | None = None,
    prompt_versions: Mapping[str, Sequence[str]] | None = None,
    calls: Sequence[LLMUsage] = (),
) -> EvaluationReport:
    metrics: dict[str, Metric] = {}
    for name, value in report.metrics.items():
        is_ratio = name in {
            "precision",
            "recall",
            "false_positive_rate",
            "accuracy",
            "macro_f1",
        }
        metrics[name] = Metric(
            value=value,
            unit="fraction" if is_ratio else "count",
            direction=(
                "higher"
                if name in {"precision", "recall", "accuracy", "macro_f1"}
                else "lower"
                if name in {"false_positive", "false_negative", "false_positive_rate"}
                else "informational"
            ),
        )
    return _evaluation_report(
        benchmark=report.dataset,
        benchmark_version=PHASE2_BENCHMARK_VERSION,
        dataset_name=report.dataset,
        dataset_version=dataset_version,
        dataset_sha256=dataset_sha256,
        case_ids=case_ids,
        metrics=metrics,
        parameters=parameters,
        details={
            "calibration_status": report.calibration_status,
            "provenance": report.provenance,
        },
        source_files=source_files,
        model_specs=model_specs,
        prompt_versions=prompt_versions,
        calls=calls,
    )


def _evaluation_report(
    *,
    benchmark: str,
    benchmark_version: str,
    dataset_name: str,
    dataset_version: str,
    dataset_sha256: str,
    case_ids: Sequence[str],
    metrics: dict[str, Metric],
    parameters: Mapping[str, JsonValue],
    details: Mapping[str, JsonValue],
    source_files: Sequence[Path],
    model_specs: Mapping[Role, ModelSpec] | None,
    prompt_versions: Mapping[str, Sequence[str]] | None,
    calls: Sequence[LLMUsage],
) -> EvaluationReport:
    if not case_ids:
        raise ValueError("Um relatório de evals precisa de pelo menos um caso.")
    normalized_specs = dict(model_specs or {})
    prompt_hashes = {
        name: tuple(sorted(set(versions))) for name, versions in (prompt_versions or {}).items()
    }
    if calls and (not normalized_specs or not prompt_hashes):
        raise ValueError("Chamadas de LLM exigem specs e hashes dos prompts utilizados.")
    return EvaluationReport(
        benchmark=benchmark,
        benchmark_version=benchmark_version,
        created_at=datetime.now(UTC),
        dataset=DatasetIdentity(
            name=dataset_name,
            version=dataset_version,
            sha256=dataset_sha256,
            case_ids=tuple(case_ids),
        ),
        parameters={key: value for key, value in parameters.items()},
        model_specs=normalized_specs,
        prompt_versions=prompt_hashes,
        source_sha256={path.name: _sha256(path) for path in source_files},
        metrics=metrics,
        failures=0,
        usage=UsageSummary.from_calls(calls),
        details={key: value for key, value in details.items()},
        notes=("Relatório normalizado para metis.evals; calibração não inferida automaticamente.",),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dataset_sha256(path: Path) -> str:
    """Calcula a identidade de uma fixture/manifesto sem carregar seu conteúdo no relatório."""
    return _sha256(path)
