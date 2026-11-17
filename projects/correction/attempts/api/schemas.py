"""Contratos HTTP do app attempts: o formato de entrada e de saída de cada rota."""

from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import Field

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import HumanDecision
from projects.correction.pipeline.services import Submission


class SubmissionResponse(Schema):
    attempt_id: str
    run_id: str
    attempt_number: int
    status: str
    created: bool

    @classmethod
    def from_submission(cls, submission: Submission) -> SubmissionResponse:
        return cls(
            attempt_id=str(submission.attempt.pk),
            run_id=str(submission.run.pk),
            attempt_number=submission.attempt.attempt_number,
            status=submission.run.status,
            created=submission.created,
        )


class RunEventResponse(Schema):
    event_type: str
    from_status: str
    to_status: str
    stage: str
    task_id: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_event(cls, event: RunEvent) -> RunEventResponse:
        return cls(
            event_type=event.event_type,
            from_status=event.from_status,
            to_status=event.to_status,
            stage=event.stage,
            task_id=event.task_id,
            actor=event.actor,
            payload=event.payload,
            created_at=event.created_at,
        )


class RunResponse(Schema):
    run_id: str
    attempt_id: str
    attempt_number: int
    status: str
    stage: str | None
    version: int
    last_error: str
    created_at: datetime
    updated_at: datetime
    events: list[RunEventResponse]

    @classmethod
    def from_run(cls, run: Run) -> RunResponse:
        """`run` vem do `Run.get_with_events`, com a attempt e os eventos já carregados."""
        return cls(
            run_id=str(run.pk),
            attempt_id=str(run.attempt_id),
            attempt_number=run.attempt.attempt_number,
            status=run.status,
            stage=run.stage or None,
            version=run.version,
            last_error=run.last_error,
            created_at=run.created_at,
            updated_at=run.updated_at,
            events=[RunEventResponse.from_event(event) for event in run.events.all()],
        )


class IntegrityFindingResponse(Schema):
    kind: str
    severity: str
    message: str
    evidence: dict[str, Any]


class IntegrityResponse(Schema):
    run_id: str
    risk: str
    rules_version: str
    coverage: dict[str, bool]
    findings: list[IntegrityFindingResponse]


class DecisionRequest(Schema):
    decision: HumanDecision
    note: str = Field(default="", max_length=2000)
