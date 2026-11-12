"""Medição por chamada; a persistência é injetada pelo pipeline na etapa 1.4."""

from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Protocol

from projects.correction.agents.specs import Provider, Role


@dataclass(frozen=True)
class LLMUsage:
    run_id: str
    stage: str
    role: Role
    agent: str
    provider: Provider
    model_id: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    latency_ms: int
    success: bool
    error: str | None = None
    cost_usd: Decimal | None = None


class UsageSink(Protocol):
    def record(self, call: LLMUsage) -> None: ...


class NullUsageSink:
    def record(self, call: LLMUsage) -> None:
        """Usado onde a persistência de LLMCall ainda não foi implementada."""


class MemoryUsageSink:
    """Sink de teste que também aceita chamadas concorrentes."""

    def __init__(self) -> None:
        self.calls: list[LLMUsage] = []
        self._lock = Lock()

    def record(self, call: LLMUsage) -> None:
        with self._lock:
            self.calls.append(call)
