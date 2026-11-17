"""Passes por seção: saída tipada, retomada e checkpoint da rodada."""

import json

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    EvaluatorSlot,
    Observation,
    ReviewState,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role, development_spec
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.section_pass import (
    RunReviewCheckpoints,
    SectionPassStep,
    _scoped,
    split_section_text,
)
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.document_map import MapSection


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


def _observation(
    *,
    kind: str = "strength",
    possibly_elsewhere: bool = False,
    quote: str = "O método usa dados públicos.",
) -> dict[str, object]:
    return {
        "id": "obs-1",
        "section_id": "sec_method",
        "role": "method",
        "kind": kind,
        "statement": "A seção descreve o uso dos dados.",
        "evidence": [{"quote": quote, "section_id": "sec_method"}],
        "criteria": ["soundness"],
        "severity": "minor",
        "possibly_elsewhere": possibly_elsewhere,
        "confidence": 0.7,
    }


def _step(
    *,
    factory: FakeAgentFactory | None = None,
    checkpoints: FakeCheckpoints | None = None,
    max_section_chars: int = 24_000,
) -> tuple[SectionPassStep, FakeAgentFactory, FakeCheckpoints]:
    selected_factory = factory or FakeAgentFactory()
    selected_checkpoints = checkpoints or FakeCheckpoints()
    return (
        SectionPassStep(
            context=_context(),
            slot=EvaluatorSlot.A,
            factory=selected_factory,
            checkpoints=selected_checkpoints,
            max_workers=2,
            max_section_chars=max_section_chars,
        ),
        selected_factory,
        selected_checkpoints,
    )


def test_section_pass_uses_snapshot_role_schema_and_rubric_context() -> None:
    factory = FakeAgentFactory(
        scripts={
            "sections/method": [
                {
                    "section_id": "sec_method",
                    "observations": [_observation()],
                }
            ]
        }
    )
    step, factory, checkpoints = _step(factory=factory)

    state = step.execute()

    assert len(factory.calls) == 1
    assert factory.calls[0].name == "sections/method"
    assert factory.calls[0].payload.article == "O método usa dados públicos."
    payload = json.loads(factory.calls[0].payload.prompt)
    assert payload["target_section"] == {
        "id": "sec_method",
        "title": "Método",
        "role": "method",
        "part": 1,
        "parts": 1,
    }
    criteria = {item["key"]: item for item in payload["criteria"]}
    assert criteria["soundness"]["question"]
    assert criteria["soundness"]["rubric_text"] is None
    assert state.observations[0].id == "sec_method:method:1:obs-1"
    assert state.observations[0].criteria == (Criterion.SOUNDNESS,)
    assert checkpoints.state == state and checkpoints.writes == 1


def test_section_pass_is_idempotent_and_keeps_uncertain_missing_marker() -> None:
    factory = FakeAgentFactory(
        scripts={
            "sections/method": [
                {
                    "section_id": "sec_method",
                    "observations": [_observation(kind="missing", possibly_elsewhere=True)],
                }
            ]
        }
    )
    step, factory, checkpoints = _step(factory=factory)

    first = step.execute()
    second = step.execute()

    assert len(factory.calls) == 1
    assert first == second == checkpoints.state
    assert checkpoints.writes == 1
    assert first.observations[0].kind == "missing"
    assert first.observations[0].possibly_elsewhere is True


def test_other_sections_do_not_call_an_evaluator() -> None:
    context = _context()
    context = context.model_copy(
        update={
            "document_map": context.document_map.model_copy(
                update={
                    "sections": (
                        MapSection(
                            id="sec_method",
                            title="Método",
                            roles=(SectionRole.OTHER,),
                            first_sentence="O método usa dados públicos.",
                        ),
                    )
                }
            )
        }
    )
    factory = FakeAgentFactory()
    checkpoints = FakeCheckpoints()
    step = SectionPassStep(
        context=context,
        slot=EvaluatorSlot.A,
        factory=factory,
        checkpoints=checkpoints,
        max_workers=1,
    )

    state = step.execute()

    assert state == ReviewState() and factory.calls == [] and checkpoints.writes == 0


def test_long_sections_split_contiguously_and_preserve_all_text() -> None:
    text = "parágrafo um\n\nparágrafo dois muito maior\n\nparágrafo três"

    chunks = split_section_text(text, max_chars=20)

    assert len(chunks) > 1
    assert "".join(chunks) == text
    assert all(len(chunk) <= 20 for chunk in chunks)


def test_long_section_prefers_last_paragraph_boundary_before_words() -> None:
    text = "curto texto\n\num parágrafo bem maior que continua"

    chunks = split_section_text(text, max_chars=30)

    assert chunks[0] == "curto texto"
    assert "".join(chunks) == text
    assert all(len(chunk) <= 30 for chunk in chunks)


def test_oversized_paragraph_falls_back_to_word_and_character_boundaries() -> None:
    text = "palavra longa" * 5

    chunks = split_section_text(text, max_chars=12)

    assert len(chunks) > 1
    assert "".join(chunks) == text
    assert all(len(chunk) <= 12 for chunk in chunks)


@pytest.mark.django_db
def test_database_checkpoint_persists_round_and_refuses_stale_owner(run: Run) -> None:
    task_id = "e4-section-pass"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    store = RunReviewCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        model_spec=development_spec(Role.EVALUATOR_A),
    )
    observation = Observation.model_validate(_observation())
    state = ReviewState(observations=(observation,))

    assert store.read_state() == ReviewState()
    store.store_state(state)
    assert store.read_state() == state

    Run.objects.filter(pk=run.pk).update(current_task_id="replacement-task")
    with pytest.raises(RunConflict, match="perdeu a posse"):
        store.read_state()


def _raw_observation(**changes: object) -> Observation:
    return Observation.model_validate(
        {
            "id": "o1",
            "section_id": "sec_9",
            "role": "results",
            "kind": "weakness",
            "statement": "O método não diz como os dados foram escolhidos.",
            "criteria": ["soundness", "impact"],
            "severity": "minor",
            "confidence": 0.7,
        }
        | changes
    )


def test_observation_is_scoped_to_the_requested_section_role_and_criteria() -> None:
    criteria: list[dict[str, object]] = [{"key": "soundness"}, {"key": "replicability"}]

    scoped = _scoped(_raw_observation(), "sec_3", SectionRole.METHOD, criteria, "1")

    assert scoped is not None
    assert (scoped.id, scoped.section_id, scoped.role) == (
        "sec_3:method:1:o1",
        "sec_3",
        SectionRole.METHOD,
    )
    assert scoped.criteria == (Criterion.SOUNDNESS,)


def test_observation_without_any_requested_criterion_is_dropped() -> None:
    criteria: list[dict[str, object]] = [{"key": "clarity"}]

    assert _scoped(_raw_observation(), "sec_3", SectionRole.METHOD, criteria, "1") is None
