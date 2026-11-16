"""Revisão parcial e limite de pendências, sem chamadas a provedores reais."""

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    CrossCheckResult,
    EvaluationMode,
    EvaluatorSlot,
    Evidence,
    Issue,
    ItemRef,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role, development_spec
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.revision import (
    MarkUnresolvedStep,
    RevisionStep,
    RunRevisionCheckpoints,
    has_pending_items,
    no_pending_items,
)
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.pipeline.errors import InvalidEvaluationOutput


def _context() -> EvaluationContext:
    return EvaluationContextBuilder(_context_run()).build()


def _state() -> ReviewState:
    observation = Observation(
        id="obs-method",
        section_id="sec_method",
        role=SectionRole.METHOD,
        kind="strength",
        statement="O método usa dados públicos.",
        evidence=(Evidence(quote="O método usa dados públicos.", section_id="sec_method"),),
        criteria=(Criterion.SOUNDNESS,),
        severity="minor",
        confidence=0.8,
    )
    check = CrossCheckResult(
        id="check-independent",
        kind="method_vs_question",
        verdict="consistent",
        criteria=(Criterion.REPLICABILITY,),
        severity="minor",
    )
    synthesis = CriterionSynthesis(
        criterion_key=Criterion.SOUNDNESS,
        grade=3,
        justification="O método descreve a origem dos dados.",
        observation_ids=(observation.id,),
        confidence=0.8,
    )
    return ReviewState(
        observations=(observation,),
        cross_checks=(check,),
        criteria=(synthesis,),
    )


def _previous_verdicts() -> dict[tuple[ItemType, str], ItemVerdict]:
    return {
        (ItemType.OBSERVATION, "obs-method"): ItemVerdict(
            item_type=ItemType.OBSERVATION,
            item_key="obs-method",
            verdict=Verdict.INVALID,
            issues=(
                Issue(
                    category="ungrounded",
                    excerpt="O método usa dados públicos.",
                    reason="A observação precisa ser reformulada à luz da seção.",
                ),
            ),
        ),
        (ItemType.CRITERION, Criterion.SOUNDNESS.value): ItemVerdict(
            item_type=ItemType.CRITERION,
            item_key=Criterion.SOUNDNESS.value,
            verdict=Verdict.VALID,
        ),
        (ItemType.CHECK, "check-independent"): ItemVerdict(
            item_type=ItemType.CHECK,
            item_key="check-independent",
            verdict=Verdict.VALID,
        ),
    }


def _accepted_observation() -> dict[str, object]:
    return {
        "item_type": "observation",
        "item_key": "obs-method",
        "action": "accept",
        "justification": "Reformulei a afirmação para corresponder à seção.",
        "replacement": {
            **_state().observations[0].model_dump(mode="json"),
            "kind": "weakness",
            "statement": "O artigo não detalha como os dados públicos foram selecionados.",
        },
    }


class FakeCheckpoints:
    run_id = "fake-run"
    task_id = "fake-task"

    def __init__(
        self,
        *,
        round_number: int = 2,
        state: ReviewState | None = None,
        verdicts: dict[tuple[ItemType, str], ItemVerdict] | None = None,
    ) -> None:
        self.round_number = round_number
        self.previous_state = _state()
        self.previous_verdicts = _previous_verdicts()
        self.current_state = state
        self.current_verdicts = verdicts or {}
        self.writes = 0
        self.copied: set[tuple[ItemType, str]] = set()

    def assert_owned(self) -> None:
        return None

    def read_previous_state(self) -> ReviewState:
        return self.previous_state

    def read_previous_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        return self.previous_verdicts

    def read_current_state(self) -> ReviewState | None:
        return self.current_state

    def read_current_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        return self.current_verdicts

    def store_current_state(self, state: ReviewState) -> None:
        self.current_state = state
        self.writes += 1

    def carry_forward_valid_verdicts(self, *, excluded: set[tuple[ItemType, str]]) -> None:
        for key, verdict in self.previous_verdicts.items():
            if verdict.verdict is Verdict.VALID and key not in excluded:
                self.current_verdicts[key] = verdict
                self.copied.add(key)

    def mark_unresolved(self, items: tuple[ItemRef, ...]) -> ReviewState:
        assert self.current_state is not None
        existing = {(item.item_type, item.item_key): item for item in self.current_state.unresolved}
        existing.update({(item.item_type, item.item_key): item for item in items})
        self.current_state = self.current_state.model_copy(
            update={"unresolved": tuple(existing.values())}
        )
        return self.current_state


