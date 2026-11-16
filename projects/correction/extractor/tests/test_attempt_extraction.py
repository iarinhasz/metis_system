"""O E1 de uma attempt: lê o PDF do storage, divide e guarda; o mesmo PDF reaproveita, e o retry
do estágio retoma das respostas guardadas."""

from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from pydantic import BaseModel

from projects.correction.attempts.models import Article, Attempt
from projects.correction.extractor.attempt_extraction import (
    extract_attempt,
    extraction_payload,
    extraction_version,
)
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import InvalidModelAnswer, ModelUnavailable
from projects.correction.extractor.models import ExtractionStep
from projects.correction.extractor.schemas import ParsedReferences
from projects.correction.extractor.session import DocumentSession, SessionOpener
from projects.correction.extractor.tests.fakes import FakeSession
from projects.correction.extractor.tests.test_service import PDF, SCAN, complete, content

# Com transação de verdade: as chamadas em paralelo gravam as respostas das próprias threads, em
# outra conexão, que o rollback do teste comum não desfaria.
pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("media_root")]


class FailsOnce:
    """Cai com o modelo fora do ar na primeira pergunta com aquele schema."""

    def __init__(self, session: FakeSession, output: type[BaseModel]) -> None:
        self._session, self._output, self.failed = session, output, False

    def ask[T: BaseModel](self, prompt: str, output: type[T], *, with_document: bool = True) -> T:
        if output is self._output and not self.failed:
            self.failed = True
            raise ModelUnavailable("429")
        return self._session.ask(prompt, output, with_document=with_document)

    def opener(self) -> SessionOpener:
        def open_failing(config: DocumentConfig, pdf: bytes) -> DocumentSession:
            del config, pdf
            return self

        return open_failing


@pytest.fixture
def attempt() -> Attempt:
    article = Article.get_or_create_by_external_id("artigo-e1")
    attempt, _ = Attempt.create_next(
        article,
        sha256="c" * 64,
        file=ContentFile(PDF, name="paper.pdf"),
        original_filename="paper.pdf",
        size_bytes=len(PDF),
        submitted_by="test-service",
    )
    return attempt


def test_extracts_the_pdf_from_storage_and_stores_it(attempt: Attempt, media_root: Path) -> None:
    session = FakeSession(SCAN, complete())

    extraction, reused = extract_attempt(attempt.pk, opener=session.opener())

    assert not reused
    assert (extraction.sha256, extraction.version) == (
        attempt.sha256,
        extraction_version(ARTICLE_CONFIG),
    )
    assert extraction.article.section("abstract") is not None
    assert len(session.prompts) == 1 + 4 + 1 + 1  # mapa, seções, referências e figuras


def test_same_pdf_reuses_the_stored_extraction(attempt: Attempt) -> None:
    first, _ = extract_attempt(attempt.pk, opener=FakeSession(SCAN, complete()).opener())
    session = FakeSession(SCAN, complete())

    again, reused = extract_attempt(attempt.pk, opener=session.opener())

    assert reused and again.pk == first.pk
    assert session.prompts == []


def test_a_new_extractor_version_extracts_again(attempt: Attempt) -> None:
    first, _ = extract_attempt(attempt.pk, opener=FakeSession(SCAN, complete()).opener())
    config = ARTICLE_CONFIG.model_copy(update={"model": "outro-modelo"})

    second, reused = extract_attempt(attempt.pk, config, FakeSession(SCAN, complete()).opener())

    assert not reused and second.pk != first.pk


def test_version_changes_with_the_config() -> None:
    other = ARTICLE_CONFIG.model_copy(update={"min_coverage": 0.9})

    assert extraction_version(ARTICLE_CONFIG) == extraction_version(ARTICLE_CONFIG)
    assert extraction_version(ARTICLE_CONFIG) != extraction_version(other)


def test_event_payload_has_counts_and_ids_but_no_text(attempt: Attempt) -> None:
    sections = complete()
    sections["1 Introducao"] = [content("Texto que nao esta no PDF.")]
    extraction, reused = extract_attempt(attempt.pk, opener=FakeSession(SCAN, sections).opener())

    payload = extraction_payload(extraction, reused=reused)

    assert payload == {
        "extraction_id": str(extraction.pk),
        "reused": False,
        "model": "google/gemini-3.6-flash",
        "sections": 4,
        "below_check": ["sec_2"],
        "references": 1,
        "citations": 0,
        "unlinked_citations": 0,
        "figures": 0,
        "figures_described": 0,
    }


def test_a_stage_retry_does_not_ask_again_what_was_answered(attempt: Attempt) -> None:
    first = FakeSession(SCAN, complete())
    with pytest.raises(ModelUnavailable):
        extract_attempt(attempt.pk, opener=FailsOnce(first, ParsedReferences).opener())
    assert len(first.prompts) == 1 + 4  # mapa e seções; as referências caíram

    retry = FakeSession(SCAN, complete())
    extraction, reused = extract_attempt(attempt.pk, opener=retry.opener())

    assert not reused
    assert extraction.article.section("abstract") is not None
    assert len(retry.prompts) == 1 + 1  # só as referências e a lista de figuras
    assert retry.calls_per_title == {}
    assert ExtractionStep.stored(attempt.sha256, extraction_version(ARTICLE_CONFIG)) == {}


def test_an_invalid_answer_forgets_the_stored_steps(attempt: Attempt) -> None:
    sections = complete()
    sections["Resumo"] = [content("")]

    with pytest.raises(InvalidModelAnswer):
        extract_attempt(attempt.pk, opener=FakeSession(SCAN, sections).opener())

    assert ExtractionStep.stored(attempt.sha256, extraction_version(ARTICLE_CONFIG)) == {}
