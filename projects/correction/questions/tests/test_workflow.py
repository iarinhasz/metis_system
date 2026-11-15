"""E2 real com Workflow Agno, tasks eager, fakes e PostgreSQL."""

from typing import Any
from unittest.mock import Mock

import pytest

from projects.correction.agents.fakes import FakeAgentFactory, InvalidFor
from projects.correction.agents.specs import Role
from projects.correction.attempts.models import LLMCall, Run, RunEvent
from projects.correction.attempts.status import RunPurpose, RunStatus, Stage
from projects.correction.extractor.models import Extraction
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import LLMUnavailable
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.services import recover_run
from projects.correction.pipeline.usage import DatabaseUsageSink
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.models import Question, RubricField
from projects.correction.questions.profile import QuestionSnapshot
from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import (
    PRIVATE_TEXT,
    article,
    field_answer,
    topic_answer,
)
from projects.correction.questions.workflow import run_profiling

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_mode")]


def prepare(run: Run, *, ambiguous_sections: bool = False) -> None:
    document = article()
    if ambiguous_sections:
        base = document.sections[0]
        document = document.model_copy(
            update={
                "sections": (
                    base,
                    base.model_copy(update={"id": "sec_2", "title": "Nossa proposta", "key": None}),
                    base.model_copy(
                        update={"id": "sec_3", "title": "Medindo o efeito", "key": None}
                    ),
                )
            }
        )
    assert Run.claim_stage(run.pk, Stage.EXTRACTION, "e1") is not None
    extraction = Extraction.store(run.attempt.sha256, "workflow-25", document)
    assert Run.attach_extraction(run.pk, "e1", extraction)
    assert Run.complete_stage(run.pk, "e1", RunStatus.EXTRACTED) is not None


def generic_question() -> Question:
    question = Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    RubricField.create(
        question=question, key="context", label="Contexto", rubric_text="Texto curado.", order=0
    )
    return question


@pytest.fixture
def factory(run: Run, monkeypatch: pytest.MonkeyPatch) -> FakeAgentFactory:
    fake = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={"profiler_field": [field_answer()], "profiler_topic": [topic_answer()]},
    )

    def create(*args: Any, **kwargs: Any) -> FakeAgentFactory:
        return fake

    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", create)
    return fake


def test_fixture_reaches_profiled_with_question_and_snapshot(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    factory: FakeAgentFactory,
    publisher: Mock,
) -> None:
    question = generic_question()
    prepare(run)
    publish_stage(str(run.pk), Stage.PROFILING)
    profiled = Run.get_by_id(run.pk)
    assert profiled.status == RunStatus.PROFILED
    assert profiled.question_id == question.pk
    assert profiled.purpose == RunPurpose.EVALUATION
    assert profiled.profile["classification"]["taxonomy_version"] == profiling_taxonomy.version
    assert profiled.profile["classification"]["confidence"] == 0.9
    assert profiled.profile["document_map"]["abstract"] == PRIVATE_TEXT
    assert profiled.profile["section_roles"][0]["roles"] == ["other"]
    assert profiled.profile["complete"] is True
    snapshot = profiled.config_snapshot
    assert snapshot["question"]["id"] == str(question.pk)
    assert snapshot["question"]["rubric_fields"][0]["rubric_text"] == "Texto curado."
    assert set(snapshot["model_specs"]) == {role.value for role in Role}
    assert "api_key" not in str(snapshot)
    assert [call.name for call in factory.calls] == ["profiler_field", "profiler_topic"]
    calls = LLMCall.for_run(run.pk)
    assert len(calls) == 2 and all(call.success and call.cost_usd is not None for call in calls)
    assert all(snapshot["prompt_versions"][call.agent] == call.prompt_version for call in calls)
    publisher.assert_called_once_with(str(run.pk), Stage.INTEGRITY)
    event = RunEvent.for_run(run.pk)[-1]
    assert PRIVATE_TEXT not in str(event.payload)


def test_missing_question_waits_and_recovery_reuses_classification(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    factory: FakeAgentFactory,
    publisher: Mock,
) -> None:
    prepare(run)
    publish_stage(str(run.pk), Stage.PROFILING)
    waiting = Run.get_by_id(run.pk)
    assert waiting.status == RunStatus.WAITING_SETUP and waiting.question_id is None
    assert "classification" in waiting.profile and "complete" not in waiting.profile
    publisher.assert_not_called()
    question = generic_question()
    recover_run(run.pk, actor="admin:test")
    publish_stage(str(run.pk), Stage.PROFILING)
    profiled = Run.get_by_id(run.pk)
    assert profiled.status == RunStatus.PROFILED and profiled.question_id == question.pk
    assert len(factory.calls) == 2


def test_provider_retry_in_topic_does_not_repeat_field(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    monkeypatch: pytest.MonkeyPatch,
    publisher: Mock,
) -> None:
    generic_question()
    prepare(run)
    fake = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [LLMUnavailable("503"), topic_answer()],
        },
    )
    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", lambda *a, **kw: fake)
    publish_stage(str(run.pk), Stage.PROFILING)
    assert Run.get_by_id(run.pk).status == RunStatus.PROFILED
    assert [call.name for call in fake.calls] == [
        "profiler_field",
        "profiler_topic",
        "profiler_topic",
    ]
    assert [call.success for call in LLMCall.for_run(run.pk)] == [True, False, True]
    assert len([e for e in RunEvent.for_run(run.pk) if e.event_type == "retry_scheduled"]) == 1


