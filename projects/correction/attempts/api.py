"""Rotas HTTP para submissão de artigos e consulta do processamento."""

import hashlib
from datetime import datetime
from functools import partial
from pathlib import PurePath
from typing import Annotated, Any

from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError, connection, transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema
from ninja.files import UploadedFile as NinjaUploadedFile

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.attempts.publishing import publish_extraction
from projects.correction.metis.authentication import ServiceBearerAuth
from projects.correction.metis.config import settings

router = Router(auth=ServiceBearerAuth())


class SubmissionResponse(Schema):
    attempt_id: str
    run_id: str
    attempt_number: int
    status: str
    created: bool


class RunEventResponse(Schema):
    event_type: str
    from_status: str
    to_status: str
    stage: str
    task_id: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime


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


def _file_sha256(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def _safe_filename(filename: str) -> str:
    return PurePath(filename.replace("\\", "/")).name[:255] or "submission.pdf"


@router.post(
    "/attempts",
    response={200: SubmissionResponse, 202: SubmissionResponse, 400: dict[str, str]},
)
def submit_attempt(
    request: HttpRequest,
    file: Annotated[NinjaUploadedFile, File(...)],
    external_id: Annotated[str, Form(...)],
) -> tuple[int, SubmissionResponse] | tuple[int, dict[str, str]]:
    """Recebe PDF, cria uma versão quando necessário e agenda E1 após o commit."""
    del request
    external_id = external_id.strip()
    if not external_id or len(external_id) > 255:
        return 400, {"detail": "external_id é obrigatório."}
    size_bytes = file.size
    if size_bytes is None or size_bytes <= 0 or size_bytes > settings.max_upload_mb * 1024 * 1024:
        return 400, {"detail": "Arquivo vazio ou acima do limite de tamanho."}

    file.seek(0)
    if file.read(5) != b"%PDF-":
        file.seek(0)
        return 400, {"detail": "O arquivo enviado não tem cabeçalho PDF válido."}
    file.seek(0)
    sha256 = _file_sha256(file)
    safe_filename = _safe_filename(file.name or "submission.pdf")
    queued_run_id: str | None = None

    with transaction.atomic():
        article, _ = Article.objects.get_or_create(external_id=external_id)
        attempt = Attempt.objects.find_by_sha256(article, sha256)
        created = attempt is None
        if attempt is None:
            attempt, created = Attempt.objects.create_next(
                article,
                sha256=sha256,
                file=file,
                original_filename=safe_filename,
                size_bytes=size_bytes,
                submitted_by="service-api",
            )

        run = attempt.runs.order_by("-created_at", "-pk").first()
        if run is None:
            run = Run.objects.create(attempt=attempt)
            queued_run_id = str(run.pk)
        elif created:
            queued_run_id = str(run.pk)

        if queued_run_id:
            transaction.on_commit(partial(publish_extraction, queued_run_id), robust=True)

    return (202 if created else 200), SubmissionResponse(
        attempt_id=str(attempt.pk),
        run_id=str(run.pk),
        attempt_number=attempt.attempt_number,
        status=run.status,
        created=created,
    )


@router.get("/runs/{run_id}", response=RunResponse)
def get_run(request: HttpRequest, run_id: str) -> RunResponse:
    """Devolve o estado atual e a trilha de eventos em ordem cronológica."""
    del request
    run = get_object_or_404(
        Run.objects.select_related("attempt").prefetch_related("events"), pk=run_id
    )
    events = [
        RunEventResponse(
            event_type=event.event_type,
            from_status=event.from_status,
            to_status=event.to_status,
            stage=event.stage,
            task_id=event.task_id,
            actor=event.actor,
            payload=event.payload,
            created_at=event.created_at,
        )
        for event in run.events.all()
    ]
    return RunResponse(
        run_id=str(run.pk),
        attempt_id=str(run.attempt_id),
        attempt_number=run.attempt.attempt_number,
        status=run.status,
        stage=run.stage or None,
        version=run.version,
        last_error=run.last_error,
        created_at=run.created_at,
        updated_at=run.updated_at,
        events=events,
    )


def health_check() -> tuple[int, dict[str, str]]:
    """Verifica a conexão com o Postgres para o healthcheck do container."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return 503, {"status": "unavailable"}
    return 200, {"status": "ok"}
