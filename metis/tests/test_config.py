"""Validation tests for centralized runtime configuration."""

import pytest
from pydantic import ValidationError

from metis.config import MetisSettings


@pytest.mark.parametrize(
    "override",
    [
        {"stage_soft_time_limit_seconds": 1800},
        {"stage_time_limit_seconds": 7200},
        {"stage_retry_backoff_max_seconds": 7200},
        {"stale_stage_after_seconds": 1800},
        {"max_stage_claims": 4},
    ],
)
def test_rejects_contradictory_timing(override: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        MetisSettings.model_validate(override)


def test_splits_and_cleans_csv_hosts() -> None:
    config = MetisSettings(allowed_hosts=" example.org, localhost ,, api.example.org ")

    assert config.allowed_hosts == ["example.org", "localhost", "api.example.org"]