def test_retry_in_roles_preserves_resolution_and_each_finished_role(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    monkeypatch: pytest.MonkeyPatch,
    publisher: Mock,
) -> None:
    question = generic_question()
    prepare(run, ambiguous_sections=True)
    fake = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [topic_answer()],
            "section_role_classifier": [
                {"roles": ["method"], "confidence": 0.9},
                LLMUnavailable("503"),
                {"roles": ["results"], "confidence": 0.9},
            ],
        },
    )
    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", lambda *a, **kw: fake)
    publish_stage(str(run.pk), Stage.PROFILING)
    profiled = Run.get_by_id(run.pk)
    assert profiled.status == RunStatus.PROFILED and profiled.question_id == question.pk
    assert [role["roles"] for role in profiled.profile["section_roles"]] == [
        ["other"],
        ["method"],
        ["results"],
    ]
    assert [call.name for call in fake.calls].count("section_role_classifier") == 3
    assert len(LLMCall.for_run(run.pk)) == 5


def test_invalid_answers_exhaust_only_the_local_budget(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    monkeypatch: pytest.MonkeyPatch,
    publisher: Mock,
) -> None:
    prepare(run)
    fake = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={
            "profiler_field": [InvalidFor(50)],
        },
    )
    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", lambda *a, **kw: fake)
    publish_stage(str(run.pk), Stage.PROFILING)
    failed = Run.get_by_id(run.pk)
    assert failed.status == RunStatus.ERROR_LLM
    assert len(fake.calls) == settings.profiling_max_attempts
    assert not [e for e in RunEvent.for_run(run.pk) if e.event_type == "retry_scheduled"]
    assert PRIVATE_TEXT not in failed.last_error
    publisher.assert_not_called()


def test_missing_taxonomy_waits_without_model_calls(
    run: Run, factory: FakeAgentFactory, publisher: Mock
) -> None:
    prepare(run)
    publish_stage(str(run.pk), Stage.PROFILING)
    assert Run.get_by_id(run.pk).status == RunStatus.WAITING_SETUP
    assert not factory.calls


def test_retry_pins_specs_prompts_and_taxonomy(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generic_question()
    prepare(run)
    assert Run.claim_stage(run.pk, Stage.PROFILING, "e2") is not None
    first = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [LLMUnavailable("503")],
        },
    )
    with pytest.raises(LLMUnavailable):
        run_profiling(str(run.pk), "e2", factory=first)
    snapshot = Run.get_by_id(run.pk).config_snapshot
    assert (
        snapshot["prompt_versions"]["profiler_topic"] == LLMCall.for_run(run.pk)[-1].prompt_version
    )
    monkeypatch.setattr(settings, "profiling_taxonomy_version", "outra-versao")
    monkeypatch.setattr(settings, "fast", settings.fast.model_copy(update={"model_id": "changed"}))
    monkeypatch.setattr(
        "projects.correction.questions.workflow.template", lambda name: "outro prompt"
    )
    second = FakeAgentFactory(
        str(run.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={"profiler_topic": [topic_answer()]},
    )
    result = run_profiling(str(run.pk), "e2", factory=second)
    assert result.taxonomy_version == profiling_taxonomy.version
    assert [call.name for call in second.calls] == ["profiler_topic"]
    assert second.models.specs[Role.FAST].model_id == snapshot["model_specs"]["fast"]["model_id"]
    topic_calls = [call for call in LLMCall.for_run(run.pk) if call.agent == "profiler_topic"]
    assert len(topic_calls) == 2 and topic_calls[0].prompt_version == topic_calls[1].prompt_version


def test_obsolete_task_cannot_save_or_continue(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    factory: FakeAgentFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from projects.correction.questions.profiler import classify_field

    prepare(run)
    assert Run.claim_stage(run.pk, Stage.PROFILING, "old") is not None

    def lost(*args: Any, **kwargs: Any) -> Any:
        value = classify_field(*args, **kwargs)
        Run.release_stale(run.pk)
        return value

    monkeypatch.setattr("projects.correction.questions.workflow.classify_field", lost)
    with pytest.raises(RunConflict):
        run_profiling(str(run.pk), "old", factory=factory)
    current = Run.get_by_id(run.pk)
    assert current.status == RunStatus.EXTRACTED and current.profile == {}
    assert len(factory.calls) == 1


def test_rubric_check_uses_the_supplied_draft(
    run: Run,
    profiling_taxonomy: TaxonomySnapshot,
    monkeypatch: pytest.MonkeyPatch,
    publisher: Mock,
) -> None:
    draft = Question.create(name="Rascunho", method="standard", is_generic=True)
    snapshot = QuestionSnapshot(
        id=draft.pk,
        version=1,
        name=draft.name,
        method="standard",
        is_generic=True,
        taxonomy_node_code=None,
        taxonomy_version=None,
        rubric_fields=(),
    )
    research = Run.create(
        attempt=run.attempt,
        purpose=RunPurpose.RUBRIC_CHECK,
        config_snapshot={"question": snapshot.model_dump(mode="json")},
    )
    prepare(research)
    fake = FakeAgentFactory(
        str(research.pk),
        Stage.PROFILING,
        DatabaseUsageSink(),
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [topic_answer()],
        },
    )
    monkeypatch.setattr("projects.correction.pipeline.stages.AgentFactory", lambda *a, **kw: fake)
    publish_stage(str(research.pk), Stage.PROFILING)
    profiled = Run.get_by_id(research.pk)
    assert profiled.status == RunStatus.INTEGRITY_CHECKED and profiled.question_id == draft.pk
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED
