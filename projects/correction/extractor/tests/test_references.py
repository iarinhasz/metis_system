"""A lista de referências separada em campos e conferida contra o texto da seção."""

import pytest

from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import InvalidModelAnswer
from projects.correction.extractor.references import parse_references
from projects.correction.extractor.schemas import HeadingScan, ParsedReferences
from projects.correction.extractor.tests.fakes import FakeSession, raw_entry

FIRST = "[1] C. Pereira. Sistemas distribuidos na pratica. Editora Exemplo, 2020."
SECOND = "[2] A. Silva e B. Souza. Filas de mensagens sob carga constante. Revista Y, 12(3), 2019a."
TEXT = f"{FIRST}\n\n{SECOND}"
INVENTED = "[3] D. Inventado. Uma obra que nao esta na lista de referencias do artigo. 2021."
SCAN = HeadingScan(title="t", authors=(), language="pt", headings=())


def scripted(*answers: ParsedReferences) -> FakeSession:
    return FakeSession(SCAN, {}, references=list(answers))


def answer(*entries: str, **fields: object) -> ParsedReferences:
    return ParsedReferences(references=tuple(raw_entry(e, **fields) for e in entries))


def test_entries_get_ids_in_order_and_cleaned_fields() -> None:
    parsed = ParsedReferences(
        references=(
            raw_entry(
                f"  {FIRST}  ",
                marker="[1]",
                authors=("C. Pereira", " "),
                title=" Sistemas distribuidos na pratica ",
                year="2020",
                venue="Editora Exemplo",
                doi="",
            ),
            raw_entry(SECOND, marker="[2]", authors=("A. Silva", "B. Souza"), year="2019a"),
        )
    )
    session = scripted(parsed)

    first, second = parse_references(session, ARTICLE_CONFIG, TEXT)

    assert (first.id, first.raw, first.marker, first.authors, first.title, first.doi) == (
        "ref_1",
        FIRST,
        "[1]",
        ("C. Pereira",),
        "Sistemas distribuidos na pratica",
        None,
    )
    assert (second.id, second.year) == ("ref_2", "2019a")


def test_the_call_goes_without_the_pdf() -> None:
    session = scripted(answer(FIRST, SECOND))

    parse_references(session, ARTICLE_CONFIG, TEXT)

    [prompt] = session.without_document
    assert f"<referencias>\n{TEXT}\n</referencias>" in prompt


def test_invented_entry_is_dropped_and_the_call_asked_again() -> None:
    session = scripted(answer(FIRST, SECOND, INVENTED), answer(FIRST, SECOND))

    references = parse_references(session, ARTICLE_CONFIG, TEXT)

    assert [r.raw for r in references] == [FIRST, SECOND]
    retry = session.prompts[1]
    assert "não estão na lista" in retry and "D. Inventado" in retry


def test_missing_entry_is_quoted_in_the_retry() -> None:
    session = scripted(answer(FIRST), answer(FIRST, SECOND))

    references = parse_references(session, ARTICLE_CONFIG, TEXT)

    assert len(references) == 2
    assert (
        "ficaram de fora" in session.prompts[1]
        and "Filas de mensagens sob carga" in session.prompts[1]
    )


def test_keeps_the_best_answer_when_retries_run_out() -> None:
    session = scripted(answer(FIRST), answer(INVENTED))

    references = parse_references(session, ARTICLE_CONFIG, TEXT)

    assert [r.raw for r in references] == [FIRST]


def test_no_entry_from_the_list_is_an_invalid_answer() -> None:
    session = scripted(answer(INVENTED))

    with pytest.raises(InvalidModelAnswer, match="nenhuma referência"):
        parse_references(session, ARTICLE_CONFIG, TEXT)
