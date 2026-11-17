"""Contrato e preparação dos dados do E1 sem depender de um provedor de modelos."""

import pytest
from pydantic import ValidationError

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentFigure,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)
from projects.correction.extractor.peerread import peerread_to_document


def sample_document() -> ExtractedDocument:
    return ExtractedDocument(
        title="Um artigo",
        authors=("Ana Pesquisadora",),
        language="pt",
        abstract="Resumo do artigo.",
        sections=(
            DocumentSection(
                id="sec_1",
                title="Introdução",
                level=1,
                parent_id=None,
                key="introduction",
                text="Apresentamos o problema. Ver Figura 1.",
            ),
            DocumentSection(
                id="sec_2",
                title="Motivação",
                level=2,
                parent_id="sec_1",
                key="motivation",
                text="A literatura discute o problema.",
            ),
        ),
        references=(
            DocumentReference(
                id="ref_1",
                raw="Pesquisadora, A. Um estudo. 2024.",
                authors=("Ana Pesquisadora",),
                title="Um estudo",
                year="2024",
            ),
        ),
        citation_mentions=(
            CitationMention(
                reference_id="ref_1",
                marker="[1]",
                sentence="A literatura discute o problema.",
                section_id="sec_2",
                start_offset=0,
                end_offset=len("A literatura discute o problema."),
            ),
        ),
        figures=(
            DocumentFigure(
                id="fig_1",
                kind="figure",
                label="Figura 1",
                page=2,
                caption="Arquitetura do sistema.",
                section_id="sec_1",
                offset=len("Apresentamos o problema. Ver Figura 1."),
            ),
            DocumentFigure(
                id="fig_2",
                kind="table",
                label="Tabela 1",
                caption="Resultados da avaliação.",
            ),
        ),
    )


def test_document_validates_nested_sections_and_references() -> None:
    document = sample_document()

    assert document.contract_version == "1.0"
    assert document.sections[1].parent_id == "sec_1"
    assert document.citation_mentions[0].reference_id == "ref_1"


def test_document_and_nested_sections_are_immutable() -> None:
    document = sample_document()

    with pytest.raises(ValidationError):
        document.title = "Outro título"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        document.sections[0].text = "Alterado"  # type: ignore[misc]


def test_document_rejects_missing_abstract_and_unknown_citation_section() -> None:
    values = sample_document().model_dump()
    values["abstract"] = ""
    with pytest.raises(ValidationError, match="abstract"):
        ExtractedDocument.model_validate(values)

    values = sample_document().model_dump()
    values["citation_mentions"][0]["section_id"] = "missing"
    with pytest.raises(ValidationError, match="Seção da citação"):
        ExtractedDocument.model_validate(values)

    values = sample_document().model_dump()
    values["sections"] = []
    with pytest.raises(ValidationError, match="sections"):
        ExtractedDocument.model_validate(values)


def test_document_rejects_invalid_section_hierarchy() -> None:
    values = sample_document().model_dump()
    values["sections"][1]["parent_id"] = "missing"

    with pytest.raises(ValidationError, match="Seção pai inexistente"):
        ExtractedDocument.model_validate(values)


def test_render_includes_metadata_nested_sections_references_and_figure_position() -> None:
    rendered = "\n".join(sample_document().render_for_llm())

    assert "# Um artigo" in rendered
    assert "## Introdução" in rendered
    assert "### Motivação" in rendered
    assert "[FIGURA Figura 1: Arquitetura do sistema.]" in rendered
    assert "[TABELA Tabela 1: Resultados da avaliação.]" in rendered
    assert "Pesquisadora, A. Um estudo. 2024." in rendered
    assert rendered.index("Ver Figura 1.") < rendered.index("[FIGURA Figura 1")


def test_render_selects_section_and_splits_long_sections_at_paragraphs() -> None:
    document = ExtractedDocument(
        title="Longo",
        language="en",
        abstract="Abstract.",
        sections=(
            DocumentSection(
                id="sec_1",
                title="Method",
                level=1,
                parent_id=None,
                text=("A" * 300) + "\n\n" + ("B" * 300),
            ),
            DocumentSection(
                id="sec_2",
                title="Details",
                level=2,
                parent_id="sec_1",
                text="Detail.",
            ),
        ),
    )

    chunks = document.render_for_llm("sec_1", max_chars=300)

    assert len(chunks) >= 3
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert all("# Longo" in chunk for chunk in chunks)
    assert any("### Details" in chunk for chunk in chunks)


def test_peerread_row_is_converted_without_model_calls() -> None:
    row = {
        "name": "paper.json",
        "metadata": {
            "title": "Paper title",
            "authors": ["Author One"],
            "abstractText": "An abstract.",
            "sections": [
                {"heading": "1 Introduction", "text": "See [1] in this study."},
                {"heading": "1.1 Background", "text": "Prior work."},
                {"heading": "References", "text": "not included as body text"},
            ],
            "references": [
                {
                    "author": ["Author Two"],
                    "title": "Prior work",
                    "venue": "Journal",
                    "year": 2020,
                }
            ],
            "referenceMentions": [
                {
                    "referenceID": 0,
                    "context": "See [1] in this study.",
                }
            ],
        },
    }

    document = peerread_to_document(row)

    assert document.title == "Paper title"
    assert document.sections[1].parent_id == "sec_1"
    assert all(section.title != "References" for section in document.sections)
    assert document.references[0].id == "ref_1"
    assert document.citation_mentions[0].reference_id == "ref_1"
    assert document.citation_mentions[0].section_id == "sec_1"