class FakeSynthesisRefresher:
    def __init__(self, checkpoints: FakeCheckpoints | RunRevisionCheckpoints) -> None:
        self.checkpoints = checkpoints
        self.calls: list[tuple[Criterion, ...]] = []

    def refresh(self, criteria: tuple[Criterion, ...]) -> ReviewState:
        self.calls.append(criteria)
        state = self.checkpoints.read_current_state()
        assert state is not None
        updated = tuple(
            item.model_copy(
                update={
                    "grade": 4,
                    "justification": "A versão revisada usa a evidência corrigida.",
                }
            )
            if item.criterion_key in criteria
            else item
            for item in state.criteria
        )
        changed = {(item.item_type, item.item_key): item for item in state.changed_items}
        changed.update(
            {
                (ItemType.CRITERION, criterion.value): ItemRef(
                    item_type=ItemType.CRITERION,
                    item_key=criterion.value,
                )
                for criterion in criteria
            }
        )
        state = state.model_copy(
            update={"criteria": updated, "changed_items": tuple(changed.values())}
        )
        self.checkpoints.store_current_state(state)
        return state


def _step(
    response: object,
    checkpoints: FakeCheckpoints | None = None,
) -> tuple[RevisionStep, FakeCheckpoints, FakeAgentFactory, FakeSynthesisRefresher]:
    store = checkpoints or FakeCheckpoints()
    factory = FakeAgentFactory(scripts={"reviser": [response]})
    refresher = FakeSynthesisRefresher(store)
    return (
        RevisionStep(
            _context(),
            EvaluatorSlot.A,
            factory,
            store,
            synthesis_refresher=refresher,
        ),
        store,
        factory,
        refresher,
    )


def test_accept_updates_one_item_refreshes_only_its_synthesis_and_carries_forward() -> None:
    step, checkpoints, factory, refresher = _step(_accepted_observation())

    state = step.execute()

    assert len(factory.calls) == 1
    assert factory.calls[0].name == "reviser"
    assert "sec_method" in (factory.calls[0].payload.article or "")
    assert state.observations[0].kind == "weakness"
    assert state.criteria[0].grade == 4
    assert refresher.calls == [(Criterion.SOUNDNESS,)]
    assert checkpoints.copied == {(ItemType.CHECK, "check-independent")}
    assert (ItemType.OBSERVATION, "obs-method") in {
        (item.item_type, item.item_key) for item in state.changed_items
    }


def test_rebut_preserves_item_and_attaches_grounded_evidence() -> None:
    response = {
        "item_type": "observation",
        "item_key": "obs-method",
        "action": "rebut",
        "justification": "A seção confirma a afirmação original.",
        "evidence": [{"quote": "dados públicos", "section_id": "sec_method"}],
    }
    step, _, _, refresher = _step(response)

    state = step.execute()

    assert state.observations[0].statement == _state().observations[0].statement
    assert state.observations[0].evidence[-1].quote == "dados públicos"
    assert state.revisions[0].action == "rebut"
    assert refresher.calls == [(Criterion.SOUNDNESS,)]


def test_rebut_rejects_evidence_not_in_document() -> None:
    response = {
        "item_type": "observation",
        "item_key": "obs-method",
        "action": "rebut",
        "justification": "A afirmação está correta.",
        "evidence": [{"quote": "trecho inventado", "section_id": "sec_method"}],
    }
    step, checkpoints, _, _ = _step(response)

    with pytest.raises(InvalidEvaluationOutput, match="não foi localizada"):
        step.execute()

    assert checkpoints.current_state is not None
    assert checkpoints.current_state.revisions == ()
    assert checkpoints.current_state.observations == _state().observations


def test_revision_is_idempotent_after_checkpoint_and_does_not_copy_changed_votes() -> None:
    response = _accepted_observation()
    step, checkpoints, factory, refresher = _step(response)

    first = step.execute()
    second = step.execute()

    assert first == second
    assert len(factory.calls) == 1
    assert refresher.calls == [(Criterion.SOUNDNESS,)]
    assert checkpoints.copied == {(ItemType.CHECK, "check-independent")}


