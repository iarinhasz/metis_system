"""Consultas e persistência de relatórios de integridade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models, transaction

if TYPE_CHECKING:
    from collections.abc import Sequence

    from projects.correction.integrity.models import IntegrityReport
    from projects.correction.integrity.rules import FindingRecord


class IntegrityReportManagement:
    objects: ClassVar[models.Manager[IntegrityReport]]

    @classmethod
    @transaction.atomic
    def create_with_findings(
        cls,
        *,
        run_id: Any,
        risk_level: str,
        rules_version: str,
        coverage: dict[str, object],
        narrative: str,
        findings: Sequence[FindingRecord],
    ) -> IntegrityReport:
        from projects.correction.integrity.models import IntegrityFinding

        report, _ = cls.objects.update_or_create(
            run_id=run_id,
            defaults={
                "risk_level": risk_level,
                "rules_version": rules_version,
                "coverage": coverage,
                "narrative": narrative,
            },
        )
        report.findings.all().delete()
        IntegrityFinding.objects.bulk_create(
            [
                IntegrityFinding(
                    report=report,
                    finding_type=finding.finding_type,
                    severity=finding.severity,
                    verdict=finding.verdict,
                    section_id=finding.section_id,
                    target_start=finding.target_start,
                    target_end=finding.target_end,
                    source_start=finding.source_start,
                    source_end=finding.source_end,
                    target_excerpt=finding.target_excerpt,
                    source_excerpt=finding.source_excerpt,
                    source_title=finding.source_title,
                    source_id=finding.source_id,
                    source_doi=finding.source_doi or "",
                    confidence=finding.confidence,
                    rationale=finding.rationale,
                )
                for finding in findings
            ]
        )
        return report
