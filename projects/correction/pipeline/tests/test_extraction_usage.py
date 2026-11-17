"""O E1 injeta o run real no runner; extrações reaproveitadas não geram custo novo."""

import json
from decimal import Decimal

import pytest

from projects.correction.agents.tests.http_stub import Response, provider_server
from projects.correction.agents.usage import UsageSink
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import Stage
from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.models import Extraction
from projects.correction.extractor.schemas import HeadingScan
from projects.correction.extractor.session import AgnoSession, DocumentSession, SessionOpener
from projects.correction.extractor.tests.pdfs import make_pdf
from projects.correction.metis.config import settings
from projects.correction.pipeline.stages import ExtractionStage, StageContext

pytestmark = pytest.mark.django_db(transaction=True)


def article() -> ExtractedArticle:
    return ExtractedArticle(
        title="Sintético",
        authors=(),
        language="pt",
        model="google/gemini-2.5-flash",
        sections=(
            ExtractedSection(
                id="sec_1",
                title="Resumo",
                level=1,
                parent_id=None,
                key="abstract",
                text="Texto sintético.",
                has_footnotes=False,
                coverage=None,
                fidelity=None,
            ),
        ),
    )


def context(run: Run) -> StageContext:
    task_id = "tarefa-e1"
    assert Run.claim_stage(run.pk, Stage.EXTRACTION, task_id) is not None
    return StageContext(str(run.pk), str(run.attempt_id), task_id, Stage.EXTRACTION)


def test_e1_records_the_actual_run_through_the_sdk_and_injected_sink(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "google_api_key", "sintetica-local")
    scan = {"title": "Sintético", "authors": [], "language": "pt", "headings": []}
    with provider_server() as server:
        server.queue(
            Response(
                {
                    "candidates": [
                        {
                            "content": {"role": "model", "parts": [{"text": json.dumps(scan)}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 20,
                        "candidatesTokenCount": 5,
                        "cachedContentTokenCount": 4,
                        "thoughtsTokenCount": 7,
                    },
                }
            )
        )

        def local_session(
            config: DocumentConfig,
            pdf: bytes,
            *,
            run_id: str,
            usage_sink: UsageSink,
            task_id: str,
        ) -> DocumentSession:
            assert task_id == "tarefa-e1"
            return AgnoSession(
                config,
                pdf,
                run_id=run_id,
                usage_sink=usage_sink,
                task_id=task_id,
                client_params={"http_options": {"base_url": server.url}},
            )

        def extract(attempt_id: object, *, opener: SessionOpener) -> tuple[Extraction, bool]:
            assert str(attempt_id) == str(run.attempt_id)
            session = opener(ARTICLE_CONFIG, make_pdf(["Resumo", "Texto sintético."]))
            assert session.ask("Liste as seções.", HeadingScan).title == "Sintético"
            return Extraction.store(run.attempt.sha256, "e1-uso", article()), False

        monkeypatch.setattr("projects.correction.pipeline.stages.AgnoSession", local_session)
        monkeypatch.setattr("projects.correction.pipeline.stages.extract_attempt", extract)
        outcome = ExtractionStage().execute(context(run))
        assert len(server.requests) == 1

    [call] = LLMCall.for_run(run.pk)
    assert call.stage == Stage.EXTRACTION and call.agent == "document_extractor"
    assert call.role == "vision" and call.model == ARTICLE_CONFIG.model
    assert (call.input_tokens, call.output_tokens, call.cached_tokens) == (20, 12, 4)
    assert call.cost_usd == Decimal("0.00003492")
    assert len(call.prompt_version) == 64
    assert outcome.payload["reused"] is False
    assert str(Run.get_by_id(run.pk).extraction_id) == outcome.payload["extraction_id"]


def test_reusing_extraction_has_no_new_calls_even_without_a_provider_key(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setattr(settings, "gemini_key", "")
    stored = Extraction.store(run.attempt.sha256, extraction_version(ARTICLE_CONFIG), article())

    outcome = ExtractionStage().execute(context(run))

    assert outcome.payload["reused"] is True
    assert outcome.payload["extraction_id"] == str(stored.pk)
    assert LLMCall.for_run(run.pk) == []
