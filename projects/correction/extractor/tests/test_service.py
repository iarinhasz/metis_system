"""O caso de uso: o mapa na chamada 1 e uma chamada por seção, com a cobertura conferida
contra o texto de um PDF gerado no teste."""

import pytest

from projects.correction.extractor.article import Citation
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import (
    InvalidModelAnswer,
    MissingRequiredSections,
    ModelUnavailable,
)
from projects.correction.extractor.schemas import (
    FigureScan,
    HeadingScan,
    ParsedReferences,
    ScannedFigure,
    ScannedHeading,
    SectionContent,
)
from projects.correction.extractor.service import extract_article
from projects.correction.extractor.tests.fakes import FakeSession, raw_entry
from projects.correction.extractor.tests.pdfs import make_pdf

ABSTRACT = "Este artigo mede o tempo de resposta de filas de mensagens sob carga constante."
INTRO_1 = "Filas de mensagens desacoplam produtores e consumidores em sistemas distribuidos."
INTRO_2 = "Medir o tempo de resposta ajuda a dimensionar a quantidade de consumidores necessaria."
CONTEXT = "O contexto deste trabalho sao servicos que recebem picos curtos de requisicoes."
REFERENCE = "[1] C. Pereira. Sistemas distribuidos na pratica. Editora Exemplo, 2020."

PDF = make_pdf(
    [
        "Filas de mensagens sob carga",
        "Resumo",
        ABSTRACT,
        "1 Introducao",
        INTRO_1,
        INTRO_2,
        "1.1 Contexto",
        CONTEXT,
        "Referencias",
        REFERENCE,
    ]
)
SCAN = HeadingScan(
    title=" Filas de mensagens sob carga ",
    authors=("Ana Souza", " "),
    language="PT",
    headings=(
        ScannedHeading(title="Resumo", level=1),
        ScannedHeading(title="1 Introducao", level=1),
        ScannedHeading(title="1.1 Contexto", level=2),
        ScannedHeading(title="Referencias", level=1),
    ),
)


def content(*paragraphs: str, footnotes: bool = False) -> SectionContent:
    return SectionContent(text="\n\n".join(paragraphs), has_footnotes=footnotes)


def complete() -> dict[str, list[SectionContent]]:
    return {
        "Resumo": [content(ABSTRACT)],
        "1 Introducao": [content(INTRO_1, INTRO_2)],
        "1.1 Contexto": [content(CONTEXT)],
        "Referencias": [content(REFERENCE)],
    }


def test_asks_each_section_and_checks_its_coverage() -> None:
    session = FakeSession(SCAN, complete())

    article = extract_article(PDF, opener=session.opener())

    assert (article.title, article.authors, article.language, article.model) == (
        "Filas de mensagens sob carga",
        ("Ana Souza",),
        "pt",
        "google/gemini-2.5-flash",
    )
    assert [
        (s.id, s.key, s.parent_id, s.text, s.coverage, s.fidelity) for s in article.sections
    ] == [
        ("sec_1", "abstract", None, ABSTRACT, 1.0, 1.0),
        ("sec_2", None, None, f"{INTRO_1}\n\n{INTRO_2}", 1.0, 1.0),
        ("sec_3", None, "sec_2", CONTEXT, 1.0, 1.0),
        # A referência não tem prosa para a cobertura, mas a fidelidade confere.
        ("sec_4", "references", None, REFERENCE, None, 1.0),
    ]
    assert len(session.prompts) == 1 + 4 + 1 + 1  # mapa, seções, referências e figuras


def test_each_prompt_names_the_section_and_where_it_ends() -> None:
    session = FakeSession(SCAN, complete())

    extract_article(PDF, opener=session.opener())

    prompts = {p for p in session.prompts if "Seção:" in p}
    assert any(
        'Seção: "1.1 Contexto", dentro da seção "1 Introducao"' in p
        and 'termina no título "Referencias"' in p
        for p in prompts
    )
    assert any('Seção: "Referencias"' in p and "termina no fim do documento" in p for p in prompts)
    assert all("<<" not in p for p in prompts)
    assert all("deixe de fora o texto das notas" in p for p in prompts)


def test_asks_again_a_section_that_skipped_text() -> None:
    sections = complete()
    sections["1 Introducao"] = [content(INTRO_1), content(INTRO_1, INTRO_2)]
    session = FakeSession(SCAN, sections)

    article = extract_article(PDF, opener=session.opener())

    intro = article.sections[1]
    assert (intro.text, intro.coverage) == (f"{INTRO_1}\n\n{INTRO_2}", 1.0)
    assert session.calls_per_title["1 Introducao"] == 2
    [retry] = [p for p in session.prompts if "deixou de fora" in p]
    assert 'Seção: "1 Introducao"' in retry and INTRO_2[:40] in retry


