from __future__ import annotations

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)
from projects.correction.integrity.consistency import check_citation_consistency
from projects.correction.integrity.resolution import ReferenceResolution


def test_reports_uncited_reference_unmatched_citation_and_self_citation_rate() -> None:
    document = ExtractedDocument(
        title="Paper",
        authors=("Ada Lovelace",),
        language="en",
        abstract="An abstract.",
        sections=(DocumentSection(id="s1", title="Body", level=1, text="Claims [1]."),),
        references=(
            DocumentReference(id="r1", raw="Ada Lovelace, 2020", authors=("Lovelace, Ada",)),
            DocumentReference(id="r2", raw="Other author, 2021"),
        ),
        citation_mentions=(
            CitationMention(reference_id="r1", sentence="Claims [1].", section_id="s1"),
            CitationMention(reference_id=None, sentence="Orphan [9].", section_id="s1"),
        ),
    )
    resolutions = (
        ReferenceResolution(reference_id="r1", status="ok", authors=("Ada Lovelace",)),
        ReferenceResolution(reference_id="r2", status="ok", authors=("Other Author",)),
    )

    result = check_citation_consistency(document, resolutions)

    assert result.uncited_reference_ids == ("r2",)
    assert result.citation_without_reference_count == 1
    assert result.cited_reference_count == 1
    assert result.self_citation_count == 1
    assert result.self_citation_rate == 1
