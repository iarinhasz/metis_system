"""Fixtures compartilhadas pelos testes do Metis."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from projects.correction.attempts.models import Article, Attempt, Run
from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.models import Extraction
from projects.correction.metis.celery import app


@pytest.fixture
def publisher(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Troca o envio ao broker por um mock, para o teste ver o que seria publicado."""
    mock = Mock()
    monkeypatch.setattr("projects.correction.pipeline.publishing.publish_stage", mock)
    return mock


@pytest.fixture
def fake_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Troca a extração do E1 (chamadas ao modelo) por uma fixa, guardada no banco."""

    def extract(attempt_id: object, **kwargs: object) -> tuple[Extraction, bool]:
        attempt = Attempt.get_by_id(attempt_id)
        section = ExtractedSection(
            id="sec_1",
            title="Resumo",
            level=1,
            parent_id=None,
            key="abstract",
            text="Resumo do artigo.",
            has_footnotes=False,
            coverage=None,
            fidelity=None,
        )
        article = ExtractedArticle(
            title="Artigo", authors=(), language="pt", model="fake/modelo", sections=(section,)
        )
        return Extraction.store(attempt.sha256, "teste", article), False

    monkeypatch.setattr("projects.correction.pipeline.stages.extract_attempt", extract)


@pytest.fixture
def eager_mode() -> Iterator[None]:
    """Roda as tasks na hora, no mesmo processo; as fixtures escolhem os provedores.

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
def fake_profiling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os testes da máquina de estados isolam o E2; o workflow tem integração própria."""
    from projects.correction.pipeline.stages import ProfilingStage, StageContext, StageOutcome

    def profile(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        return StageOutcome()

    monkeypatch.setattr(ProfilingStage, "execute", profile)


@pytest.fixture
def eager_celery(fake_extraction: None, fake_profiling: None, eager_mode: None) -> None:
    """Pipeline eager com os provedores de E1 e E2 substituídos nos testes de orquestração."""


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
