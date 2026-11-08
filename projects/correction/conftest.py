"""Fixtures compartilhadas pelos testes do Metis."""

from collections.abc import Iterator

import pytest

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.metis.celery import app


@pytest.fixture
def eager_celery() -> Iterator[None]:
    """Roda as tasks na hora, no mesmo processo.

    Sem propagar exceções: com propagate, o Celery repassa o Retry ao chamador em vez de
    reexecutar a task. O StageTask registra no run todo erro do execute(), e os testes
    olham o status.
    """
    previous = (app.conf.task_always_eager, app.conf.task_eager_propagates)
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = False
    yield
    app.conf.task_always_eager, app.conf.task_eager_propagates = previous


@pytest.fixture
def run() -> Run:
    """Um run novo, no checkpoint `received`, de um artigo com uma versão."""
    article = Article.get_or_create_by_external_id("artigo-1")
    attempt, _ = Attempt.create_next(
        article,
        sha256="a" * 64,
        file="submissions/artigo-1/paper.pdf",
        original_filename="paper.pdf",
        size_bytes=128,
        submitted_by="test-service",
    )
    return Run.create(attempt=attempt)
