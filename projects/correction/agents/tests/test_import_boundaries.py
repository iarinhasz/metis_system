"""D16: SDKs centralizados e nenhuma dependência dos agentes nos domínios."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

CORRECTION = Path(__file__).resolve().parents[2]


def violations(source: str, relative: Path) -> list[str]:
    inside_agents = relative.parts[0] == "agents"
    package = "projects.correction." + ".".join(relative.parent.parts)
    errors: list[str] = []
    for node in ast.walk(ast.parse(source)):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = resolve_name("." * node.level + base, package)
            names = [base, *(f"{base}.{alias.name}" for alias in node.names)]
        else:
            continue
        for name in names:
            if not inside_agents:
                if name == "agno" or name.startswith(("agno.agent", "agno.models")):
                    errors.append(
                        f"{relative}:{node.lineno}: criação de agente/modelo fora de agents"
                    )
                if name.startswith("agno.workflow") and relative.name != "workflow.py":
                    errors.append(f"{relative}:{node.lineno}: workflow fora de workflow.py")
            elif name.startswith("projects.correction."):
                owner = name.split(".")[2]
                # A reexportação desta exceção é o contrato explícito da etapa 1.3.
                shared_error = name in {
                    "projects.correction.pipeline.errors",
                    "projects.correction.pipeline.errors.LLMUnavailable",
                }
                if owner not in {"agents", "metis"} and not shared_error:
                    errors.append(f"{relative}:{node.lineno}: agents depende de {name}")
    return sorted(set(errors))


def test_project_import_boundaries() -> None:
    errors = [
        error
        for path in CORRECTION.rglob("*.py")
        for error in violations(path.read_text(encoding="utf-8"), path.relative_to(CORRECTION))
    ]
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    ("source", "path"),
    [
        ("from agno.agent import Agent", "extractor/session.py"),
        ("import agno.models.google", "extractor/session.py"),
        ("from agno import models", "extractor/session.py"),
        ("from agno.workflow import Step", "evaluation/steps.py"),
        ("from projects.correction.attempts.models import Run", "agents/factory.py"),
        ("from projects.correction import attempts", "agents/factory.py"),
        ("from ..extractor import models", "agents/factory.py"),
    ],
)
def test_boundary_guard_detects_absolute_relative_and_parent_imports(
    source: str, path: str
) -> None:
    assert violations(source, Path(path))


def test_workflow_and_canonical_error_imports_are_allowed() -> None:
    assert not violations("from agno.workflow import Step", Path("evaluation/workflow.py"))
    assert not violations(
        "from projects.correction.pipeline.errors import LLMUnavailable", Path("agents/errors.py")
    )
