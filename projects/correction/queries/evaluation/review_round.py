"""Gravação do E4 e leitura das últimas rodadas completas para o E5."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from projects.correction.agents.schemas.evaluation import EvaluatorSlot, ItemType, Verdict
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.contracts import ReviewedSlot
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.criteria import EvaluationConfig, get_method

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.agents.schemas.evaluation import EvaluationMode, ReviewState
    from projects.correction.agents.specs import ModelSpec
    from projects.correction.evaluation.models import ReviewRound


class ReviewRoundManagement:
    objects: ClassVar[models.Manager[ReviewRound]]

    @classmethod
    @transaction.atomic
    def store(
        cls,
        run_id: Any,
        task_id: str,
        *,
        slot: EvaluatorSlot,
        round_number: int,
        mode: EvaluationMode,
        model_spec: ModelSpec,
        state: ReviewState,
    ) -> ReviewRound:
        run = Run.lock_for_stage(run_id, task_id, RunStatus.EVALUATING)
        config_data = run.config_snapshot.get("evaluation_config")
        config = (
            EvaluationConfig.model_validate(config_data)
            if config_data
            else get_method(run.config_snapshot.get("method", "standard"))
        )
        scales = {item.key: item.grades for item in config.criteria}
        if any(item.grade not in scales[item.criterion_key] for item in state.criteria):
            raise ValidationError("A nota não pertence à escala permitida do critério.")
        values = state.model_dump(mode="json")
        row = cls.objects.filter(run=run, evaluator_slot=slot, round_number=round_number).first()
        if row is not None and row.ready:
            raise RunConflict("A rodada finalizada é imutável.")
        if row is not None and row.verdicts.exists():
            raise RunConflict("Uma revisão julgada exige nova rodada.")
        if row is None:
            row = cls.objects.model(run=run, evaluator_slot=slot, round_number=round_number)
        row.mode, row.model_spec = mode, model_spec.model_dump(mode="json")
        for name, value in values.items():
            setattr(row, name, value)
        row.updated_at = timezone.now()
        row.full_clean()
        row.save()
        return row

    @classmethod
    @transaction.atomic
    def finalize(cls, round_id: Any, task_id: str) -> ReviewRound:
        row = cls.objects.select_related("run").get(pk=round_id)
        Run.lock_for_stage(row.run_id, task_id, RunStatus.EVALUATING)
        row = cls.objects.select_for_update().get(pk=round_id)
        state = row.state
        unresolved = {(item.item_type, item.item_key) for item in state.unresolved}
        verdicts = {(item.item_type, item.item_key): item.verdict for item in row.verdicts.all()}
        keys = {(ItemType.OBSERVATION, item.id) for item in state.observations}
        keys |= {(ItemType.CHECK, item.id) for item in state.cross_checks}
        keys |= {(ItemType.CRITERION, item.criterion_key) for item in state.criteria}
        if not unresolved <= keys or any(
            verdicts.get(key) != Verdict.VALID and key not in unresolved for key in keys
        ):
            raise RunConflict("Todos os itens precisam de veredito válido ou marcação unresolved.")
        if not state.criteria:
            raise RunConflict("A rodada não contém sínteses de critérios.")
        observations = {item.id for item in state.observations}
        checks = {item.id for item in state.cross_checks}
        for criterion in state.criteria:
            if (
                not set(criterion.observation_ids) <= observations
                or not set(criterion.check_ids) <= checks
            ):
                raise RunConflict("A síntese cita ids que não pertencem à rodada.")
        row.ready = True
        row.updated_at = timezone.now()
        row.save(update_fields=["ready", "updated_at"])
        return row

    @classmethod
    def latest_for_consolidation(cls, run_id: Any) -> tuple[ReviewedSlot, ...]:
        rows = (
            cls.objects.filter(run_id=run_id)
            .order_by("evaluator_slot", "-round_number")
            .prefetch_related("verdicts")
        )
        latest: dict[str, ReviewRound] = {}
        for row in rows:
            latest.setdefault(row.evaluator_slot, row)
        if set(latest) != set(EvaluatorSlot) or any(not row.ready for row in latest.values()):
            return ()
        return tuple(
            ReviewedSlot(
                slot=EvaluatorSlot(slot),
                round_number=row.round_number,
                mode=row.mode,
                model_spec=row.model_spec,
                state=row.state,
                verdicts=tuple(verdict.item for verdict in row.verdicts.all()),
            )
            for slot, row in sorted(latest.items())
        )
