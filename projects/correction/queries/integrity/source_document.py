"""Consultas e importação de SourceDocument e SourceChunk."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from django.db import models, transaction

from projects.correction.integrity.embeddings import EMBEDDING_DIMENSIONS

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from projects.correction.integrity.models import SourceChunk, SourceDocument


@dataclass(frozen=True)
class SourceChunkInput:
    section_id: str
    section_title: str
    section_key: str
    chunk_index: int
    text: str
    embedding: Sequence[float]


class SourceDocumentManagement:
    """Operações de corpus herdadas por `SourceDocument`."""

    objects: ClassVar[models.Manager[SourceDocument]]

    @classmethod
    def find_by_source_identifier(
        cls, source: str, source_identifier: str
    ) -> SourceDocument | None:
        return cls.objects.filter(source=source, source_identifier=source_identifier).first()

    @classmethod
    def by_source(cls, source: str) -> QuerySet[SourceDocument]:
        return cls.objects.filter(source=source)

    @classmethod
    def import_with_chunks(
        cls,
        *,
        source: str,
        source_identifier: str,
        title: str,
        doi: str | None,
        authors: list[str],
        metadata: dict[str, object],
        chunks: Sequence[SourceChunkInput],
    ) -> tuple[SourceDocument, bool]:
        from projects.correction.integrity.models import SourceChunk

        with transaction.atomic():
            document, created = cls.objects.get_or_create(
                source=source,
                source_identifier=source_identifier,
                defaults={
                    "title": title,
                    "doi": doi,
                    "authors": authors,
                    "source_metadata": metadata,
                },
            )
            if not created:
                return document, False

            SourceChunk.objects.bulk_create(
                [
                    SourceChunk(
                        document=document,
                        section_id=chunk.section_id,
                        section_title=chunk.section_title,
                        section_key=chunk.section_key,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        embedding=list(chunk.embedding),
                    )
                    for chunk in chunks
                ]
            )
        return document, True


class SourceChunkManagement:
    """Busca vetorial dos chunks do corpus."""

    objects: ClassVar[models.Manager[SourceChunk]]

    @classmethod
    def by_source(cls, source: str) -> QuerySet[SourceChunk]:
        return cls.objects.filter(document__source=source)

    @classmethod
    def nearest_by_embedding(
        cls, embedding: Sequence[float], *, limit: int = 10
    ) -> QuerySet[SourceChunk]:
        from pgvector.django import CosineDistance

        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"O vetor deve ter {EMBEDDING_DIMENSIONS} dimensões.")
        if limit < 1:
            raise ValueError("limit deve ser maior que zero.")
        return cls.objects.annotate(
            cosine_distance=CosineDistance("embedding", list(embedding))
        ).order_by("cosine_distance")[:limit]
