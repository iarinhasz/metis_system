"""Prompts do extractor, um arquivo `.md` por chamada, nesta pasta, com marcadores `<<nome>>`.

`str.format` fica de fora: os prompts podem ter chaves de JSON.
"""

import hashlib
import re
from functools import cache
from pathlib import Path
from typing import Final

PROMPTS_DIR: Final = Path(__file__).resolve().parent
MARKER: Final = re.compile(r"<<(\w+)>>")


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


@cache
def fingerprint() -> str:
    """Hash de todos os prompts desta pasta: entra na versão da extração guardada."""
    digest = hashlib.sha256()
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def render_prompt(template: str, **values: str) -> str:
    """Troca cada `<<nome>>` pelo valor; falta de valor ou marcador sobrando é erro."""
    markers = set(MARKER.findall(template))
    if missing := sorted(markers - values.keys()):
        raise ValueError(f"Faltam valores para os marcadores: {missing}")
    if unused := sorted(values.keys() - markers):
        raise ValueError(f"Valores sem marcador no prompt: {unused}")
    return MARKER.sub(lambda match: values[match.group(1)], template)
