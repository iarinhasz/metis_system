"""Julgamento cruzado, validação dos excerpts e persistência auditável."""

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    EvaluationMode,
    EvaluatorSlot,
    Issue,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Family, ModelSpec, Provider
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.judge import JudgeStep, RunJudgeCheckpoints
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.tests.test_context import _context_run


def _context() -> EvaluationContext:
    return EvaluationContextBuilder(_context_run()).build()


def _state() -> ReviewState:
    observation = Observation(
        id="obs-1",
        section_id="sec_method",
        role=SectionRole.METHOD,
        kind="strength",
        statement="O método usa dados públicos.",
        criteria=(Criterion.SOUNDNESS,),
        severity="minor",
        confidence=0.8,
    )
    synthesis = CriterionSynthesis(
        criterion_key=Criterion.SOUNDNESS,
        grade=3,
        justification="O método descreve a origem dos dados.",
        observation_ids=(observation.id,),
        confidence=0.8,
    )
    return ReviewState(observations=(observation,), criteria=(synthesis,))


def _report(
    *,
    observation_verdict: Verdict = Verdict.VALID,
    excerpt: str | None = None,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "item_type": ItemType.OBSERVATION.value,
        "item_key": "obs-1",
        "verdict": observation_verdict.value,
        "issues": [],
    }
    if observation_verdict is Verdict.INVALID:
        observation["issues"] = [
            {
                "category": "ungrounded",
                "excerpt": excerpt or "O método usa dados públicos.",
                "reason": "A evidência não sustenta a afirmação.",
            }
        ]
    return {
        "items": [
            observation,
            {
                "item_type": ItemType.CRITERION.value,
                "item_key": Criterion.SOUNDNESS.value,
                "verdict": "valid",
                "issues": [],
            },
        ]
    }


class FakeCheckpoints:
    def __init__(
        self,
        state: ReviewState,
        *,
        verdicts: dict[tuple[ItemType, str], ItemVerdict] | None = None,
        grades: Mapping[EvaluatorSlot, Mapping[str, int]] | None = None,
    ) -> None:
        self.state = state
        self.verdicts = verdicts or {}
        self.grades = grades or {}
        self.writes: list[tuple[ItemVerdict, ModelSpec]] = []
        self.ownership_checks = 0

    def assert_owned(self) -> None:
        self.ownership_checks += 1

    def read_state(self) -> ReviewState:
        return self.state

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        return self.verdicts

    def read_slot_grades(self) -> Mapping[EvaluatorSlot, Mapping[str, int]]:
        return self.grades

    def record(self, item: ItemVerdict, judge_model: ModelSpec) -> None:
        self.writes.append((item, judge_model))
        self.verdicts[(item.item_type, item.item_key)] = item


def _step(
    *,
    scripts: Sequence[object],
    checkpoints: FakeCheckpoints | None = None,
    usage: MemoryUsageSink | None = None,
) -> tuple[JudgeStep, EvaluationContext, FakeAgentFactory, FakeCheckpoints]:
    context = _context()
    factory = FakeAgentFactory(scripts={"judge": scripts}, usage_sink=usage)
    store = checkpoints or FakeCheckpoints(
        _state(),
        grades={
            EvaluatorSlot.A: {"soundness": 2},
            EvaluatorSlot.B: {"soundness": 4},
            EvaluatorSlot.C: {"soundness": 5},
        },
    )
    return (
        JudgeStep(context, EvaluatorSlot.A, factory, store),
        context,
        factory,
        store,
    )


def test_judges_all_items_missing_verdict_with_cross_family_and_divergences() -> None:
    usage = MemoryUsageSink()
    step, context, factory, checkpoints = _step(scripts=[_report()], usage=usage)

    judged = step.execute()

    assert len(judged) == 2
    evaluator = context.evaluator(EvaluatorSlot.A).model
    assert usage.calls[0].provider != evaluator.provider
    assert usage.calls[0].model_id != evaluator.model_id
    assert len(factory.calls) == 1
    prompt_data = json.loads(factory.calls[0].payload.prompt)
    assert prompt_data["divergence_hints"] == {"soundness": [4, 5]}
    assert len(prompt_data["items_to_judge"]) == 2
    assert "Artigo sintético" in (factory.calls[0].payload.article or "")
    assert len(checkpoints.writes) == 2


def test_validator_rejected_items_are_never_sent_to_judge() -> None:
    state = _state()
    rejected = ItemVerdict(
        item_type=ItemType.OBSERVATION,
        item_key="obs-1",
        verdict=Verdict.INVALID,
        issues=(
            Issue(
                category="ungrounded",
                excerpt="O método usa dados públicos.",
                reason="Trecho não localizado no documento.",
            ),
        ),
    )
    store = FakeCheckpoints(
        state,
        verdicts={(ItemType.OBSERVATION, "obs-1"): rejected},
    )
    step, _, factory, _ = _step(scripts=[{"items": [_report()["items"][1]]}], checkpoints=store)

    judged = step.execute()

    assert [(item.item_type, item.item_key) for item in judged] == [
        (ItemType.CRITERION, Criterion.SOUNDNESS.value)
    ]
    sent = json.loads(factory.calls[0].payload.prompt)
    assert [(item["item_type"], item["item_key"]) for item in sent["items_to_judge"]] == [
        (ItemType.CRITERION.value, Criterion.SOUNDNESS.value)
    ]


