"""Documentos-fonte e chunks vetoriais do corpus de integridade, e o relatório de integridade
de cada run (E3) com os achados."""

from django.db import models
from pgvector.django import HnswIndex, VectorField

from projects.correction.attempts.models import TimeStampModel
from projects.correction.integrity.embeddings import EMBEDDING_DIMENSIONS
from projects.correction.integrity.findings import Finding, FindingKind, Severity
from projects.correction.queries.integrity.report import (
    IntegrityFindingManagement,
    IntegrityReportManagement,
)
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


SEVERITY_CHOICES = [(severity.value, severity.value) for severity in Severity]


class IntegrityReport(IntegrityReportManagement, TimeStampModel):
    run = models.OneToOneField(
        "attempts.Run", on_delete=models.PROTECT, related_name="integrity_report"
    )
    risk = models.CharField(max_length=8, choices=SEVERITY_CHOICES)
    rules_version = models.CharField(max_length=32)
    # O que foi conferido: uma checagem que não rodou não pode contar como "sem achado".
    coverage = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f"Integridade do run {self.run_id} ({self.risk})"


class IntegrityFinding(IntegrityFindingManagement, TimeStampModel):
    report = models.ForeignKey(IntegrityReport, on_delete=models.CASCADE, related_name="findings")
    position = models.PositiveIntegerField()
    kind = models.CharField(max_length=32, choices=[(k.value, k.value) for k in FindingKind])
    severity = models.CharField(max_length=8, choices=SEVERITY_CHOICES)
    message = models.TextField()
    evidence = models.JSONField(default=dict)

    class Meta:
        ordering = ["report", "position"]
        constraints = [
            models.UniqueConstraint(fields=["report", "position"], name="integrity_finding_uniq")
        ]

    def __str__(self) -> str:
        return f"{self.severity}: {self.message}"

    @property
    def finding(self) -> Finding:
        return Finding(
            kind=FindingKind(self.kind),
            severity=Severity(self.severity),
            message=self.message,
            evidence=self.evidence,
        )
