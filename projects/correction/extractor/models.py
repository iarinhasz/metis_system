"""O artigo dividido em seções, guardado para não chamar o modelo de novo pelo mesmo PDF."""

from django.db import models

from projects.correction.attempts.models import TimeStampModel
from projects.correction.extractor.article import ExtractedArticle
from projects.correction.queries.extractor.extraction import ExtractionManagement


class Extraction(ExtractionManagement, TimeStampModel):
    """Único por PDF (sha256) e versão do extractor (hash da config e dos prompts): mudar o
    modelo ou um prompt força uma extração nova; um run novo do mesmo PDF reaproveita esta."""

    sha256 = models.CharField(max_length=64)
    version = models.CharField(max_length=64)
    content = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sha256", "version"], name="extraction_sha_version_uniq"
            )
        ]

    def __str__(self) -> str:
        return f"Extração {self.sha256[:12]} ({self.version})"

    @property
    def article(self) -> ExtractedArticle:
        return ExtractedArticle.model_validate(self.content)
