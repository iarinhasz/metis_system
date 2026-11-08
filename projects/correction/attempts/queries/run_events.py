"""Consultas da trilha de auditoria (RunEvent, append-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models

if TYPE_CHECKING:
    from projects.correction.attempts.models import Run, RunEvent


class RunEventManagement(models.Manager["RunEvent"]):
    """Grava eventos de forma idempotente pela `event_key` única."""

    def is_persisted(self, event_id: Any) -> bool:
        return self.filter(pk=event_id).exists()

    def append(
        self,
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
        event, _ = self.get_or_create(
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