def test_invalid_excerpt_triggers_one_corrective_call() -> None:
    step, _, factory, _ = _step(
        scripts=[
            _report(observation_verdict=Verdict.INVALID, excerpt="Trecho inventado"),
            _report(observation_verdict=Verdict.INVALID),
        ]
    )

    judged = step.execute()

    assert len(factory.calls) == 2
    correction = json.loads(factory.calls[1].payload.prompt)
    assert correction["excerpt_errors"][0]["excerpt"] == "Trecho inventado"
    observation = next(item for item in judged if item.item_type is ItemType.OBSERVATION)
    assert observation.verdict is Verdict.INVALID


def test_persistent_invalid_excerpt_is_discarded() -> None:
    bad = _report(observation_verdict=Verdict.INVALID, excerpt="Trecho inventado")
    step, _, factory, _ = _step(scripts=[bad, bad])

    judged = step.execute()

    observation = next(item for item in judged if item.item_type is ItemType.OBSERVATION)
    assert len(factory.calls) == 2
    assert observation.verdict is Verdict.VALID
    assert observation.issues == ()


def test_slot_c_judge_family_is_crossed_from_its_configured_model() -> None:
    context = _context()
    context = context.model_copy(
        update={
            "evaluators": tuple(
                item.model_copy(
                    update={
                        "model": item.model.model_copy(
                            update={"family": Family.GPT, "provider": Provider.OPENAI}
                        )
                    }
                )
                if item.slot is EvaluatorSlot.C
                else item
                for item in context.evaluators
            )
        }
    )
    usage = MemoryUsageSink()
    factory = FakeAgentFactory(scripts={"judge": [_report()]}, usage_sink=usage)
    step = JudgeStep(context, EvaluatorSlot.C, factory, FakeCheckpoints(_state()))

    step.execute()

    assert usage.calls[0].provider == "google"
    assert (
        factory.models.judge_for(context.evaluator(EvaluatorSlot.C).model).family is Family.GEMINI
    )


def test_missing_item_is_asked_again_and_counts_as_valid_if_still_missing() -> None:
    observation_only = {"items": [_report()["items"][0]]}
    step, _, factory, _ = _step(scripts=[observation_only, observation_only])

    judged = step.execute()

    correction = json.loads(factory.calls[1].payload.prompt)
    assert correction["missing_items"] == [
        {"item_type": "criterion", "item_key": Criterion.SOUNDNESS.value}
    ]
    assert {(item.item_key, item.verdict) for item in judged} == {
        ("obs-1", Verdict.VALID),
        (Criterion.SOUNDNESS.value, Verdict.VALID),
    }


def test_near_miss_verdicts_from_real_models_are_cleaned_not_fatal() -> None:
    report = _report(observation_verdict=Verdict.INVALID)
    observation, criterion = report["items"]
    unjustified = {**observation, "issues": []}
    flagged_valid = {**criterion, "issues": observation["issues"]}
    unrequested = {**criterion, "item_key": "outro"}
    step, _, factory, _ = _step(
        scripts=[{"items": [unjustified, flagged_valid, unrequested, unjustified]}]
    )

    judged = step.execute()

    assert len(factory.calls) == 1
    assert [(item.item_key, item.verdict, item.issues) for item in judged] == [
        ("obs-1", Verdict.VALID, ()),
        (Criterion.SOUNDNESS.value, Verdict.VALID, ()),
    ]


@pytest.mark.django_db
def test_database_checkpoint_persists_judge_model_and_skips_existing_verdict(run: Run) -> None:
    task_id = "e4-judge"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    context = _context()
    review = ReviewRound.store(
        run.pk,
        task_id,
        slot=EvaluatorSlot.A,
        round_number=1,
        mode=EvaluationMode.SECTIONED,
        model_spec=context.evaluator(EvaluatorSlot.A).model,
        state=_state(),
    )
    checkpoints = RunJudgeCheckpoints(run_id=str(run.pk), task_id=task_id, slot=EvaluatorSlot.A)
    factory = FakeAgentFactory(scripts={"judge": [_report()]})
    step = JudgeStep(context, EvaluatorSlot.A, factory, checkpoints)

    judged = step.execute()
    rerun = step.execute()
    stored = list(JudgeVerdict.objects.filter(round=review).order_by("item_key"))

    assert len(judged) == 2 and rerun == ()
    assert len(factory.calls) == 1
    assert all(item.source == VerdictSource.JUDGE and item.judge_model for item in stored)
