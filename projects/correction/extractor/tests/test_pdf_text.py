"""Texto do PDF lido localmente, usado na estratégia TEXT e no PDF grande demais."""

import pytest

from projects.correction.extractor.errors import UnreadablePdf
from projects.correction.extractor.pdf_text import read_pdf_text
from projects.correction.extractor.tests.pdfs import ARTICLE_LINES, make_pdf


def test_reads_the_text_without_loose_page_numbers() -> None:
    text = read_pdf_text(make_pdf([*ARTICLE_LINES, "7"]))

    assert text.splitlines() == ARTICLE_LINES


@pytest.mark.parametrize(
    "pdf", [b"%PDF-1.4\nlixo sem estrutura\n%%EOF\n", make_pdf([])], ids=["corrompido", "sem-texto"]
)
def test_rejects_pdf_without_readable_text(pdf: bytes) -> None:
    with pytest.raises(UnreadablePdf):
        read_pdf_text(pdf)
