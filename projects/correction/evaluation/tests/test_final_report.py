from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.consolidation import MetaReview
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.models import FinalReport
from projects.correction.evaluation.report import ReportContent
from projects.correction.evaluation.workflow import run_consolidation
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.queries.attempts.run import RunConflict

pytestmark = pytest.mark.django_db

VALID_META = {
    "strengths": [
        {
            "text": "O método especifica os parâmetros.",
            "criterion_keys": ["soundness"],
            "evidence_ids": ["a:criterion:soundness", "a:observation:obs-1"],
        }
    ]
}
INVALID_META = {
    "strengths": [
        {
            "text": "Esta afirmação não tem suporte.",
            "criterion_keys": ["soundness"],
            "evidence_ids": ["unknown-id"],
        }
    ]
}


def test_report_contains_structured_sections_integrity_versions_and_fixed_scores(
    consolidating_run: Run,
) -> None:
    factory = FakeAgentFactory(scripts={"meta_reviewer": [VALID_META]})
    result = run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    row = FinalReport.for_run(consolidating_run.pk)
    assert row is not None and result.report_id == row.pk
    content = ReportContent.model_validate(row.content)
    assert set(content.strengths[0].evidence_ids) <= content.evidence.keys()
    assert content.total_score == 4 and content.recommendation == "accept"
    assert len(content.criteria) == 7 and len(content.sections) == 1
    assert content.sections[0].observations[0].id == "a:observation:obs-1"
    assert content.integrity.status == "not_checked" and content.integrity.risk_level is None
    assert content.versions.review_rounds == {"a": 1, "b": 1, "c": 1}
    assert content.versions.question.id == consolidating_run.question_id
    assert content.strengths[0].evidence_ids == ("a:criterion:soundness", "a:observation:obs-1")
    assert "<script>" not in row.markdown and "&lt;script&gt;" in row.markdown
    assert "api_key" not in str(row.content)
    assert Run.get_by_id(consolidating_run.pk).status == RunStatus.CONSOLIDATING
    again = run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    assert again == result and len(factory.calls) == 1
    with pytest.raises(ValidationError, match="imutável"):
        row.save()


def test_meta_reviewer_cannot_return_or_change_a_grade(consolidating_run: Run) -> None:
    with pytest.raises(ValueError):
        MetaReview.model_validate({"total_score": 1})
    factory = FakeAgentFactory(scripts={"meta_reviewer": [{"total_score": 1}, VALID_META]})
    run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    report = FinalReport.for_run(consolidating_run.pk)
    assert report is not None and report.total_score == Decimal(4) and len(factory.calls) == 2


@pytest.mark.parametrize("second", [VALID_META, INVALID_META])
def test_unknown_references_are_retried_once_then_unsupported_points_are_removed(
    consolidating_run: Run, second: dict[str, object]
) -> None:
    factory = FakeAgentFactory(scripts={"meta_reviewer": [INVALID_META, second]})
    run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    row = FinalReport.for_run(consolidating_run.pk)
    assert row is not None and len(factory.calls) == 2
    assert bool(row.content["strengths"]) == (second == VALID_META)
    assert any(
        warning.startswith("meta_points_dropped") for warning in row.content["warnings"]
    ) == (second == INVALID_META)
    assert "unknown-id" not in str(row.content)


def test_provider_failure_keeps_aggregation_and_resumes_without_recomputing(
    consolidating_run: Run,
) -> None:
    factory = FakeAgentFactory(scripts={"meta_reviewer": [LLMUnavailable("503"), VALID_META]})
    with pytest.raises(LLMUnavailable):
        run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    checkpoint = Run.get_by_id(consolidating_run.pk).consolidation["aggregation"]
    assert FinalReport.for_run(consolidating_run.pk) is None
    run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    assert Run.get_by_id(consolidating_run.pk).consolidation["aggregation"] == checkpoint
    assert len(factory.calls) == 2
    with pytest.raises(RunConflict):
        run_consolidation(str(consolidating_run.pk), "old-task", factory=factory)


def test_retry_preserves_the_meta_reference_retry_budget(consolidating_run: Run) -> None:
    factory = FakeAgentFactory(
        scripts={"meta_reviewer": [INVALID_META, LLMUnavailable("503"), VALID_META]}
    )
    with pytest.raises(LLMUnavailable):
        run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    assert Run.get_by_id(consolidating_run.pk).consolidation["meta_progress"]["attempts"] == 1
    run_consolidation(str(consolidating_run.pk), "e5", factory=factory)
    row = FinalReport.for_run(consolidating_run.pk)
    assert row is not None and row.content["strengths"] and len(factory.calls) == 3
    assert Run.get_by_id(consolidating_run.pk).consolidation["meta_progress"]["attempts"] == 2


def test_missing_evaluation_is_setup_required_and_never_pays_for_meta_review(run: Run) -> None:
    from projects.correction.attempts.status import STAGES

    for spec in STAGES:
        Run.claim_stage(run.pk, spec.stage, "e5")
        if spec.stage.value == "consolidation":
            break
        Run.complete_stage(run.pk, "e5", spec.completed)
    factory = FakeAgentFactory()
    with pytest.raises(SetupRequired):
        run_consolidation(str(run.pk), "e5", factory=factory)
    assert factory.calls == [] and FinalReport.for_run(run.pk) is None
