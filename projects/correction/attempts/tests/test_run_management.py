"""Testes transacionais para posse, transições e eventos do run."""

from collections.abc import Iterator

import pytest

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.attempts.queries import InvalidTransition, RunConflict
from projects.correction.attempts.status import STAGES, HumanDecision, RunStatus, Stage


@pytest.fixture
def attempt(db: None) -> Iterator[Attempt]:
    article = Article.objects.create(external_id="article-1")
    yield Attempt.objects.create(
        article=article,
        attempt_number=1,
        file="submissions/article-1/paper.pdf",
        original_filename="paper.pdf",
        size_bytes=128,
        sha256="a" * 64,
        submitted_by="test-service",
    )


@pytest.fixture
def run(attempt: Attempt) -> Run:
    return Run.objects.create(attempt=attempt)


@pytest.mark.django_db
def test_claim_moves_checkpoint_to_running(run: Run) -> None:
    claimed = Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert claimed is not None
    assert claimed.status == RunStatus.EXTRACTING
    assert claimed.stage == Stage.EXTRACTION
    assert claimed.current_task_id == "task-1"
    assert claimed.stage_claims == 1
    assert claimed.version == 2
    assert claimed.events.count() == 2


@pytest.mark.django_db
def test_second_task_cannot_claim_but_owner_can_reclaim(run: Run) -> None:
    Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-2") is None
    resumed = Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert resumed is not None
    assert resumed.stage_claims == 2
    assert resumed.events.count() == 2


@pytest.mark.django_db
def test_complete_requires_ownership(run: Run) -> None:
    Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    assert Run.objects.complete_stage(run.pk, "task-2", RunStatus.EXTRACTED) is None
    completed = Run.objects.complete_stage(run.pk, "task-1", RunStatus.EXTRACTED)

    assert completed is not None
    assert completed.status == RunStatus.EXTRACTED
    assert completed.current_task_id is None


@pytest.mark.django_db
def test_claim_outside_checkpoint_has_no_effect(run: Run) -> None:
    assert Run.objects.claim_stage(run.pk, Stage.PROFILING, "task-1") is None
    run.refresh_from_db()

    assert run.status == RunStatus.RECEIVED
    assert run.events.count() == 1


@pytest.mark.django_db
def test_invalid_transition_raises(run: Run) -> None:
    Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    with pytest.raises(InvalidTransition):
        Run.objects.complete_stage(run.pk, "task-1", RunStatus.WAITING_HUMAN_REVIEW)


@pytest.mark.django_db
def test_new_attempt_supersedes_pending_runs(run: Run) -> None:
    article = run.attempt.article
    second, created = Attempt.objects.create_next(
        article,
        sha256="b" * 64,
        file="submissions/article-1/paper-v2.pdf",
        original_filename="paper-v2.pdf",
        size_bytes=256,
        submitted_by="test-service",
    )
    run.refresh_from_db()

    assert created
    assert second.attempt_number == 2
    assert run.status == RunStatus.SUPERSEDED


@pytest.mark.django_db
def test_decide_outside_gate_conflicts(run: Run) -> None:
    with pytest.raises(RunConflict):
        Run.objects.decide(run.pk, HumanDecision.CONTINUE, actor="reviewer")


@pytest.mark.django_db
def test_recover_returns_to_failed_stage_checkpoint(run: Run) -> None:
    task_id = "task-1"
    for spec in STAGES[:4]:
        assert Run.objects.claim_stage(run.pk, spec.stage, task_id) is not None
        if spec.stage == Stage.EVALUATION:
            Run.objects.fail_stage(run.pk, task_id, RunStatus.ERROR_LLM, error="temporary")
            break
        Run.objects.complete_stage(run.pk, task_id, spec.completed)

    recovered = Run.objects.recover(run.pk, actor="reviewer")

    assert recovered.status == RunStatus.INTEGRITY_CHECKED
    assert recovered.current_task_id is None


@pytest.mark.django_db
def test_events_are_not_duplicated_for_retry(run: Run) -> None:
    event = {"wait_seconds": 60}
    Run.objects.record_retry(run.pk, "task-1", 1, event)
    Run.objects.record_retry(run.pk, "task-1", 1, event)

    assert run.events.filter(event_type="retry_scheduled").count() == 1
