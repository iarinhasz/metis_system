"""Strategy que monta os passos isolados do avaliador conforme o modo do Run."""

from typing import Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    ReviewState,
)
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.cross_checks import CrossCheckStep
from projects.correction.evaluation.section_pass import SectionPassStep
from projects.correction.evaluation.synthesis import SynthesisStep
from projects.correction.evaluation.whole_document import WholeDocumentStep


class EvaluationExecutor(Protocol):
    def execute(self) -> ReviewState: ...


class EvaluationCheckpoints(Protocol):
    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def store_state(self, state: ReviewState) -> None: ...


def evaluator_steps(
    context: EvaluationContext,
    slot: EvaluatorSlot,
    factory: AgentFactory,
    checkpoints: EvaluationCheckpoints,
    *,
    max_workers: int = 1,
) -> tuple[EvaluationExecutor, ...]:
    """Monta a estratégia sectioned ou whole_document a partir do snapshot do Run."""
    if context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT:
        return (WholeDocumentStep(context, slot, factory, checkpoints),)
    return (
        SectionPassStep(context, slot, factory, checkpoints, max_workers=max_workers),
        CrossCheckStep(context, slot, factory, checkpoints, max_workers=max_workers),
        SynthesisStep(context, slot, factory, checkpoints),
    )
