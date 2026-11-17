from __future__ import annotations

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)
from projects.correction.integrity.consistency import CitationConsistency
from projects.correction.integrity.cross_phases import cross_phase_findings
from projects.correction.integrity.existence import ReferenceExistence
from projects.correction.integrity.resolution import ReferenceResolution
from projects.correction.integrity.retraction import RetractionFinding
from projects.correction.integrity.rules import FindingRecord


def _document(*, cited: bool) -> ExtractedDocument:
    return ExtractedDocument(
        title="Paper",
        language="en",
        abstract="Abstract.",
        sections=(DocumentSection(id="s1", title="Body", level=1, text="Copied words."),),
        references=(DocumentReference(id="r1", raw="Source"),),
        citation_mentions=(
            (CitationMention(reference_id="r1", sentence="Claim", section_id="s1"),)
            if cited
            else ()
        ),
    )


def _finding() -> FindingRecord:
    return FindingRecord(
        finding_type="similarity_lexical",
        severity="high",
        verdict="verbatim_copy",
        section_id="s1",
        target_start=0,
        target_end=13,
        target_excerpt="Copied words.",
        source_excerpt="Copied words.",
        source_id="doi:10.1234/source",
        source_doi="10.1234/source",
    )


def test_unreferenced_similar_source_becomes_missing_citation() -> None:
    findings = cross_phase_findings(
        (_finding(),),
        _document(cited=False),
        (ReferenceResolution(reference_id="r1", status="ok", doi="10.9999/other"),),
        (),
        (),
        CitationConsistency(
            uncited_reference_ids=("r1",),
            citation_without_reference_count=0,
            cited_reference_count=0,
            self_citation_count=0,
            self_citation_rate=0,
        ),
        (),
    )

    assert any(item.finding_type == "missing_citation" for item in findings)


def test_cited_source_is_not_marked_missing_and_retraction_is_retained() -> None:
    resolution = ReferenceResolution(
        reference_id="r1",
        status="ok",
        doi="10.1234/source",
        title="Source",
    )
    retraction = RetractionFinding(
        reference_id="r1",
        doi="10.1234/source",
        title="Source",
        evidence=("OpenAlex marks retracted",),
    )
    findings = cross_phase_findings(
        (_finding(),),
        _document(cited=True),
        (resolution,),
        (
            ReferenceExistence(
                reference_id="r1",
                status="ok",
                resolution=resolution,
            ),
        ),
        (retraction,),
        CitationConsistency(
            uncited_reference_ids=(),
            citation_without_reference_count=0,
            cited_reference_count=1,
            self_citation_count=0,
            self_citation_rate=0,
        ),
        (),
    )

    assert not any(item.finding_type == "missing_citation" for item in findings)
    assert any(item.finding_type == "retracted_source" for item in findings)
    assert any(item.finding_type == "retracted_reference" for item in findings)
