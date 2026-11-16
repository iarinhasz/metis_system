"""Documentos-fonte e chunks vetoriais do corpus de integridade."""

from django.db import models
from pgvector.django import HnswIndex, VectorField

from projects.correction.attempts.models import TimeStampModel
from projects.correction.integrity.embeddings import EMBEDDING_DIMENSIONS
from projects.correction.queries.integrity.phase_checkpoint import (
    IntegrityPhaseCheckpointManagement,
)
from projects.correction.queries.integrity.report import IntegrityReportManagement
from projects.correction.queries.integrity.source_document import (
    SourceChunkManagement,
    SourceDocumentManagement,
)


class SourceDocument(SourceDocumentManagement, TimeStampModel):
    source = models.CharField(max_length=64)
    source_identifier = models.CharField(max_length=512)
    doi = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    title = models.TextField()
    authors = models.JSONField(default=list, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_identifier"], name="source_document_source_id_uniq"
            )
        ]
        indexes = [models.Index(fields=["source", "doi"], name="source_document_source_doi_idx")]
        ordering = ["source", "source_identifier"]

    def __str__(self) -> str:
        return self.title


class SourceChunk(SourceChunkManagement, TimeStampModel):
    document = models.ForeignKey(SourceDocument, on_delete=models.CASCADE, related_name="chunks")
    section_id = models.CharField(max_length=128)
    section_title = models.CharField(max_length=512)
    section_key = models.CharField(max_length=128, blank=True)
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="source_chunk_doc_index_uniq"
            )
        ]
        indexes = [
            HnswIndex(
                name="source_chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]
        ordering = ["document_id", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.document.title} · {self.section_title} · {self.chunk_index}"


class IntegrityReport(IntegrityReportManagement, TimeStampModel):
    run = models.OneToOneField(
        "attempts.Run", on_delete=models.PROTECT, related_name="integrity_report"
    )
    risk_level = models.CharField(
        max_length=8,
        choices=[("low", "Baixo"), ("medium", "Médio"), ("high", "Alto")],
    )
    rules_version = models.CharField(max_length=32)
    coverage = models.JSONField(default=dict)
    narrative = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Relatório de integridade {self.pk} ({self.risk_level})"


class IntegrityPhaseCheckpoint(IntegrityPhaseCheckpointManagement, TimeStampModel):
    class Phase(models.TextChoices):
        RESOLUTION = "resolution", "Resolução"
        SIMILARITY = "similarity", "Similaridade"
        CITATIONS = "citations", "Citações"

    run = models.ForeignKey(
        "attempts.Run", on_delete=models.PROTECT, related_name="integrity_phase_checkpoints"
    )
    phase = models.CharField(max_length=16, choices=Phase.choices)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "phase"], name="integrity_phase_run_uniq")
        ]
        ordering = ["run_id", "phase"]

    def __str__(self) -> str:
        return f"Run {self.run_id} · {self.phase}"


class IntegrityFinding(TimeStampModel):
    report = models.ForeignKey(IntegrityReport, on_delete=models.CASCADE, related_name="findings")
    finding_type = models.CharField(max_length=48)
    severity = models.CharField(
        max_length=8,
        choices=[("low", "Baixa"), ("medium", "Média"), ("high", "Alta")],
    )
    verdict = models.CharField(max_length=48, blank=True)
    section_id = models.CharField(max_length=128, blank=True)
    target_start = models.PositiveIntegerField(null=True, blank=True)
    target_end = models.PositiveIntegerField(null=True, blank=True)
    source_start = models.PositiveIntegerField(null=True, blank=True)
    source_end = models.PositiveIntegerField(null=True, blank=True)
    target_excerpt = models.TextField(blank=True)
    source_excerpt = models.TextField(blank=True)
    source_title = models.TextField(blank=True)
    source_id = models.CharField(max_length=512, blank=True)
    source_doi = models.CharField(max_length=255, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    rationale = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["report", "severity"], name="integrity_finding_sev_idx")]

    def __str__(self) -> str:
        return f"{self.finding_type} ({self.severity})"
