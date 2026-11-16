"""Geração local de embeddings multilíngues com FastEmbed."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from threading import Lock
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fastembed import TextEmbedding

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIMENSIONS = 1024
MAX_CHUNK_WORDS = 300


class TextEmbedder(Protocol):
    def embed(self, documents: list[str]) -> Iterable[Sequence[float]]: ...


class _FastEmbedder:
    def __init__(self, model: TextEmbedding) -> None:
        self._model = model

    def embed(self, documents: list[str]) -> Iterable[Sequence[float]]:
        for vector in self._model.embed(documents):
            yield [float(value) for value in vector.tolist()]


_model: TextEmbedder | None = None
_model_lock = Lock()


def _get_model() -> TextEmbedder:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from fastembed import TextEmbedding

                _model = _FastEmbedder(TextEmbedding(model_name=EMBEDDING_MODEL))
    return _model


def embed_documents(texts: Sequence[str]) -> list[list[float]]:
    """Gera vetores de passagem, carregando o modelo apenas no primeiro uso."""
    if not texts:
        return []
    model_inputs = [f"passage: {text}" for text in texts]
    vectors = [[float(value) for value in vector] for vector in _get_model().embed(model_inputs)]
    if len(vectors) != len(texts) or any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
        raise ValueError(
            f"{EMBEDDING_MODEL} deve devolver um vetor de {EMBEDDING_DIMENSIONS} "
            "dimensões para cada texto."
        )
    return vectors


def embed_query(text: str) -> list[float]:
    """Gera o vetor de consulta com o prefixo exigido pelo modelo E5."""
    if not text.strip():
        raise ValueError("A consulta de embedding não pode ser vazia.")
    vectors = [
        [float(value) for value in vector] for vector in _get_model().embed([f"query: {text}"])
    ]
    if len(vectors) != 1 or len(vectors[0]) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"{EMBEDDING_MODEL} deve devolver um vetor de {EMBEDDING_DIMENSIONS} dimensões."
        )
    return vectors[0]
