"""Contratos com provedores reais. Fora do CI: pytest -m llm, com chaves no .env.

Só usa texto sintético. Sem chave configurada, o teste do provedor é pulado explicitamente.
"""

import pytest
from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.run.base import RunStatus

from projects.correction.agents.tests.contract_support import (
    PROMPT,
    Provider,
    agent,
    assert_usage,
    model,
)
from projects.correction.metis.config import settings

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_live_nested_schema_and_metrics(provider: Provider) -> None:
    if provider == "openai":
        key, model_id = settings.openai_api_key, settings.agno_contract_openai_model
        missing = "METIS_OPENAI_API_KEY"
    else:
        key, model_id = settings.gemini_key, settings.agno_contract_google_model
        missing = "GEMINI_KEY"
    if not key:
        pytest.skip(f"Configure {missing} no .env para conferir o provedor real.")

    run = agent(model(provider, key=key, model_id=model_id, timeout=30)).run(PROMPT)
    assert run.status == RunStatus.completed
    assert_usage(run)


@pytest.mark.parametrize("provider", ["openai", "google"])
def test_live_invalid_key_exposes_authentication_error(provider: Provider) -> None:
    client = model(provider, key="metis-spike-deliberately-invalid", timeout=10)
    with pytest.raises(ModelProviderError) as caught:
        client.invoke([Message(role="user", content="Teste sintético.")], Message(role="assistant"))

    assert caught.value.status_code in {400, 401, 403}
    assert "key" in str(caught.value).lower()
