"""Configuração do app de integridade."""

from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate


class IntegrityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects.correction.integrity"
    verbose_name = "Integridade"

    def ready(self) -> None:
        post_migrate.connect(_ensure_reviewers, sender=self)


def _ensure_reviewers(**kwargs: Any) -> None:
    """Depois das migrações, o grupo do gate existe. Este handler pode rodar antes do que o
    Django usa para criar as permissões, então as do run e do E3 são criadas aqui antes."""
    from django.apps import apps
    from django.contrib.auth.management import create_permissions

    from projects.correction.queries.integrity.reviewers import ensure_reviewers_group

    for label in ("attempts", "integrity"):
        create_permissions(apps.get_app_config(label), verbosity=0)
    ensure_reviewers_group()
