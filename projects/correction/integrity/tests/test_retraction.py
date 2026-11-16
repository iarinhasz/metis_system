from __future__ import annotations

from projects.correction.integrity.resolution import ReferenceResolution
from projects.correction.integrity.retraction import find_retracted_references


def test_flags_retraction_but_not_correction() -> None:
    resolutions = (
        ReferenceResolution(
            reference_id="retracted",
            status="ok",
            doi="10.1234/retracted",
            title="Retracted",
            crossref_update_to=({"type": "retraction", "doi": "10.5678/notice"},),
        ),
        ReferenceResolution(
            reference_id="corrected",
            status="ok",
            doi="10.1234/corrected",
            title="Corrected",
            crossref_update_to=({"type": "correction", "doi": "10.5678/correction"},),
            is_retracted=False,
        ),
    )

    findings = find_retracted_references(resolutions)

    assert [item.reference_id for item in findings] == ["retracted"]
    assert "Crossref update-to" in findings[0].evidence[0]
