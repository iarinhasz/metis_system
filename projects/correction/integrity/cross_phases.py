"""Cruzamento determinístico entre achados de similaridade e citações."""

from __future__ import annotations

from collections.abc import Sequence

from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.alignment import CitationAlignmentResult
from projects.correction.integrity.consistency import CitationConsistency
from projects.correction.integrity.existence import ReferenceExistence
from projects.correction.integrity.resolution import ReferenceResolution
from projects.correction.integrity.retraction import RetractionFinding
from projects.correction.integrity.rules import FindingRecord

_UNATTRIBUTED_VERDICTS = {"verbatim_copy", "paraphrase_without_attribution"}


def cross_phase_findings(
    phase1_findings: Sequence[FindingRecord],
    document: ExtractedDocument,
    resolutions: Sequence[ReferenceResolution],
    existence: Sequence[ReferenceExistence],
    retractions: Sequence[RetractionFinding],
    consistency: CitationConsistency,
    alignments: Sequence[CitationAlignmentResult],
) -> tuple[FindingRecord, ...]:
    records: list[FindingRecord] = list(phase1_findings)
    cited_ids = {
        mention.reference_id
        for mention in document.citation_mentions
        if mention.reference_id is not None
    }
    references_by_doi = {
        _normalize_doi(result.doi): result
        for result in resolutions
        if result.doi and result.reference_id in cited_ids
    }
    retracted_by_doi = {
        _normalize_doi(item.doi): item for item in retractions if item.doi is not None
    }
    for finding in phase1_findings:
        if finding.verdict not in _UNATTRIBUTED_VERDICTS:
            continue
        doi = _finding_doi(finding)
        cited_doi = doi is not None and doi in references_by_doi
        if not cited_doi:
            records.append(
                FindingRecord(
                    finding_type="missing_citation",
                    severity="high" if finding.verdict == "verbatim_copy" else "medium",
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
                    source_doi=finding.source_doi,
                    confidence=finding.confidence,
                    rationale="Fonte similar não vinculada às referências do manuscrito.",
                )
            )
        if doi and doi in retracted_by_doi:
            retraction = retracted_by_doi[doi]
            records.append(
                FindingRecord(
                    finding_type="retracted_source",
                    severity="medium",
                    verdict="retracted_source",
                    section_id=finding.section_id,
                    target_start=finding.target_start,
                    target_end=finding.target_end,
                    target_excerpt=finding.target_excerpt,
                    source_excerpt=finding.source_excerpt,
                    source_title=retraction.title or finding.source_title,
                    source_id=finding.source_id,
                    source_doi=doi,
                    rationale="A fonte similar está marcada como retratada.",
                )
            )
    existence_by_id = {item.reference_id: item for item in existence}
    for reference_id, result in existence_by_id.items():
        if result.status == "ok":
            continue
        records.append(
            FindingRecord(
                finding_type=(
                    "nonexistent_reference" if result.status == "not_found" else "metadata_mismatch"
                ),
                severity="medium",
                verdict=result.status,
                source_id=reference_id,
                source_title=result.resolution.title or "",
                source_doi=result.resolution.doi,
                rationale=result.rationale or "Referência não validada.",
            )
        )
    for item in retractions:
        if item.reference_id not in cited_ids:
            continue
        records.append(
            FindingRecord(
                finding_type="retracted_reference",
                severity="medium",
                verdict="retracted_source",
                source_id=item.reference_id,
                source_title=item.title or "",
                source_doi=item.doi,
                rationale="A referência citada está marcada como retratada.",
            )
        )
    for reference_id in consistency.uncited_reference_ids:
        records.append(
            FindingRecord(
                finding_type="uncited_reference",
                severity="low",
                source_id=reference_id,
                rationale="Entrada bibliográfica sem menção correspondente no texto.",
            )
        )
    if consistency.citation_without_reference_count:
        records.append(
            FindingRecord(
                finding_type="citation_without_reference",
                severity="medium",
                rationale=(
                    f"{consistency.citation_without_reference_count} menção(ões) sem vínculo "
                    "com uma referência."
                ),
            )
        )
    for alignment in alignments:
        if alignment.label != "CONTRADICTS":
            continue
        records.append(
            FindingRecord(
                finding_type="citation_alignment_contradicts",
                severity="medium",
                verdict=alignment.label,
                section_id=alignment.section_id,
                target_excerpt=alignment.claim,
                source_id=alignment.reference_id,
                source_title=alignment.source_title,
                confidence=alignment.confidence,
                rationale=alignment.rationale,
            )
        )
    return tuple(records)


def _finding_doi(finding: FindingRecord) -> str | None:
    if finding.source_doi:
        return _normalize_doi(finding.source_doi)
    if finding.source_id.casefold().startswith("doi:"):
        return _normalize_doi(finding.source_id[4:])
    return None


def _normalize_doi(doi: str) -> str:
    return doi.strip().casefold().removeprefix("https://doi.org/").removeprefix("doi:")
