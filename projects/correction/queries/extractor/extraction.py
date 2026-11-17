"""Consultas e criação de Extraction (o artigo dividido em seções)."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.extractor.article import ExtractedArticle
    from projects.correction.extractor.models import Extraction


class ExtractionManagement:
    """Herdado por `Extraction`. Uso: `Extraction.find(sha256, version)`."""

    objects: ClassVar[models.Manager[Extraction]]

    @classmethod
    def find(cls, sha256: str, version: str) -> Extraction | None:
        return cls.objects.filter(sha256=sha256, version=version).first()

    @classmethod
    def cached_sample(cls, hashes: tuple[str, ...], version: str) -> dict[str, Extraction]:
        return {
            extraction.sha256: extraction
            for extraction in cls.objects.filter(sha256__in=hashes, version=version)
        }

    @classmethod
    def store(cls, sha256: str, version: str, article: ExtractedArticle) -> Extraction:
        """Guarda a extração; se outro run guardou a mesma antes, devolve a que já existe."""
        extraction, _ = cls.objects.get_or_create(
            sha256=sha256, version=version, defaults={"content": article.model_dump(mode="json")}
        )
        return extraction
