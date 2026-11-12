"""Validação da DocumentConfig: uma config inválida falha já no import."""

from typing import Any

import pytest
from pydantic import ValidationError

from projects.correction.extractor.config import (
    DocumentConfig,
    InputStrategy,
    Provider,
    SectionDefinition,
    normalize_label,
)


def config(**overrides: Any) -> DocumentConfig:
    values: dict[str, Any] = {
        "name": "teste",
        "strategy": InputStrategy.PDF,
        "provider": Provider.GOOGLE,
        "model": "modelo-x",
        "scan_prompt": "Liste os títulos.",
        "extraction_prompt": "Seção: <<title>>, termina <<end>>. Notas: <<footnotes>>",
        "references_prompt": "Separe: <<references>>",
        "figures_prompt": "Liste as figuras.",
        "required_sections": (SectionDefinition(key="abstract", labels=("Abstract", "Resumo")),),
        "optional_sections": (SectionDefinition(key="appendix", labels=("Apêndice",)),),
    }
    values.update(overrides)
    return DocumentConfig(**values)


def test_lists_required_then_optional_sections() -> None:
    assert [s.key for s in config().all_sections] == ["abstract", "appendix"]


@pytest.mark.parametrize("key", ["Abstract", "1abstract", "abstract-section", ""])
def test_section_key_must_be_snake_case(key: str) -> None:
    with pytest.raises(ValidationError, match="snake_case"):
        SectionDefinition(key=key, labels=("Abstract",))


@pytest.mark.parametrize("labels", [(), ("Abstract", "  ")])
def test_section_needs_non_blank_labels(labels: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        SectionDefinition(key="abstract", labels=labels)


def test_rejects_the_same_key_in_two_sections() -> None:
    with pytest.raises(ValidationError, match="chaves repetidas"):
        config(optional_sections=(SectionDefinition(key="abstract", labels=("Sumário",)),))


def test_rejects_the_same_label_in_two_sections() -> None:
    clash = SectionDefinition(key="summary", labels=("  resumo ",))

    with pytest.raises(ValidationError, match="não daria para saber"):
        config(optional_sections=(clash,))


@pytest.mark.parametrize("field", ["name", "model", "scan_prompt"])
def test_rejects_blank_values(field: str) -> None:
    with pytest.raises(ValidationError, match="valor vazio"):
        config(**{field: "   "})


@pytest.mark.parametrize("missing", ["<<title>>", "<<end>>", "<<footnotes>>"])
def test_extraction_prompt_needs_every_marker(missing: str) -> None:
    prompt = "Seção: <<title>>, termina <<end>>. Notas: <<footnotes>>".replace(missing, "")

    with pytest.raises(ValidationError, match=missing):
        config(extraction_prompt=prompt)


@pytest.mark.parametrize(
    "override",
    [
        {"max_parallel_calls": 0},
        {"min_coverage": 1.5},
        {"min_fidelity": -0.1},
        {"check_retries": -1},
    ],
)
def test_rejects_invalid_call_settings(override: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        config(**override)


def test_footnotes_are_ignored_by_default() -> None:
    assert config().ignore_footnotes is True


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        config(temperature=0.2)


def test_config_is_frozen() -> None:
    with pytest.raises(ValidationError):
        config().model = "outro"  # type: ignore[misc]


def test_normalizes_labels_for_comparison() -> None:
    assert normalize_label("  Referências   Bibliográficas ") == "referencias bibliograficas"


def test_references_prompt_needs_its_marker() -> None:
    with pytest.raises(ValidationError, match="<<references>>"):
        config(references_prompt="Separe a lista.")
