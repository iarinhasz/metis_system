"""Um veredito auditável e imutável por item de cada rodada."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import transaction

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.queries.attempts.run import RunConflict

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.agents.schemas.evaluation import ItemVerdict, VerdictSource
    from projects.correction.agents.specs import ModelSpec
    from projects.correction.evaluation.models import JudgeVerdict


class JudgeVerdictManagement:
    objects: ClassVar[models.Manager[JudgeVerdict]]

    @classmethod
    @transaction.atomic
    def record(
        cls,
        round_id: Any,
        task_id: str,
        *,
        item: ItemVerdict,
        source: VerdictSource,
        judge_model: ModelSpec | None = None,
    ) -> JudgeVerdict:
        from projects.correction.evaluation.models import ReviewRound

        review = ReviewRound.objects.get(pk=round_id)
        Run.lock_for_stage(review.run_id, task_id, RunStatus.EVALUATING)
        review = ReviewRound.objects.select_for_update().get(pk=round_id)
        if review.ready:
            raise RunConflict("A rodada finalizada é imutável.")
        state = review.state
        keys = {("observation", value.id) for value in state.observations}
        keys |= {("check", value.id) for value in state.cross_checks}
        keys |= {("criterion", value.criterion_key) for value in state.criteria}
        if (item.item_type, item.item_key) not in keys:
            raise RunConflict("O veredito cita um item que não pertence à rodada.")
        values = item.model_dump(mode="json") | {
            "source": source,
            "judge_model": judge_model.model_dump(mode="json") if judge_model else None,
        }
        row = cls.objects.filter(
            round=review, item_type=item.item_type, item_key=item.item_key
        ).first()
        if row is not None:
            if any(getattr(row, name) != value for name, value in values.items()):
                raise RunConflict("O veredito registrado é imutável.")
            return row
        row = cls.objects.model(round=review, **values)
        row.full_clean()
        row.save()
        return row
