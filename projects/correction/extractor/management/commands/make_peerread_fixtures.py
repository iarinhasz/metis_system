"""Gera fixtures locais do PeerRead para validar o contrato do E1."""

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from projects.correction.extractor.peerread import peerread_to_document


@dataclass(frozen=True)
class PeerReadFile:
    container: Path
    member: str | None = None

    def read_bytes(self) -> bytes:
        if self.member is None:
            return self.container.read_bytes()
        with zipfile.ZipFile(self.container) as archive:
            return archive.read(self.member)

    def __str__(self) -> str:
        if self.member is None:
            return str(self.container)
        return f"{self.container}:{self.member}"


class Command(BaseCommand):
    help = "Prepara fixtures ExtractedDocument do PeerRead (sem gravar por padrão)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--source-dir",
            type=Path,
            default=Path("dataset_project/raw"),
            help="Diretório com o zip do PeerRead ou JSONs parsed_pdfs extraídos.",
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("projects/correction/extractor/tests/fixtures/peerread"),
            help="Diretório de destino das fixtures.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            choices=range(10, 21),
            metavar="10..20",
            help="Quantidade de artigos válidos (padrão: 10).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Grava os arquivos. Sem esta opção, apenas valida e mostra o plano.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source_dir: Path = options["source_dir"]
        output_dir: Path = options["output_dir"]
        limit: int = options["limit"]
        sources = _peerread_sources(source_dir)
        if not sources:
            raise CommandError(
                f"Nenhum JSON parsed_pdfs ou zip do PeerRead encontrado em {source_dir}. "
                "Coloque o arquivo em dataset_project/raw e tente novamente."
            )

        documents = []
        errors = []
        for source_file in sources:
            try:
                row = json.loads(source_file.read_bytes())
                document = peerread_to_document(row)
            except (
                OSError,
                zipfile.BadZipFile,
                KeyError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                errors.append(f"{source_file}: {exc}")
                continue
            documents.append((source_file, document))
            if len(documents) == limit:
                break

        if len(documents) < limit:
            detail = "\n".join(errors[:5])
            suffix = f"\nPrimeiros registros inválidos:\n{detail}" if detail else ""
            raise CommandError(
                f"Foram encontrados apenas {len(documents)} artigos válidos; "
                f"são necessários {limit}.{suffix}"
            )

        self.stdout.write(f"{len(documents)} documentos validados para fixture:")
        for index, (source_file, document) in enumerate(documents, start=1):
            output = output_dir / f"peerread-{index:02d}.json"
            self.stdout.write(f"  {source_file} -> {output} | {document.title}")

        if not options["execute"]:
            self.stdout.write(
                self.style.WARNING("Dry-run: nenhum arquivo foi gravado. Use --execute.")
            )
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        for index, (_, document) in enumerate(documents, start=1):
            output = output_dir / f"peerread-{index:02d}.json"
            output.write_text(
                document.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
        self.stdout.write(self.style.SUCCESS(f"Fixtures gravadas em {output_dir}."))


def _peerread_sources(source_dir: Path) -> list[PeerReadFile]:
    if not source_dir.exists():
        return []
    if source_dir.is_file():
        json_paths: list[Path] = []
        archives = [source_dir] if zipfile.is_zipfile(source_dir) else []
    else:
        json_paths = sorted(
            path for path in source_dir.rglob("*.json") if path.parent.name == "parsed_pdfs"
        )
        if json_paths:
            return [PeerReadFile(path) for path in json_paths]
        archives = sorted(source_dir.rglob("*.zip"))

    sources = [PeerReadFile(path) for path in json_paths]
    for archive_path in archives:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                members = sorted(
                    name
                    for name in archive.namelist()
                    if name.endswith(".json") and "parsed_pdfs" in name.split("/")
                )
        except zipfile.BadZipFile:
            continue
        sources.extend(PeerReadFile(archive_path, member) for member in members)
    return sources