def test_pending_items_and_unresolved_marking_observe_checkpoint_state() -> None:
    state = _state()
    rejected = _previous_verdicts()[(ItemType.OBSERVATION, "obs-method")]
    checkpoints = FakeCheckpoints(
        round_number=3,
        state=state,
        verdicts={(ItemType.OBSERVATION, "obs-method"): rejected},
    )

    assert has_pending_items(checkpoints)
    assert not no_pending_items(checkpoints)
    unresolved = MarkUnresolvedStep(checkpoints, max_revisions=2).execute()

    assert unresolved == (ItemRef(item_type=ItemType.OBSERVATION, item_key="obs-method"),)
    assert not has_pending_items(checkpoints)


def test_mark_unresolved_leaves_a_clean_first_round_unchanged() -> None:
    checkpoints = FakeCheckpoints(round_number=1, state=_state(), verdicts={})

    assert MarkUnresolvedStep(checkpoints, max_revisions=2).execute() == ()
    assert checkpoints.current_state is not None
    assert checkpoints.current_state.unresolved == ()


def test_revision_step_rejects_wrong_target_and_missing_replacement() -> None:
    mismatched = _accepted_observation() | {"item_key": "other"}
    step, _, _, _ = _step(mismatched)
    with pytest.raises(InvalidEvaluationOutput, match="cita outro item"):
        step.execute()

    missing_replacement = _accepted_observation() | {"replacement": None}
    step, _, _, _ = _step(missing_replacement)
    with pytest.raises(InvalidEvaluationOutput, match="precisa trazer o item corrigido"):
        step.execute()


@pytest.mark.django_db
def test_database_revision_round_copies_only_unchanged_valid_verdicts(run: Run) -> None:
    task_id = "e4-revision"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    context = _context()
    previous = ReviewRound.store(
        run.pk,
        task_id,
        slot=EvaluatorSlot.A,
        round_number=1,
        mode=EvaluationMode.SECTIONED,
        model_spec=development_spec(Role.EVALUATOR_A),
        state=_state(),
    )
    JudgeVerdict.record(
        previous.pk,
        task_id,
        item=_previous_verdicts()[(ItemType.OBSERVATION, "obs-method")],
        source=VerdictSource.VALIDATOR,
    )
    for key in (Criterion.SOUNDNESS.value, "check-independent"):
        item_type = ItemType.CRITERION if key == Criterion.SOUNDNESS.value else ItemType.CHECK
        JudgeVerdict.record(
            previous.pk,
            task_id,
            item=ItemVerdict(item_type=item_type, item_key=key, verdict=Verdict.VALID),
            source=VerdictSource.VALIDATOR,
        )
    checkpoints = RunRevisionCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        mode=EvaluationMode.SECTIONED,
        model_spec=development_spec(Role.EVALUATOR_A),
        round_number=2,
    )
    factory = FakeAgentFactory(scripts={"reviser": [_accepted_observation()]})
    refresher = FakeSynthesisRefresher(checkpoints)

    state = RevisionStep(
        context,
        EvaluatorSlot.A,
        factory,
        checkpoints,
        synthesis_refresher=refresher,
    ).execute()
    current = ReviewRound.objects.get(
        run=run,
        evaluator_slot=EvaluatorSlot.A,
        round_number=2,
    )

    assert state.observations[0].kind == "weakness"
    assert set(current.verdicts.values_list("item_type", "item_key")) == {
        (ItemType.CHECK, "check-independent")
    }
    assert factory.calls and current.verdicts.get().source == VerdictSource.VALIDATOR


@pytest.mark.django_db
def test_database_marks_only_invalid_items_unresolved_after_limit(run: Run) -> None:
    task_id = "e4-unresolved"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    context = _context()
    review = ReviewRound.store(
        run.pk,
        task_id,
        slot=EvaluatorSlot.A,
        round_number=3,
        mode=EvaluationMode.SECTIONED,
        model_spec=development_spec(Role.EVALUATOR_A),
        state=_state(),
    )
    rejected = _previous_verdicts()[(ItemType.OBSERVATION, "obs-method")]
    JudgeVerdict.record(review.pk, task_id, item=rejected, source=VerdictSource.VALIDATOR)
    checkpoints = RunRevisionCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        mode=EvaluationMode.SECTIONED,
        model_spec=context.evaluator(EvaluatorSlot.A).model,
        round_number=3,
    )

    unresolved = MarkUnresolvedStep(checkpoints, max_revisions=2).execute()

    assert unresolved == (ItemRef(item_type=ItemType.OBSERVATION, item_key="obs-method"),)
    assert ReviewRound.objects.get(pk=review.pk).state.unresolved == unresolved
