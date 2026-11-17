"""Contratos de revisão e julgamento, sem dependência dos models do domínio."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.section_roles import SectionRole

type Text = Annotated[str, Field(min_length=1, max_length=20000)]
type Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
# Inteiro com limites, e não Literal[1..5]: o SDK do Gemini só aceita enum de texto e recusa o
# schema inteiro ("Input should be a valid string") onde aparece uma nota.
type Grade = Annotated[int, Field(ge=1, le=5)]


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class EvaluatorSlot(StrEnum):
    A = "a"
    B = "b"
    C = "c"


class EvaluationMode(StrEnum):
    SECTIONED = "sectioned"
    WHOLE_DOCUMENT = "whole_document"


class ItemType(StrEnum):
    OBSERVATION = "observation"
    CHECK = "check"
    CRITERION = "criterion"


class Verdict(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class VerdictSource(StrEnum):
    VALIDATOR = "validator"
    JUDGE = "judge"


class Evidence(Output):
    quote: Text
    section_id: Text


class Observation(Output):
    id: Text
    section_id: Text
    role: SectionRole
    kind: Literal["strength", "weakness", "missing", "inconsistency"]
    statement: Text
    evidence: tuple[Evidence, ...] = ()
    criteria: tuple[Criterion, ...] = Field(min_length=1)
    severity: Literal["minor", "major", "critical"]
    possibly_elsewhere: bool = False
    confidence: Confidence


class SectionObservations(Output):
    section_id: Text
    observations: tuple[Observation, ...]


class CrossCheckResult(Output):
    id: Text
    kind: Literal["claims_vs_results", "method_vs_question", "figure_vs_text"]
    verdict: Literal["consistent", "inconsistent", "unclear"]
    evidence: tuple[Evidence, ...] = ()
    criteria: tuple[Criterion, ...] = Field(min_length=1)
    severity: Literal["minor", "major", "critical"]


class CriterionSynthesis(Output):
    criterion_key: Criterion
    grade: Grade
    justification: Text
    observation_ids: tuple[str, ...] = ()
    check_ids: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()  # Modo whole_document.
    confidence: Confidence


class CriteriaSynthesis(Output):
    criteria: tuple[CriterionSynthesis, ...]


class ItemRef(Output):
    item_type: ItemType
    item_key: Text


class Issue(Output):
    category: Literal[
        "ungrounded", "factual_error", "contradiction", "rubric_mismatch", "off_topic"
    ]
    excerpt: Text
    reason: Text


class ItemVerdict(ItemRef):
    verdict: Verdict
    issues: tuple[Issue, ...] = ()


class JudgeReport(Output):
    items: tuple[ItemVerdict, ...]


class RevisionResponse(ItemRef):
    action: Literal["accept", "rebut"]
    justification: Text
    evidence: tuple[Evidence, ...] = ()
    # Tipado, e não um dict livre: a saída estruturada da OpenAI recusa um objeto sem schema
    # (400 "schema must have a 'type' key"). O tipo certo para o alvo é conferido na revisão.
    replacement: Observation | CrossCheckResult | CriterionSynthesis | None = None


class ReviewState(Output):
    observations: tuple[Observation, ...] = ()
    cross_checks: tuple[CrossCheckResult, ...] = ()
    criteria: tuple[CriterionSynthesis, ...] = ()
    unresolved: tuple[ItemRef, ...] = ()
    changed_items: tuple[ItemRef, ...] = ()
    revisions: tuple[RevisionResponse, ...] = ()

    @model_validator(mode="after")
    def unique_items(self) -> ReviewState:
        groups = (
            tuple(item.id for item in self.observations),
            tuple(item.id for item in self.cross_checks),
            tuple(item.criterion_key for item in self.criteria),
            tuple((item.item_type, item.item_key) for item in self.unresolved),
        )
        if any(len(set(group)) != len(group) for group in groups):
            raise ValueError("Ids de itens e critérios precisam ser únicos dentro da rodada.")
        return self
