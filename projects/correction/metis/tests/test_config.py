"""Validation tests for centralized runtime configuration."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from projects.correction.agents.schemas.evaluation import EvaluationMode
from projects.correction.metis.config import MetisSettings


@pytest.mark.parametrize(
    "override",
    [
        {"stage_soft_time_limit_seconds": 1800},
        {"stage_time_limit_seconds": 7200},
        {"stage_retry_backoff_max_seconds": 7200},
        {"stale_stage_after_seconds": 1800},
        {"max_stage_claims": 4},
        {"llm_timeout_seconds": 1500},
    ],
)
def test_rejects_contradictory_timing(override: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        MetisSettings.model_validate(override)


def test_splits_and_cleans_csv_hosts() -> None:
    config = MetisSettings(allowed_hosts=" example.org, localhost ,, api.example.org ")

    assert config.allowed_hosts == ["example.org", "localhost", "api.example.org"]


def test_evaluation_mode_is_configurable_and_defaults_to_sectioned() -> None:
    assert MetisSettings(_env_file=None).evaluation_mode is EvaluationMode.SECTIONED
    assert MetisSettings(_env_file=None, evaluation_mode="whole_document").evaluation_mode is (
        EvaluationMode.WHOLE_DOCUMENT
    )


@pytest.mark.parametrize("budget", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_run_budget_must_be_positive_and_finite(budget: str) -> None:
    with pytest.raises(ValidationError):
        MetisSettings(llm_run_budget_usd=budget)


def test_optional_run_budget_is_read_as_decimal_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("METIS_LLM_RUN_BUDGET_USD", raising=False)
    assert MetisSettings(_env_file=None).llm_run_budget_usd is None
    monkeypatch.setenv("METIS_LLM_RUN_BUDGET_USD", "0.123456789012")
    assert MetisSettings(_env_file=None).llm_run_budget_usd == Decimal("0.123456789012")
