"""Gravação e consulta do uso dos modelos, sem guardar prompt nem resposta."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.agents.usage import LLMUsage
    from projects.correction.attempts.models import LLMCall


class LLMCallManagement:
    """Herdado por `LLMCall`; cada execução, inclusive um retry, cria uma linha própria."""

    objects: ClassVar[models.Manager[LLMCall]]

    @classmethod
    def record_usage(cls, call: LLMUsage) -> LLMCall:
        return cls.objects.create(
            run_id=call.run_id,
            stage=call.stage,
            role=call.role,
            agent=call.agent,
            provider=call.provider,
            model=call.model_id,
            prompt_version=call.prompt_version,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            cached_tokens=call.cached_tokens,
            cache_write_tokens=call.cache_write_tokens,
            reasoning_tokens=call.reasoning_tokens,
            cost_usd=call.cost_usd,
            latency_ms=call.latency_ms,
            success=call.success,
            error=call.error or "",
        )

    @classmethod
    def for_run(cls, run_id: Any) -> list[LLMCall]:
        return list(cls.objects.filter(run_id=run_id).order_by("created_at", "id"))
