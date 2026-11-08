"""Registro das tasks de estágio no app Celery, uma por estágio."""

from projects.correction.metis.celery import app
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
