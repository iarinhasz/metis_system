"""Strategy dos modos e execução whole_document com saídas estruturadas."""

import json

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    EvaluationMode,
    EvaluatorSlot,
    ItemRef,
    ItemType,
    ReviewState,
)
from projects.correction.agents.specs import Role, development_spec
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.cross_checks import CrossCheckStep
from projects.correction.evaluation.modes import evaluator_steps
from projects.correction.evaluation.section_pass import SectionPassStep
from projects.correction.evaluation.synthesis import SynthesisStep
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.evaluation.whole_document import (
    RunWholeDocumentCheckpoints,
    WholeDocumentStep,
)
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict

type OutputData = dict[str, list[dict[str, object]]]


class FakeCheckpoints:
    def __init__(self, state: ReviewState | None = None) -> None:
        self.state = state or ReviewState()
        self.writes = 0

    def assert_owned(self) -> None:
        return None

    def read_state(self) -> ReviewState:
        return self.state

    def store_state(self, state: ReviewState) -> None:
        self.state = state
        self.writes += 1


def _context(mode: EvaluationMode = EvaluationMode.SECTIONED) -> EvaluationContext:
    run = _context_run()
    run.config_snapshot["evaluation_mode"] = mode.value
    return EvaluationContextBuilder(run).build()


def _output(context: EvaluationContext) -> OutputData:
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    return {
        "criteria": [
            {
                "criterion_key": key.value,
                "grade": 3,
                "justification": f"A evidência sustenta {key.value}.",
                "evidence": [{"quote": "O método usa dados públicos.", "section_id": "sec_method"}],
                "confidence": 0.8,
            }
            for key in active
        ]
    }


def test_evaluator_strategy_selects_steps_from_run_snapshot() -> None:
    factory = FakeAgentFactory()
    checkpoints = FakeCheckpoints()
    sectioned = evaluator_steps(_context(), EvaluatorSlot.A, factory, checkpoints, max_workers=2)
    whole = evaluator_steps(
        _context(EvaluationMode.WHOLE_DOCUMENT), EvaluatorSlot.A, factory, checkpoints
    )

    assert tuple(type(step) for step in sectioned) == (
        SectionPassStep,
        CrossCheckStep,
        SynthesisStep,
    )
    assert len(whole) == 1 and isinstance(whole[0], WholeDocumentStep)


def test_builder_persists_selected_mode_in_run_snapshot() -> None:
    run = _context_run()
    builder = EvaluationContextBuilder(run, evaluation_mode=EvaluationMode.WHOLE_DOCUMENT)

    snapshot = builder.snapshot()
    run.config_snapshot.update(snapshot)
    context = EvaluationContextBuilder(run).build()

    assert snapshot["evaluation_mode"] == EvaluationMode.WHOLE_DOCUMENT.value
    assert context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT


def test_whole_document_synthesizes_all_active_criteria_in_one_call() -> None:
    context = _context(EvaluationMode.WHOLE_DOCUMENT)
    usage = MemoryUsageSink()
    factory = FakeAgentFactory(
        scripts={"whole_document_reviewer": [_output(context)]}, usage_sink=usage
    )
    checkpoints = FakeCheckpoints()
    step = WholeDocumentStep(context, EvaluatorSlot.A, factory, checkpoints)

    state = step.execute()

    assert len(factory.calls) == 1
    assert usage.calls[0].model_id == context.evaluator(EvaluatorSlot.A).model.model_id
    assert len(state.criteria) == len(_output(context)["criteria"])
    assert checkpoints.state == state and checkpoints.writes == 1
    article = json.loads(factory.calls[0].payload.article or "{}")
    assert article["title"] == context.article.title
    assert article["sections"][-1]["id"] == "sec_method"
    assert factory.calls[0].name == "whole_document_reviewer"
    assert all(item.evidence and not item.observation_ids for item in state.criteria)


