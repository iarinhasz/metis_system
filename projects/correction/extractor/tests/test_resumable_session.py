"""A sessão que retoma: guarda cada resposta no banco e devolve as guardadas sem chamar o modelo."""

import pytest

from projects.correction.extractor.models import ExtractionStep
from projects.correction.extractor.resumable_session import ResumableSession, step_key
from projects.correction.extractor.schemas import HeadingScan, ParsedReferences
from projects.correction.extractor.tests.fakes import FakeSession, raw_entry
from projects.correction.extractor.tests.test_service import SCAN

pytestmark = pytest.mark.django_db

SHA = "d" * 64
OTHER_SCAN = HeadingScan(title="Outro", authors=(), language="en", headings=())


def test_a_stored_answer_comes_back_without_calling_the_model() -> None:
    first = FakeSession(SCAN, {})
    asked = ResumableSession(first, SHA, "v1").ask("mapeie", HeadingScan)

    again = FakeSession(OTHER_SCAN, {})
    replayed = ResumableSession(again, SHA, "v1").ask("mapeie", HeadingScan)

    assert replayed == asked == SCAN
    assert (len(first.prompts), again.prompts) == (1, [])


def test_tuples_and_nulls_survive_the_round_trip() -> None:
    entry = raw_entry("Silva, A. (2020). Filas.", authors=("Silva, A.",), year="2020", doi=None)
    answer = ParsedReferences(references=(entry,))
    first = FakeSession(SCAN, {}, references=[answer])
    ResumableSession(first, SHA, "v1").ask("separe", ParsedReferences, with_document=False)

    replayed = ResumableSession(FakeSession(SCAN, {}), SHA, "v1").ask(
        "separe", ParsedReferences, with_document=False
    )

    assert replayed == answer


def test_another_pdf_or_version_asks_the_model() -> None:
    ResumableSession(FakeSession(SCAN, {}), SHA, "v1").ask("mapeie", HeadingScan)

    other_pdf, other_version = FakeSession(OTHER_SCAN, {}), FakeSession(OTHER_SCAN, {})
    ResumableSession(other_pdf, "e" * 64, "v1").ask("mapeie", HeadingScan)
    ResumableSession(other_version, SHA, "v2").ask("mapeie", HeadingScan)

    assert (len(other_pdf.prompts), len(other_version.prompts)) == (1, 1)


def test_prompt_schema_and_document_flag_make_different_steps() -> None:
    keys = {
        step_key("mapeie", HeadingScan, with_document=True),
        step_key("mapeie de novo", HeadingScan, with_document=True),
        step_key("mapeie", ParsedReferences, with_document=True),
        step_key("mapeie", HeadingScan, with_document=False),
    }

    assert len(keys) == 4


def test_forget_drops_the_steps_of_that_pdf_and_version_only() -> None:
    ResumableSession(FakeSession(SCAN, {}), SHA, "v1").ask("mapeie", HeadingScan)
    ResumableSession(FakeSession(SCAN, {}), SHA, "v2").ask("mapeie", HeadingScan)

    ExtractionStep.forget(SHA, "v1")

    assert ExtractionStep.stored(SHA, "v1") == {}
    assert len(ExtractionStep.stored(SHA, "v2")) == 1
