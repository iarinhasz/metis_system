"""Testes transacionais para posse, transições e eventos do run."""

import pytest

from projects.correction.attempts.models import Article, Attempt, Run, RunEvent
from projects.correction.attempts.status import STAGES, HumanDecision, RunStatus, Stage
from projects.correction.queries.attempts.run import InvalidTransition, RunConflict


def events(run: Run, event_type: str | None = None) -> list[RunEvent]:
    return [e for e in RunEvent.for_run(run.pk) if event_type in (None, e.event_type)]


@pytest.fixture
def attempt(db: None) -> Attempt:
    article = Article.get_or_create_by_external_id("article-1")
    attempt, _ = Attempt.create_next(
        article,
        sha256="a" * 64,
        file="submissions/article-1/paper.pdf",
        original_filename="paper.pdf",
        size_bytes=128,
        submitted_by="test-service",
    )
    return attempt


@pytest.fixture
def run(attempt: Attempt) -> Run:
    return Run.create(attempt=attempt)


@pytest.mark.django_db
def test_create_starts_at_received_with_one_event(run: Run) -> None:
    assert run.status == RunStatus.RECEIVED
    assert run.version == 1
    assert [e.to_status for e in events(run)] == [RunStatus.RECEIVED]


@pytest.mark.django_db
def test_claim_moves_checkpoint_to_running(run: Run) -> None:
    claimed = Run.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert claimed is not None
    assert claimed.status == RunStatus.EXTRACTING
    assert claimed.stage == Stage.EXTRACTION
    assert claimed.current_task_id == "task-1"
    assert claimed.stage_claims == 1
    assert claimed.version == 2
    assert len(events(claimed)) == 2


@pytest.mark.django_db
def test_second_task_cannot_claim_but_owner_can_reclaim(run: Run) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert Run.claim_stage(run.pk, Stage.EXTRACTION, "task-2") is None
    resumed = Run.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert resumed is not None
    assert resumed.stage_claims == 2
    assert len(events(resumed)) == 2


@pytest.mark.django_db
def test_complete_requires_ownership(run: Run) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert Run.complete_stage(run.pk, "task-2", RunStatus.EXTRACTED) is None
    completed = Run.complete_stage(run.pk, "task-1", RunStatus.EXTRACTED)

    assert completed is not None
    assert completed.status == RunStatus.EXTRACTED
    assert completed.current_task_id is None


@pytest.mark.django_db
def test_claim_outside_checkpoint_has_no_effect(run: Run) -> None:
    assert Run.claim_stage(run.pk, Stage.PROFILING, "task-1") is None
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.RECEIVED
    assert len(events(run)) == 1


@pytest.mark.django_db
def test_invalid_transition_raises(run: Run) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    with pytest.raises(InvalidTransition):
        Run.complete_stage(run.pk, "task-1", RunStatus.WAITING_HUMAN_REVIEW)


@pytest.mark.django_db
def test_new_attempt_supersedes_pending_runs(attempt: Attempt, run: Run) -> None:
    second, created = Attempt.create_next(
        attempt.article,
        sha256="b" * 64,
        file="submissions/article-1/paper-v2.pdf",
        original_filename="paper-v2.pdf",
        size_bytes=256,
        submitted_by="test-service",
    )
    run = Run.get_by_id(run.pk)

    assert created
    assert second.attempt_number == 2
    assert run.status == RunStatus.SUPERSEDED


@pytest.mark.django_db
def test_same_file_returns_existing_attempt(attempt: Attempt) -> None:
    again, created = Attempt.create_next(
        attempt.article,
        sha256=attempt.sha256,
        file="submissions/article-1/paper-copy.pdf",
        original_filename="paper-copy.pdf",
        size_bytes=128,
        submitted_by="test-service",
    )

    assert not created
    assert again.pk == attempt.pk


@pytest.mark.django_db
def test_decide_outside_gate_conflicts(run: Run) -> None:
    with pytest.raises(RunConflict):
        Run.decide(run.pk, HumanDecision.CONTINUE, actor="reviewer")


@pytest.mark.django_db
def test_recover_returns_to_failed_stage_checkpoint(run: Run) -> None:
    task_id = "task-1"
    for spec in STAGES[:4]:
        assert Run.claim_stage(run.pk, spec.stage, task_id) is not None
        if spec.stage == Stage.EVALUATION:
            Run.fail_stage(run.pk, task_id, RunStatus.ERROR_LLM, error="temporary")
            break
        Run.complete_stage(run.pk, task_id, spec.completed)

    recovered = Run.recover(run.pk, actor="reviewer")

    assert recovered.status == RunStatus.INTEGRITY_CHECKED
    assert recovered.current_task_id is None


@pytest.mark.django_db
def test_events_are_not_duplicated_for_retry(run: Run) -> None:
    event = {"wait_seconds": 60}
    Run.record_retry(run.pk, "task-1", 1, event)
    Run.record_retry(run.pk, "task-1", 1, event)

    assert len(events(run, "retry_scheduled")) == 1
