"""Publicação de tarefas de pipeline após persistir o estado no banco."""

from celery import current_app

from projects.correction.metis.config import settings


def publish_extraction(run_id: str) -> None:
    """Envia somente o identificador do run para a fila de extração."""
    current_app.conf.update(broker_url=settings.redis_url)
    current_app.send_task("pipeline.extract_attempt", args=[run_id], queue="extraction")
