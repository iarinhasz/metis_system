"""Semantic alignment of manuscript passages with the local vector corpus."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from math import sqrt
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.embeddings import embed_documents, embed_query

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


class SemanticConfig(BaseModel):
    """Thresholds for vector candidate retrieval and sentence alignment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nearest_chunks: int = Field(default=5, ge=1)
    similarity_threshold: float = Field(default=0.82, gt=0, le=1)
    min_aligned_sentences: int = Field(default=2, ge=1)


class SentenceAlignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_text: str
    source_text: str
    target_start: int = Field(ge=0)
    target_end: int = Field(ge=0)
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    similarity: float = Field(ge=0, le=1)


class SemanticOverlap(BaseModel):
    """A monotonic set of semantically aligned manuscript and corpus sentences."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_section_id: str
    target_section_title: str
    target_start: int = Field(ge=0)
    target_end: int = Field(ge=0)
    target_text: str
    source_document_id: str
    source_identifier: str
    source_title: str
    source_section_id: str
    source_section_title: str
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    source_text: str
    source_language: str | None = None
    target_language: str
    cross_language: bool | None = None
    similarity: float = Field(ge=0, le=1)
    alignments: tuple[SentenceAlignment, ...] = Field(min_length=1)


class CorpusDocument(Protocol):
    @property
    def pk(self) -> object: ...

    @property
    def source_identifier(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def source_metadata(self) -> dict[str, object]: ...


class CorpusChunk(Protocol):
    @property
    def pk(self) -> object: ...

    @property
    def text(self) -> str: ...

    @property
    def section_id(self) -> str: ...

    @property
    def section_title(self) -> str: ...

    @property
    def document(self) -> CorpusDocument: ...


class ChunkSearch(Protocol):
    def __call__(self, embedding: Sequence[float], *, limit: int = 10) -> Iterable[CorpusChunk]: ...


QueryEmbedder = Callable[[str], Sequence[float]]
PassageEmbedder = Callable[[Sequence[str]], Sequence[Sequence[float]]]


@dataclass(frozen=True)
class _TextSpan:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class _TargetParagraph:
    section_id: str
    section_title: str
    text: str
    start: int
    sentences: tuple[_TextSpan, ...]


def find_semantic_overlaps(
    document: ExtractedDocument,
    *,
    config: SemanticConfig | None = None,
    chunk_search: ChunkSearch | None = None,
    query_embedder: QueryEmbedder | None = None,
    passage_embedder: PassageEmbedder | None = None,
) -> tuple[SemanticOverlap, ...]:
    """Find high-similarity sentence sequences through HNSW corpus candidates.

    Each manuscript paragraph retrieves its nearest stored chunks using the
    repository's cosine-HNSW query. Candidate sentences are then embedded and
    aligned monotonically in both documents; unrelated text from the same topic
    does not pass unless the sentence-level cosine threshold is met.
    """
    selected_config = config or SemanticConfig()
    search = chunk_search or _default_chunk_search()
    embed_query_text = query_embedder or embed_query
    embed_passages = passage_embedder or embed_documents
    paragraphs = _target_paragraphs(document)
    source_vectors: dict[str, Sequence[float]] = {}
    found: dict[tuple[str, str, int, int], SemanticOverlap] = {}

    for paragraph in paragraphs:
        target_vectors = tuple(embed_query_text(sentence.text) for sentence in paragraph.sentences)
        candidate_chunks = search(
            embed_query_text(paragraph.text), limit=selected_config.nearest_chunks
        )
        for chunk in candidate_chunks:
            source_sentences = _sentence_spans(chunk.text, 0)
            if not source_sentences:
                continue
            missing = [
                sentence.text
                for sentence in source_sentences
                if sentence.text not in source_vectors
            ]
            if missing:
                vectors = embed_passages(missing)
                if len(vectors) != len(missing):
                    raise ValueError("O embedder deve devolver um vetor para cada frase-fonte.")
                source_vectors.update(zip(missing, vectors, strict=True))

            similarities = tuple(
                tuple(
                    _cosine_similarity(target_vector, source_vectors[source_sentence.text])
                    for source_sentence in source_sentences
                )
                for target_vector in target_vectors
            )
            matrix = _mutual_nearest_matrix(similarities, selected_config.similarity_threshold)
            aligned = _monotonic_alignment(matrix, selected_config.similarity_threshold)
            if len(aligned) < selected_config.min_aligned_sentences:
                continue
            overlap = _make_overlap(document, paragraph, chunk, source_sentences, aligned)
            key = (
                overlap.source_document_id,
                str(chunk.pk),
                overlap.target_start,
                overlap.target_end,
            )
            previous = found.get(key)
            if previous is None or overlap.similarity > previous.similarity:
                found[key] = overlap

    return tuple(
        sorted(
            found.values(),
            key=lambda item: (
                item.target_section_id,
                item.target_start,
                item.source_document_id,
                item.source_start,
            ),
        )
    )


def _default_chunk_search() -> ChunkSearch:
    from projects.correction.integrity.models import SourceChunk

    return SourceChunk.nearest_by_embedding


def _target_paragraphs(document: ExtractedDocument) -> tuple[_TargetParagraph, ...]:
    sections = [("abstract", "Abstract", document.abstract)]
    sections.extend((section.id, section.title, section.text) for section in document.sections)
    paragraphs: list[_TargetParagraph] = []
    for section_id, title, text in sections:
        start = 0
        for boundary in _PARAGRAPH_BREAK.finditer(text):
            _append_target_paragraph(paragraphs, section_id, title, text, start, boundary.start())
            start = boundary.end()
        _append_target_paragraph(paragraphs, section_id, title, text, start, len(text))
    return tuple(paragraphs)


def _append_target_paragraph(
    paragraphs: list[_TargetParagraph],
    section_id: str,
    title: str,
    text: str,
    start: int,
    end: int,
) -> None:
    raw = text[start:end]
    leading = len(raw) - len(raw.lstrip())
    paragraph_text = raw.strip()
    if not paragraph_text:
        return
    paragraph_start = start + leading
    sentences = _sentence_spans(paragraph_text, paragraph_start)
    if sentences:
        paragraphs.append(
            _TargetParagraph(
                section_id=section_id,
                section_title=title,
                text=paragraph_text,
                start=paragraph_start,
                sentences=sentences,
            )
        )


def _sentence_spans(text: str, offset: int) -> tuple[_TextSpan, ...]:
    spans: list[_TextSpan] = []
    start = 0
    for boundary in _SENTENCE_BREAK.finditer(text):
        _append_sentence(spans, text, start, boundary.start(), offset)
        start = boundary.end()
    _append_sentence(spans, text, start, len(text), offset)
    return tuple(spans)


def _append_sentence(spans: list[_TextSpan], text: str, start: int, end: int, offset: int) -> None:
    raw = text[start:end]
    leading = len(raw) - len(raw.lstrip())
    sentence = raw.strip()
    if sentence:
        sentence_start = start + leading
        spans.append(
            _TextSpan(
                text=sentence,
                start=offset + sentence_start,
                end=offset + sentence_start + len(sentence),
            )
        )


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Os vetores de frases devem ter a mesma dimensão.")
    left_values = tuple(float(value) for value in left)
    right_values = tuple(float(value) for value in right)
    left_squared_norm = 0.0
    right_squared_norm = 0.0
    for left_value, right_value in zip(left_values, right_values, strict=True):
        left_squared_norm += left_value * left_value
        right_squared_norm += right_value * right_value
    left_norm = sqrt(left_squared_norm)
    right_norm = sqrt(right_squared_norm)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = 0.0
    for left_value, right_value in zip(left_values, right_values, strict=True):
        dot_product += left_value * right_value
    score = dot_product / (left_norm * right_norm)
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return score


def _mutual_nearest_matrix(
    similarities: Sequence[Sequence[float]], threshold: float
) -> tuple[tuple[float, ...], ...]:
    if not similarities or not similarities[0]:
        return ()
    target_count = len(similarities)
    source_count = len(similarities[0])
    target_best = [
        max(range(source_count), key=lambda source_index: similarities[target_index][source_index])
        for target_index in range(target_count)
    ]
    source_best = [
        max(range(target_count), key=lambda target_index: similarities[target_index][source_index])
        for source_index in range(source_count)
    ]
    return tuple(
        tuple(
            score
            if score >= threshold
            and target_best[target_index] == source_index
            and source_best[source_index] == target_index
            else 0.0
            for source_index, score in enumerate(row)
        )
        for target_index, row in enumerate(similarities)
    )


def _monotonic_alignment(
    similarities: Sequence[Sequence[float]], threshold: float
) -> tuple[tuple[int, int, float], ...]:
    target_count = len(similarities)
    source_count = len(similarities[0]) if target_count else 0
    scores = [[0.0] * (source_count + 1) for _ in range(target_count + 1)]
    choices = [[""] * (source_count + 1) for _ in range(target_count + 1)]

    for target_index in range(1, target_count + 1):
        for source_index in range(1, source_count + 1):
            best = scores[target_index - 1][source_index]
            choice = "target"
            if scores[target_index][source_index - 1] > best:
                best = scores[target_index][source_index - 1]
                choice = "source"
            similarity = similarities[target_index - 1][source_index - 1]
            if similarity >= threshold:
                matched = scores[target_index - 1][source_index - 1] + similarity
                if matched >= best:
                    best = matched
                    choice = "match"
            scores[target_index][source_index] = best
            choices[target_index][source_index] = choice

    aligned: list[tuple[int, int, float]] = []
    target_index, source_index = target_count, source_count
    while target_index and source_index:
        choice = choices[target_index][source_index]
        if choice == "match":
            aligned.append(
                (
                    target_index - 1,
                    source_index - 1,
                    similarities[target_index - 1][source_index - 1],
                )
            )
            target_index -= 1
            source_index -= 1
        elif choice == "target":
            target_index -= 1
        else:
            source_index -= 1
    return tuple(reversed(aligned))


def _make_overlap(
    document: ExtractedDocument,
    paragraph: _TargetParagraph,
    chunk: CorpusChunk,
    source_sentences: tuple[_TextSpan, ...],
    aligned: tuple[tuple[int, int, float], ...],
) -> SemanticOverlap:
    first_target, first_source, _ = aligned[0]
    last_target, last_source, _ = aligned[-1]
    target_first = paragraph.sentences[first_target]
    target_last = paragraph.sentences[last_target]
    source_first = source_sentences[first_source]
    source_last = source_sentences[last_source]
    target_start = target_first.start
    target_end = target_last.end
    source_start = source_first.start
    source_end = source_last.end
    alignment_details = tuple(
        SentenceAlignment(
            target_text=paragraph.sentences[target_index].text,
            source_text=source_sentences[source_index].text,
            target_start=paragraph.sentences[target_index].start,
            target_end=paragraph.sentences[target_index].end,
            source_start=source_sentences[source_index].start,
            source_end=source_sentences[source_index].end,
            similarity=similarity,
        )
        for target_index, source_index, similarity in aligned
    )
    metadata = chunk.document.source_metadata
    source_language_value = metadata.get("language")
    source_language = (
        source_language_value.casefold()
        if isinstance(source_language_value, str) and source_language_value
        else None
    )
    return SemanticOverlap(
        target_section_id=paragraph.section_id,
        target_section_title=paragraph.section_title,
        target_start=target_start,
        target_end=target_end,
        target_text=paragraph.text[target_start - paragraph.start : target_end - paragraph.start],
        source_document_id=str(chunk.document.pk),
        source_identifier=chunk.document.source_identifier,
        source_title=chunk.document.title,
        source_section_id=chunk.section_id,
        source_section_title=chunk.section_title,
        source_start=source_start,
        source_end=source_end,
        source_text=chunk.text[source_start:source_end],
        source_language=source_language,
        target_language=document.language,
        cross_language=(
            source_language != document.language.casefold() if source_language is not None else None
        ),
        similarity=sum(item[2] for item in aligned) / len(aligned),
        alignments=alignment_details,
    )
