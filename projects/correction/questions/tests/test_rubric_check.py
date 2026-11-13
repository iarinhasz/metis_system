"""Criação atômica de lotes e operações do admin, sem provedores externos."""

from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import RunPurpose, RunStatus, Stage
from projects.correction.questions.curation_errors import CurationConflict, CurationError
from projects.correction.questions.models import Question, RubricField
from projects.correction.questions.rubric_check import start_rubric_check
from projects.correction.questions.tests.rubric_check_helpers import (
    cache_attempt,
    draft,
    sample_attempt,
)

pytestmark = pytest.mark.django_db


def test_batch_freezes_the_draft_without_changing_the_active_question_or_existing_runs(
    run: Run,
    publisher: Mock,
    django_capture_on_commit_callbacks: Any,
) -> None:
    active = draft(active=True)
    source = draft()
    extraction = cache_attempt(run.attempt)
    other = sample_attempt("sample-2")
    batch_id = uuid4()
    with django_capture_on_commit_callbacks(execute=True):
        batch = start_rubric_check(
            source.pk,
            attempt_ids=(run.attempt_id, other.pk),
            revision=source.updated_at.isoformat(),
            batch_id=batch_id,
            actor="admin:curator",
        )
        publisher.assert_not_called()
    assert batch.created and len(batch.runs) == 2
    assert publisher.call_count == 2
    assert {args.args[1] for args in publisher.call_args_list} == {Stage.EXTRACTION}
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED
    assert Run.latest_for_attempt(run.attempt) == run
    assert Question.get_by_id(active.pk).active and Question.get_by_id(active.pk).validated
    assert Question.get_by_id(active.pk).updated_at == active.updated_at
    assert Question.get_by_id(source.pk).updated_at == source.updated_at
    for created in batch.runs:
        assert created.purpose == RunPurpose.RUBRIC_CHECK and created.question_id == source.pk
        assert (
            created.config_snapshot["question"]["rubric_fields"][0]["rubric_text"]
            == "Texto original do rascunho."
        )
        assert RunEvent.for_run(created.pk)[0].actor == "admin:curator"
        assert Run.get_with_events(created.pk, public=True) is None
        if created.attempt_id == run.attempt_id:
            assert created.extraction_id == extraction.pk


def test_repeated_submission_is_idempotent_and_editing_does_not_change_the_snapshot(
    publisher: Mock,
    django_capture_on_commit_callbacks: Any,
) -> None:
    source = draft()
    attempt = sample_attempt("sample")
    revision = source.updated_at.isoformat()
    batch_id = uuid4()
    with django_capture_on_commit_callbacks(execute=True):
        first = start_rubric_check(
            source.pk,
            attempt_ids=(attempt.pk,),
            revision=revision,
            batch_id=batch_id,
            actor="admin:curator",
        )
        [field] = RubricField.for_question(source)
        field.rubric_text = "Texto editado depois do teste."
        RubricField.save_curation(field)
        repeated = start_rubric_check(
            source.pk,
            attempt_ids=(attempt.pk,),
            revision=revision,
            batch_id=batch_id,
            actor="admin:curator",
        )
    assert first.runs[0].pk == repeated.runs[0].pk and not repeated.created
    assert publisher.call_count == 1
    assert (
        Run.get_by_id(first.runs[0].pk).config_snapshot["question"]["rubric_fields"][0][
            "rubric_text"
        ]
        == "Texto original do rascunho."
    )
    with pytest.raises(CurationConflict, match="outra amostra"):
        start_rubric_check(
            source.pk,
            attempt_ids=(uuid4(),),
            revision=revision,
            batch_id=batch_id,
            actor="admin:curator",
        )


@pytest.mark.parametrize(
    "invalid",
    [
        "active",
        "stale",
        "empty",
        "missing_cache",
        "partial_cache",
        "missing_attempt",
        "duplicate",
        "oversize",
    ],
)
def test_invalid_samples_or_drafts_create_no_partial_batch(invalid: str, run: Run) -> None:
    source = draft(active=invalid == "active")
    batch_id = uuid4()
    attempt_ids: tuple[UUID, ...] = (run.attempt_id,)
    if invalid not in {"missing_cache", "partial_cache"}:
        cache_attempt(run.attempt)
    revision = "stale" if invalid == "stale" else source.updated_at.isoformat()
    if invalid == "empty":
        attempt_ids = ()
    elif invalid == "missing_attempt":
        attempt_ids = (run.attempt_id, uuid4())
    elif invalid == "partial_cache":
        attempt_ids = (run.attempt_id, sample_attempt("cached").pk)
    elif invalid == "duplicate":
        attempt_ids = (run.attempt_id, run.attempt_id)
    elif invalid == "oversize":
        attempt_ids = tuple(uuid4() for _ in range(21))
    with pytest.raises(CurationError):
        start_rubric_check(
            source.pk,
            attempt_ids=attempt_ids,
            revision=revision,
            batch_id=batch_id,
            actor="admin:curator",
        )
    assert Run.rubric_check_batch(source.pk, batch_id) == []


def test_empty_rubric_cannot_be_tested() -> None:
    source = Question.create(name="Sem campos", method="standard", is_generic=True, active=False)
    attempt = sample_attempt("sample")
    with pytest.raises(CurationError, match="campo de rubrica"):
        start_rubric_check(
            source.pk,
            attempt_ids=(attempt.pk,),
            revision=source.updated_at.isoformat(),
            batch_id=uuid4(),
            actor="admin:curator",
        )


def test_admin_selects_cached_attempts_and_creates_a_batch_only_on_post(
    admin_client: Client,
    run: Run,
) -> None:
    source = draft()
    attempt = sample_attempt("sample")
    url = reverse("admin:questions_question_rubric_check", args=[source.pk])
    page = admin_client.get(url)
    assert page.status_code == 200
    assert (
        str(attempt.pk) in page.content.decode()
        and str(run.attempt_id) not in page.content.decode()
    )
    form = page.context["form"]
    batch_id = form.initial["batch_id"]
    assert Run.rubric_check_batch(source.pk, batch_id) == []
    data = {
        "revision": form.initial["revision"],
        "batch_id": str(batch_id),
        "attempts": [str(attempt.pk)],
    }
    posted = admin_client.post(url, data)
    expected = reverse("admin:questions_question_rubric_check_results", args=[source.pk, batch_id])
    assert posted.status_code == 302 and posted["Location"] == expected
    assert len(Run.rubric_check_batch(source.pk, batch_id)) == 1
    assert admin_client.post(url, data)["Location"] == expected
    assert len(Run.rubric_check_batch(source.pk, batch_id)) == 1
    result = admin_client.get(expected)
    assert result.status_code == 200 and b"rubric-results" in result.content
    assert "Relatório ainda não disponível" in result.content.decode()
    assert "<script>alert(1)</script>" not in result.content.decode()


def test_admin_action_links_to_sample_selection_without_starting_runs(admin_client: Client) -> None:
    source = draft()
    response = admin_client.post(
        reverse("admin:questions_question_changelist"),
        {
            "action": "rubric_check_selected",
            "_selected_action": [str(source.pk)],
            "index": "0",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse(
        "admin:questions_question_rubric_check", args=[source.pk]
    )


@pytest.mark.parametrize(
    "missing",
    [
        "questions.change_question",
        "attempts.add_run",
        "attempts.view_attempt",
        "attempts.view_run",
        "evaluation.view_finalreport",
    ],
)
def test_launch_requires_permissions_even_on_direct_post(
    admin_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    source = draft()
    monkeypatch.setattr(User, "has_perm", lambda self, perm, obj=None: perm != missing)
    response = admin_client.post(
        reverse("admin:questions_question_rubric_check", args=[source.pk]), {}
    )
    assert response.status_code == 403


def test_results_are_private_and_scoped_to_the_question(
    admin_client: Client, client: Client
) -> None:
    source = draft()
    attempt = sample_attempt("sample")
    batch = start_rubric_check(
        source.pk,
        attempt_ids=(attempt.pk,),
        revision=source.updated_at.isoformat(),
        batch_id=uuid4(),
        actor="admin:curator",
    )
    url = reverse("admin:questions_question_rubric_check_results", args=[source.pk, batch.id])
    assert client.get(url).status_code == 302
    other = draft()
    assert (
        admin_client.get(
            reverse(
                "admin:questions_question_rubric_check_results",
                args=[other.pk, batch.id],
            )
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            reverse(
                "admin:questions_question_rubric_check_results",
                args=[source.pk, uuid4()],
            )
        ).status_code
        == 404
    )


def test_results_require_report_permission(
    admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = draft()
    monkeypatch.setattr(
        User, "has_perm", lambda self, perm, obj=None: perm != "evaluation.view_finalreport"
    )
    assert (
        admin_client.get(
            reverse(
                "admin:questions_question_rubric_check_results",
                args=[source.pk, uuid4()],
            )
        ).status_code
        == 403
    )


def test_launch_post_requires_csrf(admin_user: User) -> None:
    source = draft()
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin_user)
    batch_id = uuid4()
    response = client.post(
        reverse("admin:questions_question_rubric_check", args=[source.pk]),
        {"batch_id": str(batch_id)},
    )
    assert response.status_code == 403
    assert Run.rubric_check_batch(source.pk, batch_id) == []
