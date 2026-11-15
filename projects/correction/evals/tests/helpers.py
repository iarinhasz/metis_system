"""Relatório sintético mínimo para exercitar contratos e comparações sem LLM."""

from datetime import UTC, datetime

from projects.correction.agents.specs import Role, development_spec
from projects.correction.evals.contracts import DatasetIdentity, EvaluationReport, Metric


def report() -> EvaluationReport:
    return EvaluationReport(
        benchmark="synthetic",
        benchmark_version="1",
        created_at=datetime(2026, 11, 13, tzinfo=UTC),
        dataset=DatasetIdentity(
            name="synthetic", version="1", sha256="a" * 64, case_ids=("a", "b")
        ),
        parameters={"limit": 2},
        model_specs={Role.FAST: development_spec(Role.FAST)},
        prompt_versions={"classifier": ("b" * 64,)},
        source_sha256={"runner.py": "c" * 64},
        metrics={
            "accuracy": Metric(value=0.5, unit="fraction", direction="higher"),
            "failures": Metric(value=1, unit="count", direction="lower"),
            "unmeasured": Metric(value=None, unit="fraction", direction="higher"),
        },
        failures=1,
    )


def changed(original: EvaluationReport, **values: object) -> EvaluationReport:
    return EvaluationReport.model_validate(original.model_dump(mode="python") | values)
