"""Uma linha por execução, no PostgreSQL, inclusive sob falha e concorrência."""

import logging
from collections.abc import Mapping, Sequence
from decimal import Decimal

import pytest
from agno.metrics import RunMetrics
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from django.test import Client
from django.urls import reverse

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory, InvalidFor
from projects.correction.agents.limits import ProviderLimiter
from projects.correction.agents.pricing import ModelPrice, Pricing
from projects.correction.agents.prompts import RenderedPrompt
from projects.correction.agents.runner import MeasuredRunner
from projects.correction.agents.schemas import PendingOutput
from projects.correction.agents.specs import Family, ModelSpec, Provider, Role, development_spec
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import Stage
from projects.correction.metis.concurrency import bounded_map
from projects.correction.metis.config import MetisSettings
from projects.correction.pipeline.usage import DatabaseUsageSink

pytestmark = pytest.mark.django_db(transaction=True)


def factory(
    run: Run,
    *,
    config: MetisSettings | None = None,
    pricing: Pricing | None = None,
    scripts: Mapping[str | Role, Sequence[object]] | None = None,
) -> FakeAgentFactory:
    return FakeAgentFactory(
        str(run.pk),
        Stage.EVALUATION,
        DatabaseUsageSink(),
        config=config,
        pricing=pricing,
        scripts=scripts,
    )


def test_every_runner_execution_records_exact_tokens_cost_and_prompt_version(run: Run) -> None:
    spec = development_spec(Role.EVALUATOR_A)
    agents = factory(
        run,
        pricing=Pricing(
            {(spec.provider, spec.model_id): ModelPrice(Decimal(2), Decimal(8), Decimal("0.5"))}
        ),
    )
    result = agents.build(
        "synthesizer",
        Role.EVALUATOR_A,
        PendingOutput,
        prompt=RenderedPrompt("Instrução sintética.", "f" * 64),
    ).run("O manuscrito não deve ser gravado na auditoria.")

    [call] = LLMCall.for_run(run.pk)
    assert call.run_id == run.pk and call.stage == Stage.EVALUATION
    assert call.role == Role.EVALUATOR_A and call.agent == "synthesizer"
    assert call.provider == spec.provider and call.model == spec.model_id
    assert call.prompt_version == "f" * 64
    assert (call.input_tokens, call.output_tokens, call.cached_tokens) == (20, 5, 4)
    assert call.cost_usd == result.usage.cost_usd == Decimal("0.000074")
    assert call.latency_ms >= 0 and call.success and call.error == ""
    assert "manuscrito" not in str(vars(call))


def test_unknown_model_still_records_usage_with_null_cost(
    run: Run, caplog: pytest.LogCaptureFixture
) -> None:
    config = MetisSettings(_env_file=None, evaluator_a={"model_id": "sem-preço"})
    with caplog.at_level(logging.WARNING, logger="projects.correction.agents.pricing"):
        factory(run, config=config).build(
            "synthesizer",
            Role.EVALUATOR_A,
            PendingOutput,
            prompt=RenderedPrompt("Sintético.", "a" * 64),
        ).run("Pergunta.")

    [call] = LLMCall.for_run(run.pk)
    assert call.cost_usd is None and call.input_tokens == 20 and call.success
    assert "Preço não cadastrado" in caplog.text and "sem-preço" in caplog.text


@pytest.mark.parametrize("invalid", [True, False])
def test_invalid_answers_and_unavailable_models_are_also_recorded(run: Run, invalid: bool) -> None:
    script = InvalidFor(1) if invalid else LLMUnavailable("resposta confidencial do provedor")
    runner = factory(run, scripts={Role.FAST: [script]}).profiler_field()
    if invalid:
        assert not runner.run("Pergunta.").valid
    else:
        with pytest.raises(LLMUnavailable):
            runner.run("Pergunta.")

    [call] = LLMCall.for_run(run.pk)
    assert not call.success
    assert call.error == ("InvalidOutput" if invalid else "LLMUnavailable")
    assert "confidencial" not in call.error


def test_identical_retries_are_separate_paid_calls(run: Run) -> None:
    runner = factory(run).profiler_field()
    runner.run("Mesma pergunta.")
    runner.run("Mesma pergunta.")
    first, second = LLMCall.for_run(run.pk)
    assert first.pk != second.pk
    assert first.cost_usd == second.cost_usd


@pytest.mark.parametrize("provider", list(Provider))
def test_billable_reasoning_and_cache_write_counts_are_persisted(
    run: Run, provider: Provider
) -> None:
    spec = ModelSpec(
        provider=provider,
        model_id="sintético",
        family=Family.GPT if provider is Provider.OPENAI else Family.GEMINI,
    )
    output = RunOutput(
        status=RunStatus.completed,
        content=PendingOutput(summary="Sintético."),
        metrics=RunMetrics(
            input_tokens=20,
            output_tokens=5,
            cache_read_tokens=4,
            cache_write_tokens=3,
            reasoning_tokens=7,
            duration=0.125,
        ),
    )
    runner = MeasuredRunner(
        lambda payload: output,
        PendingOutput,
        run_id=str(run.pk),
        stage=Stage.EVALUATION,
        role=Role.FAST,
        agent="profiler_field",
        spec=spec,
        prompt_version="b" * 64,
        usage_sink=DatabaseUsageSink(),
        limiter=ProviderLimiter(1),
        pricing=Pricing(
            {(provider, spec.model_id): ModelPrice(Decimal(2), Decimal(8), Decimal("0.5"))}
        ),
    )
    runner.run("Pergunta.")
    [call] = LLMCall.for_run(run.pk)
    assert call.output_tokens == (12 if provider is Provider.GOOGLE else 5)
    assert call.reasoning_tokens == 7 and call.cache_write_tokens == 3
    assert call.cost_usd == Decimal("0.000130" if provider is Provider.GOOGLE else "0.000074")
    assert call.latency_ms == 125


def test_concurrent_calls_are_all_recorded_under_their_run(run: Run) -> None:
    runner = factory(run).profiler_field()
    bounded_map(lambda index: runner.run(f"Pergunta {index}."), range(12), max_workers=3)
    calls = LLMCall.for_run(run.pk)
    assert len(calls) == len({call.pk for call in calls}) == 12
    assert all(call.run_id == run.pk and call.stage == Stage.EVALUATION for call in calls)
    other_run = Run.create(attempt=run.attempt)
    assert LLMCall.for_run(other_run.pk) == []


def test_admin_is_read_only_even_on_direct_post(admin_client: Client, run: Run) -> None:
    factory(run).profiler_field().run("Pergunta.")
    [call] = LLMCall.for_run(run.pk)
    detail_url = reverse("admin:attempts_llmcall_change", args=[call.pk])
    assert admin_client.get(reverse("admin:attempts_llmcall_changelist")).status_code == 200
    assert admin_client.get(detail_url).status_code == 200
    assert admin_client.post(detail_url, {"cost_usd": "999"}).status_code == 403
    assert admin_client.get(reverse("admin:attempts_llmcall_add")).status_code == 403
    assert (
        admin_client.post(reverse("admin:attempts_llmcall_delete", args=[call.pk])).status_code
        == 403
    )
    [stored] = LLMCall.for_run(run.pk)
    assert stored.cost_usd == call.cost_usd
