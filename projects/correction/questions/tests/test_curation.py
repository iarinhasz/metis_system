"""Rascunho, aprovação, ativação, edição e snapshots com PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import pytest
from django.db import close_old_connections, connections
from django.db.models import query

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory, InvalidFor
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.extractor.models import Extraction
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.curation import draft_question
from projects.correction.questions.curation_errors import CurationConflict, CurationError
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.profile import QuestionSnapshot
from projects.correction.questions.profiler import profile_article
from projects.correction.questions.resolver import resolve_question
from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import (
    FIELD,
    article,
    field_answer,
    topic_answer,
)
from projects.correction.questions.workflow import run_profiling

pytestmark = pytest.mark.django_db


@pytest.fixture
def node(profiling_taxonomy: TaxonomySnapshot) -> TaxonomyNode:
    return next(
        node for node in TaxonomyNode.for_version(profiling_taxonomy.version) if node.code == FIELD
    )


def draft(node: TaxonomyNode | None = None) -> Question:
    return draft_question(
        method="standard", taxonomy_node_id=node.pk if node else None, factory=FakeAgentFactory()
    )


def profile_factory() -> FakeAgentFactory:
    return FakeAgentFactory(
        scripts={"profiler_field": [field_answer()], "profiler_topic": [topic_answer()]}
    )


@pytest.mark.parametrize("generic", [False, True])
def test_draft_is_unvalidated_and_uses_only_taxonomy_and_method(
    node: TaxonomyNode, generic: bool
) -> None:
    factory = FakeAgentFactory()
    question = draft_question(
        method="standard", taxonomy_node_id=None if generic else node.pk, factory=factory
    )
    assert question.is_generic == generic and question.version == 1
    assert not question.validated and not question.active
    assert {field.key for field in RubricField.for_question(question)} == {
        key.value for key in Criterion
    }
    [call] = factory.calls
    assert call.name == "question_drafter"
    assert call.payload.article is None and call.payload.document is None
    assert all(key.value in call.payload.prompt for key in Criterion)
    assert (node.code in call.payload.prompt) == (not generic)


def test_draft_never_enters_resolution_before_validation_and_activation(node: TaxonomyNode) -> None:
    question = draft(node)
    profile = profile_article(
        article(), factory=profile_factory(), taxonomy_version=node.taxonomy_version
    )
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")
    validated = Question.validate_for_use(question.pk)
    assert validated.version == 2 and validated.validated and not validated.active
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")
    Question.set_active(question.pk, True)
    assert resolve_question(profile, method="standard").question.id == question.pk
    Question.set_active(question.pk, False)
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")


def test_cannot_activate_a_draft_or_validate_an_empty_rubric() -> None:
    question = Question.create(name="Vazia", method="standard", is_generic=True, active=False)
    with pytest.raises(CurationError, match="Valide"):
        Question.set_active(question.pk, True)
    with pytest.raises(CurationError, match="rubrica"):
        Question.validate_for_use(question.pk)
    assert Question.get_by_id(question.pk).version == 1


@pytest.mark.parametrize("generic", [False, True])
def test_activation_conflict_keeps_the_current_question(node: TaxonomyNode, generic: bool) -> None:
    first, second = draft(None if generic else node), draft(None if generic else node)
    Question.validate_for_use(first.pk)
    Question.set_active(first.pk, True)
    Question.validate_for_use(second.pk)
    with pytest.raises(CurationConflict):
        Question.set_active(second.pk, True)
    assert Question.get_by_id(first.pk).active
    assert not Question.get_by_id(second.pk).active


def test_invalid_answers_retry_without_persisting_partial_drafts() -> None:
    factory = FakeAgentFactory(scripts={"question_drafter": [InvalidFor(3)]})
    with pytest.raises(CurationError, match="rascunho válido"):
        draft_question(method="standard", factory=factory)
    assert len(factory.calls) == 3 and Question.for_curation() == []


def test_provider_unavailable_does_not_create_a_question() -> None:
    factory = FakeAgentFactory(scripts={"question_drafter": [LLMUnavailable("503")]})
    with pytest.raises(LLMUnavailable):
        draft_question(method="standard", factory=factory)
    assert len(factory.calls) == 1 and Question.for_curation() == []


def test_draft_and_rubrics_are_created_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    create = RubricField.create
    calls: list[None] = []

    def fail_second(*args: Any, **kwargs: Any) -> RubricField:
        calls.append(None)
        if len(calls) == 2:
            raise ValueError("Falha sintética")
        return create(*args, **kwargs)

    monkeypatch.setattr(RubricField, "create", fail_second)
    with pytest.raises(ValueError, match="sintética"):
        draft()
    assert Question.for_curation() == []


def test_editing_rubric_and_deleting_fields_require_new_validation(node: TaxonomyNode) -> None:
    question = draft(node)
    Question.validate_for_use(question.pk)
    Question.set_active(question.pk, True)
    field = RubricField.for_question(question)[0]
    field.rubric_text = "Contexto revisado."
    RubricField.save_curation(field)
    edited = Question.get_by_id(question.pk)
    assert not edited.validated and not edited.active and edited.version == 2
    Question.validate_for_use(question.pk)
    Question.set_active(question.pk, True)
    RubricField.delete_curation(field.pk, question_id=question.pk)
    assert not Question.get_by_id(question.pk).validated


def test_stale_editor_is_refused(node: TaxonomyNode) -> None:
    original = draft(node)
    revision = original.updated_at.isoformat()
    changed = Question.get_by_id(original.pk)
    changed.name = "Editado por outra pessoa"
    Question.save_curation(changed, revision=revision)
    original.name = "Edição obsoleta"
    with pytest.raises(CurationConflict, match="mudou"):
        Question.save_curation(original, revision=revision)
    assert Question.get_by_id(original.pk).name == changed.name


def persist_run_profile(run: Run) -> None:
    extraction = Extraction.store(run.attempt.sha256, "curation-test", article())
    assert Run.claim_stage(run.pk, Stage.EXTRACTION, "e1") is not None
    assert Run.attach_extraction(run.pk, "e1", extraction)
    Run.complete_stage(run.pk, "e1", RunStatus.EXTRACTED)
    assert Run.claim_stage(run.pk, Stage.PROFILING, "e2") is not None
    run_profiling(str(run.pk), "e2", factory=profile_factory())
    Run.complete_stage(run.pk, "e2", RunStatus.PROFILED)


def test_new_validation_preserves_the_snapshot_of_old_runs(run: Run, node: TaxonomyNode) -> None:
    question = draft(node)
    Question.validate_for_use(question.pk)
    Question.set_active(question.pk, True)
    persist_run_profile(run)
    old_snapshot = Run.get_by_id(run.pk).config_snapshot["question"]
    field = RubricField.for_question(question)[0]
    field.rubric_text = "Rubrica nova, revisada por uma pessoa."
    RubricField.save_curation(field)
    Question.validate_for_use(question.pk)
    Question.set_active(question.pk, True)
    second = Run.create(attempt=run.attempt)
    persist_run_profile(second)
    assert Run.get_by_id(run.pk).config_snapshot["question"] == old_snapshot
    assert old_snapshot["version"] == 2
    new_snapshot = Run.get_by_id(second.pk).config_snapshot["question"]
    assert new_snapshot["version"] == 3
    assert new_snapshot["rubric_fields"][0]["rubric_text"] == field.rubric_text


@pytest.mark.django_db(transaction=True)
def test_resolution_cannot_mix_approved_question_with_concurrent_unreviewed_rubrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = draft()
    Question.validate_for_use(question.pk)
    Question.set_active(question.pk, True)
    original_text = RubricField.for_question(question)[0].rubric_text
    loaded, writer_started, writer_done = Event(), Event(), Event()
    prefetch = query.prefetch_related_objects

    def pause_before_rubrics(instances: list[Question], *lookups: Any) -> None:
        if instances and isinstance(instances[0], Question):
            loaded.set()
            assert writer_started.wait(5)
            assert not writer_done.wait(0.2), "A leitura deve manter a Question travada."
        prefetch(instances, *lookups)

    monkeypatch.setattr(query, "prefetch_related_objects", pause_before_rubrics)

    def read() -> list[QuestionSnapshot]:
        close_old_connections()
        try:
            return Question.resolution_candidates(method="standard", taxonomy_version="", codes=())
        finally:
            connections.close_all()

    def edit() -> None:
        close_old_connections()
        try:
            assert loaded.wait(5)
            field = RubricField.for_question(question)[0]
            field.rubric_text = "Edição ainda não aprovada."
            writer_started.set()
            RubricField.save_curation(field)
            writer_done.set()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        reading, editing = pool.submit(read), pool.submit(edit)
        [snapshot] = reading.result(timeout=10)
        editing.result(timeout=10)
    assert snapshot.version == 2 and snapshot.rubric_fields[0].rubric_text == original_text
    assert writer_done.is_set() and not Question.get_by_id(question.pk).validated
