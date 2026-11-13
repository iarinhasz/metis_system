"""Base dos estágios (Template Method); E1 e E2 reais, E3 a E5 ainda stubs.

Ciclo de uma task: claim → execute() → complete → publica o próximo estágio após o commit.
Cada estágio implementa só o execute(). A posse do run é pelo id da task Celery, que se
mantém em retry() e na reentrega, de modo que a mesma mensagem retoma o estágio.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from celery import Task
from celery.utils.time import get_exponential_backoff_interval
from django.db import transaction

from projects.correction.agents.factory import AgentFactory
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import (
    NEXT_STAGE,
    STAGE_BY_NAME,
    RunStatus,
    Stage,
    StageSpec,
)
from projects.correction.extractor.attempt_extraction import extract_attempt, extraction_payload
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.session import AgnoSession, DocumentSession
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import StageError, TransientStageError
from projects.correction.pipeline.publishing import publish_stage_on_commit
from projects.correction.pipeline.usage import DatabaseUsageSink
from projects.correction.questions.workflow import run_profiling

logger = logging.getLogger(__name__)

# O Task do Celery só é genérico nos stubs (celery-types), não em tempo de execução.
if TYPE_CHECKING:
    _TaskBase = Task[[str], None]
else:
    _TaskBase = Task


@dataclass(frozen=True)
class StageContext:
    """Entrada de um estágio, só com ids: o que mais for preciso é lido do banco."""

    run_id: str
    attempt_id: str
    task_id: str
    stage: Stage


@dataclass(frozen=True)
class StageOutcome:
    """Resultado de um estágio. `halt` pausa o run no gate humano (só o E3 usa)."""

    payload: dict[str, Any] = field(default_factory=dict)
    halt: bool = False


class StageTask(_TaskBase):
    """Task Celery de um estágio; as subclasses definem `stage` e `execute()`."""

    stage: ClassVar[Stage]
    typing = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.name = STAGE_BY_NAME[cls.stage].task_name

    @property
    def spec(self) -> StageSpec:
        return STAGE_BY_NAME[self.stage]

    def execute(self, ctx: StageContext) -> StageOutcome:
        raise NotImplementedError

    def run(self, run_id: str) -> None:
        task_id = self.request.id
        if not task_id:
            raise RuntimeError("A task de estágio precisa de um id para registrar a posse.")
        run = Run.claim_stage(run_id, self.stage, task_id)
        if run is None:
            logger.info("Claim negado: run=%s stage=%s task=%s", run_id, self.stage, task_id)
            return

        ctx = StageContext(
            run_id=str(run.pk), attempt_id=str(run.attempt_id), task_id=task_id, stage=self.stage
        )
        try:
            outcome = self.execute(ctx)
        except TransientStageError as exc:
            self._retry_or_fail(ctx, exc)
            return
        except StageError as exc:
            self._fail(ctx, exc.failure_status, exc)
            return
        except Exception as exc:
            logger.exception("Erro inesperado: run=%s stage=%s", ctx.run_id, ctx.stage)
            self._fail(ctx, RunStatus.ERROR_UNEXPECTED, exc)
            return
        self._complete(ctx, outcome)

    def _complete(self, ctx: StageContext, outcome: StageOutcome) -> None:
        target = RunStatus.WAITING_HUMAN_REVIEW if outcome.halt else self.spec.completed
        with transaction.atomic():
            run = Run.complete_stage(ctx.run_id, ctx.task_id, target, payload=outcome.payload)
            if run is None:
                logger.info("Posse perdida antes de concluir: run=%s", ctx.run_id)
                return
            next_stage = NEXT_STAGE[self.stage]
            if not outcome.halt and next_stage is not None:
                publish_stage_on_commit(ctx.run_id, next_stage)

    def _fail(self, ctx: StageContext, status: RunStatus, exc: BaseException) -> None:
        Run.fail_stage(
            ctx.run_id,
            ctx.task_id,
            status,
            error=_describe(exc),
            payload={"exception": type(exc).__name__, "retries": self.request.retries or 0},
        )

    def _retry_or_fail(self, ctx: StageContext, exc: TransientStageError) -> None:
        retries = self.request.retries or 0
        if retries >= settings.stage_max_retries:
            self._fail(ctx, exc.failure_status, exc)
            return
        if not Run.is_owned_by(ctx.run_id, ctx.task_id):
            logger.info("Posse perdida antes do retry: run=%s", ctx.run_id)
            return
        countdown = get_exponential_backoff_interval(
            factor=settings.stage_retry_backoff_seconds,
            retries=retries,
            maximum=settings.stage_retry_backoff_max_seconds,
            full_jitter=True,
        )
        Run.record_retry(
            ctx.run_id,
            ctx.task_id,
            retries + 1,
            {
                "error": _describe(exc),
                "exception": type(exc).__name__,
                "wait_seconds": countdown,
            },
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=settings.stage_max_retries)


def _describe(exc: BaseException) -> str:
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


class ExtractionStage(StageTask):
    stage = Stage.EXTRACTION

    def execute(self, ctx: StageContext) -> StageOutcome:
        def open_session(config: DocumentConfig, pdf: bytes) -> DocumentSession:
            return AgnoSession(
                config,
                pdf,
                run_id=ctx.run_id,
                usage_sink=DatabaseUsageSink(),
                task_id=ctx.task_id,
            )

        extraction, reused = extract_attempt(ctx.attempt_id, opener=open_session)
        Run.attach_extraction(ctx.run_id, ctx.task_id, extraction)
        return StageOutcome(payload=extraction_payload(extraction, reused=reused))


class ProfilingStage(StageTask):
    stage = Stage.PROFILING

    def execute(self, ctx: StageContext) -> StageOutcome:
        result = run_profiling(
            ctx.run_id,
            ctx.task_id,
            factory=AgentFactory(ctx.run_id, ctx.stage, DatabaseUsageSink(), task_id=ctx.task_id),
        )
        return StageOutcome(payload=result.model_dump(mode="json"))


class IntegrityStage(StageTask):
    stage = Stage.INTEGRITY

    def execute(self, ctx: StageContext) -> StageOutcome:
        # Stub até o M4: o risco é sempre baixo e o run segue sem passar pelo gate.
        return StageOutcome(payload={"risk": "low"})


class EvaluationStage(StageTask):
    stage = Stage.EVALUATION

    def execute(self, ctx: StageContext) -> StageOutcome:
        return StageOutcome()


class ConsolidationStage(StageTask):
    stage = Stage.CONSOLIDATION

    def execute(self, ctx: StageContext) -> StageOutcome:
        return StageOutcome()
