"""Divide o artigo: a chamada 1 mapeia as seções, e a chamada 2, feita uma vez por seção e em
paralelo, traz o texto de cada uma, conferido contra o texto do PDF (ver section_answer.py).
Depois, uma chamada separa a lista de referências em campos (references.py), e o código liga
as chamadas no texto a ela (citations.py). Por fim, uma chamada lista as figuras e as tabelas
(figures.py), o código acha as frases que as citam (figure_mentions.py), e uma chamada por
figura, em paralelo, descreve cada uma (figure_descriptions.py)."""

from concurrent.futures import Future, ThreadPoolExecutor

from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.citations import find_citations
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.coverage import local_sections, reference_text
from projects.correction.extractor.errors import (
    InvalidModelAnswer,
    MissingRequiredSections,
    UnreadablePdf,
)
from projects.correction.extractor.figure_descriptions import describe_figures
from projects.correction.extractor.figure_mentions import find_figure_mentions
from projects.correction.extractor.figures import scan_figures
from projects.correction.extractor.pdf_text import read_pdf_pages
from projects.correction.extractor.prompts import load_prompt, render_prompt
from projects.correction.extractor.references import parse_references
from projects.correction.extractor.schemas import HeadingScan
from projects.correction.extractor.section_answer import SectionAnswer, ask_section
from projects.correction.extractor.section_map import (
    SectionMap,
    build_section_map,
    missing_required,
    section_end,
    section_target,
)
from projects.correction.extractor.session import AgnoSession, DocumentSession, SessionOpener


def extract_article(
    pdf: bytes,
    config: DocumentConfig = ARTICLE_CONFIG,
    opener: SessionOpener = AgnoSession,
) -> ExtractedArticle:
    session = opener(config, pdf)
    scan = session.ask(config.scan_prompt, HeadingScan)
    section_map = build_section_map(scan, config)
    # Antes das chamadas por seção, as mais caras: sem as obrigatórias, o artigo é rejeitado.
    if missing := missing_required(section_map, config):
        raise MissingRequiredSections(f"Sem as seções obrigatórias: {', '.join(missing)}.")

    reference = _reference_text(pdf)
    local_texts = (
        local_sections(reference, section_map) if reference else dict.fromkeys(section_map)
    )
    answers = _extract_sections(session, config, section_map, local_texts)

    required = {d.key for d in config.required_sections}
    empty = [
        s.key
        for s in section_map.values()
        if s.key in required and not answers[s.id].content.text.strip()
    ]
    if empty:
        raise InvalidModelAnswer(f"Seções obrigatórias voltaram vazias: {', '.join(empty)}.")

    sections = tuple(
        ExtractedSection(
            **mapped.model_dump(),
            text=answers[mapped.id].content.text.strip(),
            has_footnotes=answers[mapped.id].content.has_footnotes,
            coverage=answers[mapped.id].coverage,
            fidelity=answers[mapped.id].fidelity,
        )
        for mapped in section_map.values()
    )
    references_text = "\n\n".join(s.text for s in sections if s.key == "references")
    references = parse_references(session, config, references_text)
    figures = scan_figures(session, config, reference)
    figure_mentions = find_figure_mentions(sections, figures)
    figures = describe_figures(session, config, figures, figure_mentions)

    return ExtractedArticle(
        title=scan.title.strip(),
        authors=tuple(name.strip() for name in scan.authors if name.strip()),
        language=scan.language.strip().lower(),
        model=f"{config.provider}/{config.model}",
        sections=sections,
        references=references,
        citations=find_citations(sections, references),
        figures=figures,
        figure_mentions=figure_mentions,
    )


def _extract_sections(
    session: DocumentSession,
    config: DocumentConfig,
    section_map: SectionMap,
    local_texts: dict[str, str | None],
) -> dict[str, SectionAnswer]:
    """Uma chamada por seção, até `max_parallel_calls` ao mesmo tempo. Uma falha cancela o resto
    e sobe: quem tenta de novo é o Celery."""
    footnotes = load_prompt("footnotes_ignore" if config.ignore_footnotes else "footnotes_keep")
    with ThreadPoolExecutor(max_workers=config.max_parallel_calls) as pool:
        futures: dict[str, Future[SectionAnswer]] = {
            section_id: pool.submit(
                ask_section,
                session,
                config,
                render_prompt(
                    config.extraction_prompt,
                    title=section_target(section_map, section_id),
                    end=section_end(section_map, section_id),
                    footnotes=footnotes,
                ),
                local_texts[section_id],
            )
            for section_id in section_map
        }
        try:
            return {section_id: future.result() for section_id, future in futures.items()}
        except BaseException:
            for future in futures.values():
                future.cancel()
            raise


def _reference_text(pdf: bytes) -> str | None:
    """O texto do PDF lido aqui, a referência das conferências. Se o pypdf não acha texto no
    PDF (escaneado), nada é verificado: o modelo ainda consegue lê-lo."""
    try:
        return reference_text(read_pdf_pages(pdf))
    except UnreadablePdf:
        return None
