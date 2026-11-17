"""Testes do gate humano e do reprocessamento, com Celery em modo eager."""

from collections.abc import Callable
from typing import Any

import pytest

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import HumanDecision, RunStatus, Stage
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import LLMUnavailable, SetupRequired
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.services import decide_run, recover_run
from projects.correction.pipeline.stages import (
    EvaluationStage,
    ExtractionStage,
    IntegrityStage,
    ProfilingStage,
    StageContext,
    StageOutcome,
)
from projects.correction.queries.attempts.run import RunConflict

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_celery")]

Execute = Callable[[Any, StageContext], StageOutcome]


def transitions(run: Run) -> list[str]:
    return [e.to_status for e in RunEvent.for_run(run.pk) if e.event_type == "transition"]


def spy(calls: list[str], name: str) -> Execute:
    """Stub de estágio que só registra que rodou."""

    def execute(self: Any, ctx: StageContext) -> StageOutcome:
        calls.append(name)
        return StageOutcome()

    return execute


def high_risk(self: IntegrityStage, ctx: StageContext) -> StageOutcome:
    return StageOutcome(payload={"risk": "high"}, halt=True)


def llm_down(self: EvaluationStage, ctx: StageContext) -> StageOutcome:
    raise LLMUnavailable("429 do provedor")


@pytest.fixture
def gated_run(run: Run, monkeypatch: pytest.MonkeyPatch) -> Run:
    """Um run parado no gate humano depois de um E3 de risco alto."""
    monkeypatch.setattr(IntegrityStage, "execute", high_risk)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    gated = Run.get_by_id(run.pk)
    assert gated.status == RunStatus.WAITING_HUMAN_REVIEW
    return gated


def test_continue_resumes_at_evaluation_and_reaches_done(gated_run: Run) -> None:
    decide_run(gated_run.pk, HumanDecision.CONTINUE, actor="admin:ana", note="Trecho citado")
    run = Run.get_by_id(gated_run.pk)

    assert run.status == RunStatus.DONE
    assert transitions(run)[-6:] == [
        "waiting_human_review",
        "integrity_checked",
        "evaluating",
        "evaluated",
        "consolidating",
        "done",
    ]
    decision = next(e for e in RunEvent.for_run(run.pk) if e.to_status == "integrity_checked")
    assert decision.actor == "admin:ana"
    assert decision.payload == {"decision": "continue", "note": "Trecho citado"}


def test_close_ends_the_run_without_evaluating(
    gated_run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(EvaluationStage, "execute", spy(calls, "E4"))

    decide_run(gated_run.pk, HumanDecision.CLOSE, actor="admin:ana")

    assert Run.get_by_id(gated_run.pk).status == RunStatus.CLOSED_BY_REVIEWER
    assert calls == []


def test_decide_outside_gate_conflicts_and_changes_nothing(run: Run) -> None:
    with pytest.raises(RunConflict):
        decide_run(run.pk, HumanDecision.CONTINUE, actor="admin:ana")

    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED


def test_recover_resumes_failed_evaluation_without_redoing_earlier_stages(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "stage_max_retries", 1)
    monkeypatch.setattr(EvaluationStage, "execute", llm_down)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    assert Run.get_by_id(run.pk).status == RunStatus.ERROR_LLM

    calls: list[str] = []
    monkeypatch.setattr(ExtractionStage, "execute", spy(calls, "E1"))
    monkeypatch.setattr(ProfilingStage, "execute", spy(calls, "E2"))
    monkeypatch.setattr(IntegrityStage, "execute", spy(calls, "E3"))
    monkeypatch.setattr(EvaluationStage, "execute", spy(calls, "E4"))
    recover_run(run.pk, actor="admin:ana")
    run = Run.get_by_id(run.pk)

    assert run.status == RunStatus.DONE
    assert calls == ["E4"]
    assert transitions(run)[-6:] == [
        "error_llm",
        "integrity_checked",
        "evaluating",
        "evaluated",
        "consolidating",
        "done",
    ]


def test_recover_from_waiting_setup_reruns_only_profiling(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_question(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        raise SetupRequired("nenhuma Question disponível")

    monkeypatch.setattr(ProfilingStage, "execute", no_question)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    assert Run.get_by_id(run.pk).status == RunStatus.WAITING_SETUP

    calls: list[str] = []
    monkeypatch.setattr(ExtractionStage, "execute", spy(calls, "E1"))
    monkeypatch.setattr(ProfilingStage, "execute", spy(calls, "E2"))
    recover_run(run.pk, actor="admin:ana")

    assert Run.get_by_id(run.pk).status == RunStatus.DONE
    assert calls == ["E2"]


def test_recover_refuses_a_run_that_did_not_fail(run: Run) -> None:
    with pytest.raises(RunConflict):
        recover_run(run.pk, actor="admin:ana")

    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED
