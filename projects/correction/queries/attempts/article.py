"""Consultas e criação de Article."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.attempts.models import Article


class ArticleManagement:
    """Herdado por `Article`. Uso: `Article.get_or_create_by_external_id(external_id)`."""

    objects: ClassVar[models.Manager[Article]]

    @classmethod
    def find_by_external_id(cls, external_id: str) -> Article | None:
        return cls.objects.filter(external_id=external_id).first()

    @classmethod
    def get_or_create_by_external_id(cls, external_id: str) -> Article:
        article, _ = cls.objects.get_or_create(external_id=external_id)
        return article

    @classmethod
    def get_locked(cls, article_id: Any) -> Article:
        """Trava a linha do artigo até o fim da transação corrente."""
        return cls.objects.select_for_update().get(pk=article_id)
