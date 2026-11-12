"""Configuração inválida falha na subida, antes de construir clientes."""

from typing import Any

import pytest
from pydantic import ValidationError

from projects.correction.agents.specs import (
    Family,
    ModelSpec,
    Provider,
    Role,
    development_spec,
    validate_catalog,
)
from projects.correction.metis.config import MetisSettings


@pytest.mark.parametrize(
    "override",
    [
        {"provider": "desconhecido"},
        {"model_id": "  "},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
        {"family": "gemini"},
        {"params": {"api_key": "segredo"}},
        {"params": {"retries": 4}},
        {"params": {"thinking_budget": 0}},
        {"params": {"temperature": "quente"}},
        {"params": {"temperature": 3}},
        {"params": {"max_tokens": 0}},
        {"params": {"stop": [12]}},
    ],
)
def test_invalid_spec(override: dict[str, Any]) -> None:
    values = development_spec(Role.EVALUATOR_A).model_dump() | override
    with pytest.raises(ValidationError):
        ModelSpec.model_validate(values)


def test_spec_is_frozen_and_serializable() -> None:
    spec = development_spec(Role.EVALUATOR_A)
    assert ModelSpec.model_validate_json(spec.model_dump_json()) == spec
    with pytest.raises(ValidationError):
        spec.model_id = "outro"  # type: ignore[misc]


def test_missing_role_fails_catalog_validation() -> None:
    specs = MetisSettings(_env_file=None).model_specs
    del specs[Role.EVALUATOR_C]
    with pytest.raises(ValueError, match="evaluator_c"):
        validate_catalog(specs)


@pytest.mark.parametrize(
    "override",
    [
        {"evaluator_a": None},
        {"llm_max_concurrency": 0},
        {"judge_google": {"provider": "openai", "family": "gpt"}},
        {"evaluator_c": {"timeout_seconds": 1500}},
    ],
)
def test_invalid_settings_fail_at_startup(override: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        MetisSettings(_env_file=None, **override)


def test_environment_can_override_one_role_and_nested_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METIS_EVALUATOR_A__MODEL_ID", "modelo-local")
    monkeypatch.setenv("METIS_EVALUATOR_A__TIMEOUT_SECONDS", "12")
    monkeypatch.setenv(
        "METIS_EVALUATOR_C", '{"provider":"google","family":"gemini","model_id":"outro-gemini"}'
    )
    config = MetisSettings(_env_file=None)
    assert config.evaluator_a.model_id == "modelo-local"
    assert config.evaluator_a.timeout_seconds == 12
    assert config.evaluator_a.family is Family.GPT
    assert config.evaluator_c.provider is Provider.GOOGLE
    assert set(config.model_specs) == set(Role)


def test_google_key_alias_preserves_the_existing_e1_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_KEY", "chave-legada")
    monkeypatch.delenv("METIS_GOOGLE_API_KEY", raising=False)
    assert MetisSettings(_env_file=None).google_api_key == "chave-legada"
    monkeypatch.setenv("METIS_GOOGLE_API_KEY", "chave-nova")
    assert MetisSettings(_env_file=None).google_api_key == "chave-nova"
