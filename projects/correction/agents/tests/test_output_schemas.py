"""Os schemas de saída do E4 e do E5 cabem na saída estruturada da OpenAI e do Gemini.

Cada provedor recusa o pedido inteiro por um detalhe do schema, e os testes com fakes não chamam
o provedor; por isso os dois casos só apareceram num run real:
- a OpenAI, um campo sem tipo, como um `dict[str, JsonValue]` (400 "schema must have a 'type'
  key");
- o SDK do Gemini, um `enum` que não é de texto, como `Literal[1, 2, 3, 4, 5]` na nota.
"""

from typing import Any

import pytest
from pydantic import BaseModel

from projects.correction.agents.schemas.consolidation import MetaReview
from projects.correction.agents.schemas.evaluation import (
    CriteriaSynthesis,
    CrossCheckResult,
    JudgeReport,
    RevisionResponse,
    SectionObservations,
)

TYPED_KEYS = ("type", "anyOf", "oneOf", "allOf", "$ref", "enum", "const")


def _untyped(schema: dict[str, Any], path: str = "#") -> list[str]:
    """Os subschemas sem tipo, como o `{}` que o `JsonValue` gera em `$defs`."""
    found = [] if any(key in schema for key in TYPED_KEYS) else [path]
    children: list[tuple[str, Any]] = [
        (f"{key}/{name}", child)
        for key in ("properties", "$defs")
        for name, child in (schema.get(key) or {}).items()
    ]
    children += [
        (f"{key}/{index}", child)
        for key in ("anyOf", "oneOf", "allOf")
        for index, child in enumerate(schema.get(key) or ())
    ]
    children += [
        (key, schema[key])
        for key in ("items", "additionalProperties")
        if isinstance(schema.get(key), dict)
    ]
    for name, child in children:
        found.extend(_untyped(child, f"{path}/{name}"))
    return found


def _non_text_enums(node: Any, path: str = "#") -> list[str]:
    if isinstance(node, list):
        return [p for i, item in enumerate(node) for p in _non_text_enums(item, f"{path}/{i}")]
    if not isinstance(node, dict):
        return []
    found = [path] if any(not isinstance(v, str) for v in node.get("enum", ())) else []
    for key, child in node.items():
        found.extend(_non_text_enums(child, f"{path}/{key}"))
    return found


SCHEMAS = [
    SectionObservations,
    CrossCheckResult,
    CriteriaSynthesis,
    JudgeReport,
    RevisionResponse,
    MetaReview,
]


@pytest.mark.parametrize("schema", SCHEMAS)
def test_every_field_has_a_type(schema: type[BaseModel]) -> None:
    assert _untyped(schema.model_json_schema()) == []


@pytest.mark.parametrize("schema", SCHEMAS)
def test_enums_are_text(schema: type[BaseModel]) -> None:
    assert _non_text_enums(schema.model_json_schema()) == []


def test_revision_replacement_is_one_of_the_revisable_items() -> None:
    replacement = RevisionResponse.model_json_schema()["properties"]["replacement"]
    refs = {option.get("$ref", "").rsplit("/", 1)[-1] for option in replacement["anyOf"]}
    assert refs == {"Observation", "CrossCheckResult", "CriterionSynthesis", ""}
