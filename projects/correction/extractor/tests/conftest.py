"""Fixtures dos testes do extractor."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from django.test import override_settings

from projects.correction.extractor.tests.http_stub import StubServer
from projects.correction.metis.config import settings


@pytest.fixture
def stub_server() -> Iterator[StubServer]:
    server = StubServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def gemini_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Uma chave qualquer: os testes falam com o servidor local, nunca com o Google."""
    monkeypatch.setattr(settings, "gemini_key", "chave-de-teste")
    monkeypatch.setattr(settings, "google_api_key", "chave-de-teste")
    return "chave-de-teste"


@pytest.fixture
def media_root(tmp_path: Path) -> Iterator[Path]:
    """Storage numa pasta temporária, para o teste não gravar no MEDIA_ROOT de verdade."""
    with override_settings(MEDIA_ROOT=tmp_path):
        yield tmp_path
