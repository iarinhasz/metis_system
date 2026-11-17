"""Persistência de uso injetada nos agentes de cada estágio."""

from projects.correction.agents.usage import LLMUsage
from projects.correction.attempts.models import LLMCall


class DatabaseUsageSink:
    """O runner já fornece run e estágio; o sink só grava a medição em `queries/`."""

    def record(self, call: LLMUsage) -> None:
        LLMCall.record_usage(call)
