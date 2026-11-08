"""Testes do healthcheck do container."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_reports_ok() -> None:
    response = Client().get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_reports_unavailable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("projects.correction.metis.api.database_is_available", lambda: False)

    response = Client().get("/health/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
