"""Amostras sintéticas em cache e rubricas independentes da Question ativa."""

import hashlib

from projects.correction.agents.schemas.evaluation import EvaluatorSlot, VerdictSource
from projects.correction.agents.specs import Family, Role, development_spec
from projects.correction.attempts.models import Article, Attempt
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.tests.helpers import review
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.models import Extraction
from projects.correction.pipeline.stages import StageContext, StageOutcome
from projects.correction.questions.models import Question, RubricField
from projects.correction.questions.tests.profiling_helpers import article


def draft(*, active: bool = False) -> Question:
    question = Question.create(
        name="Ativa" if active else "Rascunho <script>alert(1)</script>",
        method="standard",
        is_generic=True,
        active=active,
        validated=active,
    )
    RubricField.create(
        question=question,
        key="context",
        label="Contexto",
        rubric_text="Rubrica ativa." if active else "Texto original do rascunho.",
    )
    return question


def sample_attempt(name: str) -> Attempt:
    paper = Article.get_or_create_by_external_id(name)
    attempt, _ = Attempt.create_next(
        paper,
        sha256=hashlib.sha256(name.encode()).hexdigest(),
        file=f"missing/{name}.pdf",
        original_filename=f"{name}.pdf",
        size_bytes=128,
        submitted_by="test-service",
    )
    cache_attempt(attempt)
    return attempt


def cache_attempt(attempt: Attempt) -> Extraction:
    document = article()
    section = document.sections[1].model_copy(
        update={
            "id": "sec_3",
            "title": "Método",
            "key": None,
            "text": "Os parâmetros foram definidos.",
        }
    )
    return Extraction.store(
        attempt.sha256,
        extraction_version(ARTICLE_CONFIG),
        document.model_copy(update={"sections": (*document.sections, section)}),
    )


def judged_evaluation(ctx: StageContext) -> StageOutcome:
    """Substitui somente o E4 ausente; E1, E2, E5, banco e tasks continuam reais."""
    for slot in EvaluatorSlot:
        data = review(slot)
        row = ReviewRound.store(
            ctx.run_id,
            ctx.task_id,
            slot=slot,
            round_number=1,
            mode=data.mode,
            model_spec=data.model_spec,
            state=data.state,
        )
        for verdict in data.verdicts:
            JudgeVerdict.record(
                row.pk,
                ctx.task_id,
                item=verdict,
                source=VerdictSource.JUDGE,
                judge_model=development_spec(
                    Role.JUDGE_GOOGLE if data.model_spec.family == Family.GPT else Role.JUDGE_OPENAI
                ),
            )
        ReviewRound.finalize(row.pk, ctx.task_id)
    return StageOutcome()
