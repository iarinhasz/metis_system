"""Agno e SDKs reais contra HTTP local: schema, métricas, falhas e retries."""

from uuid import uuid4

import pytest
from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.run.base import RunStatus

from projects.correction.agents.tests.contract_support import (
    PROMPT,
    ContractAnswer,
    Provider,
    agent,
    answer,
    assert_usage,
    error,
    model,
    sent_schema,
)
from projects.correction.agents.tests.http_stub import Response, provider_server


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_nested_schema_literal_metrics_and_run_id(provider: Provider) -> None:
    with provider_server() as server:
        server.queue(answer(provider))
        runner = agent(model(provider, url=server.url))
        task_id = str(uuid4())
        run = runner.run(PROMPT, run_id=task_id)

        assert run.status == RunStatus.completed and run.run_id == task_id
        assert_usage(run, exact=True)
        assert runner.telemetry is False and runner.store_media is False
        assert len(server.requests) == 1
        schema = sent_schema(server.requests[0])
        assert "findings" in schema and "valid" in schema and "invalid" in schema


@pytest.mark.parametrize("provider", ["openai", "google"])
@pytest.mark.parametrize("text", ['{"findings":', '{"findings": [], "language": "inventado"}'])
def test_invalid_output_remains_a_string(provider: Provider, text: str) -> None:
    with provider_server() as server:
        server.queue(answer(provider, text))
        run = agent(model(provider, url=server.url)).run(PROMPT)

        assert run.status == RunStatus.completed
        assert isinstance(run.content, str) and not isinstance(run.content, ContractAnswer)
        assert len(server.requests) == 1


@pytest.mark.parametrize("provider", ["openai", "google"])
@pytest.mark.parametrize("status", [401, 429, 503])
def test_model_exposes_provider_exception_and_status(provider: Provider, status: int) -> None:
    with provider_server() as server:
        server.queue(error(provider, status))
        client = model(provider, url=server.url)
        with pytest.raises(ModelProviderError) as caught:
            client.invoke([Message(role="user", content="teste")], Message(role="assistant"))

        assert caught.value.status_code == status
        assert caught.value.__cause__ is not None
        expected = (
            {401: "AuthenticationError", 429: "RateLimitError", 503: "InternalServerError"}[status]
            if provider == "openai"
            else "ServerError"
            if status >= 500
            else "ClientError"
        )
        assert type(caught.value.__cause__).__name__ == expected
        assert len(server.requests) == 1


@pytest.mark.parametrize("provider", ["openai", "google"])
@pytest.mark.parametrize(("status", "requests"), [(401, 1), (429, 2), (503, 2)])
def test_agent_returns_error_after_model_retries(
    provider: Provider, status: int, requests: int
) -> None:
    with provider_server() as server:
        server.queue(*[error(provider, status) for _ in range(requests)])
        run = agent(model(provider, url=server.url, retries=1)).run(PROMPT)

        assert run.status == RunStatus.error
        assert isinstance(run.content, str) and "Falha" in run.content
        assert len(server.requests) == requests


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_transient_failure_then_success(provider: Provider) -> None:
    with provider_server() as server:
        server.queue(error(provider, 503), answer(provider))
        run = agent(model(provider, url=server.url, retries=1)).run(PROMPT)
        assert run.status == RunStatus.completed
        assert_usage(run, exact=True)
        assert len(server.requests) == 2


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_short_timeout_becomes_an_error_run(provider: Provider) -> None:
    with provider_server() as server:
        response = answer(provider)
        server.queue(Response(response.payload, delay=0.3))
        run = agent(model(provider, url=server.url, timeout=0.05)).run(PROMPT)

        assert run.status == RunStatus.error
        assert isinstance(run.content, str)
        assert "timed out" in run.content.lower() or "timeout" in run.content.lower()
        assert len(server.requests) == 1


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_model_timeout_retains_the_sdk_cause(provider: Provider) -> None:
    with provider_server() as server:
        response = answer(provider)
        server.queue(Response(response.payload, delay=0.3))
        client = model(provider, url=server.url, timeout=0.05)
        with pytest.raises(ModelProviderError) as caught:
            client.invoke([Message(role="user", content="teste")], Message(role="assistant"))

        expected = "APITimeoutError" if provider == "openai" else "ReadTimeout"
        assert type(caught.value.__cause__).__name__ == expected
