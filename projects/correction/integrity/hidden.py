"""Fase 0: o texto escondido que o E1 achou no PDF (`scan_hidden_text`) vira achado. Só código."""

from typing import Final

from projects.correction.extractor.article import ExtractedArticle
from projects.correction.integrity.findings import Finding, FindingKind
from projects.correction.integrity.rules import IntegrityRules

REASON_LABELS: Final[dict[str, str]] = {
    "color": "da cor do fundo",
    "size": "em fonte minúscula",
    "outside_page": "fora da página",
    "under_image": "atrás de uma imagem",
    "instruction": "com instrução a um revisor de IA",
}


def hidden_text_findings(article: ExtractedArticle, rules: IntegrityRules) -> list[Finding]:
    findings = []
    for passage in article.hidden_text_findings:
        kind = (
            FindingKind.HIDDEN_INSTRUCTION
            if "instruction" in passage.reasons
            else FindingKind.HIDDEN_TEXT
        )
        # Na ordem de REASON_LABELS: como está escondido e, por último, se é instrução.
        how = ", ".join(
            label for reason, label in REASON_LABELS.items() if reason in passage.reasons
        )
        findings.append(
            Finding(
                kind=kind,
                severity=rules.severity[kind],
                message=f"Texto escondido na página {passage.page}: {how}.",
                evidence={
                    "page": passage.page,
                    "text": passage.text,
                    "reasons": list(passage.reasons),
                },
            )
        )
    return findings
