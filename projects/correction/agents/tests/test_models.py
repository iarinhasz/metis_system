"""Família cruzada e clientes reais contra HTTP local, sem chamadas externas."""

import pytest
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat

from projects.correction.agents.errors import MissingProviderKey
from projects.correction.agents.models import ModelFactory
from projects.correction.agents.specs import Family, ModelSpec, Provider, Role
from projects.correction.metis.config import MetisSettings


def model_factory() -> ModelFactory:
    return ModelFactory(
        MetisSettings(_env_file=None).model_specs,
        openai_api_key="openai-sintetica",
        google_api_key="google-sintetica",
    )


@pytest.mark.parametrize("role", list(Role))
def test_every_model_has_a_judge_from_the_other_family(role: Role) -> None:
    factory = model_factory()
    spec = factory.specs[role]
    assert factory.judge_for(spec).family is not spec.family


@pytest.mark.parametrize("family", list(Family))
def test_slot_c_can_change_family(family: Family) -> None:
    factory = model_factory()
    provider = Provider.OPENAI if family is Family.GPT else Provider.GOOGLE
    spec = ModelSpec(provider=provider, family=family, model_id="slot-c")
    assert factory.judge_for(spec).family is not family


@pytest.mark.parametrize("provider", list(Provider))
def test_explicit_credentials_timeout_and_retry_policy(provider: Provider) -> None:
    factory = model_factory()
    family = Family.GPT if provider is Provider.OPENAI else Family.GEMINI
    spec = ModelSpec(provider=provider, family=family, model_id="sintetico", timeout_seconds=0.5)
    model = factory.build(spec)
    assert model.retries == 1 and model.exponential_backoff
    assert not model.retry_with_guidance
    if isinstance(model, OpenAIChat):
        params = model._get_client_params()
        assert params["api_key"] == "openai-sintetica"
        assert params["max_retries"] == 0 and params["timeout"] == 0.5
    else:
        assert isinstance(model, Gemini)
        assert model.api_key == "google-sintetica"
        assert model.client_params is not None
        assert model.client_params["http_options"] == {
            "timeout": 500,
            "retry_options": {"attempts": 1},
        }


def test_client_overrides_cannot_replace_credentials_or_retry_policy() -> None:
    specs = MetisSettings(_env_file=None).model_specs
    factory = ModelFactory(
        specs,
        openai_api_key="explicita",
        google_api_key="explicita",
        client_params={Provider.OPENAI: {"api_key": "ignorada", "max_retries": 99}},
    )
    model = factory.build(specs[Role.EVALUATOR_A])
    assert isinstance(model, OpenAIChat)
    assert model._get_client_params()["api_key"] == "explicita"
    assert model._get_client_params()["max_retries"] == 0


def test_missing_key_fails_before_requesting_a_model() -> None:
    specs = MetisSettings(_env_file=None).model_specs
    factory = ModelFactory(specs, openai_api_key="", google_api_key="")
    with pytest.raises(MissingProviderKey):
        factory.build(specs[Role.EVALUATOR_A])
