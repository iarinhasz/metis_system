"""Testes das rotas de submissão e consulta de runs."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any
from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.attempts.status import Stage
from projects.correction.metis.config import settings

PDF_V1 = b"%PDF-1.7\nconteudo de teste\n"


CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], Any]]]]


@pytest.fixture
def publisher(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock = Mock()
    monkeypatch.setattr("projects.correction.pipeline.publishing.publish_stage", mock)
    return mock


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
    first_run = Run.objects.get(pk=first.json()["run_id"])
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
    assert Article.objects.count() == 0


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
    assert Attempt.objects.count() == 0


@pytest.mark.django_db
def test_run_status_lists_events_in_order(authenticated_client: Client) -> None:
    submitted = authenticated_client.post(
        "/api/attempts",
        {"external_id": "artigo-1", "file": SimpleUploadedFile("artigo.pdf", PDF_V1)},
    ).json()
    run = Run.objects.get(pk=submitted["run_id"])
    Run.objects.claim_stage(run.pk, Stage.EXTRACTION, "task-1")

    response = authenticated_client.get(f"/api/runs/{run.pk}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "extracting"
    assert [event["to_status"] for event in body["events"]] == ["received", "extracting"]
