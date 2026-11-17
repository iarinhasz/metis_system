"""Chamadas no texto ligadas às entradas da lista de referências, só com código."""

import pytest

from projects.correction.extractor.article import Citation, ExtractedSection, Reference
from projects.correction.extractor.citations import find_citations


def ref(index: int, authors: list[str], year: str | None, marker: str | None = None) -> Reference:
    return Reference(
        id=f"ref_{index}",
        raw=f"Entrada {index}.",
        marker=marker,
        authors=tuple(authors),
        title="Um titulo",
        year=year,
        venue=None,
        doi=None,
        arxiv_id=None,
    )


def section(text: str, section_id: str = "sec_1", key: str | None = None) -> ExtractedSection:
    return ExtractedSection(
        id=section_id,
        title="Seção",
        level=1,
        parent_id=None,
        key=key,
        text=text,
        has_footnotes=False,
        coverage=None,
        fidelity=None,
    )


def links(text: str, references: list[Reference]) -> list[tuple[str | None, str]]:
    return [(c.reference_id, c.marker) for c in find_citations([section(text)], references)]


NUMBERED = [ref(i, ["Autor A."], "2020", marker=f"[{i}]") for i in range(1, 8)]
AUTHOR_YEAR = [
    ref(1, ["Silva, A."], "2020a"),
    ref(2, ["Souza B", "Lima C"], "2019"),
    ref(3, ["Maria Ávila"], "2018"),
    ref(4, ["Silva, J."], "2020b"),
    ref(5, ["Li, W.", "Wu, Y."], "2021"),
]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Filas [3] crescem.", [("ref_3", "[3]")]),
        ("Filas [1, 4] crescem.", [("ref_1", "[1, 4]"), ("ref_4", "[1, 4]")]),
        ("Filas [2–4] crescem.", [("ref_2", "[2–4]"), ("ref_3", "[2–4]"), ("ref_4", "[2–4]")]),
        (
            "Filas [2-3; 6] crescem.",
            [("ref_2", "[2-3; 6]"), ("ref_3", "[2-3; 6]"), ("ref_6", "[2-3; 6]")],
        ),
        # Número sem entrada: a chamada fica, sem ligação (a 5.3 usa).
        ("Filas [5, 9] crescem.", [("ref_5", "[5, 9]"), (None, "[5, 9]")]),
    ],
)
def test_numeric_calls(text: str, expected: list[tuple[str | None, str]]) -> None:
    assert links(text, NUMBERED) == expected


@pytest.mark.parametrize(
    "text", ["No intervalo [0, 1] a função cresce.", "Os valores [12, 40] estão fora da lista."]
)
def test_brackets_that_are_not_citations_are_ignored(text: str) -> None:
    assert links(text, NUMBERED) == []


def test_unnumbered_list_links_numeric_calls_by_position() -> None:
    unnumbered = [ref(i, ["Autor A."], "2020") for i in range(1, 4)]

    assert links("Como em [2].", unnumbered) == [("ref_2", "[2]")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Souza et al. (2019) mostram.", [("ref_2", "Souza et al. (2019)")]),
        ("Souza e Lima (2019) mostram.", [("ref_2", "Souza e Lima (2019)")]),
        ("Ávila (2018) mostra.", [("ref_3", "Ávila (2018)")]),
        ("Avila (2018) mostra.", [("ref_3", "Avila (2018)")]),
        ("Li and Wu (2021) mostram.", [("ref_5", "Li and Wu (2021)")]),
        ("Silva (2020a) mostra.", [("ref_1", "Silva (2020a)")]),
        (
            "Outros discordam (e.g., Silva, 2020a; Ávila 2018).",
            [("ref_1", "Silva, 2020a"), ("ref_3", "Ávila 2018")],
        ),
        (
            "Já se viu (Silva, 2020a, 2020b).",
            [("ref_1", "Silva, 2020a, 2020b"), ("ref_4", "Silva, 2020a, 2020b")],
        ),
        # Forma de citação sem entrada na lista: fica, sem ligação.
        ("Antes (Pereira et al., 2015).", [(None, "Pereira et al., 2015")]),
    ],
)
def test_author_year_calls(text: str, expected: list[tuple[str | None, str]]) -> None:
    assert links(text, AUTHOR_YEAR) == expected


@pytest.mark.parametrize(
    "text",
    [
        "A COVID-19 (2020) mudou tudo.",  # nome seguido de ano que não é citação
        "Silva (2020) é ambíguo.",  # 2020a e 2020b: mais de uma entrada
        "Um intervalo [0, 1] no texto.",  # artigo autor-ano: colchete não é citação
    ],
)
def test_weak_or_ambiguous_author_year_calls_are_dropped(text: str) -> None:
    assert links(text, AUTHOR_YEAR) == []


def test_offsets_and_sentence_point_to_the_call() -> None:
    text = "Primeira frase. Segundo Souza et al. (2019), filas crescem sob carga. Fim."

    [citation] = find_citations([section(text)], AUTHOR_YEAR)

    assert text[citation.start : citation.end] == citation.marker == "Souza et al. (2019)"
    assert citation.sentence == "Segundo Souza et al. (2019), filas crescem sob carga."


def test_reference_section_and_empty_sections_are_skipped() -> None:
    sections = [
        section("Como em [1].", "sec_1"),
        section("[1] Autor A. Um titulo. 2020.", "sec_2", key="references"),
        section("", "sec_3"),
    ]

    citations = find_citations(sections, NUMBERED)

    assert citations == (
        Citation(
            reference_id="ref_1",
            marker="[1]",
            sentence="Como em [1].",
            section_id="sec_1",
            start=8,
            end=11,
        ),
    )


def test_no_references_no_citations() -> None:
    assert find_citations([section("Como em [1].")], []) == ()


def test_style_follows_the_list_and_the_calls() -> None:
    # Lista sem numeração, mas o texto só cita por número: o estilo é numérico.
    unnumbered = [ref(i, ["Autor A."], "2020") for i in range(1, 4)]

    assert links("Ver [1] e [3]. Também [2].", unnumbered) == [
        ("ref_1", "[1]"),
        ("ref_3", "[3]"),
        ("ref_2", "[2]"),
    ]


TIES = [
    ref(1, ["Agić, Ž.", "Tiedemann, J.", "Merkler, D."], "2015"),
    ref(2, ["Agić, Ž.", "Ljubešić, N."], "2015"),
    ref(3, ["Wang, S."], "2015"),
]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Agić et al. (2015) mostram.", [("ref_1", "Agić et al. (2015)")]),
        ("Já se viu (Agić and Ljubešić, 2015).", [("ref_2", "Agić and Ljubešić, 2015")]),
        ("Agić e Ljubešić (2015) mostram.", [("ref_2", "Agić e Ljubešić (2015)")]),
    ],
)
def test_same_first_author_and_year_is_resolved_by_coauthors(
    text: str, expected: list[tuple[str | None, str]]
) -> None:
    assert links(text, TIES) == expected


def test_single_author_call_picks_the_single_author_entry() -> None:
    entries = [ref(1, ["Wang, S."], "2015"), ref(2, ["Wang, S.", "Jiang, J."], "2015")]

    assert links("Antes (Wang, 2015).", entries) == [("ref_1", "Wang, 2015")]
