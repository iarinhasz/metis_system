"""A cobertura: quanto do texto do PDF a seção devolvida pelo modelo traz."""

import pytest

from projects.correction.extractor.coverage import (
    coverage,
    fidelity,
    local_sections,
    missing_sentences,
    prose_sentences,
    reference_text,
)
from projects.correction.extractor.section_map import MappedSection, SectionMap

PROSE = "Filas de mensagens desacoplam produtores e consumidores em sistemas distribuidos."
MORE = "Medir o tempo de resposta ajuda a dimensionar a quantidade de consumidores."


def mapped(*titles: str) -> SectionMap:
    return {
        f"sec_{i}": MappedSection(id=f"sec_{i}", title=t, level=1, parent_id=None, key=None)
        for i, t in enumerate(titles, start=1)
    }


def test_reference_drops_page_headers_footers_and_numbers() -> None:
    pages = [
        "Publicado na Conferencia X\nPrimeira linha.\n1",
        "Publicado na Conferencia X\nSegunda linha.\n2",
        "Publicado na Conferencia X\nTerceira linha.\n3",
    ]

    assert reference_text(pages) == "Primeira linha.\nSegunda linha.\nTerceira linha."


def test_cuts_each_section_from_its_title_to_the_next() -> None:
    reference = f"Resumo\n{PROSE}\n1 Introducao\n{MORE}\nReferencias\n[1] Pereira, 2020."

    slices = local_sections(reference, mapped("Resumo", "1 Introducao", "Referencias"))

    assert slices == {
        "sec_1": f"\n{PROSE}\n",
        "sec_2": f"\n{MORE}\n",
        "sec_3": "\n[1] Pereira, 2020.",
    }


def test_title_search_ignores_case_accents_and_spacing() -> None:
    reference = f"1  INTRODUÇÃO\n{PROSE}"

    assert local_sections(reference, mapped("1 Introducao")) == {"sec_1": f"\n{PROSE}"}


def test_title_not_found_leaves_the_section_unverified() -> None:
    reference = f"Resumo\n{PROSE}\nReferencias\n{MORE}"

    slices = local_sections(reference, mapped("Resumo", "Titulo que nao existe", "Referencias"))

    assert slices["sec_2"] is None
    assert slices["sec_1"] == f"\n{PROSE}\n"


def test_titles_are_searched_in_order() -> None:
    # "Metodo" aparece antes no texto, citado na introdução; a seção é a segunda ocorrência.
    reference = f"Introducao\nComo mostra o Metodo, {PROSE}\nMetodo\n{MORE}"

    slices = local_sections(reference, mapped("Introducao", "Metodo"))

    assert slices["sec_2"] == f"\n{MORE}"


def test_full_copy_covers_everything() -> None:
    assert coverage(f"{PROSE} {MORE}", f"{PROSE}\n\n{MORE}") == 1.0


def test_skipped_sentence_lowers_the_coverage() -> None:
    value = coverage(f"{PROSE} {MORE}", PROSE)

    assert value is not None and 0.4 < value < 0.6


def test_spacing_hyphenation_case_and_accents_do_not_count() -> None:
    local = "Filas de mensagens desaco-\nplam produtores e consumidores em sistemas distribuídos."

    assert coverage(local, PROSE.upper()) == pytest.approx(1.0, abs=0.15)


def test_text_spliced_into_a_sentence_only_costs_its_own_words() -> None:
    # A extração local colou uma nota de rodapé no meio da frase; o modelo a tirou.
    local = (
        "Filas de mensagens desacoplam produtores 3Nota sobre outro assunto qualquer aqui "
        "e consumidores em sistemas distribuidos."
    )

    value = coverage(local, PROSE)

    assert value is not None and value > 0.3


@pytest.mark.parametrize(
    "sentence",
    [
        "Figure 2: Accuracy per epoch for every model trained on the dataset.",
        "Tabela 1 mostra os resultados de todos os modelos em todos os conjuntos.",
        "IMDB 82/50 97/88 36/12 74 11.9 CR 61/50 73/12 55/38 22 4.7 MR 63/50 77/14 55/38",
        "Curta demais.",
    ],
)
def test_captions_tables_and_short_lines_are_not_prose(sentence: str) -> None:
    assert prose_sentences(sentence) == []


def test_nothing_to_verify_gives_none() -> None:
    assert coverage(None, PROSE) is None
    assert coverage("[1] Pereira, 2020.", PROSE) is None


def test_words_glued_by_the_model_do_not_count() -> None:
    glued = "Filas de mensagens desacoplamprodutores e consumidores em sistemasdistribuidos."

    assert coverage(PROSE, glued) == 1.0


def test_fidelity_measures_how_much_of_the_answer_is_in_the_section() -> None:
    foreign = "Este paragrafo pertence a outra secao do artigo e foi copiado no lugar errado."

    assert fidelity(PROSE, PROSE) == 1.0
    assert fidelity(PROSE, foreign) == 0.0
    value = fidelity(PROSE, f"{PROSE} {foreign}")
    assert value is not None and 0.3 < value < 0.7


def test_fidelity_without_answer_or_local_text_is_none() -> None:
    assert fidelity(PROSE, "") is None
    assert fidelity(None, PROSE) is None


def test_lists_the_missing_sentences_in_order() -> None:
    third = "Uma terceira frase de prosa com palavras suficientes para contar aqui."

    assert missing_sentences(f"{PROSE} {MORE} {third}", PROSE, limit=1) == [MORE]
    assert missing_sentences(f"{PROSE} {MORE} {third}", PROSE, limit=5) == [MORE, third]
    assert missing_sentences(None, PROSE, limit=2) == []
