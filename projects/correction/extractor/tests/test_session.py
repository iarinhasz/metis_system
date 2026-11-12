"""A sessão do Agno contra um servidor HTTP local no lugar da API do Gemini."""

import json
import logging
from typing import Any

import pytest

from projects.correction.extractor.config import InputStrategy
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import (
    InvalidModelAnswer,
    MissingModelKey,
    ModelUnavailable,
)
from projects.correction.extractor.schemas import HeadingScan
from projects.correction.extractor.session import INLINE_LIMIT_BYTES, AgnoSession
from projects.correction.extractor.tests.http_stub import StubResponse, StubServer
from projects.correction.extractor.tests.pdfs import ARTICLE_LINES, make_pdf
from projects.correction.metis.config import settings

GENERATE = "/v1beta/models/gemini-2.5-flash:generateContent"
SCAN = {"title": "Um estudo", "authors": ["Ana Souza"], "language": "pt", "headings": []}


def answer(payload: Any, finish_reason: str = "STOP") -> StubResponse:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return StubResponse.json(
        {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": finish_reason,
                }
            ]
        }
    )


def session(
    server: StubServer, pdf: bytes, strategy: InputStrategy = InputStrategy.PDF
) -> AgnoSession:
    config = ARTICLE_CONFIG.model_copy(update={"strategy": strategy})
    params = {"http_options": {"base_url": server.url, "timeout": 5000}}
    return AgnoSession(config, pdf, client_params=params)


def parts(server: StubServer) -> list[dict[str, Any]]:
    [request] = server.requests
    assert request.path == GENERATE
    parts: list[dict[str, Any]] = request.json()["contents"][0]["parts"]
    return parts


@pytest.mark.usefixtures("gemini_key")
def test_sends_the_pdf_and_returns_the_schema(stub_server: StubServer) -> None:
    stub_server.queue(answer(SCAN))
    pdf = make_pdf(ARTICLE_LINES)

    scan = session(stub_server, pdf).ask("Liste os títulos.", HeadingScan)

    assert scan == HeadingScan.model_validate(SCAN)
    sent = parts(stub_server)
    assert {"text": "Liste os títulos."} in sent
    assert any(part.get("inlineData", {}).get("mimeType") == "application/pdf" for part in sent)
    config = stub_server.requests[0].json()["generationConfig"]
    assert config["temperature"] == 0
    # A SDK manda o nome do proto (snake_case); a API aceita esse nome e o camelCase.
    assert config["thinkingConfig"] == {"thinking_budget": 0}
    assert config["responseMimeType"] == "application/json"


@pytest.mark.usefixtures("gemini_key")
def test_text_strategy_sends_the_text_instead_of_the_pdf(stub_server: StubServer) -> None:
    stub_server.queue(answer(SCAN))

    session(stub_server, make_pdf(ARTICLE_LINES), InputStrategy.TEXT).ask("Liste.", HeadingScan)

    sent = parts(stub_server)
    assert not any("inlineData" in part for part in sent)
    [text] = [part["text"] for part in sent]
    assert text.startswith("<artigo>\n") and ARTICLE_LINES[3] in text and text.endswith("Liste.")


@pytest.mark.usefixtures("gemini_key")
def test_pdf_too_big_to_go_inline_goes_as_text(stub_server: StubServer) -> None:
    stub_server.queue(answer(SCAN))
    big = make_pdf(ARTICLE_LINES, padding_bytes=INLINE_LIMIT_BYTES)

    session(stub_server, big).ask("Liste.", HeadingScan)

    assert not any("inlineData" in part for part in parts(stub_server))


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize(("status", "code"), [(429, "RESOURCE_EXHAUSTED"), (503, "UNAVAILABLE")])
def test_provider_failure_is_transient(stub_server: StubServer, status: int, code: str) -> None:
    error = {"error": {"code": status, "message": "falhou", "status": code}}
    stub_server.queue(StubResponse.json(error, status=status))

    with pytest.raises(ModelUnavailable, match="indisponível"):
        session(stub_server, make_pdf(ARTICLE_LINES)).ask("Liste.", HeadingScan)


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize(
    "response",
    [
        answer({"title": "Sem os outros campos"}),
        answer('{"title": "cortado', finish_reason="MAX_TOKENS"),
        StubResponse.json({"candidates": [{"finishReason": "RECITATION"}]}),
    ],
    ids=["fora-do-schema", "cortada", "bloqueada"],
)
def test_answer_that_is_not_the_schema_is_invalid(
    stub_server: StubServer, response: StubResponse
) -> None:
    stub_server.queue(response)

    with pytest.raises(InvalidModelAnswer):
        session(stub_server, make_pdf(ARTICLE_LINES)).ask("Liste.", HeadingScan)


def test_needs_the_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_key", "")
    monkeypatch.setattr(settings, "google_api_key", "")

    with pytest.raises(MissingModelKey, match="GEMINI_KEY"):
        AgnoSession(ARTICLE_CONFIG, make_pdf(ARTICLE_LINES))


def test_agno_warnings_with_manuscript_text_stay_out_of_the_log() -> None:
    logger = logging.getLogger("agno")

    def record(level: int) -> logging.LogRecord:
        return logger.makeRecord("agno", level, __file__, 1, "trecho do manuscrito", (), None)

    assert not logger.filter(record(logging.WARNING))
    assert logger.filter(record(logging.ERROR))
