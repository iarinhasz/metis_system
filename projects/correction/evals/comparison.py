"""Compara métricas somente quando tarefa, amostra e política coincidem."""

from pydantic import Field

from projects.correction.evals.contracts import EvaluationReport, FrozenModel, fingerprint


class MetricDelta(FrozenModel):
    baseline: int | float | None
    candidate: int | float | None
    delta: int | float | None
    improved: bool | None
    unit: str


class ReportComparison(FrozenModel):
    format: str = "metis.evals.comparison"
    schema_version: int = 1
    baseline_variant: str
    candidate_variant: str
    baseline_report: str
    candidate_report: str
    comparable: bool
    reasons: tuple[str, ...]
    metrics: dict[str, MetricDelta] = Field(default_factory=dict)


def compare_reports(baseline: EvaluationReport, candidate: EvaluationReport) -> ReportComparison:
    reasons = []
    if (baseline.benchmark, baseline.benchmark_version) != (
        candidate.benchmark,
        candidate.benchmark_version,
    ):
        reasons.append("benchmark ou versão do benchmark diferentes")
    if baseline.dataset != candidate.dataset:
        reasons.append("dataset ou casos selecionados diferentes")
    if fingerprint(baseline.parameters) != fingerprint(candidate.parameters):
        reasons.append("parâmetros de medição diferentes")

    def definitions(report: EvaluationReport) -> dict[str, tuple[str, str]]:
        return {name: (metric.unit, metric.direction) for name, metric in report.metrics.items()}

    if definitions(baseline) != definitions(candidate):
        reasons.append("definições de métricas diferentes")
    metrics = {}
    if not reasons:
        for name, before in baseline.metrics.items():
            after = candidate.metrics[name]
            delta = (
                after.value - before.value
                if after.value is not None and before.value is not None
                else None
            )
            improved = None
            if delta is not None and delta != 0 and before.direction != "informational":
                improved = delta > 0 if before.direction == "higher" else delta < 0
            metrics[name] = MetricDelta(
                baseline=before.value,
                candidate=after.value,
                delta=delta,
                improved=improved,
                unit=before.unit,
            )
    return ReportComparison(
        baseline_variant=baseline.variant_id,
        candidate_variant=candidate.variant_id,
        baseline_report=baseline.report_id,
        candidate_report=candidate.report_id,
        comparable=not reasons,
        reasons=tuple(reasons),
        metrics=metrics,
    )
