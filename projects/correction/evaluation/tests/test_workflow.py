from typing import Any

import pytest

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.attempts.models import LLMCall, Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evaluation.models import FinalReport
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.usage import DatabaseUsageSink

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_mode")]


def test_e5_retries_provider_failure_then_finishes_with_a_single_report(
    evaluated_run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = FakeAgentFactory(
        str(evaluated_run.pk),
        Stage.CONSOLIDATION,
        DatabaseUsageSink(),
        scripts={"meta_reviewer": [LLMUnavailable("503"), {}]},
    )

    def build(*args: Any, **kwargs: Any) -> FakeAgentFactory:
        return factory

    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", build)
    publish_stage(str(evaluated_run.pk), Stage.CONSOLIDATION)
    completed = Run.get_by_id(evaluated_run.pk)
    assert completed.status == RunStatus.DONE
    row = FinalReport.for_run(completed.pk)
    assert row is not None and row.total_score == 4
    calls = LLMCall.for_run(completed.pk)
    assert [call.success for call in calls] == [False, True]
    assert completed.config_snapshot["prompt_versions"]["meta_reviewer"] == calls[-1].prompt_version
    events = RunEvent.for_run(completed.pk)
    assert len([event for event in events if event.event_type == "retry_scheduled"]) == 1
    assert "Artigo" not in str(events[-1].payload)
    publish_stage(str(completed.pk), Stage.CONSOLIDATION)
    assert FinalReport.for_run(completed.pk).pk == row.pk  # type: ignore[union-attr]
    assert len(factory.calls) == 2
