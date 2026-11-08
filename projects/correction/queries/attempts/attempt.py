"""Consultas e criação de Attempt (as versões de um artigo)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models, transaction

if TYPE_CHECKING:
    from projects.correction.attempts.models import Article, Attempt


class AttemptManagement:
    """Herdado por `Attempt`. Uso: `Attempt.create_next(article, sha256=..., ...)`."""

    objects: ClassVar[models.Manager[Attempt]]

    @classmethod
    def find_by_sha256(cls, article: Article, sha256: str) -> Attempt | None:
        return cls.objects.filter(article=article, sha256=sha256).first()

    @classmethod
    @transaction.atomic
    def create_next(
        cls,
        article: Article,
        *,
        sha256: str,
        **fields: Any,
    ) -> tuple[Attempt, bool]:
        """Cria a próxima versão do artigo; o mesmo arquivo devolve a versão que já existe."""
        locked_article = type(article).get_locked(article.pk)
        existing = cls.find_by_sha256(locked_article, sha256)
        if existing:
            return existing, False

        latest = cls.objects.filter(article=locked_article).aggregate(
            max_number=models.Max("attempt_number")
        )
        attempt = cls.objects.create(
            article=locked_article,
            attempt_number=(latest["max_number"] or 0) + 1,
            sha256=sha256,
            **fields,
        )
        from projects.correction.attempts.models import Run

        Run.supersede_other_attempts(locked_article, attempt)
        return attempt, True
