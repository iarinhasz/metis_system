"""Comando de geração controlada de fixtures PeerRead."""

import json
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

from django.core.management.base import OutputWrapper

from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.extractor.management.commands.make_peerread_fixtures import Command


def _peerread_row(number: int) -> dict[str, object]:
    return {
        "name": f"paper-{number}.json",
        "metadata": {
            "title": f"Paper {number}",
            "authors": ["Author"],
            "abstractText": "An abstract.",
            "sections": [{"heading": "Introduction", "text": "Body."}],
            "references": [],
            "referenceMentions": [],
        },
    }


def _write_source_data(source_dir: Path) -> None:
    data_dir = source_dir / "PeerRead-master/data/iclr/train/parsed_pdfs"
    data_dir.mkdir(parents=True)
    for number in range(10):
        path = data_dir / f"paper-{number}.json"
        path.write_text(json.dumps(_peerread_row(number)), encoding="utf-8")


def _write_source_archive(source_dir: Path) -> Path:
    source_dir.mkdir(parents=True)
    archive_path = source_dir / "PeerRead.zip"
    with ZipFile(archive_path, "w") as archive:
        for number in range(10):
            member = f"PeerRead-master/data/iclr/train/parsed_pdfs/paper-{number}.json"
            archive.writestr(member, json.dumps(_peerread_row(number)))
    return archive_path


def _invoke(command: Command, *, source: Path, output: Path, execute: bool) -> str:
    stream = StringIO()
    command.stdout = OutputWrapper(stream)
    command.handle(
        source_dir=source,
        output_dir=output,
        limit=10,
        execute=execute,
    )
    return stream.getvalue()


def test_peerread_fixture_command_defaults_to_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    output = tmp_path / "fixtures"
    _write_source_data(source)

    result = _invoke(Command(), source=source, output=output, execute=False)

    assert "Dry-run" in result
    assert not output.exists()


def test_peerread_fixture_command_writes_valid_documents_on_execute(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    output = tmp_path / "fixtures"
    _write_source_data(source)

    _invoke(Command(), source=source, output=output, execute=True)

    files = sorted(output.glob("*.json"))
    assert len(files) == 10
    documents = [ExtractedDocument.model_validate_json(path.read_text()) for path in files]
    assert documents[0].title == "Paper 0"
    assert documents[-1].title == "Paper 9"


def test_peerread_fixture_command_reads_jsons_from_zip(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    output = tmp_path / "fixtures"
    _write_source_archive(source)

    result = _invoke(Command(), source=source, output=output, execute=True)

    assert "PeerRead.zip:PeerRead-master/data/iclr/train/parsed_pdfs/paper-0.json" in result
    assert len(list(output.glob("*.json"))) == 10
