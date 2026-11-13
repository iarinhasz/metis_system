"""Consultas e operações transacionais de Run: o único ponto que muda o status."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import transaction
from django.utils import timezone

from projects.correction.attempts.status import (
    CHECKPOINTS,
    FINAL,
    RECOVERABLE,
    RUNNING,
    STAGE_BY_CHECKPOINT,
    STAGE_BY_NAME,
    STAGE_BY_RUNNING_STATUS,
    STAGE_FAILURES,
    TRANSITIONS,
    HumanDecision,
    RunPurpose,
    RunStatus,
    Stage,
)

if TYPE_CHECKING:
    from datetime import datetime

    from django.db import models

    from projects.correction.attempts.models import Article, Attempt, Run, RunEvent
    from projects.correction.extractor.models import Extraction


class InvalidTransition(ValueError):
    """Indica uma transição não prevista na máquina de estados."""


class RunConflict(ValueError):
    """Indica uma operação válida somente em outro estado do run."""


def _run_event() -> type[RunEvent]:
    from projects.correction.attempts.models import RunEvent

    return RunEvent


def _values(statuses: frozenset[RunStatus]) -> list[str]:
    return sorted(status.value for status in statuses)


class RunManagement:
    """Herdado por `Run`. Uso: `Run.claim_stage(run_id, stage, task_id)`.

    Toda mudança de status passa por aqui: valida a transição, trava a linha e grava o
    `RunEvent` na mesma transação.
    """

    objects: ClassVar[models.Manager[Run]]

    @classmethod
    def get_by_id(cls, run_id: Any) -> Run:
        return cls.objects.get(pk=run_id)

    @classmethod
    def get_with_events(cls, run_id: Any, *, public: bool = False) -> Run | None:
        """Run com a attempt e a trilha de eventos já carregadas, sem N+1."""
        runs = cls.objects.filter(purpose=RunPurpose.EVALUATION) if public else cls.objects.all()
        return runs.select_related("attempt").prefetch_related("events").filter(pk=run_id).first()

    @classmethod
    def latest_for_attempt(cls, attempt: Attempt) -> Run | None:
        return (
            cls.objects.filter(attempt=attempt, purpose=RunPurpose.EVALUATION)
            .order_by("-created_at", "-pk")
            .first()
        )

    @classmethod
    def for_profiling(cls, run_id: Any, task_id: str) -> Run:
        run = (
            cls.objects.select_related("extraction")
            .filter(pk=run_id, current_task_id=task_id, status=RunStatus.PROFILING)
            .first()
        )
        if run is None:
            raise RunConflict("A task perdeu a posse do perfil.")
        return run

    @classmethod
    @transaction.atomic
    def initialize_profiling(cls, run_id: Any, task_id: str, snapshot: dict[str, Any]) -> Run:
        run = cls._locked(run_id)
        cls._require_profiling_owner(run, task_id)
        if "profiling" not in run.config_snapshot:
            run.config_snapshot = {**run.config_snapshot, **snapshot}
            run.updated_at = timezone.now()
            run.save(update_fields=["config_snapshot", "updated_at"])
        return run

    @classmethod
    @transaction.atomic
    def checkpoint_profile(
        cls,
        run_id: Any,
        task_id: str,
        key: str,
        value: Any,
        *,
        prompt_versions: dict[str, str],
        question_id: Any = None,
    ) -> None:
        """Persiste um passo, sem perder os anteriores e sem aceitar uma task obsoleta."""
        run = cls._locked(run_id)
        cls._require_profiling_owner(run, task_id)
        run.profile = {**run.profile, key: value}
        run.config_snapshot = {
            **run.config_snapshot,
            "prompt_versions": {
                **run.config_snapshot.get("prompt_versions", {}),
                **prompt_versions,
            },
        }
        fields = ["profile", "config_snapshot", "updated_at"]
        if question_id is not None:
            run.question_id = question_id
            run.config_snapshot["question"] = value["question"]
            fields.append("question")
        run.updated_at = timezone.now()
        run.save(update_fields=fields)

    @staticmethod
    def _require_profiling_owner(run: Run, task_id: str) -> None:
        if run.status != RunStatus.PROFILING or run.current_task_id != task_id:
            raise RunConflict("A task perdeu a posse do perfil.")

    @classmethod
    @transaction.atomic
    def record_profiling_prompt(cls, run_id: Any, task_id: str, name: str, version: str) -> None:
        """Registra a versão antes da chamada, inclusive quando o provedor vai falhar."""
        run = cls._locked(run_id)
        cls._require_profiling_owner(run, task_id)
        run.config_snapshot = {
            **run.config_snapshot,
            "prompt_versions": {**run.config_snapshot.get("prompt_versions", {}), name: version},
        }
        run.updated_at = timezone.now()
        run.save(update_fields=["config_snapshot", "updated_at"])

    @classmethod
    def attach_extraction(cls, run_id: Any, task_id: str, extraction: Extraction) -> bool:
        """Liga a extração ao run, só se o E1 ainda está com esta task (posse)."""
        updated = cls.objects.filter(
            pk=run_id, current_task_id=task_id, status=RunStatus.EXTRACTING
        ).update(extraction=extraction, updated_at=timezone.now())
        return updated == 1

    @classmethod
    def is_owned_by(cls, run_id: Any, task_id: str) -> bool:
        """Diz se a task ainda é a dona do estágio em execução."""
        return cls.objects.filter(pk=run_id, current_task_id=task_id).exists()

    @classmethod
    def ids_stalled_at_checkpoint(cls, *, before: datetime) -> list[Any]:
        """Runs num checkpoint sem mudança desde `before`: a publicação pode ter se perdido."""
        return list(
            cls.objects.filter(status__in=_values(CHECKPOINTS), updated_at__lt=before)
            .order_by("updated_at")
            .values_list("pk", flat=True)
        )

    @classmethod
    def ids_with_stale_stage(cls, *, before: datetime) -> list[Any]:
        """Runs com um estágio rodando desde antes de `before`: o worker pode ter morrido."""
        return list(
            cls.objects.filter(status__in=_values(RUNNING), stage_started_at__lt=before)
            .order_by("stage_started_at")
            .values_list("pk", flat=True)
        )

    @classmethod
    def lock_if_stalled_at_checkpoint(cls, run_id: Any, *, before: datetime) -> Run | None:
        """Trava o run se ele continua parado no checkpoint; se andou, devolve None."""
        return (
            cls.objects.select_for_update()
            .filter(pk=run_id, status__in=_values(CHECKPOINTS), updated_at__lt=before)
            .first()
        )

    @classmethod
    def lock_if_stage_is_stale(cls, run_id: Any, *, before: datetime) -> Run | None:
        """Trava o run se o estágio continua travado; se andou, devolve None."""
        return (
            cls.objects.select_for_update()
            .filter(pk=run_id, status__in=_values(RUNNING), stage_started_at__lt=before)
            .first()
        )

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        attempt: Attempt,
        actor: str = "pipeline",
        purpose: RunPurpose | str = RunPurpose.EVALUATION,
        config_snapshot: dict[str, Any] | None = None,
    ) -> Run:
        """Cria o run no checkpoint `received`, já com o primeiro evento."""
        run = cls.objects.create(
            attempt=attempt,
            status=RunStatus.RECEIVED,
            version=1,
            purpose=RunPurpose(purpose),
            config_snapshot=config_snapshot or {},
        )
        _run_event().append(
            run,
            event_type="transition",
            from_status="",
            to_status=run.status,
            actor=actor,
            event_key=f"{run.pk}:{run.version}",
        )
        return run

    @classmethod
    def _locked(cls, run_id: Any) -> Run:
        return cls.objects.select_for_update().get(pk=run_id)

    @classmethod
    def _transition(
        cls,
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
        _run_event().append(
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

    @classmethod
    @transaction.atomic
    def claim_stage(cls, run_id: Any, stage: Stage | str, task_id: str) -> Run | None:
        spec = STAGE_BY_NAME[Stage(stage)]
        run = cls._locked(run_id)
        status = RunStatus(run.status)

        if status == spec.checkpoint:
            prior_claims = run.stage_claims if run.stage == spec.stage else 0
            return cls._transition(
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

    @classmethod
    @transaction.atomic
    def complete_stage(
        cls,
        run_id: Any,
        task_id: str,
        to_status: RunStatus | str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> Run | None:
        run = cls._locked(run_id)
        status = RunStatus(run.status)
        if status not in RUNNING or run.current_task_id != task_id:
            return None
        target = RunStatus(to_status)
        if target not in {
            STAGE_BY_RUNNING_STATUS[status].completed,
            RunStatus.WAITING_HUMAN_REVIEW,
        }:
            raise InvalidTransition(f"Destino inválido para conclusão do estágio: {target}.")
        return cls._transition(
            run,
            target,
            task_id=task_id,
            payload=payload,
            updates={"current_task_id": None, "stage_started_at": None},
        )

    @classmethod
    @transaction.atomic
    def fail_stage(
        cls,
        run_id: Any,
        task_id: str,
        to_status: RunStatus | str,
        *,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> Run | None:
        run = cls._locked(run_id)
        if RunStatus(run.status) not in RUNNING or run.current_task_id != task_id:
            return None
        target = RunStatus(to_status)
        if target not in STAGE_FAILURES:
            raise InvalidTransition(f"Destino não é uma falha de estágio: {target}.")
        event_payload = {**(payload or {}), "error": error}
        return cls._transition(
            run,
            target,
            task_id=task_id,
            payload=event_payload,
            updates={"last_error": error, "current_task_id": None, "stage_started_at": None},
        )

    @classmethod
    @transaction.atomic
    def record_retry(
        cls, run_id: Any, task_id: str, retry_number: int, payload: dict[str, Any]
    ) -> None:
        run = cls._locked(run_id)
        _run_event().append(
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

    @classmethod
    @transaction.atomic
    def decide(
        cls,
        run_id: Any,
        decision: HumanDecision | str,
        *,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> Run:
        run = cls._locked(run_id)
        if RunStatus(run.status) != RunStatus.WAITING_HUMAN_REVIEW:
            raise RunConflict("O run não está aguardando revisão humana.")
        decision = HumanDecision(decision)
        target = (
            RunStatus.INTEGRITY_CHECKED
            if decision == HumanDecision.CONTINUE
            else RunStatus.CLOSED_BY_REVIEWER
        )
        return cls._transition(
            run,
            target,
            actor=actor,
            payload={**(payload or {}), "decision": decision},
        )

    @classmethod
    @transaction.atomic
    def recover(cls, run_id: Any, *, actor: str) -> Run:
        """Volta ao checkpoint do estágio que falhou.

        É uma retomada decidida por alguém, então os contadores do reconciliador recomeçam.
        """
        run = cls._locked(run_id)
        if RunStatus(run.status) not in RECOVERABLE:
            raise RunConflict("Somente runs recuperáveis podem ser reprocessados.")
        if not run.stage:
            raise RunConflict("O run não registra qual estágio deve ser retomado.")
        checkpoint = STAGE_BY_NAME[Stage(run.stage)].checkpoint
        return cls._transition(
            run,
            checkpoint,
            actor=actor,
            updates={
                "current_task_id": None,
                "stage_started_at": None,
                "last_error": "",
                "stage_claims": 0,
                "publish_count": 0,
            },
        )

    @classmethod
    @transaction.atomic
    def abandon(cls, run_id: Any, *, error: str, actor: str = "reconciler") -> Run:
        """Leva a `error_unexpected` um run que o reconciliador desistiu de retomar.

        Parado num checkpoint, o run passa a registrar o estágio que deveria começar ali,
        para o "Reprocessar" voltar a esse mesmo checkpoint.
        """
        run = cls._locked(run_id)
        status = RunStatus(run.status)
        updates: dict[str, Any] = {
            "last_error": error,
            "current_task_id": None,
            "stage_started_at": None,
        }
        if status in CHECKPOINTS:
            next_stage = STAGE_BY_CHECKPOINT[status].stage
            if run.stage != next_stage:
                updates.update({"stage": next_stage, "stage_claims": 0})
        elif status not in RUNNING:
            raise RunConflict("Só um run parado num checkpoint ou num estágio pode ser abandonado.")
        return cls._transition(
            run,
            RunStatus.ERROR_UNEXPECTED,
            actor=actor,
            task_id=run.current_task_id or "",
            payload={"error": error},
            updates=updates,
        )

    @classmethod
    @transaction.atomic
    def release_stale(cls, run_id: Any, *, actor: str = "reconciler") -> Run:
        run = cls._locked(run_id)
        status = RunStatus(run.status)
        if status not in RUNNING:
            raise RunConflict("Somente um estágio em execução pode ser liberado.")
        checkpoint = STAGE_BY_RUNNING_STATUS[status].checkpoint
        return cls._transition(
            run,
            checkpoint,
            actor=actor,
            task_id=run.current_task_id or "",
            updates={"current_task_id": None, "stage_started_at": None},
        )

    @classmethod
    @transaction.atomic
    def mark_republished(cls, run_id: Any, *, payload: dict[str, Any] | None = None) -> Run:
        run = cls._locked(run_id)
        if RunStatus(run.status) not in CHECKPOINTS:
            raise RunConflict("Somente runs em checkpoint podem ser republicados.")
        run.publish_count += 1
        run.updated_at = timezone.now()
        run.save(update_fields=["publish_count", "updated_at"])
        _run_event().append(
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

    @classmethod
    @transaction.atomic
    def supersede_other_attempts(cls, article: Article, current_attempt: Attempt) -> int:
        runs = (
            cls.objects.select_for_update()
            .filter(attempt__article=article, purpose=RunPurpose.EVALUATION)
            .exclude(attempt=current_attempt)
            .exclude(status__in=[status.value for status in FINAL])
            .order_by("pk")
        )
        count = 0
        for run in runs:
            cls._transition(
                run,
                RunStatus.SUPERSEDED,
                actor="pipeline",
                task_id=run.current_task_id or "",
                updates={"current_task_id": None, "stage_started_at": None},
            )
            count += 1
        return count
