from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
from pathlib import Path
from typing import ClassVar

import pytest
from django.core.management import call_command

from projects.correction.extractor.contract import DocumentSection, ExtractedDocument
from projects.correction.integrity import embeddings
from projects.correction.integrity.embeddings import EMBEDDING_DIMENSIONS
from projects.correction.integrity.models import SourceChunk, SourceDocument
from projects.correction.queries.integrity.source_document import SourceChunkInput

pytestmark = pytest.mark.django_db


def _document(number: int) -> ExtractedDocument:
    return ExtractedDocument(
        title=f"PeerRead article {number}",
        authors=("Author",),
        language="en",
        abstract=f"Abstract content for article {number}.",
        sections=(
            DocumentSection(
                id="sec_1",
                title="Introduction",
                level=1,
                text=f"Introduction content for article {number}.",
            ),
        ),
    )


def _write_fixtures(directory: Path, count: int = 5) -> None:
    directory.mkdir(parents=True)
    for number in range(count):
        (directory / f"peerread-{number + 1:02d}.json").write_text(
            _document(number).model_dump_json(),
            encoding="utf-8",
        )


def test_load_peerread_dry_run_does_not_write_or_embed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "fixtures"
    _write_fixtures(source)

    def fail_if_embedded(texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise AssertionError("Dry-run não deve carregar nem executar o modelo.")

    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.load_peerread.embed_documents",
        fail_if_embedded,
    )
    output = StringIO()

    call_command("load_peerread", source_dir=source, stdout=output)

    assert "5 artigos validados" in output.getvalue()
    assert "Dry-run" in output.getvalue()
    assert SourceDocument.by_source("peerread").count() == 0
    assert SourceChunk.by_source("peerread").count() == 0


def test_load_peerread_imports_five_articles_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "fixtures"
    _write_fixtures(source)

    def fake_embeddings(texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if index == 0 else 0.0 for index in range(EMBEDDING_DIMENSIONS)] for _ in texts
        ]

    monkeypatch.setattr(
        "projects.correction.integrity.management.commands.load_peerread.embed_documents",
        fake_embeddings,
    )

    call_command("load_peerread", source_dir=source, execute=True)
    call_command("load_peerread", source_dir=source, execute=True)

    assert SourceDocument.by_source("peerread").count() == 5
    assert SourceChunk.by_source("peerread").count() == 10
    first_chunk = SourceChunk.by_source("peerread").first()
    assert first_chunk is not None
    assert first_chunk.section_key == "abstract"
    assert len(first_chunk.embedding) == EMBEDDING_DIMENSIONS


def test_similarity_search_orders_chunks_by_cosine_distance() -> None:
    vectors = [
        [1.0, *[0.0] * (EMBEDDING_DIMENSIONS - 1)],
        [0.0, 1.0, *[0.0] * (EMBEDDING_DIMENSIONS - 2)],
        [-1.0, *[0.0] * (EMBEDDING_DIMENSIONS - 1)],
    ]
    document, created = SourceDocument.import_with_chunks(
        source="test",
        source_identifier="vector-search",
        title="Vector search test",
        doi=None,
        authors=[],
        metadata={},
        chunks=[
            SourceChunkInput(
                section_id="sec_1",
                section_title="Section",
                section_key="section",
                chunk_index=index,
                text=f"Chunk {index}",
                embedding=vector,
            )
            for index, vector in enumerate(vectors)
        ],
    )

    assert created
    nearest = list(SourceChunk.nearest_by_embedding(vectors[0], limit=3))

    assert [chunk.text for chunk in nearest] == ["Chunk 0", "Chunk 1", "Chunk 2"]
    assert all(chunk.document_id == document.pk for chunk in nearest)


def test_embeddings_use_multilingual_e5_query_and_passage_prefixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeEmbedder:
        inputs: ClassVar[list[str]] = []

        def embed(self, documents: list[str]) -> list[Sequence[float]]:
            self.inputs.extend(documents)
            return [[0.25] * EMBEDDING_DIMENSIONS for _ in documents]

    monkeypatch.setattr(embeddings, "_model", FakeEmbedder())

    assert len(embeddings.embed_documents(["artigo"])) == 1
    assert len(embeddings.embed_query("consulta")) == EMBEDDING_DIMENSIONS
    assert FakeEmbedder.inputs == ["passage: artigo", "query: consulta"]


def test_similarity_search_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="dimensões"):
        SourceChunk.nearest_by_embedding([1.0])
    with pytest.raises(ValueError, match="limit"):
        SourceChunk.nearest_by_embedding([0.0] * EMBEDDING_DIMENSIONS, limit=0)
