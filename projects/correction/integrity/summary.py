"""O resumo da integridade que entra no relatório final (E5)."""

from typing import Any

from projects.correction.evaluation.report import IntegritySummary
from projects.correction.integrity.models import IntegrityReport


def integrity_summary(run_id: Any) -> IntegritySummary | None:
    """None quando o E3 não rodou (o rubric check pula a integridade)."""
    report = IntegrityReport.for_run(run_id)
    if report is None:
        return None
    return IntegritySummary(
        status="checked",
        risk_level=report.risk,
        findings=tuple(finding.message for finding in IntegrityReport.findings_for(run_id)),
        coverage={"integrity_stage_implemented": True, **report.coverage},
    )
