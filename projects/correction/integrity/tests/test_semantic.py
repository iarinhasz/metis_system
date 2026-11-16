from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace

import pytest

from projects.correction.extractor.contract import DocumentSection, ExtractedDocument
from projects.correction.integrity.semantic import (
    SemanticConfig,
    find_semantic_overlaps,
)

PORTUGUESE = (
    "A equipe avaliou o m?todo proposto.",
    "Os resultados indicam melhor precis?o.",
)
ENGLISH = (
    "The team evaluated the proposed method.",
    "The results indicate improved accuracy.",
)


def _document(text: str, *, language: str = "pt") -> ExtractedDocument:
    return ExtractedDocument(
        title="Evaluation",
        authors=("Author",),
        language=language,
        abstract="Short abstract.",
        sections=(
            DocumentSection(
                id="sec_results",
                title="Results",
                level=1,
                key="results",
                text=text,
            ),
        ),
    )


class FakeVectors:
    def __init__(
        self,
        query_vectors: dict[str, Sequence[float]],
        passage_vectors: dict[str, Sequence[float]],
    ) -> None:
        self.query_vectors = query_vectors
        self.passage_vectors = passage_vectors

    def query(self, text: str) -> Sequence[float]:
        return self.query_vectors.get(text, (0.0, 0.0))

    def passages(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [self.passage_vectors[text] for text in texts]


def _chunk(text: str, *, language: str = "en") -> SimpleNamespace:
    return SimpleNamespace(
        pk=17,
        text=text,
        section_id="source-results",
        section_title="Results",
        document=SimpleNamespace(
            pk=4,
            source_identifier="peerread-04.json",
            title="A reference paper",
            source_metadata={"language": language},
        ),
    )


def test_finds_cross_language_translation_with_ordered_sentence_alignment() -> None:
    source_text = " ".join(ENGLISH)
    target_text = " ".join(PORTUGUESE)
    target_paragraph = f"Prefixo. {target_text} Encerramento."
    source_chunk = _chunk(source_text)
    vectors = FakeVectors(
        query_vectors={
            PORTUGUESE[0]: (1.0, 0.0),
            PORTUGUESE[1]: (0.0, 1.0),
            "Short abstract.": (0.0, 0.0),
            target_paragraph: (0.7, 0.7),
        },
        passage_vectors={
            ENGLISH[0]: (1.0, 0.0),
            ENGLISH[1]: (0.0, 1.0),
        },
    )
    requested_limits: list[int] = []

    def search(embedding: Sequence[float], *, limit: int = 10) -> tuple[SimpleNamespace, ...]:
        assert len(embedding) == 2
        requested_limits.append(limit)
        return (source_chunk,)

    overlaps = find_semantic_overlaps(
        _document(target_paragraph),
        config=SemanticConfig(nearest_chunks=3, similarity_threshold=0.8),
        chunk_search=search,
        query_embedder=vectors.query,
        passage_embedder=vectors.passages,
    )

    assert len(overlaps) == 1
    overlap = overlaps[0]
    target_start = target_paragraph.index(PORTUGUESE[0])
    assert overlap.target_text == target_text
    assert target_paragraph[overlap.target_start : overlap.target_end] == target_text
    assert overlap.source_text == source_text
    assert source_chunk.text[overlap.source_start : overlap.source_end] == source_text
    assert overlap.cross_language is True
    assert overlap.similarity == pytest.approx(1.0)
    assert [item.target_text for item in overlap.alignments] == list(PORTUGUESE)
    assert [item.source_text for item in overlap.alignments] == list(ENGLISH)
    assert overlap.target_start == target_start
    assert requested_limits == [3, 3]


def test_same_topic_without_sentence_similarity_does_not_pass_threshold() -> None:
    target_text = "The experiment studies model quality. Accuracy improved in the final run."
    source_text = "The paper discusses model quality. A model can be evaluated in many ways."
    vectors = FakeVectors(
        query_vectors={
            "Short abstract.": (0.0, 0.0),
            "The experiment studies model quality.": (1.0, 0.0),
            "Accuracy improved in the final run.": (0.0, 1.0),
            target_text: (0.7, 0.7),
        },
        passage_vectors={
            "The paper discusses model quality.": (0.0, 1.0),
            "A model can be evaluated in many ways.": (0.0, 1.0),
        },
    )

    overlaps = find_semantic_overlaps(
        _document(target_text, language="en"),
        chunk_search=lambda embedding, *, limit=10: (_chunk(source_text, language="en"),),
        query_embedder=vectors.query,
        passage_embedder=vectors.passages,
    )

    assert overlaps == ()


def test_only_monotonic_sentence_pairs_are_aligned() -> None:
    source_text = "An unrelated sentence. " + " ".join(ENGLISH)
    target_text = " ".join(PORTUGUESE)
    vectors = FakeVectors(
        query_vectors={
            PORTUGUESE[0]: (1.0, 0.0),
            PORTUGUESE[1]: (0.0, 1.0),
            "Short abstract.": (0.0, 0.0),
            target_text: (0.7, 0.7),
            "An unrelated sentence.": (0.3, 0.3),
        },
        passage_vectors={
            "An unrelated sentence.": (0.3, 0.3),
            ENGLISH[0]: (1.0, 0.0),
            ENGLISH[1]: (0.0, 1.0),
        },
    )
    overlaps = find_semantic_overlaps(
        _document(target_text),
        chunk_search=lambda embedding, *, limit=10: (_chunk(source_text),),
        query_embedder=vectors.query,
        passage_embedder=vectors.passages,
    )

    assert len(overlaps) == 1
    aligned_source_text = [item.source_text for item in overlaps[0].alignments]
    assert aligned_source_text == [ENGLISH[0], ENGLISH[1]]
    assert overlaps[0].source_text == " ".join(ENGLISH)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"nearest_chunks": 0},
        {"similarity_threshold": 0},
        {"similarity_threshold": 1.1},
        {"min_aligned_sentences": 0},
    ],
)
def test_semantic_config_rejects_invalid_thresholds(kwargs: dict[str, int | float]) -> None:
    with pytest.raises(ValueError):
        SemanticConfig(**kwargs)
