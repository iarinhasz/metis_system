"""Configuração do app pipeline."""

from django.apps import AppConfig


class PipelineConfig(AppConfig):
    name = "projects.correction.pipeline"
    verbose_name = "Pipeline"

    def ready(self) -> None:
        # Registra as tasks no app Celery em todo processo Django (API, admin e workers),
        # para que a publicação encontre a task pelo nome, inclusive no modo eager.
        from projects.correction.pipeline import tasks  # noqa: F401
