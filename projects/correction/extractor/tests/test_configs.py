"""A config do artigo científico."""

from projects.correction.extractor.config import (
    EXTRACTION_MARKERS,
    REFERENCES_MARKER,
    InputStrategy,
    normalize_label,
)
from projects.correction.extractor.configs import ARTICLE_CONFIG


def test_article_requires_abstract_and_references() -> None:
    assert [s.key for s in ARTICLE_CONFIG.required_sections] == ["abstract", "references"]


def test_article_goes_to_the_model_as_pdf() -> None:
    assert ARTICLE_CONFIG.strategy is InputStrategy.PDF


def test_article_accepts_portuguese_and_english_titles() -> None:
    labels = {
        definition.key: {normalize_label(label) for label in definition.labels}
        for definition in ARTICLE_CONFIG.required_sections
    }

    assert {"abstract", "resumo"} <= labels["abstract"]
    assert {"references", "referencias", "referencias bibliograficas"} <= labels["references"]


def test_article_prompts_are_loaded() -> None:
    assert "títulos das seções" in ARTICLE_CONFIG.scan_prompt
    assert all(marker in ARTICLE_CONFIG.extraction_prompt for marker in EXTRACTION_MARKERS)
    assert REFERENCES_MARKER in ARTICLE_CONFIG.references_prompt
    assert "figuras e tabelas" in ARTICLE_CONFIG.figures_prompt
    assert "<<mentions>>" in ARTICLE_CONFIG.describe_figure_prompt
    assert ARTICLE_CONFIG.describe_figures is True
    assert "literalmente" in ARTICLE_CONFIG.extraction_prompt


def test_article_ignores_the_footnotes() -> None:
    assert ARTICLE_CONFIG.ignore_footnotes is True
