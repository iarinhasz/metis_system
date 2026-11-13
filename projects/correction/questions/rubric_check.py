"""Cria um lote interno com a rubrica congelada, sem alterar a curadoria ativa."""

from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from projects.correction.attempts.models import Attempt, Run
from projects.correction.attempts.status import RunPurpose, Stage
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.models import Extraction
from projects.correction.pipeline.publishing import publish_stage_on_commit
from projects.correction.questions.criteria import get_method
from projects.correction.questions.curation_errors import CurationConflict, CurationError
from projects.correction.questions.models import Question

MAX_SAMPLE_ATTEMPTS = 20


@dataclass(frozen=True)
class RubricCheckBatch:
    id: UUID
    runs: tuple[Run, ...]
    created: bool


@transaction.atomic
def start_rubric_check(
    question_id: UUID,
    *,
    attempt_ids: tuple[UUID, ...],
    revision: str,
    batch_id: UUID,
    actor: str,
) -> RubricCheckBatch:
    if not 1 <= len(attempt_ids) <= MAX_SAMPLE_ATTEMPTS or len(set(attempt_ids)) != len(
        attempt_ids
    ):
        raise CurationError(f"Escolha de 1 a {MAX_SAMPLE_ATTEMPTS} attempts distintas.")
    # Serializa o reenvio do formulário e os editores que invalidam a mesma Question.
    question = Question.lock_for_curation(question_id)
    previous = Run.rubric_check_batch(question.pk, batch_id)
    if previous:
        if {run.attempt_id for run in previous} != set(attempt_ids):
            raise CurationConflict("Este lote já foi criado com outra amostra. Abra um novo teste.")
        return RubricCheckBatch(batch_id, tuple(previous), False)
    snapshot = Question.rubric_check_snapshot(question, revision=revision)
    attempts = Attempt.rubric_check_sample(attempt_ids)
    if len(attempts) != len(attempt_ids):
        raise CurationError("Uma das attempts não está mais disponível.")
    version = extraction_version(ARTICLE_CONFIG)
    cache = Extraction.cached_sample(tuple(attempt.sha256 for attempt in attempts), version)
    if any(attempt.sha256 not in cache for attempt in attempts):
        raise CurationError(
            "Todas as attempts precisam de extração em cache na versão atual do E1."
        )
    runs = tuple(
        Run.create(
            attempt=attempt,
            actor=actor,
            purpose=RunPurpose.RUBRIC_CHECK,
            question_id=question.pk,
            extraction=cache[attempt.sha256],
            config_snapshot={
                "method": snapshot.method,
                "evaluation_config": get_method(snapshot.method).model_dump(mode="json"),
                "question": snapshot.model_dump(mode="json"),
                "rubric_check": {
                    "batch_id": str(batch_id),
                    "question_revision": revision,
                    "extraction_version": version,
                },
            },
        )
        for attempt in attempts
    )
    for run in runs:
        publish_stage_on_commit(str(run.pk), Stage.EXTRACTION)
    return RubricCheckBatch(batch_id, runs, True)
