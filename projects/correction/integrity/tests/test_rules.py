"""Regras de risco: a gravidade de cada achado e o risco do artigo."""

from projects.correction.integrity.findings import Finding, FindingKind, Severity
from projects.correction.integrity.rules import INTEGRITY_RULES, IntegrityRules, risk_of


def finding(kind: FindingKind, severity: Severity) -> Finding:
    return Finding(kind=kind, severity=severity, message="m")


def test_no_findings_is_low_risk() -> None:
    assert risk_of([]) is Severity.LOW


def test_the_risk_is_the_highest_severity() -> None:
    findings = [
        finding(FindingKind.HIDDEN_TEXT, Severity.LOW),
        finding(FindingKind.HIDDEN_INSTRUCTION, Severity.HIGH),
    ]

    assert risk_of(findings) is Severity.HIGH


def test_a_hidden_instruction_is_high_and_hidden_text_alone_is_low() -> None:
    assert INTEGRITY_RULES.severity[FindingKind.HIDDEN_INSTRUCTION] is Severity.HIGH
    assert INTEGRITY_RULES.severity[FindingKind.HIDDEN_TEXT] is Severity.LOW


def test_severities_come_from_the_rules() -> None:
    strict = IntegrityRules(
        severity={
            FindingKind.HIDDEN_INSTRUCTION: Severity.HIGH,
            FindingKind.HIDDEN_TEXT: Severity.MEDIUM,
        }
    )

    assert strict.severity[FindingKind.HIDDEN_TEXT] is Severity.MEDIUM
