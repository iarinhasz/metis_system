"""Reconciliador: retoma os runs que o fluxo normal deixou parados.

Roda no beat (`pipeline.reconcile_runs`) e cobre duas situações:

- checkpoint sem task: o commit aconteceu, mas a publicação se perdeu → republica;
- estágio travado: o worker morreu e a mensagem não voltou → volta ao checkpoint e publica.

Cada situação tem um limite. Passou dele, o run vai para `error_unexpected` e espera alguém
reprocessar. O claim e a posse pelo id da task impedem processamento em dobro, mesmo que a
mensagem antiga ainda esteja na fila.
"""

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from projects.correction.attempts.models import Run
from projects.correction.metis.config import settings
from projects.correction.pipeline.publishing import publish_checkpoint_stage

logger = logging.getLogger(__name__)

Handler = Callable[[Any, datetime, "ReconcileReport"], None]


@dataclass
class ReconcileReport:
    """O que uma passada fez, run a run."""

    republished: list[str] = field(default_factory=list)
    released: list[str] = field(default_factory=list)
    abandoned: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return asdict(self)


def reconcile_runs(now: datetime | None = None) -> ReconcileReport:
    """Uma passada do reconciliador. `now` deixa os testes simularem o tempo passando."""
    now = now or timezone.now()
    report = ReconcileReport()

    stalled_before = now - timedelta(seconds=settings.republish_after_seconds)
    for run_id in Run.ids_stalled_at_checkpoint(before=stalled_before):
        _guarded(_republish_stalled_checkpoint, run_id, stalled_before, report)

    stale_before = now - timedelta(seconds=settings.stale_stage_after_seconds)
    for run_id in Run.ids_with_stale_stage(before=stale_before):
        _guarded(_release_stale_stage, run_id, stale_before, report)

    if report.republished or report.released or report.abandoned:
        logger.info("Reconciliador: %s", report.as_dict())
    return report


def _guarded(handler: Handler, run_id: Any, before: datetime, report: ReconcileReport) -> None:
    """Um run com problema não impede os outros; a próxima passada tenta de novo."""
    try:
        handler(run_id, before, report)
    except Exception:
        logger.exception("Reconciliador falhou no run %s", run_id)


@transaction.atomic
def _republish_stalled_checkpoint(run_id: Any, before: datetime, report: ReconcileReport) -> None:
    run = Run.lock_if_stalled_at_checkpoint(run_id, before=before)
    if run is None:
        return
    if run.publish_count >= settings.max_republish:
        _abandon(
            run,
            f"Checkpoint {run.status} sem task depois de {run.publish_count} republicações.",
            report,
        )
        return
    stalled_since = run.updated_at.isoformat()
    run = Run.mark_republished(run.pk, payload={"stalled_since": stalled_since})
    publish_checkpoint_stage(run)
    report.republished.append(str(run.pk))


@transaction.atomic
def _release_stale_stage(run_id: Any, before: datetime, report: ReconcileReport) -> None:
    run = Run.lock_if_stage_is_stale(run_id, before=before)
    if run is None:
        return
    if run.stage_claims >= settings.max_stage_claims:
        _abandon(run, f"Estágio {run.stage} travado depois de {run.stage_claims} claims.", report)
        return
    run = Run.release_stale(run.pk)
    publish_checkpoint_stage(run)
    report.released.append(str(run.pk))


def _abandon(run: Run, error: str, report: ReconcileReport) -> None:
    Run.abandon(run.pk, error=error)
    logger.warning("Run %s abandonado pelo reconciliador: %s", run.pk, error)
    report.abandoned.append(str(run.pk))
