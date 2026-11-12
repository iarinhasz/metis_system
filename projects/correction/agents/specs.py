"""Contratos dos modelos, independentes do Agno e dos apps de domínio."""

from enum import StrEnum
from math import isfinite
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator


class Provider(StrEnum):
    OPENAI = "openai"
    GOOGLE = "google"


class Family(StrEnum):
    GPT = "gpt"
    GEMINI = "gemini"


class Role(StrEnum):
    EVALUATOR_A = "evaluator_a"
    EVALUATOR_B = "evaluator_b"
    EVALUATOR_C = "evaluator_c"
    JUDGE_OPENAI = "judge_openai"
    JUDGE_GOOGLE = "judge_google"
    META_REVIEWER = "meta_reviewer"
    VISION = "vision"
    FAST = "fast"
    ADJUDICATOR = "adjudicator"


class ModelSpec(BaseModel):
    """Configuração serializável; credenciais e políticas de retry ficam fora do snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    provider: Provider
    model_id: str = Field(min_length=1)
    family: Family
    params: dict[str, JsonValue] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=600, gt=0, allow_inf_nan=False)

    @field_validator("params")
    @classmethod
    def validate_params(cls, params: dict[str, JsonValue]) -> dict[str, JsonValue]:
        allowed = {
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
            "max_completion_tokens",
            "max_output_tokens",
            "seed",
            "stop",
            "stop_sequences",
            "reasoning_effort",
            "thinking_budget",
            "include_thoughts",
            "frequency_penalty",
            "presence_penalty",
        }
        if unknown := params.keys() - allowed:
            raise ValueError(f"Parâmetros de geração desconhecidos: {sorted(unknown)}")
        return params

    @model_validator(mode="after")
    def validate_family(self) -> Self:
        expected = Family.GPT if self.provider is Provider.OPENAI else Family.GEMINI
        if self.family is not expected:
            raise ValueError(f"O provedor {self.provider} exige a família {expected}.")
        common = {"temperature", "top_p", "seed", "frequency_penalty", "presence_penalty"}
        supported = common | (
            {"max_tokens", "max_completion_tokens", "stop", "reasoning_effort"}
            if self.provider is Provider.OPENAI
            else {
                "top_k",
                "max_output_tokens",
                "stop_sequences",
                "thinking_budget",
                "include_thoughts",
            }
        )
        if unknown := self.params.keys() - supported:
            raise ValueError(f"Parâmetros incompatíveis com {self.provider}: {sorted(unknown)}")
        for name, value in self.params.items():
            if name in {"temperature", "top_p", "frequency_penalty", "presence_penalty"}:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                ):
                    raise ValueError(f"{name} precisa ser um número finito.")
                lower = -2 if name.endswith("penalty") else 0
                upper = 1 if name == "top_p" else 2
                if not lower <= value <= upper:
                    raise ValueError(f"{name} fora do intervalo {lower}–{upper}.")
            elif name in {
                "top_k",
                "max_tokens",
                "max_completion_tokens",
                "max_output_tokens",
                "seed",
                "thinking_budget",
            }:
                minimum = -1 if name == "thinking_budget" else 0 if name == "seed" else 1
                if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                    raise ValueError(f"{name} precisa ser inteiro maior ou igual a {minimum}.")
            elif name == "include_thoughts" and not isinstance(value, bool):
                raise ValueError("include_thoughts precisa ser booleano.")
            elif name == "reasoning_effort" and (
                not isinstance(value, str)
                or value
                not in {
                    "none",
                    "minimal",
                    "low",
                    "medium",
                    "high",
                    "xhigh",
                    "max",
                }
            ):
                raise ValueError("reasoning_effort desconhecido.")
            elif name in {"stop", "stop_sequences"}:
                sequences = [value] if isinstance(value, str) and name == "stop" else value
                if (
                    not isinstance(sequences, list)
                    or not sequences
                    or any(not isinstance(item, str) or not item.strip() for item in sequences)
                ):
                    raise ValueError(f"{name} precisa de sequências de texto não vazias.")
        return self


def validate_catalog(specs: dict[Role, ModelSpec]) -> dict[Role, ModelSpec]:
    """Um catálogo parcial ou um juiz da família errada impede a subida."""
    if missing := set(Role) - specs.keys():
        raise ValueError(f"Papéis sem ModelSpec: {', '.join(sorted(missing))}")
    for role, family in (
        (Role.EVALUATOR_A, Family.GPT),
        (Role.EVALUATOR_B, Family.GEMINI),
        (Role.JUDGE_OPENAI, Family.GPT),
        (Role.JUDGE_GOOGLE, Family.GEMINI),
    ):
        if specs[role].family is not family:
            raise ValueError(f"O papel {role} exige a família {family}.")
    return specs


def development_spec(role: Role) -> ModelSpec:
    """Padrões de desenvolvimento substituíveis no ambiente; não representam calibração."""
    if role in {Role.EVALUATOR_B, Role.JUDGE_GOOGLE, Role.ADJUDICATOR}:
        return ModelSpec(
            provider=Provider.GOOGLE, family=Family.GEMINI, model_id="gemini-3.8-flash"
        )
    if role in {Role.FAST, Role.VISION}:
        return ModelSpec(
            provider=Provider.GOOGLE, family=Family.GEMINI, model_id="gemini-3.5-flash-lite"
        )
    return ModelSpec(
        provider=Provider.OPENAI,
        family=Family.GPT,
        model_id="gpt-5.6-luna" if role is Role.EVALUATOR_C else "gpt-5.6-terra",
    )
