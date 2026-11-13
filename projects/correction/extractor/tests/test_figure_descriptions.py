"""A descrição de cada figura: uma chamada por figura, com falha isolada."""

import pytest

from projects.correction.extractor.article import Figure, FigureMention
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import InvalidModelAnswer, ModelUnavailable
from projects.correction.extractor.figure_descriptions import NO_MENTIONS, describe_figures
from projects.correction.extractor.schemas import DescribedFigure, HeadingScan
from projects.correction.extractor.tests.fakes import FakeSession, described

SCAN = HeadingScan(title="t", authors=(), language="pt", headings=())


def figure(index: int, label: str, kind: str = "figure") -> Figure:
    return Figure.model_validate(
        {
            "id": f"fig_{index}",
            "kind": kind,
            "label": label,
            "number": str(index),
            "page": index,
            "caption": f"{label}: o que {label} mostra.",
            "fidelity": 1.0,
        }
    )


FIGURES = [figure(1, "Figure 1"), figure(2, "Table 2", kind="table")]
MENTION = FigureMention(
    figure_id="fig_1",
    marker="Figure 1",
    sentence="Como mostra a Figure 1, a fila cresce.",
    section_id="sec_1",
    start=14,
    end=22,
)


def test_describes_each_figure_with_its_caption_and_citing_sentences() -> None:
    fake = FakeSession(
        SCAN,
        {},
        descriptions={
            "Figure 1": [
                described(
                    "  Mostra a fila.  ",
                    data_read=("eixo x: carga ", " "),
                    supports_claims=True,
                    issues=("eixo y sem unidade",),
                )
            ],
            "Table 2": [
                described("Tabela de medianas.", table_markdown=" | a | b |\n|---|---|\n| 1 | 2 | ")
            ],
        },
    )

    first, second = describe_figures(fake, ARTICLE_CONFIG, FIGURES, [MENTION])

    assert first.description is not None and second.description is not None
    assert (first.description.description, first.description.data_read) == (
        "Mostra a fila.",
        ("eixo x: carga",),
    )
    assert (first.description.supports_claims, first.description.issues) == (
        True,
        ("eixo y sem unidade",),
    )
    assert second.description.table_markdown == "| a | b |\n|---|---|\n| 1 | 2 |"
    prompts = {p.split('"')[1]: p for p in fake.prompts}
    assert "Figure 1: o que Figure 1 mostra." in prompts["Figure 1"]
    assert "- Como mostra a Figure 1, a fila cresce." in prompts["Figure 1"]
    assert NO_MENTIONS in prompts["Table 2"]


def test_the_model_down_on_one_figure_fails_the_stage_after_the_others() -> None:
    fake = FakeSession(SCAN, {}, descriptions={"Table 2": [ModelUnavailable("429")]})

    with pytest.raises(ModelUnavailable):
        describe_figures(fake, ARTICLE_CONFIG, FIGURES, [])

    # A outra foi descrita mesmo assim: a resposta dela fica guardada para o retry.
    assert sorted(fake.described) == ["Figure 1", "Table 2"]


def test_a_figure_still_invalid_stays_without_description() -> None:
    invalid: list[DescribedFigure | Exception] = [InvalidModelAnswer("fora do schema")]
    fake = FakeSession(SCAN, {}, descriptions={"Table 2": invalid})

    first, second = describe_figures(fake, ARTICLE_CONFIG, FIGURES, [])

    assert first.description is not None
    assert second.description is None


def test_invalid_answer_is_asked_again() -> None:
    fake = FakeSession(
        SCAN,
        {},
        descriptions={"Figure 1": [InvalidModelAnswer("fora do schema"), described("Agora sim.")]},
    )

    [only] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[:1], [])

    assert only.description is not None and only.description.description == "Agora sim."
    assert fake.described == ["Figure 1", "Figure 1"]


def test_invalid_answers_everywhere_leave_figures_without_description() -> None:
    invalid: list[DescribedFigure | Exception] = [InvalidModelAnswer("fora do schema")]
    fake = FakeSession(SCAN, {}, descriptions={"Figure 1": invalid, "Table 2": invalid})

    figures = describe_figures(fake, ARTICLE_CONFIG, FIGURES, [])

    assert [f.description for f in figures] == [None, None]


def test_switched_off_in_the_config() -> None:
    fake = FakeSession(SCAN, {})
    config = ARTICLE_CONFIG.model_copy(update={"describe_figures": False})

    figures = describe_figures(fake, config, FIGURES, [])

    assert [f.description for f in figures] == [None, None]
    assert fake.prompts == []


def test_description_of_another_figure_is_asked_again() -> None:
    wrong = described("Uma tabela de acurácia.", caption_start="Table 2: legenda.")
    fake = FakeSession(
        SCAN, {}, descriptions={"Figure 1": [wrong, described("O traço da adição.")]}
    )

    [only] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[:1], [])

    assert only.description is not None and only.description.description == "O traço da adição."
    retry = fake.prompts[1]
    assert "foi descrita outra figura" in retry and "«Table 2: legenda.»" in retry


def test_still_the_wrong_figure_leaves_it_without_description() -> None:
    wrong = described("Uma tabela de acurácia.", caption_start="Table 2: legenda.")
    fake = FakeSession(SCAN, {}, descriptions={"Figure 1": [wrong]})

    [only] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[:1], [])

    assert only.description is None
    assert len(fake.prompts) == 1 + ARTICLE_CONFIG.check_retries


def test_caption_start_without_the_label_is_the_same_figure() -> None:
    caption = FIGURES[0].caption
    without_label = caption.split(":", 1)[1].strip()
    fake = FakeSession(
        SCAN, {}, descriptions={"Figure 1": [described(caption_start=without_label[:40])]}
    )

    [only] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[:1], [])

    assert only.description is not None
    assert len(fake.prompts) == 1


HEADER_ONLY = "| Dataset | AUROC |\n|---|---|"
FULL_TABLE = "| Dataset | AUROC |\n|---|---|\n| Reuters 6 | 89 |"


def test_a_table_without_rows_is_asked_again() -> None:
    fake = FakeSession(
        SCAN,
        {},
        descriptions={
            "Table 2": [
                described("Uma tabela.", table_markdown=HEADER_ONLY),
                described("Uma tabela.", table_markdown=FULL_TABLE),
            ]
        },
    )

    [table] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[1:], [])

    assert table.description is not None and table.description.table_markdown == FULL_TABLE
    assert "sem as linhas de dados" in fake.prompts[1]


def test_a_table_still_without_rows_keeps_the_description_without_markdown() -> None:
    fake = FakeSession(
        SCAN, {}, descriptions={"Table 2": [described("Uma tabela.", table_markdown=HEADER_ONLY)]}
    )

    [table] = describe_figures(fake, ARTICLE_CONFIG, FIGURES[1:], [])

    assert table.description is not None
    assert (table.description.description, table.description.table_markdown) == (
        "Uma tabela.",
        None,
    )
    assert len(fake.prompts) == 1 + ARTICLE_CONFIG.check_retries
