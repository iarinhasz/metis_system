"""Testes do reconciliador: checkpoints parados e estágios travados."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from django.utils import timezone

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.metis.celery import app
from projects.correction.metis.config import settings
from projects.correction.pipeline.reconciler import reconcile_runs
from projects.correction.pipeline.services import recover_run
from projects.correction.pipeline.tasks import reconcile_runs_task

pytestmark = pytest.mark.django_db(transaction=True)


def later(seconds: int) -> datetime:
    """Um instante no futuro, para simular o tempo passando sem mexer no banco."""
    return timezone.now() + timedelta(seconds=seconds)


def checkpoint_stalled() -> datetime:
    return later(settings.republish_after_seconds + 60)


def stage_stale() -> datetime:
    return later(settings.stale_stage_after_seconds + 60)


def events(run: Run, event_type: str) -> list[RunEvent]:
    return [e for e in RunEvent.for_run(run.pk) if e.event_type == event_type]


def test_stalled_checkpoint_is_republished(run: Run, publisher: Mock) -> None:
    report = reconcile_runs(now=checkpoint_stalled())
    run = Run.get_by_id(run.pk)

    assert report.republished == [str(run.pk)]
    assert run.status == RunStatus.RECEIVED
    assert run.publish_count == 1
    assert len(events(run, "republished")) == 1
    publisher.assert_called_once_with(str(run.pk), Stage.EXTRACTION)


def test_recent_checkpoint_is_left_alone(run: Run, publisher: Mock) -> None:
    report = reconcile_runs(now=later(settings.republish_after_seconds - 60))

    assert report.as_dict() == {"republished": [], "released": [], "abandoned": []}
    assert Run.get_by_id(run.pk).publish_count == 0
    publisher.assert_not_called()


def test_republish_limit_ends_in_error_unexpected(run: Run, publisher: Mock) -> None:
    for _ in range(settings.max_republish):
        reconcile_runs(now=checkpoint_stalled())

    report = reconcile_runs(now=checkpoint_stalled())
    run = Run.get_by_id(run.pk)

    assert report.abandoned == [str(run.pk)]
    assert run.status == RunStatus.ERROR_UNEXPECTED
    assert "republicações" in run.last_error
    assert publisher.call_count == settings.max_republish


def test_abandoned_checkpoint_is_reprocessed_from_the_same_checkpoint(
    run: Run, publisher: Mock
) -> None:
    for _ in range(settings.max_republish + 1):
        reconcile_runs(now=checkpoint_stalled())

    recovered = recover_run(run.pk, actor="admin:ana")

    assert recovered.status == RunStatus.RECEIVED
    assert recovered.stage == Stage.EXTRACTION
    assert recovered.publish_count == 0


def test_stale_stage_returns_to_checkpoint_and_is_republished(run: Run, publisher: Mock) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "worker-morto")

    report = reconcile_runs(now=stage_stale())
    run = Run.get_by_id(run.pk)

    assert report.released == [str(run.pk)]
    assert run.status == RunStatus.RECEIVED
    assert run.current_task_id is None
    release = events(run, "transition")[-1]
    assert (release.from_status, release.to_status, release.actor) == (
        "extracting",
        "received",
        "reconciler",
    )
    publisher.assert_called_once_with(str(run.pk), Stage.EXTRACTION)


@pytest.mark.usefixtures("eager_celery")
def test_released_stage_runs_again_until_done(run: Run) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "worker-morto")

    reconcile_runs(now=stage_stale())

    assert Run.get_by_id(run.pk).status == RunStatus.DONE


def test_claim_limit_ends_in_error_unexpected(run: Run, publisher: Mock) -> None:
    for _ in range(settings.max_stage_claims):
        Run.claim_stage(run.pk, Stage.EXTRACTION, "worker-morto")

    report = reconcile_runs(now=stage_stale())
    run = Run.get_by_id(run.pk)

    assert report.abandoned == [str(run.pk)]
    assert run.status == RunStatus.ERROR_UNEXPECTED
    assert "claims" in run.last_error
    publisher.assert_not_called()

    recovered = recover_run(run.pk, actor="admin:ana")
    assert recovered.status == RunStatus.RECEIVED
    assert recovered.stage_claims == 0


def test_stage_within_deadline_is_left_alone(run: Run, publisher: Mock) -> None:
    Run.claim_stage(run.pk, Stage.EXTRACTION, "worker-vivo")

    report = reconcile_runs(now=later(settings.stale_stage_after_seconds - 60))

    assert report.released == []
    assert Run.get_by_id(run.pk).status == RunStatus.EXTRACTING
    publisher.assert_not_called()


def test_reconciler_runs_on_the_beat() -> None:
    entry = app.conf.beat_schedule["reconcile-runs"]

    assert entry["task"] == reconcile_runs_task.name == "pipeline.reconcile_runs"
    assert entry["schedule"] == settings.reconcile_interval_seconds
    assert entry["options"] == {"queue": "default"}
