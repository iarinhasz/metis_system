"""Os schemas de resposta servem de saída estruturada: tudo obrigatório, nada além."""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from projects.correction.extractor.schemas import (
    DescribedFigure,
    FigureScan,
    HeadingScan,
    ParsedReferences,
    ScannedHeading,
    SectionContent,
)


def objects_in(schema: dict[str, Any]) -> list[dict[str, Any]]:
    found = [schema, *schema.get("$defs", {}).values()]
    return [node for node in found if node.get("type") == "object"]


@pytest.mark.parametrize(
    "model", [HeadingScan, SectionContent, ParsedReferences, FigureScan, DescribedFigure]
)
def test_every_field_is_required_and_nothing_else_is_accepted(model: type[BaseModel]) -> None:
    for node in objects_in(model.model_json_schema()):
        assert node["additionalProperties"] is False
        assert set(node["required"]) == set(node["properties"])


def test_heading_level_starts_at_one() -> None:
    with pytest.raises(ValidationError):
        ScannedHeading(title="Introdução", level=0)


def test_reads_a_scan_answer() -> None:
    answer = {
        "title": "Um estudo",
        "authors": ["Ada Lovelace"],
        "language": "pt",
        "headings": [
            {"title": "Resumo", "level": 1},
            {"title": "1 Introdução", "level": 1},
            {"title": "1.1 Contexto", "level": 2},
        ],
    }

    scan = HeadingScan.model_validate(answer)

    assert [(h.title, h.level) for h in scan.headings] == [
        ("Resumo", 1),
        ("1 Introdução", 1),
        ("1.1 Contexto", 2),
    ]
