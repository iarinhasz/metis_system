"""Operações transacionais para tentativas e execuções."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models, transaction
from django.utils import timezone

from projects.correction.attempts.status import (
    CHECKPOINTS,
    FINAL,
    RECOVERABLE,
    RUNNING,
    STAGE_BY_NAME,
    STAGE_BY_RUNNING_STATUS,
    STAGE_FAILURES,
    TRANSITIONS,
    HumanDecision,
    RunStatus,
    Stage,
)

if TYPE_CHECKING:
    from projects.correction.attempts.models import Article, Attempt, Run


class InvalidTransition(ValueError):
    """Indica uma transição não prevista na máquina de estados."""


class RunConflict(ValueError):
    """Indica uma operação válida somente em outro estado do run."""


class AttemptManagement(models.Manager["Attempt"]):
    """Cria versões do artigo com hash e número de tentativa protegidos."""

    def find_by_sha256(self, article: Article, sha256: str) -> Attempt | None:
        return self.filter(article=article, sha256=sha256).first()

    @transaction.atomic
    def create_next(
        self,
        article: Article,
        *,
        sha256: str,
        **fields: Any,
    ) -> tuple[Attempt, bool]:
        locked_article = type(article).objects.select_for_update().get(pk=article.pk)
        existing = self.find_by_sha256(locked_article, sha256)
        if existing:
            return existing, False

        latest = self.filter(article=locked_article).aggregate(
            max_number=models.Max("attempt_number")
        )
        attempt = self.create(
            article=locked_article,
            attempt_number=(latest["max_number"] or 0) + 1,
            sha256=sha256,
            **fields,
        )
        from projects.correction.attempts.models import Run

        Run.objects.supersede_other_attempts(locked_article, attempt)
        return attempt, True


class RunManagement(models.Manager["Run"]):
    """Único ponto de escrita de status e eventos de Run."""

    @transaction.atomic
    def create(self, **kwargs: Any) -> Run:
        actor = kwargs.pop("actor", "pipeline")
        if RunStatus(kwargs.get("status", RunStatus.RECEIVED)) != RunStatus.RECEIVED:
            raise InvalidTransition("Um Run novo deve começar no checkpoint received.")
        kwargs["status"] = RunStatus.RECEIVED
        kwargs["version"] = 1
        run = super().create(**kwargs)
        self._append_event(
            run,
            event_type="transition",
            from_status="",
            to_status=run.status,
            actor=actor,
            event_key=f"{run.pk}:{run.version}",
        )
        return run

    def _locked(self, run_id: Any) -> Run:
        return self.select_for_update().get(pk=run_id)

    @staticmethod
    def _append_event(
        run: Run,
        *,
        event_type: str,
        from_status: str = "",
        to_status: str = "",
        actor: str = "pipeline",
        stage: str = "",
        task_id: str = "",
        payload: dict[str, Any] | None = None,
        event_key: str,
    ) -> None:
        from projects.correction.attempts.models import RunEvent

        RunEvent.objects.get_or_create(
            event_key=event_key,
            defaults={
                "run": run,
                "event_type": event_type,
                "from_status": from_status,
                "to_status": to_status,
                "actor": actor,
                "stage": stage,
                "task_id": task_id,
                "payload": payload or {},
            },
        )

    def _transition(
        self,
        run: Run,
        to_status: RunStatus,
        *,
        actor: str = "pipeline",
        task_id: str = "",
        payload: dict[str, Any] | None = None,
        updates: dict[str, Any] | None = None,
    ) -> Run:
        from_status = RunStatus(run.status)
        if to_status not in TRANSITIONS[from_status]:
            raise InvalidTransition(f"Transição não permitida: {from_status} → {to_status}.")
        run.status = to_status
        run.version += 1
        for field, value in (updates or {}).items():
            setattr(run, field, value)
        run.updated_at = timezone.now()
        run.save(update_fields=["status", "version", "updated_at", *(updates or {}).keys()])
        self._append_event(
            run,
            event_type="transition",
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            stage=run.stage,
            task_id=task_id,
            payload=payload,
            event_key=f"{run.pk}:{run.version}",
        )
        return run

    @transaction.atomic
    def claim_stage(self, run_id: Any, stage: Stage | str, task_id: str) -> Run | None:
        spec = STAGE_BY_NAME[Stage(stage)]
        run = self._locked(run_id)
        status = RunStatus(run.status)

        if status == spec.checkpoint:
            prior_claims = run.stage_claims if run.stage == spec.stage else 0
            return self._transition(
                run,
                spec.running,
                task_id=task_id,
                updates={
                    "stage": spec.stage,
                    "current_task_id": task_id,
                    "stage_started_at": timezone.now(),
                    "stage_claims": prior_claims + 1,
                    "publish_count": 0,
                },
            )

        if status == spec.running and run.current_task_id == task_id and run.stage == spec.stage:
            run.stage_claims += 1
            run.stage_started_at = timezone.now()
            run.updated_at = timezone.now()
            run.save(update_fields=["stage_claims", "stage_started_at", "updated_at"])
            return run
        return None

    @transaction.atomic
    def complete_stage(
        self,
        run_id: Any,
        task_id: str,
        to_status: RunStatus | str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> Run | None:
        run = self._locked(run_id)
        status = RunStatus(run.status)
        if status not in RUNNING or run.current_task_id != task_id:
            return None
        target = RunStatus(to_status)
        if target not in {
            STAGE_BY_RUNNING_STATUS[status].completed,
            RunStatus.WAITING_HUMAN_REVIEW,
        }:
            raise InvalidTransition(f"Destino inválido para conclusão do estágio: {target}.")
        return self._transition(
            run,
            target,
            task_id=task_id,
            payload=payload,
            updates={"current_task_id": None, "stage_started_at": None},
        )

    @transaction.atomic
    def fail_stage(
        self,
        run_id: Any,
        task_id: str,
        to_status: RunStatus | str,
        *,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> Run | None:
        run = self._locked(run_id)
        if RunStatus(run.status) not in RUNNING or run.current_task_id != task_id:
            return None
        target = RunStatus(to_status)
        if target not in STAGE_FAILURES:
            raise InvalidTransition(f"Destino não é uma falha de estágio: {target}.")
        event_payload = {**(payload or {}), "error": error}
        return self._transition(
            run,
            target,
            task_id=task_id,
            payload=event_payload,
            updates={"last_error": error, "current_task_id": None, "stage_started_at": None},
        )

    @transaction.atomic
    def record_retry(
        self, run_id: Any, task_id: str, retry_number: int, payload: dict[str, Any]
    ) -> None:
        run = self._locked(run_id)
        self._append_event(
            run,
            event_type="retry_scheduled",
            from_status=run.status,
            to_status=run.status,
            actor="pipeline",
            stage=run.stage,
            task_id=task_id,
            payload=payload,
            event_key=f"{run.pk}:retry:{task_id}:{retry_number}",
        )

    @transaction.atomic
    def decide(
        self,
        run_id: Any,
        decision: HumanDecision | str,
        *,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> Run:
        run = self._locked(run_id)
        if RunStatus(run.status) != RunStatus.WAITING_HUMAN_REVIEW:
            raise RunConflict("O run não está aguardando revisão humana.")
        decision = HumanDecision(decision)
        target = (
            RunStatus.INTEGRITY_CHECKED
            if decision == HumanDecision.CONTINUE
            else RunStatus.CLOSED_BY_REVIEWER
        )
        return self._transition(
            run,
            target,
            actor=actor,
            payload={**(payload or {}), "decision": decision},
        )

    @transaction.atomic
    def recover(self, run_id: Any, *, actor: str) -> Run:
        run = self._locked(run_id)
        if RunStatus(run.status) not in RECOVERABLE:
            raise RunConflict("Somente runs recuperáveis podem ser reprocessados.")
        if not run.stage:
            raise RunConflict("O run não registra qual estágio deve ser retomado.")
        checkpoint = STAGE_BY_NAME[Stage(run.stage)].checkpoint
        return self._transition(
            run,
            checkpoint,
            actor=actor,
            updates={"current_task_id": None, "stage_started_at": None, "last_error": ""},
        )

    @transaction.atomic
    def release_stale(self, run_id: Any, *, actor: str = "reconciler") -> Run:
        run = self._locked(run_id)
        status = RunStatus(run.status)
        if status not in RUNNING:
            raise RunConflict("Somente um estágio em execução pode ser liberado.")
        checkpoint = STAGE_BY_RUNNING_STATUS[status].checkpoint
        return self._transition(
            run,
            checkpoint,
            actor=actor,
            task_id=run.current_task_id or "",
            updates={"current_task_id": None, "stage_started_at": None},
        )

    @transaction.atomic
    def mark_republished(self, run_id: Any, *, payload: dict[str, Any] | None = None) -> Run:
        run = self._locked(run_id)
        if RunStatus(run.status) not in CHECKPOINTS:
            raise RunConflict("Somente runs em checkpoint podem ser republicados.")
        run.publish_count += 1
        run.updated_at = timezone.now()
        run.save(update_fields=["publish_count", "updated_at"])
        self._append_event(
            run,
            event_type="republished",
            from_status=run.status,
            to_status=run.status,
            actor="reconciler",
            stage=run.stage,
            payload=payload,
            event_key=f"{run.pk}:republished:{run.publish_count}",
        )
        return run

    @transaction.atomic
    def supersede_other_attempts(self, article: Article, current_attempt: Attempt) -> int:
        runs = (
            self.select_for_update()
            .filter(attempt__article=article)
            .exclude(attempt=current_attempt)
            .exclude(status__in=[status.value for status in FINAL])
            .order_by("pk")
        )
        count = 0
        for run in runs:
            self._transition(
                run,
                RunStatus.SUPERSEDED,
                actor="pipeline",
                task_id=run.current_task_id or "",
                updates={"current_task_id": None, "stage_started_at": None},
            )
            count += 1
        return count
