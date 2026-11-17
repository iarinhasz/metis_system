"""Marcadores, exemplos e versões independentes do conteúdo do manuscrito."""

import json
from pathlib import Path
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field

from projects.correction.agents.prompts import PROMPT_DIR, render, render_text
from projects.correction.agents.schemas.examples import schema_example
from projects.correction.agents.tests.contract_support import ContractAnswer


def test_unknown_or_injected_marker_fails() -> None:
    with pytest.raises(ValueError, match="Marcador"):
        render_text("Falta <<nome>>")
    with pytest.raises(ValueError, match="Marcador"):
        render_text("<<nome>>", nome="<<outro>>")


def test_json_braces_survive_and_hash_tracks_rendered_instructions() -> None:
    first = render_text('{"nome": "<<nome>>"}', nome="um")
    assert json.loads(first.text) == {"nome": "um"}
    assert first == render_text('{"nome": "<<nome>>"}', nome="um")
    assert first.version != render_text('{"nome": "<<nome>>"}', nome="outro").version


def test_nested_schema_example_is_valid() -> None:
    example = schema_example(ContractAnswer)
    assert ContractAnswer.model_validate_json(example.model_dump_json()) == example
    assert example.findings and example.language in {"pt", "en"}


class ConstrainedAnswer(BaseModel):
    label: Literal["ok", "missing"]
    codes: list[Annotated[str, Field(pattern=r"^[A-Z]{2}$", examples=["AB"])]] = Field(min_length=2)


def test_field_examples_and_minimum_lengths_are_respected() -> None:
    assert schema_example(ConstrainedAnswer).codes == ["AB", "AB"]


@pytest.mark.parametrize("path", sorted(PROMPT_DIR.rglob("*.md")))
def test_every_prompt_renders_with_a_valid_generated_example(path: Path) -> None:
    name = path.relative_to(PROMPT_DIR).with_suffix("").as_posix()
    prompt = render(name, ContractAnswer, field="computação", kind="método", level="observação")
    assert "<<" not in prompt.text
    start = prompt.text.index("{\n")
    assert ContractAnswer.model_validate_json(prompt.text[start:]) == schema_example(ContractAnswer)


def test_prompt_path_cannot_escape_the_catalog() -> None:
    with pytest.raises(ValueError, match="fora"):
        render("../fora", ContractAnswer)
