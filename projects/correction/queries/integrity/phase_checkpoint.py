"""Consultas e persistência idempotente dos ramos paralelos de integridade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models

if TYPE_CHECKING:
    from projects.correction.integrity.models import IntegrityPhaseCheckpoint


class IntegrityPhaseCheckpointManagement:
    objects: ClassVar[models.Manager[IntegrityPhaseCheckpoint]]

    @classmethod
    def get_checkpoint(cls, run_id: Any, phase: str) -> dict[str, Any] | None:
        row = cls.objects.filter(run_id=run_id, phase=phase).first()
        return dict(row.payload) if row is not None else None

    @classmethod
    def save_checkpoint(
        cls, run_id: Any, phase: str, payload: dict[str, Any]
    ) -> IntegrityPhaseCheckpoint:
        row, _ = cls.objects.update_or_create(
            run_id=run_id,
            phase=phase,
            defaults={"payload": payload},
        )
        return row
