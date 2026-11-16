"""Validadores determinísticos de estado: evidência, escala e referências."""

import pytest

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CrossCheckResult,
    EvaluationMode,
    EvaluatorSlot,
    Evidence,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    RevisionResponse,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role, development_spec
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.evaluation.validators import (
    RunValidationCheckpoints,
    ValidateStep,
    ValidatorChain,
    normalize_quote,
)
from projects.correction.pipeline.errors import InvalidEvaluationOutput


def _context(mode: EvaluationMode = EvaluationMode.SECTIONED) -> EvaluationContext:
    run = _context_run()
    run.config_snapshot["evaluation_mode"] = mode.value
    return EvaluationContextBuilder(run).build()


def _state(context: EvaluationContext) -> ReviewState:
    active = next(
        paper
        for paper in context.evaluation_config.paper_types
        if paper.paper_type is context.profile.paper_type
    ).active
    observation = Observation(
        id="obs-supported",
        section_id="sec_method",
        role=SectionRole.METHOD,
        kind="strength",
        statement="O método descreve os dados utilizados.",
        evidence=(Evidence(quote="O método usa dados públicos.", section_id="sec_method"),),
        criteria=active,
        severity="minor",
        confidence=0.8,
    )
    check = CrossCheckResult(
        id="check-soundness",
        kind="method_vs_question",
        verdict="consistent",
        evidence=(Evidence(quote="O método usa dados públicos.", section_id="sec_method"),),
        criteria=(Criterion.SOUNDNESS,),
        severity="minor",
    )
    criteria = tuple(
        {
            "criterion_key": key,
            "grade": 3,
            "justification": f"A evidência descreve o critério {key.value}.",
            "observation_ids": (observation.id,)
            if context.evaluation_mode is EvaluationMode.SECTIONED
            else (),
            "check_ids": (
                (check.id,)
                if key is Criterion.SOUNDNESS
                and context.evaluation_mode is EvaluationMode.SECTIONED
                else ()
            ),
            "evidence": (
                (Evidence(quote="O método usa dados públicos.", section_id="sec_method"),)
                if context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT
                else ()
            ),
            "confidence": 0.75,
        }
        for key in active
    )
    from projects.correction.agents.schemas.evaluation import CriterionSynthesis

    return ReviewState(
        observations=(observation,) if context.evaluation_mode is EvaluationMode.SECTIONED else (),
        cross_checks=(check,) if context.evaluation_mode is EvaluationMode.SECTIONED else (),
        criteria=tuple(CriterionSynthesis.model_validate(item) for item in criteria),
    )


class FakeCheckpoints:
    def __init__(self, state: object) -> None:
        self.state = state
        self.verdicts: dict[tuple[ItemType, str], ItemVerdict] = {}
        self.writes = 0

    def assert_owned(self) -> None:
        return None

    def read_state(self) -> object:
        return self.state

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        return self.verdicts

    def record(self, item: ItemVerdict) -> None:
        self.verdicts[(item.item_type, item.item_key)] = item
        self.writes += 1


def test_valid_sectioned_and_whole_document_outputs() -> None:
    for mode in EvaluationMode:
        context = _context(mode)
        assert ValidatorChain(context).validate(_state(context)) == ()


def test_quote_with_line_wrap_hyphenation_matches() -> None:
    context = _context()
    section = context.article.sections[-1].model_copy(
        update={"text": "O método usa dados públi-\ncos."}
    )
    article = context.article.model_copy(
        update={"sections": (*context.article.sections[:-1], section)}
    )
    wrapped_context = context.model_copy(update={"article": article})

    assert normalize_quote("públi-\ncos") == normalize_quote("públicos")
    assert ValidatorChain(wrapped_context).validate(_state(context)) == ()


def test_fabricated_quote_is_invalidated_against_its_section() -> None:
    context = _context()
    state = _state(context)
    observation = state.observations[0].model_copy(
        update={"evidence": (Evidence(quote="Trecho inventado.", section_id="sec_method"),)}
    )
    candidate = state.model_copy(update={"observations": (observation,)})

    [invalid] = ValidatorChain(context).validate(candidate)

    assert invalid.item_type is ItemType.OBSERVATION
    assert invalid.item_key == "obs-supported" and invalid.verdict is Verdict.INVALID
    assert invalid.issues[0].category == "ungrounded"


