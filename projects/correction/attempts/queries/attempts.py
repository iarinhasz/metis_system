"""Consultas e criação de Attempt (versões do artigo)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models, transaction

if TYPE_CHECKING:
    from projects.correction.attempts.models import Article, Attempt


class AttemptManagement(models.Manager["Attempt"]):
    """Cria versões do artigo com hash e número de tentativa protegidos."""

    def find_by_sha256(self, article: Article, sha256: str) -> Attempt | None:
        return self.filter(article=article, sha256=sha256).first()

    @transaction.atomic
    def create_next(
        self,
        article: Article,
        *,
        sha256: str,
        **fields: Any,
    ) -> tuple[Attempt, bool]:
        locked_article = type(article).objects.select_for_update().get(pk=article.pk)
        existing = self.find_by_sha256(locked_article, sha256)
        if existing:
            return existing, False

        latest = self.filter(article=locked_article).aggregate(
            max_number=models.Max("attempt_number")
        )
        attempt = self.create(
            article=locked_article,
            attempt_number=(latest["max_number"] or 0) + 1,
            sha256=sha256,
            **fields,
        )
        from projects.correction.attempts.models import Run

        Run.objects.supersede_other_attempts(locked_article, attempt)
        return attempt, True
