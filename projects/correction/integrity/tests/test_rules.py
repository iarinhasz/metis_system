from __future__ import annotations

from projects.correction.integrity.rules import (
    FindingRecord,
    RiskLevel,
    RiskPolicy,
    decide_risk,
)


def _policy() -> RiskPolicy:
    return RiskPolicy(
        high_verbatim_sentences=3,
        high_paraphrase_fraction=0.2,
        high_nonexistent_references=3,
    )


def test_hidden_ai_instruction_is_high_risk() -> None:
    decision = decide_risk(
        [FindingRecord("hidden_ai_instruction", "high")],
        article_text="Article text",
        policy=_policy(),
    )

    assert decision.level is RiskLevel.HIGH
    assert decision.reasons == ("hidden_ai_instruction",)


def test_three_unattributed_literal_sentences_are_high_risk() -> None:
    decision = decide_risk(
        [
            FindingRecord(
                "similarity_lexical",
                "high",
                verdict="verbatim_copy",
                target_excerpt="First sentence. Second sentence! Third sentence?",
            )
        ],
        article_text="Article text",
        policy=_policy(),
    )

    assert decision.level is RiskLevel.HIGH
    assert "long_unattributed_verbatim_copy" in decision.reasons


def test_paraphrase_fraction_and_missing_reference_thresholds_are_configurable() -> None:
    paraphrase = FindingRecord(
        "similarity_semantic",
        "medium",
        verdict="paraphrase_without_attribution",
        section_id="s1",
        target_start=0,
        target_end=21,
    )
    high = decide_risk(
        [paraphrase],
        article_text={"s1": "a" * 100},
        policy=_policy(),
    )
    missing = decide_risk(
        [],
        article_text="Article",
        nonexistent_references=3,
        policy=_policy(),
    )

    assert high.level is RiskLevel.HIGH
    assert "widespread_unattributed_paraphrase" in high.reasons
    assert missing.level is RiskLevel.HIGH
    assert "multiple_nonexistent_references" in missing.reasons


def test_point_paraphrase_is_medium_and_no_findings_is_low() -> None:
    medium = decide_risk(
        [FindingRecord("similarity_semantic", "medium", verdict="paraphrase_without_attribution")],
        article_text="Article",
        policy=_policy(),
    )
    low = decide_risk([], article_text="Article", policy=_policy())

    assert medium.level is RiskLevel.MEDIUM
    assert low.level is RiskLevel.LOW
