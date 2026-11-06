"""Configuração do app attempts."""

from django.apps import AppConfig


class AttemptsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects.correction.attempts"
    verbose_name = "Artigos e execuções"
