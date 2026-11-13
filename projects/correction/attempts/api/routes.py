"""Rotas HTTP do app attempts: recebem a requisição, chamam o caso de uso e respondem."""

from typing import Annotated
from uuid import UUID

from django.http import Http404, HttpRequest
from ninja import File, Form, Router, Status
from ninja.files import UploadedFile

from projects.correction.attempts.api.schemas import (
    DecisionRequest,
    RunResponse,
    SubmissionResponse,
)
from projects.correction.attempts.models import Run
from projects.correction.attempts.uploads import InvalidUpload
from projects.correction.metis.authentication import ServiceBearerAuth
from projects.correction.pipeline.services import decide_run, submit_attempt
from projects.correction.queries.attempts.run import RunConflict

router = Router(auth=ServiceBearerAuth())

RUN_NOT_FOUND = Status(404, {"detail": "Run não encontrado."})


@router.post(
    "/attempts",
    response={200: SubmissionResponse, 202: SubmissionResponse, 400: dict[str, str]},
)
def create_attempt(
    request: HttpRequest,
    file: Annotated[UploadedFile, File(...)],
    external_id: Annotated[str, Form(...)],
) -> Status[SubmissionResponse] | Status[dict[str, str]]:
    """Recebe o PDF: versão nova responde 202; o reenvio do mesmo arquivo, 200."""
    del request
    try:
        submission = submit_attempt(
            external_id=external_id, upload=file, submitted_by="service-api"
        )
    except InvalidUpload as exc:
        return Status(400, {"detail": str(exc)})
    status_code = 202 if submission.created else 200
    return Status(status_code, SubmissionResponse.from_submission(submission))


@router.get("/runs/{run_id}", response=RunResponse)
def get_run(request: HttpRequest, run_id: UUID) -> RunResponse:
    """Estado atual do run e a trilha de eventos em ordem cronológica."""
    del request
    run = Run.get_with_events(run_id, public=True)
    if run is None:
        raise Http404("Run não encontrado.")
    return RunResponse.from_run(run)


@router.post(
    "/runs/{run_id}/decision",
    response={200: RunResponse, 404: dict[str, str], 409: dict[str, str]},
)
def decide_gate(
    request: HttpRequest, run_id: UUID, body: DecisionRequest
) -> Status[RunResponse] | Status[dict[str, str]]:
    """Decisão do gate humano: `continue` segue para o E4, `close` encerra o run."""
    del request
    if Run.get_with_events(run_id, public=True) is None:
        return RUN_NOT_FOUND
    try:
        decide_run(run_id, body.decision, actor="service-api", note=body.note)
    except Run.DoesNotExist:
        return RUN_NOT_FOUND
    except RunConflict as exc:
        return Status(409, {"detail": str(exc)})
    run = Run.get_with_events(run_id)
    if run is None:
        return RUN_NOT_FOUND
    return Status(200, RunResponse.from_run(run))
