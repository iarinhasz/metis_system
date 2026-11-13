"""Snapshots de entrada e saída do E5; Decimal evita arredondar antes da decisão."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    ItemVerdict,
    ReviewState,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.questions.profile import FrozenModel


class Recommendation(StrEnum):
    ACCEPT = "accept"
    MINOR = "minor"
    MAJOR = "major"
    REJECT = "reject"


class AggregationPolicy(FrozenModel):
    version: str = "median-v1"
    # Faixas de desenvolvimento na escala 1–5; aguardam calibração no A/B do M3.
    accept_min: Decimal = Field(default=Decimal(4), ge=1, le=5, allow_inf_nan=False)
    minor_min: Decimal = Field(default=Decimal(3), ge=1, le=5, allow_inf_nan=False)
    major_min: Decimal = Field(default=Decimal(2), ge=1, le=5, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_bands(self) -> AggregationPolicy:
        if not self.major_min < self.minor_min < self.accept_min:
            raise ValueError("As faixas de recomendação precisam ser crescentes.")
        return self


class ReviewedSlot(FrozenModel):
    slot: EvaluatorSlot
    round_number: int = Field(ge=1)
    mode: EvaluationMode
    model_spec: ModelSpec
    state: ReviewState
    verdicts: tuple[ItemVerdict, ...]


class Vote(FrozenModel):
    slot: EvaluatorSlot
    round_number: int
    grade: int
    justification: str
    evidence_ids: tuple[str, ...]


class ExcludedVote(FrozenModel):
    slot: EvaluatorSlot
    reason: str


class CriterionScore(FrozenModel):
    criterion_key: Criterion
    label: str
    weight: Decimal
    grade: Decimal | None
    dispersion: Decimal | None
    votes: tuple[Vote, ...]
    excluded: tuple[ExcludedVote, ...]
    unresolved: bool


class Aggregation(FrozenModel):
    criteria: tuple[CriterionScore, ...]
    total_score: Decimal | None
    agreement: Decimal | None
    recommendation: Recommendation | None
    needs_human_review: bool
    policy: AggregationPolicy


class ConsolidationResult(FrozenModel):
    report_id: UUID
    recommendation: Recommendation | None
    needs_human_review: bool


def item_id(slot: EvaluatorSlot, kind: str, key: str) -> str:
    """O mesmo obs-1 de A e B nunca se confunde no relatório ou no meta-revisor."""
    return f"{slot}:{kind}:{key}"
