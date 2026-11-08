"""Consultas de Article."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from projects.correction.attempts.models import Article


class ArticleManagement(models.Manager["Article"]):
    def get_or_create_by_external_id(self, external_id: str) -> Article:
        article, _ = self.get_or_create(external_id=external_id)
        return article
