"""As frases que citam cada figura ou tabela."""

import pytest

from projects.correction.extractor.article import ExtractedSection, Figure
from projects.correction.extractor.figure_mentions import find_figure_mentions


def figure(index: int, kind: str, number: str) -> Figure:
    return Figure.model_validate(
        {
            "id": f"fig_{index}",
            "kind": kind,
            "label": f"{kind} {number}",
            "number": number,
            "page": 1,
            "caption": "Legenda.",
            "fidelity": None,
        }
    )


FIGURES = [
    figure(1, "figure", "1"),
    figure(2, "figure", "2"),
    figure(3, "figure", "3"),
    figure(4, "table", "1"),
    figure(5, "table", "A.1"),
]


def section(text: str, key: str | None = None) -> ExtractedSection:
    return ExtractedSection(
        id="sec_1",
        title="Seção",
        level=1,
        parent_id=None,
        key=key,
        text=text,
        has_footnotes=False,
        coverage=None,
        fidelity=None,
    )


def mentions(text: str) -> list[tuple[str | None, str]]:
    return [(m.figure_id, m.marker) for m in find_figure_mentions([section(text)], FIGURES)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Como mostra a Figure 2, cresce.", [("fig_2", "Figure 2")]),
        ("Ver Fig. 3a.", [("fig_3", "Fig. 3a")]),
        ("A Figura 1 mostra.", [("fig_1", "Figura 1")]),
        ("Ver Table 1 e Tabela A.1.", [("fig_4", "Table 1"), ("fig_5", "Tabela A.1")]),
        ("Figures 1 and 3 mostram.", [("fig_1", "Figures 1 and 3"), ("fig_3", "Figures 1 and 3")]),
        (
            "Figs. 1–3 mostram.",
            [("fig_1", "Figs. 1–3"), ("fig_2", "Figs. 1–3"), ("fig_3", "Figs. 1–3")],
        ),
        # Rótulo que não está na lista: a chamada fica, sem ligação.
        ("Ver Figure 9.", [(None, "Figure 9")]),
    ],
)
def test_calls_to_figures_and_tables(text: str, expected: list[tuple[str | None, str]]) -> None:
    assert mentions(text) == expected


def test_offsets_and_sentence() -> None:
    text = "Primeira frase. Como mostra a Figure 2, a fila cresce. Fim."

    [mention] = find_figure_mentions([section(text)], FIGURES)

    assert text[mention.start : mention.end] == "Figure 2"
    assert mention.sentence == "Como mostra a Figure 2, a fila cresce."


def test_reference_section_is_skipped() -> None:
    assert (
        find_figure_mentions([section("Figure 1 de outro artigo.", key="references")], FIGURES)
        == ()
    )
