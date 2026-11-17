"""O E3 de um run: junta os achados de cada checagem, aplica as regras de risco e grava o
relatório. Sem Workflow do Agno, como o E1: os passos são código e não chamam modelo.

Por enquanto, só a Fase 0 (o texto escondido que o E1 achou). As checagens das referências
(5.1–5.3) entram aqui também. O plágio ficou fora do escopo.
"""

from dataclasses import dataclass
from typing import Any

from projects.correction.attempts.models import Run
from projects.correction.integrity.findings import Severity
from projects.correction.integrity.hidden import hidden_text_findings
from projects.correction.integrity.models import IntegrityReport
from projects.correction.integrity.rules import (
    INTEGRITY_RULES,
    RULES_VERSION,
    IntegrityRules,
    risk_of,
)
from projects.correction.pipeline.errors import SetupRequired


@dataclass(frozen=True)
class IntegrityOutcome:
    report_id: str
    risk: Severity
    findings: int
    high: int

    def payload(self) -> dict[str, Any]:
        """O que vai para o RunEvent do E3: ids e contagens, nunca texto do manuscrito."""
        return {
            "report_id": self.report_id,
            "risk": self.risk.value,
            "findings": self.findings,
            "high": self.high,
        }


def run_integrity(
    run_id: str, task_id: str, rules: IntegrityRules = INTEGRITY_RULES
) -> IntegrityOutcome:
    run = Run.get_by_id(run_id)
    if run.extraction is None:
        raise SetupRequired("O E3 precisa da extração do E1.")
    article = run.extraction.article
    findings = hidden_text_findings(article, rules)
    risk = risk_of(findings)
    report = IntegrityReport.store(
        run_id,
        task_id,
        risk=risk,
        rules_version=RULES_VERSION,
        coverage={"hidden_text": True},  # o E1 sempre roda a busca (scan_hidden_text)
        findings=findings,
    )
    return IntegrityOutcome(
        report_id=str(report.pk),
        risk=risk,
        findings=len(findings),
        high=sum(f.severity is Severity.HIGH for f in findings),
    )
