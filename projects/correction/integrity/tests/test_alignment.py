from __future__ import annotations

from types import SimpleNamespace

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)
from projects.correction.integrity.alignment import (
    AlignmentJudgment,
    check_citation_alignment,
)
from projects.correction.integrity.resolution import ReferenceResolution


class _Runner:
    def __init__(self, labels: list[str]) -> None:
        self.labels = iter(labels)
        self.calls: list[str] = []

    def run(self, payload: str) -> SimpleNamespace:
        self.calls.append(payload)
        return SimpleNamespace(
            valid=True,
            content=AlignmentJudgment(
                label=next(self.labels),
                confidence=0.9,
                rationale="O conteúdo da fonte suporta a afirmação.",
            ),
        )


class _Factory:
    def __init__(self, runner: _Runner) -> None:
        self.runner = runner

    def citation_alignment_judge(self, *, output_schema: type[AlignmentJudgment]) -> _Runner:
        assert output_schema is AlignmentJudgment
        return self.runner


def _document(*, count: int) -> ExtractedDocument:
    return ExtractedDocument(
        title="Paper",
        language="en",
        abstract="Abstract.",
        sections=(DocumentSection(id="s1", title="Body", level=1, text="Claim."),),
        references=(DocumentReference(id="r1", raw="Source"),),
        citation_mentions=tuple(
            CitationMention(
                reference_id="r1",
                sentence=f"Claim {index}.",
                section_id="s1",
            )
            for index in range(count)
        ),
    )


def test_only_configured_k_claims_are_sent_to_the_judge() -> None:
    runner = _Runner(["SUPPORTS", "PARTIAL"])
    result = check_citation_alignment(
        _document(count=4),
        (ReferenceResolution(reference_id="r1", status="ok", abstract="Source abstract"),),
        factory=_Factory(runner),  # type: ignore[arg-type]
        max_samples=2,
    )

    assert len(result) == len(runner.calls) == 2
    assert [item.label for item in result] == ["SUPPORTS", "PARTIAL"]


def test_insufficient_result_fetches_full_text_once_per_reference() -> None:
    runner = _Runner(["INSUFFICIENT", "SUPPORTS", "INSUFFICIENT", "SUPPORTS"])
    fetches: list[str] = []

    def fetch(resolution: ReferenceResolution) -> str:
        fetches.append(resolution.reference_id)
        return "Full text supporting the claims."

    result = check_citation_alignment(
        _document(count=2),
        (ReferenceResolution(reference_id="r1", status="ok", abstract="Short abstract"),),
        factory=_Factory(runner),  # type: ignore[arg-type]
        max_samples=2,
        full_text_fetcher=fetch,
    )

    assert fetches == ["r1"]
    assert len(runner.calls) == 4
    assert all(item.full_text_used and item.label == "SUPPORTS" for item in result)
