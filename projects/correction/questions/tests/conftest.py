"""Recorte real do OpenAlex, sem rede externa nos testes."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import (
    SYNTHETIC_SUBFIELD,
    SYNTHETIC_TOPIC,
)
from projects.correction.scholarly.openalex import OpenAlexTopic


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


@pytest.fixture
def profiling_taxonomy(recorded_topics: list[dict[str, Any]]) -> TaxonomySnapshot:
    extra = deepcopy(recorded_topics[0])
    extra["id"] = SYNTHETIC_TOPIC
    extra["display_name"] = "Topic sintético para testar parentesco"
    extra["subfield"] = {"id": SYNTHETIC_SUBFIELD, "display_name": "Subfield sintético"}
    topics = tuple(TypeAdapter(list[OpenAlexTopic]).validate_python([*recorded_topics, extra]))
    snapshot = TaxonomySnapshot.from_topics(topics)
    TaxonomyNode.import_snapshot(snapshot)
    return snapshot
