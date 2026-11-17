"""Configuração do app extractor."""

from django.apps import AppConfig


class ExtractorAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects.correction.extractor"
    verbose_name = "Extração"
