"""Único construtor de clientes Agno; chaves, timeout e retries são explícitos."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from agno.models.base import Model
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat

from projects.correction.agents.errors import MissingProviderKey
from projects.correction.agents.specs import Family, ModelSpec, Provider, Role, validate_catalog


class ModelFactory:
    def __init__(
        self,
        specs: Mapping[Role, ModelSpec],
        *,
        openai_api_key: str,
        google_api_key: str,
        client_params: Mapping[Provider, dict[str, Any]] | None = None,
        retries: int = 1,
        retry_delay_seconds: float = 1,
    ) -> None:
        if retries < 0 or retry_delay_seconds < 0:
            raise ValueError("Retries e intervalo não podem ser negativos.")
        self.specs = validate_catalog(dict(specs))
        self._keys = {Provider.OPENAI: openai_api_key, Provider.GOOGLE: google_api_key}
        self._client_params = deepcopy(dict(client_params or {}))
        self._retries, self._retry_delay = retries, retry_delay_seconds

    def judge_role(self, spec: ModelSpec) -> Role:
        return Role.JUDGE_GOOGLE if spec.family is Family.GPT else Role.JUDGE_OPENAI

    def judge_for(self, spec: ModelSpec) -> ModelSpec:
        return self.specs[self.judge_role(spec)]

    def build(self, spec: ModelSpec, *, retries: int | None = None) -> Model:
        spec = ModelSpec.model_validate(spec.model_dump())
        if retries is not None and retries < 0:
            raise ValueError("Retries não podem ser negativos.")
        key = self._keys[spec.provider]
        if not key.strip():
            raise MissingProviderKey(f"Falta a chave do provedor {spec.provider}.")
        params = deepcopy(self._client_params.get(spec.provider, {}))
        params.pop("api_key", None)
        common: dict[str, Any] = {
            "id": spec.model_id,
            "api_key": key,
            "timeout": spec.timeout_seconds,
            "retries": self._retries if retries is None else retries,
            "delay_between_retries": self._retry_delay,
            "exponential_backoff": True,
            "retry_with_guidance": False,
            **spec.params,
        }
        if spec.provider is Provider.OPENAI:
            params.update(timeout=spec.timeout_seconds, max_retries=0)
            return OpenAIChat(**common, max_retries=0, client_params=params)
        http_options = dict(params.get("http_options") or {})
        http_options.update(
            timeout=max(1, int(spec.timeout_seconds * 1000)), retry_options={"attempts": 1}
        )
        params["http_options"] = http_options
        return Gemini(**common, client_params=params)
