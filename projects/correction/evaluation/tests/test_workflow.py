"""Orquestração do E4 com agentes falsos e checkpoints duráveis."""

from dataclasses import dataclass
from time import monotonic
from typing import Any, cast

import pytest

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    Verdict,
)
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import Stage
from projects.correction.evaluation.context import EvaluationContextBuilder
from projects.correction.evaluation.models import ReviewRound
from projects.correction.evaluation.tests.test_context import _advance_to_evaluation, _prepare_run
from projects.correction.evaluation.workflow import (
    _failed_step_names,
    build_evaluation_workflow,
    run_evaluation,
)
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import InvalidEvaluationOutput


def _whole_document_output(run: Run) -> dict[str, list[dict[str, object]]]:
    context = EvaluationContextBuilder(run).build()
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    return {
        "criteria": [
            {
                "criterion_key": criterion.value,
                "grade": 3,
                "justification": f"A evidência sustenta {criterion.value}.",
                "evidence": [{"quote": "O método usa dados públicos.", "section_id": "sec_method"}],
                "confidence": 0.8,
            }
            for criterion in active
        ]
    }


def _valid_judge_report(run: Run) -> dict[str, list[dict[str, str]]]:
    context = EvaluationContextBuilder(run).build()
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    return {
        "items": [
            {
                "item_type": "criterion",
                "item_key": criterion.value,
                "verdict": Verdict.VALID.value,
            }
            for criterion in active
        ]
    }


def _sectioned_scripts(run: Run) -> dict[str, object]:
    context = EvaluationContextBuilder(run).build()
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    observation_id = "sec_method:method:1:obs"
    check_id = "method_vs_question:check"
    return {
        "sections/method": {
            "section_id": "sec_method",
            "observations": [
                {
                    "id": "obs",
                    "section_id": "sec_method",
                    "role": "method",
                    "kind": "strength",
                    "statement": "O método explica os dados utilizados.",
                    "evidence": [
                        {"quote": "O método usa dados públicos.", "section_id": "sec_method"}
                    ],
                    "criteria": ["soundness", "replicability", "clarity"],
                    "severity": "minor",
                    "confidence": 0.8,
                }
            ],
        },
        "cross_checker": {
            "id": "check",
            "kind": "method_vs_question",
            "verdict": "consistent",
            "evidence": [],
            "criteria": ["soundness"],
            "severity": "minor",
        },
        "synthesizer": {
            "criteria": [
                {
                    "criterion_key": criterion.value,
                    "grade": 3,
                    "justification": f"A observação sustenta {criterion.value}.",
                    "observation_ids": (
                        [observation_id]
                        if criterion.value in {"soundness", "replicability", "clarity"}
                        else []
                    ),
                    "check_ids": [check_id] if criterion.value == "soundness" else [],
                    "confidence": 0.8,
                }
                for criterion in active
            ]
        },
        "judge": {
            "items": [
                {"item_type": "observation", "item_key": observation_id, "verdict": "valid"},
                {"item_type": "check", "item_key": check_id, "verdict": "valid"},
                *[
                    {
                        "item_type": "criterion",
                        "item_key": criterion.value,
                        "verdict": "valid",
                    }
                    for criterion in active
                ],
            ]
        },
    }


