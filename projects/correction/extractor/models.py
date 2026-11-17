"""O artigo dividido em seções, guardado para não chamar o modelo de novo pelo mesmo PDF, e as
respostas do modelo guardadas durante a extração, para o retry do estágio retomar delas."""

from django.db import models

from projects.correction.attempts.models import TimeStampModel
from projects.correction.extractor.article import ExtractedArticle
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.queries.extractor.extraction import ExtractionManagement
from projects.correction.queries.extractor.extraction_step import ExtractionStepManagement


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

    @property
    def document(self) -> ExtractedDocument:
        """Contrato público do E1, derivado sem alterar o JSON de cache persistido."""
        from projects.correction.extractor.document_adapter import to_extracted_document

        return to_extracted_document(self.article)


class ExtractionStep(ExtractionStepManagement, TimeStampModel):
    """Uma resposta do modelo durante o E1, para o retry do estágio não pagar de novo o que já
    deu certo (ver resumable_session.py). Apagada quando a `Extraction` é guardada."""

    sha256 = models.CharField(max_length=64)
    version = models.CharField(max_length=64)
    # Hash do prompt, do schema pedido e de with_document.
    key = models.CharField(max_length=64)
    answer = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sha256", "version", "key"], name="extraction_step_uniq"
            )
        ]

    def __str__(self) -> str:
        return f"Passo {self.key[:12]} da extração {self.sha256[:12]} ({self.version})"
