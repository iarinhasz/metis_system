"""Publicação de estágios: a mensagem leva só o run_id e sai depois do commit."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from django.db import transaction

from projects.correction.attempts.status import (
    STAGE_BY_CHECKPOINT,
    STAGE_BY_NAME,
    RunStatus,
    Stage,
)
from projects.correction.metis.celery import app

if TYPE_CHECKING:
    from projects.correction.attempts.models import Run


def publish_stage(run_id: str, stage: Stage) -> None:
    """Envia o run para a task e a fila do estágio, conforme o STAGES."""
    spec = STAGE_BY_NAME[Stage(stage)]
    app.signature(spec.task_name, args=[str(run_id)], queue=spec.queue).apply_async()


def publish_stage_on_commit(run_id: str, stage: Stage) -> None:
    """Agenda a publicação para depois do commit da transação corrente."""
    transaction.on_commit(partial(publish_stage, str(run_id), stage), robust=True)


def publish_checkpoint_stage(run: Run) -> None:
    """Agenda, para depois do commit, o estágio que começa no checkpoint em que o run está.

    Fora de um checkpoint (gate, erro, final), não publica nada.
    """
    spec = STAGE_BY_CHECKPOINT.get(RunStatus(run.status))
    if spec is not None:
        publish_stage_on_commit(str(run.pk), spec.stage)