def test_keeps_the_best_answer_when_retries_run_out() -> None:
    sections = complete()
    sections["1 Introducao"] = [content(INTRO_1), content("Texto que nao esta no PDF.")]
    session = FakeSession(SCAN, sections)

    article = extract_article(PDF, opener=session.opener())

    intro = article.sections[1]
    assert intro.text == INTRO_1
    assert intro.coverage is not None and 0 < intro.coverage < ARTICLE_CONFIG.min_coverage
    assert session.calls_per_title["1 Introducao"] == 1 + ARTICLE_CONFIG.check_retries


def test_runs_the_sections_in_parallel_up_to_the_limit() -> None:
    session = FakeSession(SCAN, complete(), delay_seconds=0.05)
    config = ARTICLE_CONFIG.model_copy(update={"max_parallel_calls": 2})

    extract_article(PDF, config, opener=session.opener())

    assert session.max_running == 2


def test_rejects_the_article_before_asking_the_sections() -> None:
    scan = SCAN.model_copy(update={"headings": SCAN.headings[:3]})
    session = FakeSession(scan, complete())

    with pytest.raises(MissingRequiredSections, match="references"):
        extract_article(PDF, opener=session.opener())

    assert len(session.prompts) == 1


def test_required_section_without_text_is_an_invalid_answer() -> None:
    sections = complete()
    sections["Referencias"] = [content("  ")]

    with pytest.raises(InvalidModelAnswer, match="references"):
        extract_article(PDF, opener=FakeSession(SCAN, sections).opener())


def test_a_failed_section_fails_the_extraction() -> None:
    class Failing(FakeSession):
        def ask[T: SectionContent | HeadingScan](self, prompt: str, output: type[T]) -> T:  # type: ignore[override]
            if "1.1 Contexto" in prompt:
                raise ModelUnavailable("o modelo falhou")
            return super().ask(prompt, output)

    with pytest.raises(ModelUnavailable):
        extract_article(PDF, opener=Failing(SCAN, complete()).opener())


def test_tells_which_sections_have_footnotes() -> None:
    sections = complete()
    sections["1 Introducao"] = [content(INTRO_1, INTRO_2, footnotes=True)]

    article = extract_article(PDF, opener=FakeSession(SCAN, sections).opener())

    assert [s.has_footnotes for s in article.sections] == [False, True, False, False]
    assert article.has_footnotes


def test_keeps_the_footnotes_when_the_config_asks() -> None:
    session = FakeSession(SCAN, complete())
    config = ARTICLE_CONFIG.model_copy(update={"ignore_footnotes": False})

    extract_article(PDF, config, opener=session.opener())

    section_prompts = [p for p in session.prompts if "Seção:" in p]
    assert all("copie cada nota no fim da seção" in p for p in section_prompts)


def test_pdf_without_local_text_is_not_verified() -> None:
    blank = make_pdf([])
    article = extract_article(blank, opener=FakeSession(SCAN, complete()).opener())

    assert [s.coverage for s in article.sections] == [None, None, None, None]


def test_parses_the_references_and_links_the_calls() -> None:
    sections = complete()
    cited = INTRO_1.replace("distribuidos.", "distribuidos [1].")
    sections["1 Introducao"] = [content(cited, INTRO_2)]
    references = ParsedReferences(
        references=(raw_entry(REFERENCE, marker="[1]", authors=("C. Pereira",), year="2020"),)
    )
    session = FakeSession(SCAN, sections, references=[references])

    article = extract_article(PDF, opener=session.opener())

    [reference] = article.references
    assert (reference.id, reference.marker, reference.authors) == ("ref_1", "[1]", ("C. Pereira",))
    intro = article.sections[1].text
    start = intro.index("[1]")
    assert article.citations == (
        Citation(
            reference_id="ref_1",
            marker="[1]",
            sentence=cited,
            section_id="sec_2",
            start=start,
            end=start + 3,
        ),
    )
    assert len(session.without_document) == 1


def test_lists_the_figures_and_finds_the_sentences_that_cite_them() -> None:
    caption = "Figure 1: Tempo de resposta das filas de mensagens sob carga constante."
    cited = "Como mostra a Figure 1, o tempo de resposta cresce pouco com a carga constante."
    pdf = make_pdf(["Resumo", ABSTRACT, "1 Introducao", cited, caption, "Referencias", REFERENCE])
    scan = SCAN.model_copy(
        update={"headings": (SCAN.headings[0], SCAN.headings[1], SCAN.headings[3])}
    )
    sections = {
        "Resumo": [content(ABSTRACT)],
        "1 Introducao": [content(cited)],
        "Referencias": [content(REFERENCE)],
    }
    figures = FigureScan(
        figures=(
            ScannedFigure.model_validate(
                {"label": "Figure 1", "kind": "figure", "page": 1, "caption": caption}
            ),
        )
    )
    session = FakeSession(scan, sections, figures=[figures])

    article = extract_article(pdf, opener=session.opener())

    [figure] = article.figures
    assert (figure.id, figure.label, figure.number, figure.fidelity) == (
        "fig_1",
        "Figure 1",
        "1",
        1.0,
    )
    [mention] = article.figure_mentions
    assert (mention.figure_id, mention.marker, mention.sentence) == ("fig_1", "Figure 1", cited)
    assert figure.description is not None
    assert session.described == ["Figure 1"]
