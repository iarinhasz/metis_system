"""Carrega documentos PeerRead validados no corpus local de similaridade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import ValidationError

from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.embeddings import MAX_CHUNK_WORDS, embed_documents
from projects.correction.integrity.models import SourceDocument
from projects.correction.queries.integrity.source_document import (
    SourceChunkInput,
)

DEFAULT_FIXTURES = Path("projects/correction/extractor/tests/fixtures/peerread")
SOURCE_NAME = "peerread"


@dataclass(frozen=True)
class PreparedChunk:
    section_id: str
    section_title: str
    section_key: str
    chunk_index: int
    text: str


class Command(BaseCommand):
    help = "Carrega fixtures PeerRead no corpus vetorial; grava somente com --execute."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source-dir",
            type=Path,
            default=DEFAULT_FIXTURES,
            help="Diretório de fixtures ExtractedDocument do PeerRead.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Número máximo de artigos para processar (padrão: 5).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Gera embeddings e grava no banco. Sem esta opção, apenas valida.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source_dir: Path = options["source_dir"]
        limit: int = options["limit"]
        if limit < 1:
            raise CommandError("--limit deve ser maior que zero.")
        if not source_dir.is_dir():
            raise CommandError(f"Diretório de fixtures PeerRead não encontrado: {source_dir}.")

        fixture_paths = sorted(source_dir.glob("*.json"))[:limit]
        if not fixture_paths:
            raise CommandError(f"Nenhuma fixture JSON encontrada em {source_dir}.")
        if len(fixture_paths) < limit:
            raise CommandError(
                f"Foram encontradas {len(fixture_paths)} fixtures; "
                f"são necessárias {limit} para esta carga."
            )

        documents: list[tuple[Path, ExtractedDocument, list[PreparedChunk]]] = []
        for path in fixture_paths:
            try:
                document = ExtractedDocument.model_validate_json(path.read_bytes())
            except (OSError, ValueError, ValidationError) as exc:
                raise CommandError(f"Fixture PeerRead inválida: {path}.") from exc
            chunks = _document_chunks(document)
            if not chunks:
                raise CommandError(f"A fixture não contém texto para indexar: {path}.")
            documents.append((path, document, chunks))

        self.stdout.write(
            f"{len(documents)} artigos validados; "
            f"{sum(len(chunks) for _, _, chunks in documents)} chunks planejados."
        )
        if not options["execute"]:
            self.stdout.write("Dry-run: nenhuma escrita ou inferência foi feita. Use --execute.")
            return

        imported = 0
        skipped = 0
        for path, document, chunks in documents:
            source_identifier = path.name
            if SourceDocument.find_by_source_identifier(SOURCE_NAME, source_identifier):
                skipped += 1
                continue

            vectors = embed_documents([chunk.text for chunk in chunks])
            embedded_chunks = [
                SourceChunkInput(
                    section_id=chunk.section_id,
                    section_title=chunk.section_title,
                    section_key=chunk.section_key,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            _, created = SourceDocument.import_with_chunks(
                source=SOURCE_NAME,
                source_identifier=source_identifier,
                title=document.title,
                doi=None,
                authors=list(document.authors),
                metadata={
                    "language": document.language,
                    "contract_version": document.contract_version,
                },
                chunks=embedded_chunks,
            )
            imported += int(created)
            skipped += int(not created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Corpus atualizado: {imported} artigos importados, {skipped} já existentes."
            )
        )


def _document_chunks(document: ExtractedDocument) -> list[PreparedChunk]:
    sections: list[tuple[str, str, str, str]] = [
        ("abstract", "Abstract", "abstract", document.abstract),
        *(
            (section.id, section.title, section.key or "", section.text)
            for section in document.sections
        ),
    ]
    chunks: list[PreparedChunk] = []
    for section_id, title, key, text in sections:
        words = text.split()
        for start in range(0, len(words), MAX_CHUNK_WORDS):
            chunk_words = words[start : start + MAX_CHUNK_WORDS]
            if chunk_words:
                chunks.append(
                    PreparedChunk(
                        section_id=section_id,
                        section_title=title,
                        section_key=key,
                        chunk_index=len(chunks),
                        text=" ".join(chunk_words),
                    )
                )
    return chunks
