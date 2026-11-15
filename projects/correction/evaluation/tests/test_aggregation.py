from decimal import Decimal

import pytest

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import EvaluatorSlot, ItemRef, ItemType
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.evaluation.aggregation import aggregate
from projects.correction.evaluation.contracts import Recommendation
from projects.correction.evaluation.tests.helpers import review
from projects.correction.questions.criteria import STANDARD


def test_median_resists_an_outlier_and_agreement_records_dispersion() -> None:
    result = aggregate(
        tuple(review(slot, grade) for slot, grade in zip(EvaluatorSlot, (4, 4, 1), strict=True)),
        STANDARD,
        PaperType.EMPIRICAL,
    )
    assert result.total_score == 4 and result.recommendation == Recommendation.ACCEPT
    assert result.criteria[0].dispersion == 3 and result.agreement == Decimal("0.25")


def test_weighted_total_uses_weights_and_keeps_precision_before_recommendation() -> None:
    config = STANDARD.model_copy(
        update={
            "criteria": tuple(
                item.model_copy(
                    update={
                        "weight": 2
                        if item.key == Criterion.ORIGINALITY
                        else 1
                        if item.key == Criterion.SOUNDNESS
                        else 0
                    }
                )
                for item in STANDARD.criteria
            )
        }
    )
    reviews = tuple(
        review(slot, grade) for slot, grade in zip(EvaluatorSlot, (1, 3, 5), strict=True)
    )
    changed = tuple(
        data.model_copy(
            update={
                "state": data.state.model_copy(
                    update={
                        "criteria": tuple(
                            item.model_copy(update={"grade": 4})
                            if item.criterion_key == Criterion.ORIGINALITY
                            else item
                            for item in data.state.criteria
                        )
                    }
                )
            }
        )
        for data in reviews
    )
    result = aggregate(changed, config, PaperType.EMPIRICAL)
    assert result.total_score == Decimal(11) / 3 and result.recommendation == "minor"


def test_unresolved_observation_excludes_dependent_grades_even_if_criterion_verdict_is_valid() -> (
    None
):
    reviews = tuple(review(slot) for slot in EvaluatorSlot)
    pending = reviews[0].model_copy(
        update={
            "state": reviews[0].state.model_copy(
                update={"unresolved": (ItemRef(item_type=ItemType.OBSERVATION, item_key="obs-1"),)}
            )
        }
    )
    result = aggregate((pending, *reviews[1:]), STANDARD, PaperType.EMPIRICAL)
    assert all(
        len(item.votes) == 2 and item.excluded[0].reason == "evidence_not_validated"
        for item in result.criteria
    )


def test_two_valid_votes_use_mean_and_unresolved_vote_is_excluded() -> None:
    result = aggregate(
        (
            review(EvaluatorSlot.A, 2),
            review(EvaluatorSlot.B, 5),
            review(EvaluatorSlot.C, 1, unresolved=True),
        ),
        STANDARD,
        PaperType.EMPIRICAL,
    )
    soundness = next(item for item in result.criteria if item.criterion_key == Criterion.SOUNDNESS)
    assert soundness.grade == Decimal("3.5") and len(soundness.votes) == 2
    assert soundness.unresolved and result.needs_human_review


def test_no_valid_grades_are_not_fabricated_as_zero_and_weights_are_renormalized() -> None:
    reviews = tuple(review(slot, 4, unresolved=True) for slot in EvaluatorSlot)
    result = aggregate(reviews, STANDARD, PaperType.EMPIRICAL)
    soundness = next(item for item in result.criteria if item.criterion_key == Criterion.SOUNDNESS)
    assert soundness.grade is None and result.total_score == 4
    all_pending = tuple(
        data.model_copy(
            update={
                "state": data.state.model_copy(
                    update={
                        "unresolved": tuple(
                            ItemRef(item_type=ItemType.CRITERION, item_key=key) for key in Criterion
                        )
                    }
                )
            }
        )
        for data in reviews
    )
    empty = aggregate(all_pending, STANDARD, PaperType.EMPIRICAL)
    assert empty.total_score is None and empty.agreement is None and empty.recommendation is None


def test_theoretical_papers_omit_inactive_replicability_and_require_three_distinct_slots() -> None:
    reviews = tuple(review(slot) for slot in EvaluatorSlot)
    result = aggregate(reviews, STANDARD, PaperType.THEORETICAL)
    assert Criterion.REPLICABILITY not in {score.criterion_key for score in result.criteria}
    with pytest.raises(ValueError):
        aggregate((reviews[0], reviews[0], reviews[1]), STANDARD, PaperType.EMPIRICAL)
