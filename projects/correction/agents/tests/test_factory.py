"""A fábrica real e o runner usam os SDKs contra servidores HTTP locais."""

import logging

import pytest

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.models import ModelFactory
from projects.correction.agents.specs import Family, ModelSpec, Provider, Role
from projects.correction.agents.tests.contract_support import ANSWER, ContractAnswer, answer, error
from projects.correction.agents.tests.http_stub import Response, provider_server
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.metis.config import MetisSettings


@pytest.mark.parametrize("provider", list(Provider))
def test_factory_executes_a_typed_agent_and_records_provider_metrics(provider: Provider) -> None:
    with provider_server() as server:
        server.queue(answer(provider.value), answer(provider.value))
        specs = MetisSettings(_env_file=None).model_specs
        sink = MemoryUsageSink()
        models = ModelFactory(
            specs,
            openai_api_key="sintetica",
            google_api_key="sintetica",
            client_params={
                provider: (
                    {"base_url": f"{server.url}/v1"}
                    if provider is Provider.OPENAI
                    else {"http_options": {"base_url": server.url}}
                )
            },
            retry_delay_seconds=0,
        )
        factory = AgentFactory("run-sintetico", "evaluation", sink, model_factory=models)
        role = Role.EVALUATOR_A if provider is Provider.OPENAI else Role.EVALUATOR_B
        runner = factory.build("profiler_field", role, ContractAnswer)
        first, second = runner.run("primeiro"), runner.run("segundo")
        assert first.valid and first.content == ANSWER and second.content == ANSWER
        assert len(server.requests) == len(sink.calls) == 2
        assert (
            sink.calls[0].input_tokens,
            sink.calls[0].output_tokens,
            sink.calls[0].cached_tokens,
        ) == (20, 5, 4)
        assert sink.calls[0].prompt_version == sink.calls[1].prompt_version
        messages = server.requests[1]
        assert "primeiro" not in str(messages)


@pytest.mark.parametrize("provider", list(Provider))
@pytest.mark.parametrize("status", [401, 503])
def test_factory_has_one_model_retry_and_no_sdk_retry(provider: Provider, status: int) -> None:
    with provider_server() as server:
        server.queue(error(provider.value, status))
        if status == 503:
            server.queue(answer(provider.value))
        specs = MetisSettings(_env_file=None).model_specs
        models = ModelFactory(
            specs,
            openai_api_key="sintetica",
            google_api_key="sintetica",
            client_params={
                provider: (
                    {"base_url": f"{server.url}/v1"}
                    if provider is Provider.OPENAI
                    else {"http_options": {"base_url": server.url}}
                )
            },
            retry_delay_seconds=0,
        )
        sink = MemoryUsageSink()
        factory = AgentFactory("run", "evaluation", sink, model_factory=models)
        role = Role.EVALUATOR_A if provider is Provider.OPENAI else Role.EVALUATOR_B
        runner = factory.build("profiler_field", role, ContractAnswer)
        if status == 401:
            with pytest.raises(LLMUnavailable):
                runner.run("sintético")
        else:
            assert runner.run("sintético").valid
        assert len(server.requests) == (2 if status == 503 else 1)
        assert len(sink.calls) == 1


@pytest.mark.parametrize("provider", list(Provider))
def test_factory_applies_timeout_to_the_sdk_and_records_the_failure(provider: Provider) -> None:
    with provider_server() as server:
        server.queue(Response(answer(provider.value).payload, delay=0.2))
        specs = MetisSettings(_env_file=None).model_specs
        models = ModelFactory(
            specs,
            openai_api_key="sintetica",
            google_api_key="sintetica",
            retries=0,
            client_params={
                provider: (
                    {"base_url": f"{server.url}/v1"}
                    if provider is Provider.OPENAI
                    else {"http_options": {"base_url": server.url}}
                )
            },
        )
        sink = MemoryUsageSink()
        factory = AgentFactory("run", "evaluation", sink, model_factory=models)
        spec = ModelSpec(
            provider=provider,
            family=Family.GPT if provider is Provider.OPENAI else Family.GEMINI,
            model_id="sintetico",
            timeout_seconds=0.05,
        )
        runner = factory.build("profiler_field", Role.FAST, ContractAnswer, spec=spec)
        with pytest.raises(LLMUnavailable):
            runner.run("teste de timeout")
        assert len(sink.calls) == 1 and not sink.calls[0].success


def test_provider_log_never_keeps_manuscript_text() -> None:
    logger = logging.getLogger("agno")
    record = logger.makeRecord(
        "agno", logging.ERROR, __file__, 1, "segredo %s", ("manuscrito",), None
    )
    assert logger.filter(record)
    assert "segredo" not in record.getMessage() and "manuscrito" not in record.getMessage()