def test_whole_document_refreshes_only_requested_criterion() -> None:
    context = _context(EvaluationMode.WHOLE_DOCUMENT)
    initial = tuple(
        CriterionSynthesis.model_validate(item) for item in _output(context)["criteria"]
    )
    checkpoints = FakeCheckpoints(ReviewState(criteria=initial))
    target = next(
        item for item in _output(context)["criteria"] if item["criterion_key"] == "soundness"
    )
    response = {
        "criteria": [
            target
            | {
                "grade": 4,
                "justification": "A síntese atualizada usa a evidência revisada.",
            }
        ]
    }
    factory = FakeAgentFactory(scripts={"whole_document_reviewer": [response]})
    step = WholeDocumentStep(context, EvaluatorSlot.A, factory, checkpoints)

    state = step.execute(refresh=(Criterion.SOUNDNESS,), mark_changed=True)

    assert len(factory.calls) == 1
    assert len(state.criteria) == len(initial)
    assert (
        next(item.grade for item in state.criteria if item.criterion_key is Criterion.SOUNDNESS)
        == 4
    )
    assert state.changed_items == (
        ItemRef(item_type=ItemType.CRITERION, item_key=Criterion.SOUNDNESS.value),
    )


@pytest.mark.parametrize(
    "invalid_evidence",
    [[], [{"quote": "Trecho", "section_id": "section-missing"}]],
)
def test_whole_document_requires_direct_evidence_from_known_sections(
    invalid_evidence: list[dict[str, str]],
) -> None:
    context = _context(EvaluationMode.WHOLE_DOCUMENT)
    output = _output(context)
    criteria = output["criteria"]
    assert isinstance(criteria, list)
    criteria[0]["evidence"] = invalid_evidence
    factory = FakeAgentFactory(scripts={"whole_document_reviewer": [output]})
    step = WholeDocumentStep(context, EvaluatorSlot.A, factory, FakeCheckpoints())

    with pytest.raises(InvalidEvaluationOutput):
        step.execute()


def test_whole_document_step_rejects_sectioned_snapshot() -> None:
    step = WholeDocumentStep(_context(), EvaluatorSlot.A, FakeAgentFactory(), FakeCheckpoints())

    with pytest.raises(InvalidEvaluationOutput, match="exige o modo whole_document"):
        step.execute()


@pytest.mark.django_db
def test_whole_document_checkpoint_persists_its_mode_and_refuses_stale_owner(run: Run) -> None:
    task_id = "e4-whole-document"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    context = _context(EvaluationMode.WHOLE_DOCUMENT)
    checkpoints = RunWholeDocumentCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        model_spec=development_spec(Role.EVALUATOR_A),
    )
    factory = FakeAgentFactory(scripts={"whole_document_reviewer": [_output(context)]})
    step = WholeDocumentStep(context, EvaluatorSlot.A, factory, checkpoints)

    state = step.execute()

    assert checkpoints.read_state() == state
    Run.objects.filter(pk=run.pk).update(current_task_id="replacement-task")
    with pytest.raises(RunConflict):
        checkpoints.store_state(state)


def test_whole_document_asks_again_for_a_criterion_without_valid_evidence() -> None:
    context = _context(EvaluationMode.WHOLE_DOCUMENT)
    first = _output(context)
    retry = _output(context)
    criteria, again = first["criteria"], retry["criteria"]
    assert isinstance(criteria, list) and isinstance(again, list)
    criteria[0]["evidence"] = [{"quote": "Trecho", "section_id": "section-missing"}]
    retry["criteria"] = again[:1]
    factory = FakeAgentFactory(scripts={"whole_document_reviewer": [first, retry]})
    step = WholeDocumentStep(context, EvaluatorSlot.A, factory, FakeCheckpoints())

    state = step.execute()

    assert len(factory.calls) == 2
    asked = json.loads(factory.calls[1].payload.prompt)
    assert [item["key"] for item in asked["criteria"]] == [criteria[0]["criterion_key"]]
    assert len(state.criteria) == len(criteria)
