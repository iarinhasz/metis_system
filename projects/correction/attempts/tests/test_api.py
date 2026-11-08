"""Testes das rotas de submissão, consulta de runs e decisão do gate."""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any
from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from projects.correction.attempts.models import Article, Run
from projects.correction.attempts.status import STAGES, RunStatus, Stage
from projects.correction.metis.config import settings

PDF_V1 = b"%PDF-1.7\nconteudo de teste\n"


CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], Any]]]]


@pytest.fixture
def authenticated_client(monkeypatch: pytest.MonkeyPatch) -> Client:
    monkeypatch.setattr(settings, "api_token", "token-de-teste")
    return Client(headers={"Authorization": "Bearer token-de-teste"})


@pytest.mark.django_db
def test_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "api_token", "token-de-teste")
    response = Client().post(
        "/api/attempts",
        {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_blocks_when_token_not_configured(
    authenticated_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "api_token", "")
    response = authenticated_client.post(
        "/api/attempts",
        {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_new_attempt_returns_202_and_publishes_after_commit(
    authenticated_client: Client,
    publisher: Mock,
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = authenticated_client.post(
            "/api/attempts",
            {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["attempt_number"] == 1
    assert body["status"] == "received"
    publisher.assert_called_once_with(body["run_id"], Stage.EXTRACTION)


@pytest.mark.django_db
def test_same_file_returns_existing_ids(
    authenticated_client: Client,
    publisher: Mock,
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        first = authenticated_client.post(
            "/api/attempts",
            {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
        )
        second = authenticated_client.post(
            "/api/attempts",
            {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
        )

    assert first.status_code == 202
    assert second.status_code == 200
    assert first.json()["attempt_id"] == second.json()["attempt_id"]
    assert first.json()["run_id"] == second.json()["run_id"]
    publisher.assert_called_once()


@pytest.mark.django_db
def test_new_file_creates_next_version_and_supersedes_pending_run(
    authenticated_client: Client,
) -> None:
    first = authenticated_client.post(
        "/api/attempts",
        {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
    )
    second = authenticated_client.post(
        "/api/attempts",
        {
            "external_id": "artigo-1",
            "file": SimpleUploadedFile("artigo.pdf", b"%PDF-1.7\nversao 2\n"),
        },
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["attempt_number"] == 2
    first_run = Run.get_by_id(first.json()["run_id"])
    assert first_run.status == "superseded"


@pytest.mark.django_db
def test_rejects_non_pdf(authenticated_client: Client) -> None:
    response = authenticated_client.post(
        "/api/attempts",
        {
            "external_id": "artigo-1",
            "file": SimpleUploadedFile("artigo.txt", b"texto comum"),
        },
    )

    assert response.status_code == 400
    assert Article.find_by_external_id("artigo-1") is None


@pytest.mark.django_db
def test_rejects_oversized_file(
    authenticated_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    response = authenticated_client.post(
        "/api/attempts",
        {
            "external_id": "artigo-1",
            "file": SimpleUploadedFile("artigo.pdf", b"%PDF-" + b"x" * (1024 * 1024)),
        },
    )

    assert response.status_code == 400
    assert Article.find_by_external_id("artigo-1") is None


@pytest.mark.django_db
def test_run_status_lists_events_in_order(authenticated_client: Client) -> None:
    submitted = authenticated_client.post(
        "/api/attempts",
        {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
    ).json()
    run_id = submitted["run_id"]
    Run.claim_stage(run_id, Stage.EXTRACTION, "task-1")

    response = authenticated_client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "extracting"
    assert [event["to_status"] for event in body["events"]] == ["received", "extracting"]


def at_gate(run: Run) -> Run:
    """Leva o run até o gate humano pelo RunManagement, sem rodar o Celery."""
    for spec in STAGES[:3]:
        Run.claim_stage(run.pk, spec.stage, "task-1")
        done = RunStatus.WAITING_HUMAN_REVIEW if spec.stage == Stage.INTEGRITY else spec.completed
        Run.complete_stage(run.pk, "task-1", done)
    return Run.get_by_id(run.pk)


def decision_url(run_id: Any) -> str:
    return f"/api/runs/{run_id}/decision"


@pytest.mark.django_db
def test_decision_continue_publishes_evaluation(
    authenticated_client: Client,
    publisher: Mock,
    django_capture_on_commit_callbacks: CaptureOnCommit,
    run: Run,
) -> None:
    gated = at_gate(run)

    with django_capture_on_commit_callbacks(execute=True):
        response = authenticated_client.post(
            decision_url(gated.pk),
            {"decision": "continue", "note": "Citação conferida"},
            content_type="application/json",
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "integrity_checked"
    assert body["events"][-1]["actor"] == "service-api"
    assert body["events"][-1]["payload"] == {"decision": "continue", "note": "Citação conferida"}
    publisher.assert_called_once_with(str(gated.pk), Stage.EVALUATION)


@pytest.mark.django_db
def test_decision_close_publishes_nothing(
    authenticated_client: Client,
    publisher: Mock,
    django_capture_on_commit_callbacks: CaptureOnCommit,
    run: Run,
) -> None:
    gated = at_gate(run)

    with django_capture_on_commit_callbacks(execute=True):
        response = authenticated_client.post(
            decision_url(gated.pk), {"decision": "close"}, content_type="application/json"
        )

    assert response.status_code == 200
    assert response.json()["status"] == "closed_by_reviewer"
    publisher.assert_not_called()


@pytest.mark.django_db
def test_decision_outside_gate_returns_409(authenticated_client: Client, run: Run) -> None:
    response = authenticated_client.post(
        decision_url(run.pk), {"decision": "continue"}, content_type="application/json"
    )

    assert response.status_code == 409
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED


@pytest.mark.django_db
def test_decision_for_unknown_run_returns_404(authenticated_client: Client) -> None:
    response = authenticated_client.post(
        decision_url(uuid.uuid4()), {"decision": "close"}, content_type="application/json"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_decision_rejects_unknown_value(authenticated_client: Client, run: Run) -> None:
    response = authenticated_client.post(
        decision_url(at_gate(run).pk), {"decision": "talvez"}, content_type="application/json"
    )

    assert response.status_code == 422
    assert Run.get_by_id(run.pk).status == RunStatus.WAITING_HUMAN_REVIEW


@pytest.mark.django_db
def test_decision_requires_token(monkeypatch: pytest.MonkeyPatch, run: Run) -> None:
    monkeypatch.setattr(settings, "api_token", "token-de-teste")
    response = Client().post(
        decision_url(at_gate(run).pk), {"decision": "close"}, content_type="application/json"
    )

    assert response.status_code == 401
    assert Run.get_by_id(run.pk).status == RunStatus.WAITING_HUMAN_REVIEW
