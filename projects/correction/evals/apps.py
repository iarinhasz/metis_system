"""Registro dos comandos offline; este app não tem models nem tasks de produção."""

from django.apps import AppConfig


class EvalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects.correction.evals"
