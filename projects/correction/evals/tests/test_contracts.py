from dataclasses import replace
from decimal import Decimal

import pytest
from pydantic import ValidationError

from projects.correction.agents.specs import Provider, Role
from projects.correction.agents.usage import LLMUsage
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    Metric,
    UsageSummary,
)
from projects.correction.evals.tests.helpers import changed, report


def test_round_trip_preserves_specs_parameters_prompt_hashes_and_decimal_cost() -> None:
    original = report()
    usage = UsageSummary(
        calls=1, cost_usd=Decimal("0.000000000001"), known_cost_usd=Decimal("0.000000000001")
    )
    original = changed(original, usage=usage)
    loaded = EvaluationReport.model_validate_json(original.model_dump_json())
    assert loaded == original
    assert loaded.report_id == original.report_id and loaded.variant_id == original.variant_id
    assert loaded.usage.cost_usd == Decimal("0.000000000001")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_nonfinite_or_boolean_metric_values_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        Metric(value=value, unit="score")


def test_unknown_schema_naive_dates_bad_hashes_and_duplicate_cases_are_rejected() -> None:
    original = report()
    for override in (
        {"schema_version": 2},
        {"created_at": "2026-11-13T00:00:00"},
        {"prompt_versions": {"classifier": ("not-a-hash",)}},
        {"parameters": {"temperature": float("nan")}},
        {"failures": 3},
    ):
        with pytest.raises(ValidationError):
            changed(original, **override)
    with pytest.raises(ValidationError):
        DatasetIdentity(name="duplicate", version="1", sha256="a" * 64, case_ids=("same", "same"))


def test_usage_counts_failed_and_unpriced_calls_without_turning_unknown_cost_into_zero() -> None:
    call = LLMUsage(
        run_id="case-a",
        stage="synthetic",
        role=Role.FAST,
        agent="classifier",
        provider=Provider.GOOGLE,
        model_id="fake",
        prompt_version="b" * 64,
        input_tokens=10,
        output_tokens=4,
        cached_tokens=2,
        cache_write_tokens=1,
        reasoning_tokens=3,
        latency_ms=1,
        success=False,
        cost_usd=Decimal("0.0001"),
    )
    summary = UsageSummary.from_calls([call, replace(call, cost_usd=None, success=True)])
    assert summary.calls == 2 and summary.input_tokens == 20 and summary.output_tokens == 8
    assert (
        summary.cached_tokens == 4
        and summary.cache_write_tokens == 2
        and summary.reasoning_tokens == 6
    )
    assert summary.cost_usd is None and summary.known_cost_usd == Decimal("0.0001")
    assert summary.unpriced_calls == 1
    with pytest.raises(ValidationError):
        UsageSummary(calls=1, unpriced_calls=1)
    with pytest.raises(ValidationError):
        changed(report(), usage=summary, model_specs={})
    with pytest.raises(ValidationError):
        changed(report(), usage=summary, prompt_versions={})
