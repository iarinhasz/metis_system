"""Síntese do slot: contexto restrito, validação e retomada."""

import json
from collections.abc import Callable

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    CrossCheckResult,
    EvaluatorSlot,
    ItemType,
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


def _replace_observation_id(data: dict[str, list[dict[str, object]]]) -> None:
    data["criteria"][0]["observation_ids"] = ["missing-observation"]


def _add_direct_evidence(data: dict[str, list[dict[str, object]]]) -> None:
    data["criteria"][0]["evidence"] = [{"quote": "Trecho", "section_id": "sec_method"}]


def _cite_unrelated_check(data: dict[str, list[dict[str, object]]]) -> None:
    target = next(item for item in data["criteria"] if item["criterion_key"] != "soundness")
    target["check_ids"] = ["check-soundness"]


def _repeat_and_extra(data: dict[str, list[dict[str, object]]]) -> None:
    """O mesmo critério duas vezes (fica o primeiro)."""
    data["criteria"].append({**data["criteria"][0], "grade": 1})


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


def test_asks_again_only_for_the_missing_criteria() -> None:
    context = _context()
    first = _synthesis_data(context)
    missing = first["criteria"].pop()
    factory = FakeAgentFactory(scripts={"synthesizer": [first, {"criteria": [missing]}]})
    step, factory, checkpoints = _step(factory=factory, context=context)

    state = step.execute()

    assert len(factory.calls) == 2
    retry = json.loads(factory.calls[1].payload.article or "{}")
    assert [item["key"] for item in retry["criteria"]] == [missing["criterion_key"]]
    assert str(missing["criterion_key"]) in factory.calls[1].payload.prompt
    assert {item.criterion_key.value for item in state.criteria} == {
        item["criterion_key"] for item in _synthesis_data(context)["criteria"]
    }
    assert checkpoints.writes == 1


def test_fails_when_a_criterion_is_still_missing_after_the_retry() -> None:
    context = _context()
    output = _synthesis_data(context)
    missing = output["criteria"].pop()["criterion_key"]
    factory = FakeAgentFactory(scripts={"synthesizer": [output, {"criteria": []}]})
    step, _, checkpoints = _step(factory=factory, context=context)

    with pytest.raises(InvalidEvaluationOutput, match=f"não trouxe os critérios: {missing}"):
        step.execute()
    assert checkpoints.writes == 0


@pytest.mark.parametrize(
    "mutate",
    [_replace_observation_id, _add_direct_evidence, _cite_unrelated_check, _repeat_and_extra],
)
def test_cleans_what_real_models_get_slightly_wrong(
    mutate: Callable[[dict[str, list[dict[str, object]]]], None],
) -> None:
    context = _context()
    output = _synthesis_data(context)
    mutate(output)
    factory = FakeAgentFactory(scripts={"synthesizer": [output]})
    step, factory, _ = _step(factory=factory, context=context)

    state = step.execute()

    assert len(factory.calls) == 1
    assert len(state.criteria) == len(_synthesis_data(context)["criteria"])
    for item in state.criteria:
        assert item.evidence == ()
        assert set(item.observation_ids) <= {"obs-supported"}
        assert item.check_ids in ((), ("check-soundness",))
        assert not item.check_ids or item.criterion_key is Criterion.SOUNDNESS


def test_refresh_replaces_only_requested_criterion_and_marks_it_changed() -> None:
    context = _context()
    data = _synthesis_data(context)
    initial = tuple(CriterionSynthesis.model_validate(item) for item in data["criteria"])
    state = _state(context).model_copy(update={"criteria": initial})
    target = next(item for item in data["criteria"] if item["criterion_key"] == "soundness")
    response = {
        "criteria": [
            target
            | {
                "grade": 4,
                "justification": "A síntese atualizada considera a observação corrigida.",
            }
        ]
    }
    factory = FakeAgentFactory(scripts={"synthesizer": [response]})
    checkpoints = FakeCheckpoints(state)
    step, _, _ = _step(factory=factory, checkpoints=checkpoints, context=context)

    updated = step.execute(refresh=(Criterion.SOUNDNESS,), mark_changed=True)

    assert len(factory.calls) == 1
    assert len(updated.criteria) == len(initial)
    assert (
        next(item.grade for item in updated.criteria if item.criterion_key is Criterion.SOUNDNESS)
        == 4
    )
    assert [(item.item_type, item.item_key) for item in updated.changed_items] == [
        (ItemType.CRITERION, Criterion.SOUNDNESS.value)
    ]


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
