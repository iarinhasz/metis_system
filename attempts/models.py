"""Modelos de submissão, execução do pipeline e trilha de auditoria."""

import uuid
from pathlib import PurePath
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Func
from django.db.models.functions import Now
from django.utils import timezone

from attempts.managers import AttemptManagement, RunManagement
from attempts.status import RunStatus, Stage


def private_upload_path(instance: Attempt, filename: str) -> str:
    """Armazena o PDF em caminho privado, separado por artigo e tentativa."""
    suffix = PurePath(filename).suffix.lower() or ".pdf"
    return f"submissions/{instance.article_id}/{instance.attempt_number}/{uuid.uuid7()}{suffix}"


class TimeStampModel(models.Model):
    """Base com UUIDv7 e timestamps gerados pela aplicação e pelo Postgres."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid7,
        db_default=Func(function="uuidv7", output_field=models.UUIDField()),
        editable=False,
    )
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        abstract = True


class Article(TimeStampModel):
    external_id = models.CharField(max_length=255, unique=True)
    title = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.title or self.external_id


class Attempt(TimeStampModel):
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=private_upload_path)
    original_filename = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    submitted_by = models.CharField(max_length=255)

    objects = AttemptManagement()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "attempt_number"], name="attempt_article_number_uniq"
            ),
            models.UniqueConstraint(fields=["article", "sha256"], name="attempt_article_sha_uniq"),
        ]
        ordering = ["article_id", "attempt_number"]

    def __str__(self) -> str:
        return f"{self.article} · v{self.attempt_number}"


class Run(TimeStampModel):
    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="runs")
    status = models.CharField(
        max_length=40,
        choices=[(status.value, status.value) for status in RunStatus],
        default=RunStatus.RECEIVED,
        db_index=True,
    )
    stage = models.CharField(
        max_length=24,
        choices=[(stage.value, stage.value) for stage in Stage],
        blank=True,
    )
    current_task_id = models.CharField(max_length=255, null=True, blank=True)
    stage_started_at = models.DateTimeField(null=True, blank=True)
    stage_claims = models.PositiveIntegerField(default=0)
    publish_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    last_error = models.TextField(blank=True)

    objects = RunManagement()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Run {self.pk} ({self.status})"


class RunEvent(TimeStampModel):
    class EventType(models.TextChoices):
        TRANSITION = "transition", "Transição"
        RETRY_SCHEDULED = "retry_scheduled", "Retry agendado"
        REPUBLISHED = "republished", "Republicado"

    run = models.ForeignKey(Run, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40, blank=True)
    stage = models.CharField(max_length=24, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    actor = models.CharField(max_length=64, default="pipeline")
    payload = models.JSONField(default=dict)
    event_key = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("RunEvent é append-only e não pode ser alterado.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("RunEvent é append-only e não pode ser removido.")
