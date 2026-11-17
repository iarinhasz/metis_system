"""Gravação e leitura do relatório de integridade, protegidas pela posse do E3."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import transaction

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.integrity.findings import Finding, Severity
    from projects.correction.integrity.models import IntegrityFinding, IntegrityReport


class IntegrityReportManagement:
    """Herdado por `IntegrityReport`. Uso: `IntegrityReport.for_run(run_id)`."""

    objects: ClassVar[models.Manager[IntegrityReport]]

    @classmethod
    def for_run(cls, run_id: Any) -> IntegrityReport | None:
        return cls.objects.filter(run_id=run_id).first()

    @classmethod
    def findings_for(cls, run_id: Any) -> tuple[Finding, ...]:
        report = cls.objects.filter(run_id=run_id).prefetch_related("findings").first()
        return () if report is None else tuple(row.finding for row in report.findings.all())

    @classmethod
    @transaction.atomic
    def store(
        cls,
        run_id: Any,
        task_id: str,
        *,
        risk: Severity,
        rules_version: str,
        coverage: dict[str, bool],
        findings: Sequence[Finding],
    ) -> IntegrityReport:
        """Grava o relatório do run; um retry do E3 substitui o anterior."""
        run = Run.lock_for_stage(run_id, task_id, RunStatus.CHECKING_INTEGRITY)
        report, _ = cls.objects.update_or_create(
            run=run, defaults={"risk": risk, "rules_version": rules_version, "coverage": coverage}
        )
        rows = report.findings
        rows.all().delete()
        rows.model.objects.bulk_create(
            rows.model(
                report=report,
                position=position,
                kind=finding.kind,
                severity=finding.severity,
                message=finding.message,
                evidence=finding.evidence,
            )
            for position, finding in enumerate(findings, start=1)
        )
        return report


class IntegrityFindingManagement:
    """Herdado por `IntegrityFinding`; os achados se leem pelo relatório."""

    objects: ClassVar[models.Manager[IntegrityFinding]]
