"""Registro das tasks no app Celery: uma por estágio e a do reconciliador."""

from projects.correction.metis.celery import app
from projects.correction.pipeline.reconciler import reconcile_runs
from projects.correction.pipeline.stages import (
    ConsolidationStage,
    EvaluationStage,
    ExtractionStage,
    IntegrityStage,
    ProfilingStage,
)

extract_attempt = app.register_task(ExtractionStage())
profile_attempt = app.register_task(ProfilingStage())
check_integrity = app.register_task(IntegrityStage())
evaluate_attempt = app.register_task(EvaluationStage())
consolidate_report = app.register_task(ConsolidationStage())


@app.task(name="pipeline.reconcile_runs")
def reconcile_runs_task() -> dict[str, list[str]]:
    """Task do beat: uma passada do reconciliador."""
    return reconcile_runs().as_dict()
