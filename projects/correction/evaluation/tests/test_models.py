import pytest
from pydantic import ValidationError

from projects.correction.agents.schemas.evaluation import (
    EvaluatorSlot,
    ItemType,
    ItemVerdict,
    Verdict,
    VerdictSource,
)
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import STAGES, Stage
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.tests.helpers import record_review, review
from projects.correction.queries.attempts.run import RunConflict

pytestmark = pytest.mark.django_db


def evaluating(run: Run) -> None:
    for spec in STAGES[:4]:
        Run.claim_stage(run.pk, spec.stage, "e4")
        if spec.stage == Stage.EVALUATION:
            break
        Run.complete_stage(run.pk, "e4", spec.completed)


def test_grade_outside_discrete_scale_is_rejected() -> None:
    with pytest.raises(ValidationError):
        review(EvaluatorSlot.A, 6)


def test_persisted_criterion_obeys_the_method_snapshot_scale(run: Run) -> None:
    from django.core.exceptions import ValidationError as ModelError

    from projects.correction.questions.criteria import STANDARD

    config = STANDARD.model_dump(mode="json")
    config["criteria"][0]["grades"] = [1, 2]
    narrowed = Run.create(attempt=run.attempt, config_snapshot={"evaluation_config": config})
    evaluating(narrowed)
    data = review(EvaluatorSlot.A, 4)
    with pytest.raises(ModelError, match="escala"):
        ReviewRound.store(
            narrowed.pk,
            "e4",
            slot=data.slot,
            round_number=1,
            mode=data.mode,
            model_spec=data.model_spec,
            state=data.state,
        )


def test_round_is_unique_and_only_latest_complete_round_can_feed_e5(run: Run) -> None:
    evaluating(run)
    data = review(EvaluatorSlot.A)
    for _ in range(2):
        row = ReviewRound.store(
            run.pk,
            "e4",
            slot=data.slot,
            round_number=1,
            mode=data.mode,
            model_spec=data.model_spec,
            state=data.state,
        )
    with pytest.raises(RunConflict, match="Todos"):
        ReviewRound.finalize(row.pk, "e4")
    for slot in EvaluatorSlot:
        record_review(run, review(slot))
    assert len(ReviewRound.latest_for_consolidation(run.pk)) == 3
    latest = ReviewRound.store(
        run.pk,
        "e4",
        slot=data.slot,
        round_number=2,
        mode=data.mode,
        model_spec=data.model_spec,
        state=data.state,
    )
    assert latest.round_number == 2 and ReviewRound.latest_for_consolidation(run.pk) == ()
    with pytest.raises(RunConflict, match="imutável"):
        ReviewRound.store(
            run.pk,
            "e4",
            slot=data.slot,
            round_number=1,
            mode=data.mode,
            model_spec=data.model_spec,
            state=data.state,
        )


def test_unknown_items_stale_tasks_and_unfinished_verdicts_are_rejected(run: Run) -> None:
    evaluating(run)
    data = review(EvaluatorSlot.A)
    with pytest.raises(RunConflict, match="posse"):
        ReviewRound.store(
            run.pk,
            "stale",
            slot=data.slot,
            round_number=1,
            mode=data.mode,
            model_spec=data.model_spec,
            state=data.state,
        )
    row = ReviewRound.store(
        run.pk,
        "e4",
        slot=data.slot,
        round_number=1,
        mode=data.mode,
        model_spec=data.model_spec,
        state=data.state,
    )
    with pytest.raises(RunConflict, match="não pertence"):
        JudgeVerdict.record(
            row.pk,
            "e4",
            item=ItemVerdict(
                item_type=ItemType.OBSERVATION, item_key="missing", verdict=Verdict.VALID
            ),
            source=VerdictSource.VALIDATOR,
        )
    item = data.verdicts[0]
    first = JudgeVerdict.record(row.pk, "e4", item=item, source=VerdictSource.VALIDATOR)
    assert (
        JudgeVerdict.record(row.pk, "e4", item=item, source=VerdictSource.VALIDATOR).pk == first.pk
    )
    with pytest.raises(RunConflict, match="imutável"):
        JudgeVerdict.record(
            row.pk,
            "e4",
            item=item.model_copy(update={"verdict": Verdict.INVALID}),
            source=VerdictSource.VALIDATOR,
        )
