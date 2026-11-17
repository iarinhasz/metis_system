"""Agregação determinística das últimas rodadas, sem participação do meta-revisor."""

from decimal import Decimal
from statistics import median

from projects.correction.agents.schemas.evaluation import EvaluatorSlot, ItemType, Verdict
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.evaluation.contracts import (
    Aggregation,
    AggregationPolicy,
    CriterionScore,
    ExcludedVote,
    Recommendation,
    ReviewedSlot,
    Vote,
    item_id,
)
from projects.correction.questions.criteria import EvaluationConfig


def aggregate(
    reviews: tuple[ReviewedSlot, ...],
    config: EvaluationConfig,
    paper_type: PaperType,
    *,
    policy: AggregationPolicy | None = None,
) -> Aggregation:
    policy = policy or AggregationPolicy()
    if len(reviews) != 3 or {review.slot for review in reviews} != set(EvaluatorSlot):
        raise ValueError("A consolidação precisa das últimas rodadas dos três slots.")
    active = next(paper.active for paper in config.paper_types if paper.paper_type == paper_type)
    scores = []
    for definition in config.criteria:
        if definition.key not in active:
            continue
        votes = []
        excluded = []
        for review in sorted(reviews, key=lambda item: item.slot):
            state = review.state
            unresolved = {(item.item_type, item.item_key) for item in state.unresolved}
            verdicts = {(item.item_type, item.item_key): item.verdict for item in review.verdicts}
            synthesis = next(
                (item for item in state.criteria if item.criterion_key == definition.key), None
            )
            key = (ItemType.CRITERION, definition.key)
            reason = ""
            if key in unresolved:
                reason = "unresolved"
            elif synthesis is None:
                reason = "missing"
            elif verdicts.get(key) != Verdict.VALID:
                reason = "not_validated"
            elif synthesis.grade not in definition.grades:
                reason = "grade_not_allowed"
            refs = (
                [(ItemType.OBSERVATION, value) for value in synthesis.observation_ids]
                + [(ItemType.CHECK, value) for value in synthesis.check_ids]
                if synthesis
                else []
            )
            if not reason and any(
                ref in unresolved or verdicts.get(ref) != Verdict.VALID for ref in refs
            ):
                reason = "evidence_not_validated"
            if reason:
                excluded.append(ExcludedVote(slot=review.slot, reason=reason))
                continue
            assert synthesis is not None
            votes.append(
                Vote(
                    slot=review.slot,
                    round_number=review.round_number,
                    grade=synthesis.grade,
                    justification=synthesis.justification,
                    evidence_ids=tuple(item_id(review.slot, kind, ref) for kind, ref in refs)
                    + (item_id(review.slot, ItemType.CRITERION, definition.key),),
                )
            )
        grades = [Decimal(vote.grade) for vote in votes]
        scores.append(
            CriterionScore(
                criterion_key=definition.key,
                label=definition.label,
                weight=Decimal(str(definition.weight)),
                grade=median(grades) if grades else None,
                dispersion=max(grades) - min(grades) if len(grades) >= 2 else None,
                votes=tuple(votes),
                excluded=tuple(excluded),
                unresolved=bool(excluded),
            )
        )
    available = [score for score in scores if score.grade is not None and score.weight > 0]
    weight = sum((score.weight for score in available), Decimal(0))
    total = (
        sum(
            (score.grade * score.weight for score in available if score.grade is not None),
            Decimal(0),
        )
        / weight
        if weight
        else None
    )
    definitions = {item.key: item for item in config.criteria}
    comparable = [score for score in available if score.dispersion is not None]
    agreement_weight = sum((score.weight for score in comparable), Decimal(0))
    agreement_sum = Decimal(0)
    for score in comparable:
        allowed_grades = definitions[score.criterion_key].grades
        span = Decimal(max(allowed_grades) - min(allowed_grades))
        assert score.dispersion is not None
        agreement_sum += score.weight * (1 - score.dispersion / span if span else Decimal(1))
    agreement = agreement_sum / agreement_weight if agreement_weight else None
    # Uma recomendação exige cobertura mínima de dois votos válidos em cada
    # critério ativo. A nota parcial ainda é útil para inspeção, mas não deve
    # produzir um veredito quando algum critério ficou sem cobertura suficiente.
    complete_coverage = all(len(score.votes) >= 2 for score in scores)
    recommendation = None
    if total is not None and complete_coverage:
        recommendation = (
            Recommendation.ACCEPT
            if total >= policy.accept_min
            else Recommendation.MINOR
            if total >= policy.minor_min
            else Recommendation.MAJOR
            if total >= policy.major_min
            else Recommendation.REJECT
        )
    return Aggregation(
        criteria=tuple(scores),
        total_score=total,
        agreement=agreement,
        recommendation=recommendation,
        policy=policy,
        needs_human_review=any(score.excluded or len(score.votes) < 2 for score in scores),
    )
