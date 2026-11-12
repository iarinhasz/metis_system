"""Testes do ciclo dos estágios com Celery em modo eager e transações reais."""

import json

import pytest

from projects.correction.attempts.models import Attempt, Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.metis.celery import app
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import (
    InvalidSubmission,
    LLMUnavailable,
    SetupRequired,
    TransientStageError,
)
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.stages import (
    EvaluationStage,
    ExtractionStage,
    IntegrityStage,
    ProfilingStage,
    StageContext,
    StageOutcome,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_celery")]

HAPPY_PATH = [
    "received",
    "extracting",
    "extracted",
    "profiling",
    "profiled",
    "checking_integrity",
    "integrity_checked",
    "evaluating",
    "evaluated",
    "consolidating",
    "done",
]


def transitions(run: Run) -> list[str]:
    return [e.to_status for e in RunEvent.for_run(run.pk) if e.event_type == "transition"]


def retries(run: Run) -> list[RunEvent]:
    return [e for e in RunEvent.for_run(run.pk) if e.event_type == "retry_scheduled"]


def test_happy_path_reaches_done(run: Run) -> None:
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.DONE
    assert transitions(run) == HAPPY_PATH
    assert run.current_task_id is None
    assert not retries(run)
    assert run.extraction is not None
    [extracted] = [e for e in RunEvent.for_run(run.pk) if e.to_status == "extracted"]
    assert extracted.payload["extraction_id"] == str(run.extraction.pk)
    assert "text" not in json.dumps(extracted.payload)


def test_transient_error_is_retried_and_reaches_done(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def flaky(self: ExtractionStage, ctx: StageContext) -> StageOutcome:
        calls.append(ctx.task_id)
        if len(calls) <= 2:
            raise TransientStageError("GROBID fora do ar")
        return StageOutcome()

    monkeypatch.setattr(ExtractionStage, "execute", flaky)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.DONE
    assert transitions(run) == HAPPY_PATH
    assert len(set(calls)) == 1, "o retry mantém o id da task e, com ele, a posse"
    retry_events = retries(run)
    assert len(retry_events) == 2
    for event in retry_events:
        assert event.stage == Stage.EXTRACTION
        assert event.payload["exception"] == "TransientStageError"
        assert 0 <= event.payload["wait_seconds"] <= settings.stage_retry_backoff_max_seconds


def test_exhausted_retries_end_in_error_llm(run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(self: EvaluationStage, ctx: StageContext) -> StageOutcome:
        raise LLMUnavailable("429 do provedor")

    monkeypatch.setattr(settings, "stage_max_retries", 2)
    monkeypatch.setattr(EvaluationStage, "execute", unavailable)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.ERROR_LLM
    assert run.stage == Stage.EVALUATION
    assert run.last_error == "LLMUnavailable: 429 do provedor"
    assert run.current_task_id is None
    assert len(retries(run)) == 2


def test_exhausted_transient_error_ends_in_error_external(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    def down(self: ExtractionStage, ctx: StageContext) -> StageOutcome:
        raise TransientStageError("timeout no Crossref")

    monkeypatch.setattr(settings, "stage_max_retries", 1)
    monkeypatch.setattr(ExtractionStage, "execute", down)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.ERROR_EXTERNAL


def test_invalid_submission_is_final_and_publishes_nothing(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    profiled: list[str] = []

    def invalid(self: ExtractionStage, ctx: StageContext) -> StageOutcome:
        raise InvalidSubmission("PDF sem texto")

    def profile(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        profiled.append(ctx.run_id)
        return StageOutcome()

    monkeypatch.setattr(ExtractionStage, "execute", invalid)
    monkeypatch.setattr(ProfilingStage, "execute", profile)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.REJECTED_INVALID_SUBMISSION
    assert transitions(run) == ["received", "extracting", "rejected_invalid_submission"]
    assert profiled == []
    assert not retries(run)


def test_setup_required_waits_for_setup(run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_question(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        raise SetupRequired("nenhuma Question disponível")

    monkeypatch.setattr(ProfilingStage, "execute", no_question)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.WAITING_SETUP
    assert run.stage == Stage.PROFILING


def test_unexpected_error_ends_in_error_unexpected(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bug(self: ExtractionStage, ctx: StageContext) -> StageOutcome:
        raise KeyError("campo")

    monkeypatch.setattr(ExtractionStage, "execute", bug)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.ERROR_UNEXPECTED
    assert run.last_error.startswith("KeyError")
    assert not retries(run)


def test_stage_that_lost_ownership_does_not_transition(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    def superseded_midway(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        Attempt.create_next(
            run.attempt.article,
            sha256="b" * 64,
            file="submissions/artigo-pipeline/paper-v2.pdf",
            original_filename="paper-v2.pdf",
            size_bytes=256,
            submitted_by="test-service",
        )
        return StageOutcome()

    monkeypatch.setattr(ProfilingStage, "execute", superseded_midway)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.SUPERSEDED
    assert transitions(run)[-2:] == ["profiling", "superseded"]


def test_duplicate_message_is_denied_without_effect(run: Run) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "worker-original")

    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.EXTRACTING
    assert run.current_task_id == "worker-original"
    assert transitions(run) == ["received", "extracting"]


def test_halt_pauses_at_human_review_gate(run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
    def high_risk(self: IntegrityStage, ctx: StageContext) -> StageOutcome:
        return StageOutcome(payload={"risk": "high"}, halt=True)

    monkeypatch.setattr(IntegrityStage, "execute", high_risk)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.WAITING_HUMAN_REVIEW
    assert transitions(run)[-1] == "waiting_human_review"
    gate = next(e for e in RunEvent.for_run(run.pk) if e.to_status == "waiting_human_review")
    assert gate.payload == {"risk": "high"}


def test_stage_routing_comes_from_stages() -> None:
    routes = app.conf.task_routes

    assert routes["pipeline.extract_attempt"] == {"queue": "extraction"}
    assert routes["pipeline.profile_attempt"] == {"queue": "evaluation"}
    assert routes["pipeline.check_integrity"] == {"queue": "integrity"}
    assert routes["pipeline.evaluate_attempt"] == {"queue": "evaluation"}
    assert routes["pipeline.consolidate_report"] == {"queue": "evaluation"}
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True
    assert app.conf.worker_prefetch_multiplier == 1
