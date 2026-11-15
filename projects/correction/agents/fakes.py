"""A mesma fábrica com respostas sintéticas e roteiros, sem clientes de provedor."""

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Any

from agno.metrics import RunMetrics
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from pydantic import BaseModel, ValidationError

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.limits import ProviderLimiter
from projects.correction.agents.models import ModelFactory
from projects.correction.agents.pricing import Pricing
from projects.correction.agents.prompts import RenderedPrompt
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.examples import schema_example
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import UsageSink

if TYPE_CHECKING:
    from projects.correction.metis.config import MetisSettings


@dataclass(frozen=True)
class InvalidFor:
    times: int


@dataclass(frozen=True)
class QuoteNotInDocument:
    path: tuple[str | int, ...] = ("quote",)
    quote: str = "Esta citação sintética não existe no documento."


@dataclass(frozen=True)
class MissingElsewhere:
    path: tuple[str | int, ...] = ("missing",)
    value: Any = True


@dataclass(frozen=True)
class FakeCall:
    name: str
    payload: AgentPayload


class FakeAgentFactory(AgentFactory):
    def __init__(
        self,
        run_id: str = "fake-run",
        stage: str = "test",
        usage_sink: UsageSink | None = None,
        limiter: ProviderLimiter | None = None,
        *,
        scripts: Mapping[str | Role, Sequence[object]] | None = None,
        config: MetisSettings | None = None,
        model_factory: ModelFactory | None = None,
        pricing: Pricing | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(
            run_id,
            stage,
            usage_sink,
            limiter,
            config=config,
            model_factory=model_factory,
            pricing=pricing,
            task_id=task_id,
        )
        self._scripts: dict[str, deque[object]] = {}
        for name, responses in (scripts or {}).items():
            expanded: deque[object] = deque()
            for response in responses:
                if isinstance(response, InvalidFor):
                    if response.times < 0:
                        raise ValueError("O número de respostas inválidas não pode ser negativo.")
                    expanded.extend("resposta fora do schema" for _ in range(response.times))
                else:
                    expanded.append(response)
            self._scripts[str(name)] = expanded
        self.calls: list[FakeCall] = []
        self._lock = Lock()

    def _invoke[T: BaseModel](
        self,
        name: str,
        role: Role,
        spec: ModelSpec,
        prompt: RenderedPrompt,
        output_schema: type[T],
        retries: int | None,
    ) -> Callable[[AgentPayload], RunOutput]:
        def invoke(payload: AgentPayload) -> RunOutput:
            with self._lock:
                self.calls.append(FakeCall(name, payload))
                script = self._scripts.get(name)
                if script is None:
                    script = self._scripts.get(str(role))
                response = script.popleft() if script else schema_example(output_schema)
            if isinstance(response, Exception):
                raise response
            if isinstance(response, (QuoteNotInDocument, MissingElsewhere)):
                data = schema_example(output_schema).model_dump(mode="json")
                target: Any = data
                for part in response.path[:-1]:
                    target = target[part]
                target[response.path[-1]] = (
                    response.quote if isinstance(response, QuoteNotInDocument) else response.value
                )
                response = output_schema.model_validate(data)
            elif isinstance(response, dict):
                try:
                    response = output_schema.model_validate(response)
                except ValidationError:
                    # Como o Agno: conteúdo fora do schema chega ao runner como saída inválida.
                    pass
            return RunOutput(
                run_id=self.task_id,
                content=response,
                status=RunStatus.completed,
                metrics=RunMetrics(input_tokens=20, output_tokens=5, cache_read_tokens=4),
            )

        return invoke
