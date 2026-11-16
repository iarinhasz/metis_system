"""Detecção de retratações a partir das relações Crossref e OpenAlex."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from projects.correction.integrity.resolution import ReferenceResolution


class RetractionFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_id: str
    doi: str | None = None
    title: str | None = None
    evidence: tuple[str, ...]


def find_retracted_references(
    resolutions: Sequence[ReferenceResolution],
) -> tuple[RetractionFinding, ...]:
    findings: list[RetractionFinding] = []
    for result in resolutions:
        evidence = [
            f"Crossref {key}: {relation.get('doi', 'DOI não informado')}"
            for key, relations in (
                ("update-to", result.crossref_update_to),
                ("updated-by", result.crossref_updated_by),
            )
            for relation in relations
            if str(relation.get("type", "")).casefold().replace("_", "-")
            in {"retraction", "retracted"}
        ]
        if result.is_retracted is True:
            evidence.append("OpenAlex ou relação Crossref marca a obra como retratada.")
        if evidence:
            findings.append(
                RetractionFinding(
                    reference_id=result.reference_id,
                    doi=result.doi,
                    title=result.title,
                    evidence=tuple(evidence),
                )
            )
    return tuple(findings)
