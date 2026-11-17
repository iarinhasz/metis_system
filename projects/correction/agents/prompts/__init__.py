"""Renderização sem str.format; o artigo só entra no payload, fora do hash."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from projects.correction.agents.schemas.examples import schema_example

PROMPT_DIR = Path(__file__).parent
MARKER = re.compile(r"<<([^<>]+)>>")


@dataclass(frozen=True)
class RenderedPrompt:
    text: str
    version: str


def render_text(template: str, **values: str) -> RenderedPrompt:
    text = MARKER.sub(lambda match: values.get(match[1], match[0]), template)
    if MARKER.search(text):
        raise ValueError("Marcador de prompt sem substituição.")
    return RenderedPrompt(text, hashlib.sha256(text.encode()).hexdigest())


def render(name: str, output_schema: type[BaseModel], **values: str) -> RenderedPrompt:
    return render_template(template(name), output_schema, **values)


def template(name: str) -> str:
    path = (PROMPT_DIR / f"{name}.md").resolve()
    if not path.is_relative_to(PROMPT_DIR.resolve()):
        raise ValueError("Caminho de prompt fora do catálogo.")
    return path.read_text(encoding="utf-8")


def render_template(text: str, output_schema: type[BaseModel], **values: str) -> RenderedPrompt:
    example = schema_example(output_schema).model_dump_json(indent=2)
    return render_text(text, **(values | {"example_json": example}))
