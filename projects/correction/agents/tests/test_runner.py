"""Medição única e classificação de falhas sem esconder erros de programação."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from agno.exceptions import ModelProviderError
from agno.metrics import RunMetrics
from agno.run.agent import RunOutput
from agno.run.base import RunStatus

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.limits import ProviderLimiter
from projects.correction.agents.pricing import ModelPrice, Pricing
from projects.correction.agents.runner import AgentPayload, MeasuredRunner
from projects.correction.agents.schemas import PendingOutput
from projects.correction.agents.specs import Role, development_spec
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.pipeline.errors import LLMUnavailable as PipelineLLMUnavailable


def runner(
    invoke: Callable[[AgentPayload], RunOutput], sink: MemoryUsageSink
) -> MeasuredRunner[PendingOutput]:
    spec = development_spec(Role.EVALUATOR_A)
    return MeasuredRunner(
        invoke,
        PendingOutput,
        run_id="run-1",
        stage="evaluation",
        role=Role.EVALUATOR_A,
        agent="synthesizer",
        spec=spec,
        prompt_version="versao-1",
        usage_sink=sink,
        limiter=ProviderLimiter(1),
        pricing=Pricing(
            {
                (spec.provider, spec.model_id): ModelPrice(Decimal(2), Decimal(8), Decimal("0.5")),
            }
        ),
    )


def test_success_keeps_typed_content_and_exact_usage() -> None:
    sink = MemoryUsageSink()
    answer = PendingOutput(summary="sintética")
    run = RunOutput(
        content=answer,
        status=RunStatus.completed,
        metrics=RunMetrics(
            input_tokens=20,
            output_tokens=5,
            cache_read_tokens=4,
            duration=0.125,
        ),
    )
    result = runner(lambda payload: run, sink).run(AgentPayload("pergunta", article="segredo"))
    assert result.valid and result.content == answer
    assert [result.usage] == sink.calls
    assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.cached_tokens) == (
        20,
        5,
        4,
    )
    assert result.usage.latency_ms == 125 and result.usage.cost_usd == Decimal("0.000074")
    assert result.usage.run_id == "run-1" and result.usage.stage == "evaluation"


@pytest.mark.parametrize(
    "raw", ['{"summary":"json válido ainda é str"}', "cortada", None, {"summary": "dict"}]
)
def test_unparsed_content_is_invalid_and_still_records_usage(raw: object) -> None:
    sink = MemoryUsageSink()
    result = runner(lambda payload: RunOutput(content=raw, status=RunStatus.completed), sink).run(
        "teste"
    )
    assert not result.valid and result.content is None and result.raw == raw
    assert len(sink.calls) == 1
    assert not sink.calls[0].success and sink.calls[0].error == "InvalidOutput"


def test_agent_error_status_is_an_unavailable_provider() -> None:
    sink = MemoryUsageSink()

    def invoke(payload: AgentPayload) -> RunOutput:
        return RunOutput(status=RunStatus.error, content="manuscrito confidencial")

    with pytest.raises(LLMUnavailable) as caught:
        runner(invoke, sink).run("teste")
    assert "confidencial" not in str(caught.value)
    assert len(sink.calls) == 1 and sink.calls[0].error == "ProviderError"
    assert LLMUnavailable is PipelineLLMUnavailable


@pytest.mark.parametrize(
    "error", [ModelProviderError("segredo", status_code=503), RuntimeError("bug")]
)
def test_raised_error_records_once_and_programming_error_preserves_its_type(
    error: Exception,
) -> None:
    sink = MemoryUsageSink()

    def invoke(payload: AgentPayload) -> RunOutput:
        raise error

    expected = LLMUnavailable if isinstance(error, ModelProviderError) else RuntimeError
    with pytest.raises(expected):
        runner(invoke, sink).run("teste")
    assert len(sink.calls) == 1 and not sink.calls[0].success
    assert "segredo" not in str(sink.calls[0].error)
