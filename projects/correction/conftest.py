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
def fake_consolidation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A máquina de estados isola E5; o relatório real tem integração própria."""
    from projects.correction.pipeline.stages import ConsolidationStage, StageContext, StageOutcome

    def consolidate(self: ConsolidationStage, ctx: StageContext) -> StageOutcome:
        return StageOutcome()

    monkeypatch.setattr(ConsolidationStage, "execute", consolidate)


@pytest.fixture
def fake_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os testes do ciclo do Celery isolam E4; o contexto real é coberto na avaliação."""
    from projects.correction.pipeline.stages import EvaluationStage, StageContext, StageOutcome

    def evaluate(self: EvaluationStage, ctx: StageContext) -> StageOutcome:
        return StageOutcome()

    monkeypatch.setattr(EvaluationStage, "execute", evaluate)


@pytest.fixture
def eager_celery(
    fake_extraction: None,
    fake_profiling: None,
    fake_evaluation: None,
    fake_consolidation: None,
    eager_mode: None,
) -> None:
    """Pipeline eager isolado dos estágios reais nos testes da máquina de estados."""


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
