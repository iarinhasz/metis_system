"""Divide o artigo: a chamada 1 mapeia as seções, e a chamada 2, feita uma vez por seção e em
paralelo, traz o texto de cada uma, conferido contra o texto do PDF (ver section_answer.py)."""

from concurrent.futures import Future, ThreadPoolExecutor

from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.coverage import local_sections, reference_text
from projects.correction.extractor.errors import (
    InvalidModelAnswer,
    MissingRequiredSections,
    UnreadablePdf,
)
from projects.correction.extractor.pdf_text import read_pdf_pages
from projects.correction.extractor.prompts import load_prompt, render_prompt
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

    answers = _extract_sections(session, config, section_map, _local_texts(pdf, section_map))

    required = {d.key for d in config.required_sections}
    empty = [
        s.key
        for s in section_map.values()
        if s.key in required and not answers[s.id].content.text.strip()
    ]
    if empty:
        raise InvalidModelAnswer(f"Seções obrigatórias voltaram vazias: {', '.join(empty)}.")

    return ExtractedArticle(
        title=scan.title.strip(),
        authors=tuple(name.strip() for name in scan.authors if name.strip()),
        language=scan.language.strip().lower(),
        model=f"{config.provider}/{config.model}",
        sections=tuple(
            ExtractedSection(
                **mapped.model_dump(),
                text=answers[mapped.id].content.text.strip(),
                has_footnotes=answers[mapped.id].content.has_footnotes,
                coverage=answers[mapped.id].coverage,
                fidelity=answers[mapped.id].fidelity,
            )
            for mapped in section_map.values()
        ),
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


def _local_texts(pdf: bytes, section_map: SectionMap) -> dict[str, str | None]:
    """O texto de cada seção lido localmente, a referência da cobertura. Se o pypdf não acha
    texto no PDF (escaneado), nenhuma seção é verificada: o modelo ainda consegue lê-lo."""
    try:
        pages = read_pdf_pages(pdf)
    except UnreadablePdf:
        return dict.fromkeys(section_map)
    return local_sections(reference_text(pages), section_map)
