"""Consultas da trilha de auditoria (RunEvent é append-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.attempts.models import Run, RunEvent


class RunEventManagement:
    """Herdado por `RunEvent`. Uso: `RunEvent.for_run(run_id)`."""

    objects: ClassVar[models.Manager[RunEvent]]

    @classmethod
    def for_run(cls, run_id: Any) -> list[RunEvent]:
        """Eventos do run em ordem cronológica."""
        return list(cls.objects.filter(run_id=run_id).order_by("created_at", "id"))

    @classmethod
    def is_persisted(cls, event_id: Any) -> bool:
        return cls.objects.filter(pk=event_id).exists()

    @classmethod
    def append(
        cls,
        run: Run,
        *,
        event_type: str,
        event_key: str,
        from_status: str = "",
        to_status: str = "",
        actor: str = "pipeline",
        stage: str = "",
        task_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Cria o evento; se a `event_key` já existe (retry, reentrega), devolve o existente."""
        event, _ = cls.objects.get_or_create(
            event_key=event_key,
            defaults={
                "run": run,
                "event_type": event_type,
                "from_status": from_status,
                "to_status": to_status,
                "actor": actor,
                "stage": stage,
                "task_id": task_id,
                "payload": payload or {},
            },
        )
        return event
