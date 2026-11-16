"""Síntese do slot: contexto restrito, validação e retomada."""

import json
from collections.abc import Callable

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.evaluation import (
    CrossCheckResult,
    EvaluatorSlot,
    Observation,
    ReviewState,
)
from projects.correction.agents.specs import Role, development_spec
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.synthesis import (
    RunSynthesisCheckpoints,
    SynthesisStep,
)
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict


class FakeCheckpoints:
    def __init__(self, state: ReviewState | None = None) -> None:
        self.state = state or ReviewState()
        self.writes = 0
        self.ownership_checks = 0

    def assert_owned(self) -> None:
        self.ownership_checks += 1

    def read_state(self) -> ReviewState:
        self.assert_owned()
        return self.state

    def store_state(self, state: ReviewState) -> None:
        self.assert_owned()
        self.state = state
        self.writes += 1


def _context() -> EvaluationContext:
    return EvaluationContextBuilder(_context_run()).build()


def _state(context: EvaluationContext) -> ReviewState:
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    observation = Observation(
        id="obs-supported",
        section_id="sec_method",
        role="method",
        kind="strength",
        statement="O método descreve os dados usados.",
        criteria=active,
        severity="minor",
        confidence=0.8,
    )
    check = CrossCheckResult(
        id="check-soundness",
        kind="method_vs_question",
        verdict="consistent",
        criteria=("soundness",),
        severity="minor",
    )
    return ReviewState(observations=(observation,), cross_checks=(check,))


def _synthesis_data(context: EvaluationContext) -> dict[str, list[dict[str, object]]]:
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
                "justification": f"Síntese sintética para {key.value}.",
                "observation_ids": ["obs-supported"],
                "check_ids": ["check-soundness"] if key.value == "soundness" else [],
                "confidence": 0.75,
            }
            for key in active
        ]
    }


def _remove_criterion(data: dict[str, list[dict[str, object]]]) -> None:
    data["criteria"].pop()


def _replace_observation_id(data: dict[str, list[dict[str, object]]]) -> None:
    data["criteria"][0]["observation_ids"] = ["missing-observation"]


def _add_direct_evidence(data: dict[str, list[dict[str, object]]]) -> None:
    data["criteria"][0]["evidence"] = [{"quote": "Trecho", "section_id": "sec_method"}]


def _step(
    *,
    factory: FakeAgentFactory | None = None,
    checkpoints: FakeCheckpoints | None = None,
    context: EvaluationContext | None = None,
) -> tuple[SynthesisStep, FakeAgentFactory, FakeCheckpoints]:
    selected_context = context or _context()
    selected_factory = factory or FakeAgentFactory()
    selected_checkpoints = checkpoints or FakeCheckpoints(_state(selected_context))
    return (
        SynthesisStep(
            context=selected_context,
            slot=EvaluatorSlot.A,
            factory=selected_factory,
            checkpoints=selected_checkpoints,
        ),
        selected_factory,
        selected_checkpoints,
    )


def test_synthesizes_all_pending_criteria_once_and_is_idempotent() -> None:
    context = _context()
    usage = MemoryUsageSink()
    factory = FakeAgentFactory(
        scripts={"synthesizer": [_synthesis_data(context)]}, usage_sink=usage
    )
    step, factory, checkpoints = _step(factory=factory, context=context)

    first = step.execute()
    second = step.execute()

    assert len(factory.calls) == 1
    assert usage.calls[0].model_id == context.evaluator(EvaluatorSlot.A).model.model_id
    assert len(first.criteria) == len(_synthesis_data(context)["criteria"])
    assert first == second == checkpoints.state
    assert checkpoints.writes == 1
    payload = json.loads(factory.calls[0].payload.article or "{}")
    assert {item["key"] for item in payload["criteria"]} == {
        item.criterion_key.value for item in first.criteria
    }
    assert payload["observations"][0]["id"] == "obs-supported"
    assert payload["cross_checks"][0]["id"] == "check-soundness"
    assert factory.calls[0].payload.prompt == "Sintetize os itens e critérios fornecidos."


@pytest.mark.parametrize(
    "mutate",
    [
        _remove_criterion,
        _replace_observation_id,
        _add_direct_evidence,
    ],
)
def test_rejects_incomplete_or_unfounded_synthesis(
    mutate: Callable[[dict[str, list[dict[str, object]]]], None],
) -> None:
    context = _context()
    output = _synthesis_data(context)
    mutate(output)
    factory = FakeAgentFactory(scripts={"synthesizer": [output]})
    step, _, _ = _step(factory=factory, context=context)

    with pytest.raises(InvalidEvaluationOutput):
        step.execute()


def test_rejects_check_reference_for_an_unrelated_criterion() -> None:
    context = _context()
    output = _synthesis_data(context)
    original = output["criteria"]
    target = next(item for item in original if item["criterion_key"] != "soundness")
    target["check_ids"] = ["check-soundness"]
    factory = FakeAgentFactory(scripts={"synthesizer": [output]})
    step, _, _ = _step(factory=factory, context=context)

    with pytest.raises(InvalidEvaluationOutput):
        step.execute()


@pytest.mark.django_db
def test_database_checkpoint_persists_synthesis_and_refuses_stale_owner(run: Run) -> None:
    task_id = "e4-synthesis"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    store = RunSynthesisCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        model_spec=development_spec(Role.EVALUATOR_A),
    )
    context = _context()
    store.store_state(_state(context))
    factory = FakeAgentFactory(scripts={"synthesizer": [_synthesis_data(context)]})
    step = SynthesisStep(
        context=context,
        slot=EvaluatorSlot.A,
        factory=factory,
        checkpoints=store,
    )

    state = step.execute()

    assert len(state.criteria) == len(_synthesis_data(context)["criteria"])
    assert store.read_state() == state
    Run.objects.filter(pk=run.pk).update(current_task_id="nova-tarefa")
    with pytest.raises(RunConflict):
        store.store_state(state)
