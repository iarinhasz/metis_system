"""Publicação de estágios: a mensagem leva só o run_id e sai depois do commit."""

from functools import partial

from django.db import transaction

from projects.correction.attempts.status import STAGE_BY_NAME, Stage
from projects.correction.metis.celery import app


def publish_stage(run_id: str, stage: Stage) -> None:
    """Envia o run para a task e a fila do estágio, conforme o STAGES."""
    spec = STAGE_BY_NAME[Stage(stage)]
    app.signature(spec.task_name, args=[str(run_id)], queue=spec.queue).apply_async()


def publish_stage_on_commit(run_id: str, stage: Stage) -> None:
    """Agenda a publicação para depois do commit da transação corrente."""
    transaction.on_commit(partial(publish_stage, str(run_id), stage), robust=True)
