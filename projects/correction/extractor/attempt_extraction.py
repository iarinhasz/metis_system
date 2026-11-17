"""O E1 para uma attempt: reaproveita a extração já guardada do mesmo PDF e da mesma versão do
extractor ou divide o artigo agora e guarda o resultado.

Cada resposta do modelo fica guardada enquanto a extração não termina (resumable_session.py):
se o modelo cai no meio, o retry do estágio só chama o modelo a partir de onde parou."""

import hashlib
from typing import Any

from projects.correction.attempts.models import Attempt
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.errors import InvalidModelAnswer
from projects.correction.extractor.models import Extraction, ExtractionStep
from projects.correction.extractor.prompts import fingerprint
from projects.correction.extractor.resumable_session import resumable
from projects.correction.extractor.service import extract_article
from projects.correction.extractor.session import AgnoSession, SessionOpener


def extraction_version(config: DocumentConfig) -> str:
    """Hash da config, dos prompts e da versão dos scanners locais."""
    payload = config.model_dump_json() + fingerprint() + "hidden-text-scan-v1"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def extract_attempt(
    attempt_id: Any,
    config: DocumentConfig = ARTICLE_CONFIG,
    opener: SessionOpener = AgnoSession,
) -> tuple[Extraction, bool]:
    """Devolve a extração do PDF da attempt e se ela foi reaproveitada."""
    attempt = Attempt.get_by_id(attempt_id)
    version = extraction_version(config)
    if (stored := Extraction.find(attempt.sha256, version)) is not None:
        return stored, True
    with attempt.file.open("rb") as file:
        pdf = file.read()
    try:
        article = extract_article(pdf, config, resumable(opener, attempt.sha256, version))
    except InvalidModelAnswer:
        # As respostas guardadas levariam à mesma falha no retry: ele começa do zero.
        ExtractionStep.forget(attempt.sha256, version)
        raise
    extraction = Extraction.store(attempt.sha256, version, article)
    ExtractionStep.forget(attempt.sha256, version)
    return extraction, False


def extraction_payload(
    extraction: Extraction, *, reused: bool, config: DocumentConfig = ARTICLE_CONFIG
) -> dict[str, Any]:
    """O que vai para o RunEvent do E1: ids e contagens, nunca texto do manuscrito."""
    article = extraction.article
    below = [
        section.id
        for section in article.sections
        if (section.coverage is not None and section.coverage < config.min_coverage)
        or (section.fidelity is not None and section.fidelity < config.min_fidelity)
    ]
    return {
        "extraction_id": str(extraction.pk),
        "reused": reused,
        "model": article.model,
        "sections": len(article.sections),
        "below_check": below,
        "references": len(article.references),
        "citations": len(article.citations),
        "unlinked_citations": sum(c.reference_id is None for c in article.citations),
        "figures": len(article.figures),
        "figures_described": sum(f.description is not None for f in article.figures),
    }
