"""A lista de figuras e tabelas conferida contra o texto do PDF."""

from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.figures import label_number, scan_figures
from projects.correction.extractor.schemas import FigureScan, HeadingScan, ScannedFigure
from projects.correction.extractor.tests.fakes import FakeSession

FIG_1 = "Figure 1: Tempo de resposta das filas de mensagens sob carga constante."
TAB_2 = "Table 2: Mediana do tempo de resposta por quantidade de consumidores."
REFERENCE = f"Texto do artigo.\n{FIG_1}\nMais texto do artigo.\n{TAB_2}\nFim."
INVENTED = "Figure 9: Uma legenda que nao aparece em lugar nenhum do documento."
SCAN = HeadingScan(title="t", authors=(), language="pt", headings=())


def figure(label: str, caption: str, kind: str = "figure", page: int = 1) -> ScannedFigure:
    return ScannedFigure.model_validate(
        {"label": label, "kind": kind, "page": page, "caption": caption}
    )


def scripted(*answers: FigureScan) -> FakeSession:
    return FakeSession(SCAN, {}, figures=list(answers))


def listing(*figures: ScannedFigure) -> FigureScan:
    return FigureScan(figures=figures)


COMPLETE = listing(figure("Figure 1", FIG_1), figure("Table 2", TAB_2, kind="table", page=2))


def test_lists_figures_and_tables_with_ids_numbers_and_checked_captions() -> None:
    session = scripted(COMPLETE)

    figures = scan_figures(session, ARTICLE_CONFIG, REFERENCE)

    assert [(f.id, f.kind, f.label, f.number, f.page, f.fidelity) for f in figures] == [
        ("fig_1", "figure", "Figure 1", "1", 1, 1.0),
        ("fig_2", "table", "Table 2", "2", 2, 1.0),
    ]
    assert len(session.prompts) == 1


def test_missing_caption_seen_in_the_pdf_is_asked_again() -> None:
    session = scripted(listing(figure("Figure 1", FIG_1)), COMPLETE)

    figures = scan_figures(session, ARTICLE_CONFIG, REFERENCE)

    assert [f.label for f in figures] == ["Figure 1", "Table 2"]
    assert "ficaram de fora" in session.prompts[1] and "Tabela 2" in session.prompts[1]


def test_invented_caption_is_dropped_and_asked_again() -> None:
    session = scripted(listing(figure("Figure 9", INVENTED), *COMPLETE.figures), COMPLETE)

    figures = scan_figures(session, ARTICLE_CONFIG, REFERENCE)

    assert [f.label for f in figures] == ["Figure 1", "Table 2"]
    assert "Figure 9: Uma legenda" in session.prompts[1]


def test_without_pdf_text_the_list_is_kept_unchecked() -> None:
    figures = scan_figures(scripted(listing(figure("Figure 9", INVENTED))), ARTICLE_CONFIG, None)

    assert [(f.label, f.fidelity) for f in figures] == [("Figure 9", None)]


def test_article_without_figures() -> None:
    assert scan_figures(scripted(listing()), ARTICLE_CONFIG, "Texto sem figuras.") == ()


def test_label_numbers() -> None:
    assert [label_number(x) for x in ("Figure 3", "Table A.1", "Fig. 3a", "Figura")] == [
        "3",
        "A.1",
        "3",
        None,
    ]


def test_ids_follow_the_page_order() -> None:
    session = scripted(
        listing(figure("Table 2", TAB_2, kind="table", page=3), figure("Figure 1", FIG_1, page=1))
    )

    figures = scan_figures(session, ARTICLE_CONFIG, REFERENCE)

    assert [(f.id, f.label) for f in figures] == [("fig_1", "Figure 1"), ("fig_2", "Table 2")]
