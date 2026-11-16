"""Fluxo interno completo com E2/E5 reais, HTTP do admin e E4 substituído na fronteira."""

from datetime import timedelta
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.usage import UsageSink
from projects.correction.attempts.models import LLMCall, Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evaluation.models import FinalReport
from projects.correction.metis.config import settings
from projects.correction.pipeline.publishing import publish_checkpoint_stage
from projects.correction.pipeline.reconciler import reconcile_runs
from projects.correction.pipeline.stages import EvaluationStage, IntegrityStage, StageOutcome
from projects.correction.questions.models import Question
from projects.correction.questions.rubric_check import start_rubric_check
from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import field_answer, topic_answer
from projects.correction.questions.tests.rubric_check_helpers import (
    draft,
    judged_evaluation,
    sample_attempt,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_mode")]


@pytest.fixture
def model_fakes(monkeypatch: pytest.MonkeyPatch, profiling_taxonomy: TaxonomySnapshot) -> None:
    def factory(run_id: str, stage: str, usage_sink: UsageSink, **kwargs: Any) -> FakeAgentFactory:
        return FakeAgentFactory(
            run_id,
            stage,
            usage_sink,
            scripts={
                "profiler_field": [field_answer()],
                "profiler_topic": [topic_answer()],
                "meta_reviewer": [{}],
            },
            **kwargs,
        )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "O rubric check tentou executar E1 externo, E3 ou resolução pela árvore."
        )

    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", factory)
    monkeypatch.setattr("projects.correction.pipeline.stages.extract_attempt", forbidden)
    monkeypatch.setattr("projects.correction.questions.workflow.resolve_question", forbidden)
    monkeypatch.setattr(IntegrityStage, "execute", forbidden)


def test_cached_sample_uses_draft_skips_integrity_and_compares_real_final_reports(
    model_fakes: None,
    run: Run,
    admin_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = draft(active=True)
    source = draft()
    sample = (sample_attempt("first"), sample_attempt("second"))
    monkeypatch.setattr(EvaluationStage, "execute", lambda self, ctx: judged_evaluation(ctx))
    batch = start_rubric_check(
        source.pk,
        attempt_ids=tuple(attempt.pk for attempt in sample),
        revision=source.updated_at.isoformat(),
        batch_id=uuid4(),
        actor="admin:curator",
    )
    for created in batch.runs:
        current = Run.get_by_id(created.pk)
        assert current.status == RunStatus.DONE and current.question_id == source.pk
        report = FinalReport.for_run(current.pk)
        assert report is not None and report.content["versions"]["question"]["id"] == str(source.pk)
        assert (
            report.content["versions"]["question"]["rubric_fields"][0]["rubric_text"]
            == "Texto original do rascunho."
        )
        events = RunEvent.for_run(current.pk)
        skipped = [event for event in events if event.payload.get("skipped")]
        assert len(skipped) == 1 and skipped[0].to_status == RunStatus.INTEGRITY_CHECKED
        assert not any(event.to_status == RunStatus.CHECKING_INTEGRITY for event in events)
        assert any(event.payload.get("reused") for event in events)
        assert all(call.stage != Stage.EXTRACTION for call in LLMCall.for_run(current.pk))
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED
    assert Question.get_by_id(active.pk).updated_at == active.updated_at
    page = admin_client.get(
        reverse(
            "admin:questions_question_rubric_check_results",
            args=[source.pk, batch.id],
        )
    )
    assert page.status_code == 200
    assert len(page.context["results"]) == 2
    assert all(result["report"] is not None for result in page.context["results"])
    assert page.content.decode().count("<article>") == 2
    assert "<script>alert(1)</script>" not in page.content.decode()


def test_missing_e4_leaves_a_visible_recoverable_setup_state(
    model_fakes: None,
    admin_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simula E4 ainda não disponível para preservar o cenário de setup do E5.
    monkeypatch.setattr(EvaluationStage, "execute", lambda self, ctx: StageOutcome())
    source = draft()
    sample = sample_attempt("sample")
    batch = start_rubric_check(
        source.pk,
        attempt_ids=(sample.pk,),
        revision=source.updated_at.isoformat(),
        batch_id=uuid4(),
        actor="admin:curator",
    )
    [run] = batch.runs
    current = Run.get_by_id(run.pk)
    assert current.status == RunStatus.WAITING_SETUP and current.stage == Stage.CONSOLIDATION
    assert FinalReport.for_run(run.pk) is None
    page = admin_client.get(
        reverse("admin:questions_question_rubric_check_results", args=[source.pk, batch.id])
    )
    assert page.status_code == 200 and "waiting_setup" in page.content.decode()


def test_normal_runs_cannot_skip_integrity(run: Run, publisher: Mock) -> None:
    for stage, end in (
        (Stage.EXTRACTION, RunStatus.EXTRACTED),
        (Stage.PROFILING, RunStatus.PROFILED),
    ):
        Run.claim_stage(run.pk, stage, stage)
        Run.complete_stage(run.pk, stage, end)
    assert Run.skip_rubric_check_integrity(run.pk) is None
    publish_checkpoint_stage(Run.get_by_id(run.pk))
    publisher.assert_called_once_with(str(run.pk), Stage.INTEGRITY)
    assert Run.get_by_id(run.pk).status == RunStatus.PROFILED


def test_reconciler_skips_integrity_once_and_stale_messages_cannot_run_it(publisher: Mock) -> None:
    source = draft()
    sample = sample_attempt("sample")
    batch = start_rubric_check(
        source.pk,
        attempt_ids=(sample.pk,),
        revision=source.updated_at.isoformat(),
        batch_id=uuid4(),
        actor="admin:curator",
    )
    [run] = batch.runs
    for stage, end in (
        (Stage.EXTRACTION, RunStatus.EXTRACTED),
        (Stage.PROFILING, RunStatus.PROFILED),
    ):
        Run.claim_stage(run.pk, stage, stage)
        Run.complete_stage(run.pk, stage, end)
    assert Run.claim_stage(run.pk, Stage.INTEGRITY, "stale-e3") is None
    stale = Run.get_by_id(run.pk)
    publisher.reset_mock()
    report = reconcile_runs(
        timezone.now() + timedelta(seconds=settings.republish_after_seconds + 1)
    )
    assert report.republished == [str(run.pk)]
    assert Run.get_by_id(run.pk).status == RunStatus.INTEGRITY_CHECKED
    publisher.assert_called_once_with(str(run.pk), Stage.EVALUATION)
    publish_checkpoint_stage(stale)
    assert publisher.call_count == 1
    assert len([event for event in RunEvent.for_run(run.pk) if event.payload.get("skipped")]) == 1
