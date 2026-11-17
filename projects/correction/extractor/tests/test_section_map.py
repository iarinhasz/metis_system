"""O dict das seções montado a partir dos títulos da chamada 1."""

import pytest

from projects.correction.extractor.config import SectionDefinition
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.schemas import HeadingScan, ScannedHeading
from projects.correction.extractor.section_map import (
    build_section_map,
    missing_required,
    section_end,
    section_target,
)


def scan(*headings: tuple[str, int]) -> HeadingScan:
    return HeadingScan(
        title="Um estudo",
        authors=(),
        language="pt",
        headings=tuple(ScannedHeading(title=title, level=level) for title, level in headings),
    )


def test_builds_ids_levels_and_parents_in_order() -> None:
    section_map = build_section_map(
        scan(("Resumo", 1), ("1 Introdução", 1), ("1.1 Contexto", 2), ("1.2 Escopo", 2),
             ("1.2.1 Limites", 3), ("2 Método", 1), ("Referências", 1)),
        ARTICLE_CONFIG,
    )  # fmt: skip

    assert [(s.id, s.title, s.level, s.parent_id) for s in section_map.values()] == [
        ("sec_1", "Resumo", 1, None),
        ("sec_2", "1 Introdução", 1, None),
        ("sec_3", "1.1 Contexto", 2, "sec_2"),
        ("sec_4", "1.2 Escopo", 2, "sec_2"),
        ("sec_5", "1.2.1 Limites", 3, "sec_4"),
        ("sec_6", "2 Método", 1, None),
        ("sec_7", "Referências", 1, None),
    ]


@pytest.mark.parametrize(
    ("title", "key"),
    [
        ("Abstract", "abstract"),
        ("RESUMO", "abstract"),
        ("Abstract—", "abstract"),
        ("7 References", "references"),
        ("VII. REFERÊNCIAS", "references"),
        ("Referências Bibliográficas", "references"),
        ("Bibliography:", "references"),
        ("2 Resultados", None),
        ("Referências cruzadas no texto", None),
    ],
)
def test_finds_the_sections_the_config_names(title: str, key: str | None) -> None:
    [section] = build_section_map(scan((title, 1)), ARTICLE_CONFIG).values()

    assert section.key == key


def test_the_first_section_with_the_name_keeps_the_key() -> None:
    section_map = build_section_map(scan(("Abstract", 1), ("Resumo", 1)), ARTICLE_CONFIG)

    assert [s.key for s in section_map.values()] == ["abstract", None]


def test_skips_blank_titles_and_normalizes_spaces() -> None:
    section_map = build_section_map(scan(("  ", 1), ("1   Introdução \n", 1)), ARTICLE_CONFIG)

    assert [(s.id, s.title) for s in section_map.values()] == [("sec_1", "1 Introdução")]


def test_reports_the_missing_required_sections() -> None:
    section_map = build_section_map(scan(("Resumo", 1), ("1 Introdução", 1)), ARTICLE_CONFIG)

    assert missing_required(section_map, ARTICLE_CONFIG) == ("references",)


def test_optional_sections_are_found_but_not_required() -> None:
    config = ARTICLE_CONFIG.model_copy(
        update={"optional_sections": (SectionDefinition(key="appendix", labels=("Apêndice",)),)}
    )
    section_map = build_section_map(
        scan(("Resumo", 1), ("A. Apêndice", 1), ("Referências", 1)), config
    )

    assert [s.key for s in section_map.values()] == ["abstract", "appendix", "references"]
    assert missing_required(section_map, config) == ()


def test_names_each_section_with_its_parent_and_where_it_ends() -> None:
    section_map = build_section_map(
        scan(
            ("3.2 Formulações", 1), ("Bubble Sort.", 2), ("4.1 Resultados", 1), ("Bubble Sort.", 2)
        ),
        ARTICLE_CONFIG,
    )

    assert (
        section_target(section_map, "sec_2") == '"Bubble Sort.", dentro da seção "3.2 Formulações"'
    )
    assert (
        section_target(section_map, "sec_4") == '"Bubble Sort.", dentro da seção "4.1 Resultados"'
    )
    assert section_target(section_map, "sec_1") == '"3.2 Formulações"'
    assert section_end(section_map, "sec_2") == 'no título "4.1 Resultados"'
    assert section_end(section_map, "sec_4") == "no fim do documento"
