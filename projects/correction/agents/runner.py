"""Execução tipada e uma medição por chamada, inclusive quando o provedor falha."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from agno.exceptions import ModelProviderError
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from pydantic import BaseModel

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.limits import ProviderLimiter
from projects.correction.agents.pricing import Pricing
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import LLMUsage, UsageSink


@dataclass(frozen=True)
class AgentPayload:
    prompt: str
    article: str | None = None
    document: bytes | None = None
    mime_type: str = "application/pdf"

    def text(self) -> str:
        if self.article is None:
            return self.prompt
        return f"<artigo>\n{self.article}\n</artigo>\n\n{self.prompt}"


@dataclass(frozen=True)
class AgentResult[T: BaseModel]:
    valid: bool
    content: T | None
    raw: object
    usage: LLMUsage


class AgentRunner[T: BaseModel](Protocol):
    def run(self, payload: str | AgentPayload) -> AgentResult[T]: ...


class MeasuredRunner[T: BaseModel]:
    def __init__(
        self,
        invoke: Callable[[AgentPayload], RunOutput],
        output_schema: type[T],
        *,
        run_id: str,
        stage: str,
        role: Role,
        agent: str,
        spec: ModelSpec,
        prompt_version: str,
        usage_sink: UsageSink,
        limiter: ProviderLimiter,
        pricing: Pricing,
    ) -> None:
        self._invoke, self._schema = invoke, output_schema
        self._run_id, self._stage, self._role, self._agent = run_id, stage, role, agent
        self._spec, self._prompt_version = spec, prompt_version
        self._sink, self._limiter, self._pricing = usage_sink, limiter, pricing

    def run(self, payload: str | AgentPayload) -> AgentResult[T]:
        request = AgentPayload(payload) if isinstance(payload, str) else payload
        started = perf_counter()
        run: RunOutput | None = None
        content: T | None = None
        raw: object = None
        error: str | None = None
        try:
            with self._limiter.acquire(self._spec.provider):
                started = perf_counter()
                run = self._invoke(request)
            if run.status is not RunStatus.completed:
                error = "ProviderError"
                raise LLMUnavailable(f"O modelo {self._spec.model_id} está indisponível.")
            raw = run.content
            if isinstance(raw, self._schema):
                content = raw
            else:
                error = "InvalidOutput"
        except ModelProviderError as exc:
            error = f"ModelProviderError:{exc.status_code}"
            raise LLMUnavailable(f"O modelo {self._spec.model_id} está indisponível.") from exc
        except Exception as exc:
            error = error or type(exc).__name__
            raise
        finally:
            metrics = run.metrics if run is not None else None
            input_tokens = (metrics.input_tokens or 0) if metrics else 0
            output_tokens = (metrics.output_tokens or 0) if metrics else 0
            cached_tokens = (metrics.cache_read_tokens or 0) if metrics else 0
            duration = metrics.duration if metrics else None
            elapsed = duration if duration is not None else perf_counter() - started
            usage = LLMUsage(
                run_id=self._run_id,
                stage=self._stage,
                role=self._role,
                agent=self._agent,
                provider=self._spec.provider,
                model_id=self._spec.model_id,
                prompt_version=self._prompt_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                latency_ms=max(0, int(elapsed * 1000)),
                success=content is not None,
                error=error,
                cost_usd=self._pricing.cost(
                    self._spec.provider,
                    self._spec.model_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                ),
            )
            self._sink.record(usage)
        return AgentResult(valid=content is not None, content=content, raw=raw, usage=usage)
