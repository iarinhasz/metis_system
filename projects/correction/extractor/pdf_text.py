"""Texto do PDF lido aqui mesmo, com o pypdf (Python puro, sem serviço)."""

import io
import re
import unicodedata
from typing import Final

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from projects.correction.extractor.errors import UnreadablePdf

PAGE_NUMBER: Final = re.compile(r"^\s*\d+\.?\s*$")


def read_pdf_pages(pdf: bytes) -> list[str]:
    """Texto de cada página, com as ligaduras desfeitas (`ﬁ` → `fi`). Sem texto, o PDF é
    rejeitado."""
    try:
        reader = PdfReader(io.BytesIO(pdf))
        pages = [unicodedata.normalize("NFKC", page.extract_text() or "") for page in reader.pages]
    except (PyPdfError, ValueError, OSError) as exc:
        raise UnreadablePdf(f"PDF ilegível: {type(exc).__name__}.") from exc
    if not any(page.strip() for page in pages):
        raise UnreadablePdf("PDF sem texto extraível (escaneado ou vazio).")
    return pages


def read_pdf_text(pdf: bytes) -> str:
    """Texto do PDF inteiro, sem números de página soltos."""
    lines = [
        line
        for page in read_pdf_pages(pdf)
        for line in page.splitlines()
        if not PAGE_NUMBER.match(line)
    ]
    return "\n".join(lines).strip()