def test_fabricated_rebuttal_evidence_is_invalidated() -> None:
    context = _context()
    state = _state(context)
    response = RevisionResponse(
        item_type=ItemType.OBSERVATION,
        item_key=state.observations[0].id,
        action="rebut",
        justification="A observação continua correta.",
        evidence=(Evidence(quote="Trecho novo inventado.", section_id="sec_method"),),
    )

    [invalid] = ValidatorChain(context).validate(
        state.model_copy(update={"revisions": (response,)})
    )

    assert invalid.item_type is ItemType.OBSERVATION
    assert invalid.item_key == state.observations[0].id
    assert invalid.issues[0].category == "ungrounded"


def test_invalid_grade_and_broken_internal_reference_are_flagged() -> None:
    context = _context()
    configs = tuple(
        item.model_copy(update={"grades": (1,)}) if item.key is Criterion.SOUNDNESS else item
        for item in context.evaluation_config.criteria
    )
    config = context.evaluation_config.model_copy(update={"criteria": configs})
    context = context.model_copy(update={"evaluation_config": config})
    state = _state(context)
    criterion = next(item for item in state.criteria if item.criterion_key is Criterion.SOUNDNESS)
    invalid_criterion = criterion.model_copy(update={"observation_ids": ("missing-observation",)})
    criteria = tuple(
        invalid_criterion if item.criterion_key is Criterion.SOUNDNESS else item
        for item in state.criteria
    )
    candidate = state.model_copy(update={"criteria": criteria})
    candidate_criterion = next(
        item for item in candidate.criteria if item.criterion_key is Criterion.SOUNDNESS
    )
    candidate = candidate.model_copy(
        update={
            "criteria": tuple(
                candidate_criterion.model_copy(update={"grade": 3})
                if item.criterion_key is Criterion.SOUNDNESS
                else item
                for item in candidate.criteria
            )
        }
    )

    invalid = ValidatorChain(context).validate(candidate)

    assert {issue.category for item in invalid for issue in item.issues} == {
        "rubric_mismatch",
        "ungrounded",
    }
    assert {item.item_key for item in invalid} == {Criterion.SOUNDNESS.value}


def test_repeated_criterion_question_is_invalid() -> None:
    context = _context()
    state = _state(context)
    question = next(
        item.question
        for item in context.evaluation_config.criteria
        if item.key is Criterion.SOUNDNESS
    )
    criteria = tuple(
        item.model_copy(update={"justification": question})
        if item.criterion_key is Criterion.SOUNDNESS
        else item
        for item in state.criteria
    )

    [invalid] = ValidatorChain(context).validate(state.model_copy(update={"criteria": criteria}))

    assert invalid.item_type is ItemType.CRITERION
    assert invalid.item_key == Criterion.SOUNDNESS.value
    assert invalid.issues[0].category == "rubric_mismatch"


def test_schema_errors_and_missing_criteria_stop_validation() -> None:
    context = _context()
    with pytest.raises(InvalidEvaluationOutput, match="schema E4"):
        ValidatorChain(context).validate({"observations": "inválido"})

    state = _state(context)
    with pytest.raises(InvalidEvaluationOutput, match="Faltam sínteses"):
        ValidatorChain(context).validate(state.model_copy(update={"criteria": state.criteria[:-1]}))


def test_validate_step_records_invalid_items_once() -> None:
    context = _context()
    state = _state(context)
    observation = state.observations[0].model_copy(
        update={"evidence": (Evidence(quote="Trecho inventado.", section_id="sec_method"),)}
    )
    checkpoints = FakeCheckpoints(state.model_copy(update={"observations": (observation,)}))
    step = ValidateStep(context, checkpoints)

    first = step.execute()
    second = step.execute()

    assert len(first) == 1 and second == ()
    assert first[0].item_key == observation.id
    assert checkpoints.writes == 1


@pytest.mark.django_db
def test_validate_step_persists_auditable_validator_verdict(run: Run) -> None:
    task_id = "e4-validator"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    context = _context()
    state = _state(context)
    observation = state.observations[0].model_copy(
        update={"evidence": (Evidence(quote="Trecho inventado.", section_id="sec_method"),)}
    )
    state = state.model_copy(update={"observations": (observation,)})
    review = ReviewRound.store(
        run.pk,
        task_id,
        slot=EvaluatorSlot.A,
        round_number=1,
        mode=EvaluationMode.SECTIONED,
        model_spec=development_spec(Role.EVALUATOR_A),
        state=state,
    )
    step = ValidateStep(
        context,
        RunValidationCheckpoints(
            run_id=str(run.pk),
            task_id=task_id,
            slot=EvaluatorSlot.A,
            mode=EvaluationMode.SECTIONED,
        ),
    )

    [invalid] = step.execute()
    [stored] = JudgeVerdict.objects.filter(round=review)

    assert invalid.item_key == observation.id
    assert stored.source == VerdictSource.VALIDATOR
    assert stored.item.verdict is Verdict.INVALID
