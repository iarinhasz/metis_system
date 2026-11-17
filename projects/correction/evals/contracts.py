"""Contrato compartilhado de medições offline; não depende do Django nem do banco."""

import hashlib
import json
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator

from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import LLMUsage

type Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
type Counter = Annotated[int, Field(ge=0, strict=True)]
type Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


def fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class DatasetIdentity(FrozenModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    sha256: Sha256
    case_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cases(self) -> DatasetIdentity:
        if any(not key.strip() for key in self.case_ids) or len(set(self.case_ids)) != len(
            self.case_ids
        ):
            raise ValueError("A amostra precisa de ids não vazios e distintos.")
        return self


class Metric(FrozenModel):
    value: Annotated[int, Field(strict=True)] | Annotated[float, Field(strict=True)] | None
    unit: str = Field(min_length=1)
    direction: Literal["higher", "lower", "informational"] = "informational"


class UsageSummary(FrozenModel):
    calls: Counter = 0
    input_tokens: Counter = 0
    output_tokens: Counter = 0
    cached_tokens: Counter | None = None
    cache_write_tokens: Counter | None = None
    reasoning_tokens: Counter | None = None
    cost_usd: Money | None = Decimal(0)
    # Legados podem não ter guardado a parcela conhecida de um custo incompleto.
    known_cost_usd: Money | None = Decimal(0)
    unpriced_calls: Counter = 0

    @model_validator(mode="after")
    def coherent_costs(self) -> UsageSummary:
        if self.unpriced_calls > self.calls:
            raise ValueError("Chamadas sem preço não podem exceder o total de chamadas.")
        if self.unpriced_calls:
            if self.cost_usd is not None:
                raise ValueError("Custo incompleto precisa ser nulo, não um total definitivo.")
        elif self.cost_usd is None or self.known_cost_usd != self.cost_usd:
            raise ValueError(
                "Sem chamadas sem preço, o custo total deve coincidir com o conhecido."
            )
        return self

    @classmethod
    def from_calls(cls, calls: Sequence[LLMUsage]) -> UsageSummary:
        known = sum((call.cost_usd or Decimal(0) for call in calls), Decimal(0))
        unpriced = sum(call.cost_usd is None for call in calls)
        return cls(
            calls=len(calls),
            input_tokens=sum(call.input_tokens for call in calls),
            output_tokens=sum(call.output_tokens for call in calls),
            cached_tokens=sum(call.cached_tokens for call in calls),
            cache_write_tokens=sum(call.cache_write_tokens for call in calls),
            reasoning_tokens=sum(call.reasoning_tokens for call in calls),
            cost_usd=None if unpriced else known,
            known_cost_usd=known,
            unpriced_calls=unpriced,
        )


class EvaluationReport(FrozenModel):
    format: Literal["metis.evals"] = "metis.evals"
    schema_version: Literal[1] = 1
    benchmark: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    benchmark_version: str = Field(min_length=1)
    created_at: AwareDatetime
    dataset: DatasetIdentity
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    model_specs: dict[Role, ModelSpec] = Field(default_factory=dict)
    prompt_versions: dict[str, tuple[Sha256, ...]] = Field(default_factory=dict)
    source_sha256: dict[str, Sha256] = Field(min_length=1)
    metrics: dict[str, Metric] = Field(min_length=1)
    failures: Counter = 0
    usage: UsageSummary = Field(default_factory=UsageSummary)
    details: dict[str, JsonValue] = Field(default_factory=dict)
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid_execution(self) -> EvaluationReport:
        if self.failures > len(self.dataset.case_ids):
            raise ValueError("Falhas não podem exceder os casos selecionados.")
        if self.usage.calls and (not self.model_specs or not self.prompt_versions):
            raise ValueError("Chamadas de LLM exigem ModelSpec e hashes dos prompts utilizados.")
        if any(
            not name.strip() or not versions or len(set(versions)) != len(versions)
            for name, versions in self.prompt_versions.items()
        ):
            raise ValueError("Cada prompt precisa de nome e versões distintas não vazias.")
        # Também recusa NaN/Infinity aninhados em parâmetros, detalhes ou ModelSpec.
        fingerprint(self.model_dump(mode="json"))
        return self

    @property
    def report_id(self) -> str:
        return fingerprint(self.model_dump(mode="json"))

    @property
    def variant_id(self) -> str:
        """Identifica o código, prompts e specs da variante, sem horário ou resultados."""
        return fingerprint(
            {
                "benchmark": self.benchmark,
                "benchmark_version": self.benchmark_version,
                "model_specs": {
                    role: spec.model_dump(mode="json") for role, spec in self.model_specs.items()
                },
                "prompt_versions": {
                    name: sorted(versions) for name, versions in self.prompt_versions.items()
                },
                "source_sha256": self.source_sha256,
            }
        )

    @property
    def comparison_key(self) -> str:
        """Só compara a mesma tarefa, amostra, política e definição de métricas."""
        return fingerprint(
            {
                "benchmark": self.benchmark,
                "benchmark_version": self.benchmark_version,
                "dataset": self.dataset.model_dump(mode="json"),
                "parameters": self.parameters,
                "metrics": {
                    name: {"unit": metric.unit, "direction": metric.direction}
                    for name, metric in self.metrics.items()
                },
            }
        )
