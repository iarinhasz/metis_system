"""Regras de risco do E3: a gravidade de cada tipo de achado e o risco do artigo, o maior
entre os achados. Risco alto leva o run ao gate humano (`waiting_human_review`).

Mudar uma regra pede `RULES_VERSION` nova, que fica gravada em cada relatório.
"""

from collections.abc import Iterable
from typing import Final

from pydantic import BaseModel, ConfigDict

from projects.correction.integrity.findings import SEVERITY_ORDER, Finding, FindingKind, Severity

RULES_VERSION: Final = "v1"


class IntegrityRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Instrução escondida a um revisor de IA é tentativa de manipular a avaliação; texto
    # escondido sem instrução pode ser legítimo (texto branco numa caixa escura de figura).
    severity: dict[FindingKind, Severity] = {
        FindingKind.HIDDEN_INSTRUCTION: Severity.HIGH,
        FindingKind.HIDDEN_TEXT: Severity.LOW,
    }


INTEGRITY_RULES: Final = IntegrityRules()


def risk_of(findings: Iterable[Finding]) -> Severity:
    return max((f.severity for f in findings), key=SEVERITY_ORDER.__getitem__, default=Severity.LOW)