def _revision_judge_reports(
    run: Run,
) -> tuple[
    str,
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    context = EvaluationContextBuilder(run).build()
    active = next(
        item
        for item in context.evaluation_config.paper_types
        if item.paper_type is context.profile.paper_type
    ).active
    target = active[0]
    initial = [
        {
            "item_type": "criterion",
            "item_key": criterion.value,
            "verdict": "invalid" if criterion is target else "valid",
            "issues": (
                [
                    {
                        "category": "rubric_mismatch",
                        "excerpt": "nota 3",
                        "reason": "A síntese precisa de revisão.",
                    }
                ]
                if criterion is target
                else []
            ),
        }
        for criterion in active
    ]
    revised = {
        "item_type": "criterion",
        "item_key": target.value,
        "verdict": "valid",
    }
    replacement = {
        "criterion_key": target.value,
        "grade": 4,
        "justification": f"A evidência revisada sustenta {target.value}.",
        "observation_ids": [],
        "check_ids": [],
        "evidence": [{"quote": "O método usa dados públicos.", "section_id": "sec_method"}],
        "confidence": 0.9,
    }
    response: dict[str, object] = {
        "item_type": "criterion",
        "item_key": target.value,
        "action": "accept",
        "justification": "A síntese foi corrigida com evidência direta.",
        "replacement": replacement,
    }
    return target.value, {"items": initial}, {"items": [revised]}, response


@pytest.mark.django_db(transaction=True)
def test_e4_creates_and_finalizes_round_one_for_all_slots(
    run: Run,
) -> None:
    prepared = _prepare_run(run)
    _advance_to_evaluation(prepared)
    task_id = "e4"
    Run.objects.filter(pk=prepared.pk).update(
        config_snapshot={
            **prepared.config_snapshot,
            "evaluation_mode": EvaluationMode.SECTIONED.value,
        },
    )
    active_run = Run.for_evaluation(prepared.pk, task_id)
    scripts = _sectioned_scripts(active_run)
    factory = FakeAgentFactory(
        str(prepared.pk),
        Stage.EVALUATION,
        task_id=task_id,
        scripts={
            "sections/method": [scripts["sections/method"]] * len(EvaluatorSlot),
            "cross_checker": [scripts["cross_checker"]] * len(EvaluatorSlot),
            "synthesizer": [scripts["synthesizer"]] * len(EvaluatorSlot),
            "judge": [scripts["judge"]] * len(EvaluatorSlot),
        },
    )
    started = monotonic()
    result = run_evaluation(str(prepared.pk), task_id, factory=factory)
    elapsed = monotonic() - started

    rounds = list(ReviewRound.objects.filter(run=prepared).order_by("evaluator_slot"))
    assert result["evaluators"] == [slot.value for slot in EvaluatorSlot]
    assert result["review_rounds"] == {slot.value: 1 for slot in EvaluatorSlot}
    assert len(rounds) == 3 and all(item.ready for item in rounds)
    assert len(factory.calls) == 12
    assert elapsed < settings.stage_soft_time_limit_seconds

    # Uma reentrega do estágio retoma pelos checkpoints sem repetir chamadas de modelo.
    run_evaluation(str(prepared.pk), task_id, factory=factory)
    assert len(factory.calls) == 12


@pytest.mark.django_db(transaction=True)
def test_e4_revises_invalid_items_then_finalizes_round_two(run: Run) -> None:
    prepared = _prepare_run(run)
    _advance_to_evaluation(prepared)
    task_id = "e4"
    Run.objects.filter(pk=prepared.pk).update(
        config_snapshot={
            **prepared.config_snapshot,
            "evaluation_mode": EvaluationMode.WHOLE_DOCUMENT.value,
        },
    )
    active_run = Run.for_evaluation(prepared.pk, task_id)
    response = _whole_document_output(active_run)
    target, first_judgment, second_judgment, revision = _revision_judge_reports(active_run)
    factory = FakeAgentFactory(
        str(prepared.pk),
        Stage.EVALUATION,
        task_id=task_id,
        scripts={
            "whole_document_reviewer": [response] * len(EvaluatorSlot),
            "judge": [first_judgment] * len(EvaluatorSlot) + [second_judgment] * len(EvaluatorSlot),
            "reviser": [revision] * len(EvaluatorSlot),
        },
    )

    result = run_evaluation(str(prepared.pk), task_id, factory=factory)

    rounds = list(
        ReviewRound.objects.filter(run=prepared).order_by("evaluator_slot", "round_number")
    )
    assert result["review_rounds"] == {slot.value: 2 for slot in EvaluatorSlot}
    latest = list(ReviewRound.objects.filter(run=prepared, round_number=2))
    assert len(rounds) == 6
    assert len(latest) == 3 and all(item.ready for item in latest)
    grades = [
        next(
            criterion
            for criterion in item.state.criteria
            if criterion.criterion_key.value == target
        ).grade
        for item in latest
    ]
    assert grades == [4, 4, 4]
    assert [call.name for call in factory.calls].count("reviser") == 3


@pytest.mark.django_db(transaction=True)
def test_e4_retry_resumes_after_judge_failure_without_repeating_reviewers(run: Run) -> None:
    prepared = _prepare_run(run)
    _advance_to_evaluation(prepared)
    task_id = "e4"
    Run.objects.filter(pk=prepared.pk).update(
        config_snapshot={
            **prepared.config_snapshot,
            "evaluation_mode": EvaluationMode.WHOLE_DOCUMENT.value,
        },
    )
    active_run = Run.for_evaluation(prepared.pk, task_id)
    response = _whole_document_output(active_run)
    judged = _valid_judge_report(active_run)
    factory = FakeAgentFactory(
        str(prepared.pk),
        Stage.EVALUATION,
        task_id=task_id,
        scripts={
            "whole_document_reviewer": [response] * len(EvaluatorSlot),
            "judge": [LLMUnavailable("503"), judged, judged, judged],
        },
    )

    with pytest.raises(LLMUnavailable):
        run_evaluation(str(prepared.pk), task_id, factory=factory)
    reviewer_calls_before_retry = [
        call for call in factory.calls if call.name == "whole_document_reviewer"
    ]
    run_evaluation(str(prepared.pk), task_id, factory=factory)

    assert len(reviewer_calls_before_retry) == len(EvaluatorSlot)
    assert [call.name for call in factory.calls].count("whole_document_reviewer") == 3
    assert len(ReviewRound.latest_for_consolidation(prepared.pk)) == 3


@pytest.mark.django_db(transaction=True)
def test_e4_retry_finishes_after_a_failed_synthesis_without_a_stuck_judged_round(
    run: Run,
) -> None:
    """O caso do run real: a síntese falha, o juiz não julga a rodada incompleta, e o retry
    termina sem refazer os passes por seção nem as checagens."""
    prepared = _prepare_run(run)
    _advance_to_evaluation(prepared)
    task_id = "e4"
    Run.objects.filter(pk=prepared.pk).update(
        config_snapshot={
            **prepared.config_snapshot,
            "evaluation_mode": EvaluationMode.SECTIONED.value,
        },
    )
    active_run = Run.for_evaluation(prepared.pk, task_id)
    scripts = _sectioned_scripts(active_run)
    slots = len(EvaluatorSlot)
    factory = FakeAgentFactory(
        str(prepared.pk),
        Stage.EVALUATION,
        task_id=task_id,
        scripts={
            "sections/method": [scripts["sections/method"]] * slots,
            "cross_checker": [scripts["cross_checker"]] * slots,
            # Cada slot pede a síntese duas vezes e não recebe nada; no retry, recebe.
            "synthesizer": [{"criteria": []}] * (2 * slots) + [scripts["synthesizer"]] * slots,
            "judge": [scripts["judge"]] * slots,
        },
    )

    with pytest.raises(InvalidEvaluationOutput, match="não trouxe os critérios"):
        run_evaluation(str(prepared.pk), task_id, factory=factory)
    names = [call.name for call in factory.calls]
    assert names.count("judge") == 0
    assert not any(item.verdicts.exists() for item in ReviewRound.objects.filter(run=prepared))

    result = run_evaluation(str(prepared.pk), task_id, factory=factory)

    names = [call.name for call in factory.calls]
    assert result["review_rounds"] == {slot.value: 1 for slot in EvaluatorSlot}
    assert names.count("sections/method") == slots
    assert names.count("cross_checker") == slots
    assert names.count("judge") == slots


@pytest.mark.django_db(transaction=True)
def test_e4_retry_resumes_a_revision_round_whose_judge_failed(run: Run) -> None:
    """O caso do run real: a rodada 2 já tem os vereditos válidos levados da rodada 1 quando o
    juiz dela cai; a retomada não reescreve a rodada (travava em "revisão julgada")."""
    prepared = _prepare_run(run)
    _advance_to_evaluation(prepared)
    task_id = "e4"
    Run.objects.filter(pk=prepared.pk).update(
        config_snapshot={
            **prepared.config_snapshot,
            "evaluation_mode": EvaluationMode.WHOLE_DOCUMENT.value,
        },
    )
    active_run = Run.for_evaluation(prepared.pk, task_id)
    response = _whole_document_output(active_run)
    _, first_judgment, second_judgment, revision = _revision_judge_reports(active_run)
    slots = len(EvaluatorSlot)
    factory = FakeAgentFactory(
        str(prepared.pk),
        Stage.EVALUATION,
        task_id=task_id,
        scripts={
            "whole_document_reviewer": [response] * slots,
            "judge": [first_judgment] * slots + [LLMUnavailable("503")] + [second_judgment] * slots,
            # A primeira revisão vem fora das regras (accept sem o item corrigido) e é recusada.
            "reviser": [{**revision, "replacement": None}] * slots + [revision] * slots,
        },
    )

    # A volta seguinte do laço de revisão retoma a rodada 2 no mesmo run.
    result = run_evaluation(str(prepared.pk), task_id, factory=factory)

    assert set(result["review_rounds"]) == {slot.value for slot in EvaluatorSlot}
    assert len(ReviewRound.latest_for_consolidation(prepared.pk)) == slots


def test_builder_uses_three_slots_and_snapshot_mode() -> None:
    from projects.correction.evaluation.tests.test_context import _context_run

    run = _context_run()
    run.config_snapshot["evaluation_mode"] = EvaluationMode.WHOLE_DOCUMENT.value
    context = EvaluationContextBuilder(run).build()
    workflow = build_evaluation_workflow("run", "task", context, factory=FakeAgentFactory())

    assert workflow.name == "evaluation"
    assert len(context.evaluators) == 3
    assert context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT


@dataclass
class _Step:
    """O que `_failed_step_names` lê de um `StepOutput` do Agno (que só o workflow.py importa)."""

    step_name: str
    success: bool = True
    error: str | None = None
    steps: list[_Step] | None = None


def test_failed_steps_show_the_error_of_the_inner_steps() -> None:
    inner = _Step("evaluator_a", success=False, error="Saída incompatível.")
    outer = _Step("evaluators", steps=[inner, _Step("evaluator_b")])

    failed = _failed_step_names(cast(Any, [outer]))

    assert failed == ["evaluators", "evaluator_a: Saída incompatível."]
