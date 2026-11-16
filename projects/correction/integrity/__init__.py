"""Corpus e utilitários públicos de checagem de integridade."""

from typing import TYPE_CHECKING

from projects.correction.integrity.embeddings import embed_documents, embed_query

if TYPE_CHECKING:
    from projects.correction.integrity.models import SourceChunk, SourceDocument

__all__ = ("SourceChunk", "SourceDocument", "embed_documents", "embed_query")


def __getattr__(name: str) -> object:
    if name in {"SourceChunk", "SourceDocument"}:
        from projects.correction.integrity.models import SourceChunk, SourceDocument

        return {"SourceChunk": SourceChunk, "SourceDocument": SourceDocument}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
