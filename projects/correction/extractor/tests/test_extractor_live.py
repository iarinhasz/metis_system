"""Contra o Gemini de verdade, com a GEMINI_KEY do .env e um artigo inventado.

Fora da execução padrão (custa chamadas): rode com `pytest -m llm`.
"""

import pytest

from projects.correction.extractor.service import extract_article
from projects.correction.extractor.tests.pdfs import ARTICLE_LINES, make_pdf

pytestmark = pytest.mark.llm


def test_divides_a_generated_article() -> None:
    article = extract_article(make_pdf(ARTICLE_LINES))

    abstract, references = article.section("abstract"), article.section("references")
    assert abstract is not None and "tempo de resposta" in abstract.text
    assert references is not None and "Pereira" in references.text
    assert any("Resultados" in section.title for section in article.sections)
    assert article.language == "pt"
    [reference] = article.references
    assert "Pereira" in reference.raw and reference.year == "2020"
    assert [c.reference_id for c in article.citations] == [reference.id]
