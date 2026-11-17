"""Adapta a extração persistida ao contrato público consumido pelos estágios."""

from projects.correction.extractor.article import ExtractedArticle, FigureMention
from projects.correction.extractor.contract import (
    CitationMention,
    DocumentFigure,
    DocumentFigureDescription,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)


def to_extracted_document(article: ExtractedArticle) -> ExtractedDocument:
    """Converte a saída persistida do E1 sem alterar seu JSON ou executar modelos."""
    abstract_section = article.section("abstract")
    if abstract_section is None or not abstract_section.text:
        raise ValueError("A extração não tem uma seção abstract válida.")

    sections = tuple(
        DocumentSection(
            id=section.id,
            title=section.title,
            level=section.level,
            parent_id=section.parent_id,
            key=section.key,
            text=section.text,
        )
        for section in article.sections
        if section.key not in {"abstract", "references"}
    )
    if not sections:
        raise ValueError("A extração não tem seções de conteúdo.")

    references = tuple(
        DocumentReference(
            id=reference.id,
            raw=reference.raw,
            marker=reference.marker,
            authors=reference.authors,
            title=reference.title,
            year=reference.year,
            venue=reference.venue,
            doi=reference.doi,
            arxiv_id=reference.arxiv_id,
        )
        for reference in article.references
    )
    citation_mentions = tuple(
        CitationMention(
            reference_id=citation.reference_id,
            marker=citation.marker,
            sentence=citation.sentence,
            section_id=citation.section_id,
            start_offset=citation.start,
            end_offset=citation.end,
        )
        for citation in article.citations
    )
    first_mention: dict[str, FigureMention] = {}
    for mention in article.figure_mentions:
        if mention.figure_id is not None:
            first_mention.setdefault(mention.figure_id, mention)

    def figure_position(figure_id: str) -> tuple[str | None, int | None]:
        mention = first_mention.get(figure_id)
        if mention is None:
            return None, None
        return mention.section_id, mention.end

    figures = tuple(
        DocumentFigure(
            id=figure.id,
            kind=figure.kind,
            label=figure.label,
            page=figure.page,
            caption=figure.caption,
            section_id=figure_position(figure.id)[0],
            offset=figure_position(figure.id)[1],
            description=(
                DocumentFigureDescription.model_validate(figure.description.model_dump())
                if figure.description is not None
                else None
            ),
        )
        for figure in article.figures
    )

    return ExtractedDocument(
        title=article.title,
        authors=article.authors,
        language=article.language,
        abstract=abstract_section.text,
        sections=sections,
        references=references,
        citation_mentions=citation_mentions,
        figures=figures,
        hidden_text_findings=article.hidden_text_findings,
    )
