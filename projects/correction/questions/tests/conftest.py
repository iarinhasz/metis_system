"""Recorte real do OpenAlex, sem rede externa nos testes."""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def recorded_topics() -> list[dict[str, Any]]:
    path = Path(__file__).parent / "data" / "openalex_topics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["results"])


@pytest.fixture
def taxonomy_file(tmp_path: Path, recorded_topics: list[dict[str, Any]]) -> Path:
    path = tmp_path / "topics.json"
    path.write_text(json.dumps(recorded_topics), encoding="utf-8")
    return path


@pytest.fixture
def recorded_catalog() -> dict[str, Any]:
    path = Path(__file__).parent / "data" / "openalex_catalog.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))
