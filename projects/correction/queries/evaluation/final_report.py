"""Gravação única do relatório, protegida pela posse do E5."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import transaction

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.evaluation.models import FinalReport
    from projects.correction.evaluation.report import ReportContent


class FinalReportManagement:
    objects: ClassVar[models.Manager[FinalReport]]

    @classmethod
    def for_run(cls, run_id: Any) -> FinalReport | None:
        return cls.objects.filter(run_id=run_id).first()

    @classmethod
    @transaction.atomic
    def store(cls, run_id: Any, task_id: str, content: ReportContent) -> FinalReport:
        from projects.correction.evaluation.report import render_markdown

        run = Run.lock_for_stage(run_id, task_id, RunStatus.CONSOLIDATING)
        if content.run_id != run.pk:
            raise ValueError("O relatório pertence a outro Run.")
        existing = cls.for_run(run_id)
        if existing is not None:
            return existing
        row = cls.objects.model(
            run=run,
            recommendation=content.recommendation,
            total_score=content.total_score.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            if content.total_score is not None
            else None,
            agreement=content.agreement.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            if content.agreement is not None
            else None,
            content=content.model_dump(mode="json"),
            markdown=render_markdown(content),
        )
        row.full_clean()
        row.save()
        return row
