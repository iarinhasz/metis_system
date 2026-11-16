"""Configuração do app de integridade."""

from django.apps import AppConfig


class IntegrityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects.correction.integrity"
    verbose_name = "Integridade"
