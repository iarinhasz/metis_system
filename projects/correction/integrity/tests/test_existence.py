from __future__ import annotations

from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.existence import (
    ReferenceAdjudication,
    check_reference_existence,
)
from projects.correction.integrity.resolution import ReferenceResolution


def test_accepted_resolution_skips_reference_adjudicator() -> None:
    reference = DocumentReference(id="r1", raw="A real paper", title="A real paper")
    resolution = ReferenceResolution(reference_id="r1", status="ok", title="A real paper")

    def should_not_run(*args: object) -> ReferenceAdjudication:
        raise AssertionError("A referência já foi aceita automaticamente.")

    result = check_reference_existence(
        (reference,),
        (resolution,),
        adjudicator=should_not_run,
    )

    assert result[0].status == "ok"
    assert not result[0].adjudicated


def test_only_doubtful_reference_is_adjudicated() -> None:
    references = (
        DocumentReference(id="r1", raw="A real paper", title="A real paper"),
        DocumentReference(id="r2", raw="An uncertain paper", title="An uncertain paper"),
    )
    resolutions = (
        ReferenceResolution(reference_id="r1", status="ok", title="A real paper"),
        ReferenceResolution(reference_id="r2", status="metadata_mismatch", title="Other paper"),
    )
    judged: list[str] = []

    def adjudicate(
        reference: DocumentReference, resolution: ReferenceResolution
    ) -> ReferenceAdjudication:
        judged.append(reference.id)
        assert resolution.status == "metadata_mismatch"
        return ReferenceAdjudication(
            status="not_found",
            confidence=0.97,
            rationale="Nenhuma obra corresponde aos metadados.",
        )

    results = check_reference_existence(references, resolutions, adjudicator=adjudicate)

    assert judged == ["r2"]
    assert [item.status for item in results] == ["ok", "not_found"]
    assert results[1].adjudicated
