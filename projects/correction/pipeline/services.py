"""Casos de uso que iniciam ou retomam um run.

- `submit_attempt`: recebe o PDF, cria a versão do artigo e agenda o E1.
- `decide_run`: aplica a decisão do gate humano.
- `recover_run`: reprocessa o estágio que falhou.

Todos mudam o banco pelos Managements de `queries/` e publicam o próximo estágio só depois
do commit.
"""

from dataclasses import dataclass
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.attempts.status import (
    STAGE_BY_CHECKPOINT,
    HumanDecision,
    RunStatus,
    Stage,
)
from projects.correction.attempts.uploads import (
    InvalidUpload,
    check_pdf,
    safe_filename,
    sha256_of,
)
from projects.correction.metis.config import settings
from projects.correction.pipeline.publishing import publish_stage_on_commit


@dataclass(frozen=True)
class Submission:
    attempt: Attempt
    run: Run
    created: bool


def submit_attempt(*, external_id: str, upload: UploadedFile, submitted_by: str) -> Submission:
    """Arquivo novo vira uma versão com run e E1 agendado; o mesmo arquivo devolve o que existe."""
    external_id = external_id.strip()
    if not external_id or len(external_id) > 255:
        raise InvalidUpload("external_id é obrigatório.")
    size = check_pdf(upload, max_bytes=settings.max_upload_mb * 1024 * 1024)
    sha256 = sha256_of(upload)

    with transaction.atomic():
        article = Article.get_or_create_by_external_id(external_id)
        attempt = Attempt.find_by_sha256(article, sha256)
        created = attempt is None
        if attempt is None:
            attempt, created = Attempt.create_next(
                article,
                sha256=sha256,
                file=upload,
                original_filename=safe_filename(upload.name),
                size_bytes=size,
                submitted_by=submitted_by,
            )
        run = Run.latest_for_attempt(attempt)
        if run is None:
            run = Run.create(attempt=attempt)
            publish_stage_on_commit(str(run.pk), Stage.EXTRACTION)
    return Submission(attempt=attempt, run=run, created=created)


@transaction.atomic
def decide_run(run_id: Any, decision: HumanDecision | str, *, actor: str, note: str = "") -> Run:
    """Continuar leva o run a `integrity_checked` e publica o E4; encerrar o fecha."""
    payload = {"note": note} if note else None
    run = Run.decide(run_id, decision, actor=actor, payload=payload)
    _publish_from_checkpoint(run)
    return run


@transaction.atomic
def recover_run(run_id: Any, *, actor: str) -> Run:
    """Volta o run ao checkpoint do estágio que falhou e publica esse estágio de novo."""
    run = Run.recover(run_id, actor=actor)
    _publish_from_checkpoint(run)
    return run


def _publish_from_checkpoint(run: Run) -> None:
    spec = STAGE_BY_CHECKPOINT.get(RunStatus(run.status))
    if spec is not None:
        publish_stage_on_commit(str(run.pk), spec.stage)
