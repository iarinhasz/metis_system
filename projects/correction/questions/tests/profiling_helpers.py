"""Dados sintéticos do manuscrito e respostas dos dois classificadores."""

from projects.correction.extractor.article import ExtractedArticle, ExtractedSection

FIELD = "https://openalex.org/fields/19"
OTHER_FIELD = "https://openalex.org/fields/31"
SUBFIELD = "https://openalex.org/subfields/1906"
OTHER_SUBFIELD = "https://openalex.org/subfields/3107"
TOPIC = "https://openalex.org/T10001"
OTHER_TOPIC = "https://openalex.org/T10002"
SYNTHETIC_TOPIC = "https://openalex.org/T19999"
SYNTHETIC_SUBFIELD = "https://openalex.org/subfields/1999"
PRIVATE_TEXT = "Trecho confidencial sintético que não deve aparecer nos erros."


def article() -> ExtractedArticle:
    return ExtractedArticle(
        title="Artigo sintético de geociências",
        authors=(),
        language="pt",
        model="fake",
        sections=(
            ExtractedSection(
                id="sec_1",
                title="Resumo",
                level=1,
                parent_id=None,
                key="abstract",
                text=PRIVATE_TEXT,
                has_footnotes=False,
                coverage=None,
                fidelity=None,
            ),
        ),
    )


def field_answer(*, field: str = FIELD, confidence: float = 0.95) -> dict[str, object]:
    return {
        "field": field,
        "paper_type": "empirical",
        "language": "pt",
        "keywords": ["rochas", "geoquímica"],
        "confidence": confidence,
    }


def topic_answer(
    *,
    topic: str = TOPIC,
    subfield: str = SUBFIELD,
    confidence: float = 0.9,
    secondary: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "topic": topic,
        "subfield": subfield,
        "secondary_areas": secondary,
        "confidence": confidence,
    }
