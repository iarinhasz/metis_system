"""Prompts em arquivo, com marcadores `<<nome>>`."""

import pytest

from projects.correction.extractor.prompts import load_prompt, render_prompt


def test_replaces_the_markers() -> None:
    assert render_prompt('Seções:\n<<sections>>\n{"json": 1}', sections="sec_1") == (
        'Seções:\nsec_1\n{"json": 1}'
    )


def test_marker_without_value_is_an_error() -> None:
    with pytest.raises(ValueError, match="sections"):
        render_prompt("Seções: <<sections>>")


def test_value_without_marker_is_an_error() -> None:
    with pytest.raises(ValueError, match="extra"):
        render_prompt("Sem marcador.", extra="x")


def test_loads_the_prompt_files() -> None:
    assert load_prompt("extract_section").count("<<title>>") == 1
