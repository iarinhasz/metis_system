"""Trilha das revisões e relatório imutável do E5."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from pydantic import ValidationError as SchemaError

from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    ItemType,
    ItemVerdict,
    ReviewState,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import TimeStampModel
from projects.correction.evaluation.contracts import Recommendation
from projects.correction.queries.evaluation.final_report import FinalReportManagement
from projects.correction.queries.evaluation.judge_verdict import JudgeVerdictManagement
from projects.correction.queries.evaluation.review_round import ReviewRoundManagement


class ReviewRound(ReviewRoundManagement, TimeStampModel):
    run = models.ForeignKey("attempts.Run", on_delete=models.PROTECT, related_name="review_rounds")
    evaluator_slot = models.CharField(
        max_length=1, choices=[(v.value, v.value) for v in EvaluatorSlot]
    )
    model_spec = models.JSONField()
    round_number = models.PositiveIntegerField()
    mode = models.CharField(max_length=20, choices=[(v.value, v.value) for v in EvaluationMode])
    observations = models.JSONField(default=list, blank=True)
    cross_checks = models.JSONField(default=list, blank=True)
    criteria = models.JSONField(default=list, blank=True)
    unresolved = models.JSONField(default=list, blank=True)
    changed_items = models.JSONField(default=list, blank=True)
    revisions = models.JSONField(default=list, blank=True)
    ready = models.BooleanField(default=False)

    class Meta:
        ordering = ["evaluator_slot", "round_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "evaluator_slot", "round_number"], name="review_run_slot_round_uniq"
            ),
            models.CheckConstraint(
                condition=models.Q(round_number__gte=1), name="review_round_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(evaluator_slot__in=list(EvaluatorSlot)), name="review_slot_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(mode__in=list(EvaluationMode)), name="review_mode_valid"
            ),
        ]

    @property
    def state(self) -> ReviewState:
        return ReviewState.model_validate(
            {name: getattr(self, name) for name in ReviewState.model_fields}
        )

    def clean(self) -> None:
        super().clean()
        try:
            ModelSpec.model_validate(self.model_spec)
            _ = self.state
        except SchemaError as exc:
            raise ValidationError("Snapshot de revisão inválido.") from exc


class JudgeVerdict(JudgeVerdictManagement, TimeStampModel):
    round = models.ForeignKey(ReviewRound, on_delete=models.PROTECT, related_name="verdicts")
    item_type = models.CharField(max_length=16, choices=[(v.value, v.value) for v in ItemType])
    item_key = models.CharField(max_length=255)
    verdict = models.CharField(max_length=8, choices=[(v.value, v.value) for v in Verdict])
    issues = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=16, choices=[(v.value, v.value) for v in VerdictSource])
    judge_model = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "item_type", "item_key"], name="verdict_round_type_key_uniq"
            ),
            models.CheckConstraint(
                condition=models.Q(item_type__in=list(ItemType)), name="verdict_type_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(verdict__in=list(Verdict)), name="verdict_value_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(source__in=list(VerdictSource)), name="verdict_source_valid"
            ),
        ]

    @property
    def item(self) -> ItemVerdict:
        return ItemVerdict.model_validate(
            {name: getattr(self, name) for name in ItemVerdict.model_fields}
        )

    def clean(self) -> None:
        super().clean()
        try:
            _ = self.item
            if self.judge_model is not None:
                ModelSpec.model_validate(self.judge_model)
        except SchemaError as exc:
            raise ValidationError("Veredito inválido.") from exc
        if (self.source == VerdictSource.JUDGE) != (self.judge_model is not None):
            raise ValidationError("Somente vereditos do juiz têm snapshot de judge_model.")


class FinalReport(FinalReportManagement, TimeStampModel):
    run = models.OneToOneField(
        "attempts.Run", on_delete=models.PROTECT, related_name="final_report"
    )
    recommendation = models.CharField(
        max_length=8, choices=[(v.value, v.value) for v in Recommendation], null=True, blank=True
    )
    total_score = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    agreement = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    content = models.JSONField()
    markdown = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(recommendation__in=list(Recommendation))
                | models.Q(recommendation__isnull=True),
                name="report_recommendation_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(total_score__gte=1, total_score__lte=5)
                | models.Q(total_score__isnull=True),
                name="report_score_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(agreement__gte=0, agreement__lte=1)
                | models.Q(agreement__isnull=True),
                name="report_agreement_valid",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("O relatório final é imutável; crie outro Run para reavaliar.")
        super().save(*args, **kwargs)
