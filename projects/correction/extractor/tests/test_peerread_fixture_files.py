"""As fixtures do PeerRead versionadas validam no contrato e servem para os testes da avaliação."""

import json
from pathlib import Path

import pytest

from projects.correction.extractor.contract import ExtractedDocument

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "peerread").glob("peerread-*.json"))


def test_there_are_ten_to_twenty_fixtures() -> None:
    assert 10 <= len(FIXTURES) <= 20


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_each_fixture_loads_as_a_document_and_renders(path: Path) -> None:
    document = ExtractedDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))

    assert document.sections and document.abstract
    blocks = document.render_for_llm()
    assert blocks and all(blocks)
