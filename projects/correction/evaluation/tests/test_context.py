"""Contexto do E4 montado dos snapshots persistidos no Run."""

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest

from projects.correction.agents.schemas.evaluation import EvaluatorSlot
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evaluation.context import EvaluationContextBuilder, divergence_hints
from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.models import Extraction
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.criteria import STANDARD
from projects.correction.questions.document_map import build_document_map
from projects.correction.questions.profile import (
    AreaNode,
    ArticleProfile,
    QuestionSnapshot,
)
from projects.correction.questions.section_roles import SectionAssignment
from projects.correction.questions.taxonomy import TaxonomyLevel


def _article() -> ExtractedArticle:
    abstract = ExtractedSection(
        id="sec_abstract",
        title="Resumo",
        level=1,
        parent_id=None,
        key="abstract",
        text="Este artigo apresenta um método novo.",
        has_footnotes=False,
        coverage=1,
        fidelity=1,
    )
    method = ExtractedSection(
        id="sec_method",
        title="Método",
        level=1,
        parent_id=None,
        key=None,
        text="O método usa dados públicos.",
        has_footnotes=False,
        coverage=1,
        fidelity=1,
    )
    return ExtractedArticle(
        title="Artigo sintético",
        authors=("Autora Exemplo",),
        language="pt",
        model="fake",
        sections=(abstract, method),
    )


def _classification() -> ArticleProfile:
    return ArticleProfile(
        taxonomy_version="test-v1",
        area_path=(
            AreaNode(code="domain", level=TaxonomyLevel.DOMAIN, name="Ciências"),
            AreaNode(code="field", level=TaxonomyLevel.FIELD, name="Computação"),
            AreaNode(code="subfield", level=TaxonomyLevel.SUBFIELD, name="IA"),
            AreaNode(code="topic", level=TaxonomyLevel.TOPIC, name="PLN"),
        ),
        field_confidence=0.95,
        topic_confidence=0.9,
        confidence=0.9,
        paper_type=PaperType.EMPIRICAL,
        language="pt",
        keywords=("linguagem", "modelos"),
        secondary_areas=(),
    )


def _question() -> QuestionSnapshot:
    return QuestionSnapshot(
        id=uuid4(),
        version=1,
        name="Question de teste",
        method="standard",
        is_generic=True,
        taxonomy_node_code=None,
        taxonomy_version=None,
        rubric_fields=(),
    )


def _prepare_run(run: Run) -> Run:
    article = _article()
    extraction = Extraction.store(run.attempt.sha256, "evaluation-context-test", article)
    assignments = (
        SectionAssignment(section_id="sec_abstract", roles=(SectionRole.OTHER,)),
        SectionAssignment(section_id="sec_method", roles=(SectionRole.METHOD,)),
    )
    profile = {
        "classification": _classification().model_dump(mode="json"),
        "document_map": build_document_map(article, assignments).model_dump(mode="json"),
        "complete": True,
    }
    config_snapshot = {
        "method": "standard",
        "evaluation_config": STANDARD.model_dump(mode="json"),
        "question": _question().model_dump(mode="json"),
        "model_specs": {
            role.value: spec.model_dump(mode="json") for role, spec in settings.model_specs.items()
        },
    }
    Run.objects.filter(pk=run.pk).update(
        extraction=extraction,
        profile=profile,
        config_snapshot=config_snapshot,
    )
    return Run.objects.select_related("extraction").get(pk=run.pk)


def _advance_to_evaluation(run: Run) -> None:
    path = (
        (Stage.EXTRACTION, "e1", RunStatus.EXTRACTED),
        (Stage.PROFILING, "e2", RunStatus.PROFILED),
        (Stage.INTEGRITY, "e3", RunStatus.INTEGRITY_CHECKED),
    )
    for stage, task_id, completed in path:
        assert Run.claim_stage(run.pk, stage, task_id) is not None
        assert Run.complete_stage(run.pk, task_id, completed) is not None
    assert Run.claim_stage(run.pk, Stage.EVALUATION, "e4") is not None


def _context_run() -> Run:
    article = _article()
    assignments = (
        SectionAssignment(section_id="sec_abstract", roles=(SectionRole.OTHER,)),
        SectionAssignment(section_id="sec_method", roles=(SectionRole.METHOD,)),
    )
    return cast(
        Run,
        SimpleNamespace(
            extraction=SimpleNamespace(article=article),
            profile={
                "classification": _classification().model_dump(mode="json"),
                "document_map": build_document_map(article, assignments).model_dump(mode="json"),
                "complete": True,
            },
            config_snapshot={
                "method": "standard",
                "question": _question().model_dump(mode="json"),
                "model_specs": {
                    role.value: spec.model_dump(mode="json")
                    for role, spec in settings.model_specs.items()
                },
            },
        ),
    )


def test_builder_combines_article_profile_question_criteria_and_model_slots() -> None:
    builder = EvaluationContextBuilder(_context_run())
    context = builder.build()
    snapshot = builder.snapshot()

    assert context.article.title == "Artigo sintético"
    assert context.profile.paper_type is PaperType.EMPIRICAL
    assert context.question.name == "Question de teste"
    assert [section.id for section in context.document_map.sections] == [
        "sec_abstract",
        "sec_method",
    ]
    assert context.evaluation_config == STANDARD
    assert [item.slot for item in context.evaluators] == list(EvaluatorSlot)
    assert context.evaluator("b").model == settings.model_specs[Role.EVALUATOR_B]
    assert snapshot["evaluation_models"]["c"] == settings.model_specs[Role.EVALUATOR_C].model_dump(
        mode="json"
    )


def test_builder_requires_complete_e1_and_e2_snapshots() -> None:
    run = cast(Run, SimpleNamespace(extraction=None, profile={}, config_snapshot={}))
    with pytest.raises(SetupRequired, match="extração do E1"):
        EvaluationContextBuilder(run).build()


@pytest.mark.django_db
def test_run_evaluation_snapshot_is_persisted_and_requires_owner(run: Run) -> None:
    profiled = _prepare_run(run)
    _advance_to_evaluation(profiled)
    evaluating = Run.for_evaluation(profiled.pk, "e4")
    snapshot = EvaluationContextBuilder(evaluating).snapshot()

    Run.initialize_evaluation(profiled.pk, "e4", snapshot)
    current = Run.for_evaluation(profiled.pk, "e4")
    assert current.config_snapshot["evaluation_config"] == STANDARD.model_dump(mode="json")
    assert current.config_snapshot["evaluation_models"]["c"] == settings.model_specs[
        Role.EVALUATOR_C
    ].model_dump(mode="json")

    with pytest.raises(RunConflict, match="perdeu a posse"):
        Run.initialize_evaluation(profiled.pk, "stale-task", snapshot)

    assert Run.for_evaluation(profiled.pk, "e4").config_snapshot == current.config_snapshot


def test_divergence_hints_report_other_slots_without_labeling_the_outlier() -> None:
    hints = divergence_hints(
        {
            EvaluatorSlot.A: {"soundness": 2, "clarity": 4},
            EvaluatorSlot.B: {"soundness": 4, "clarity": 4},
            EvaluatorSlot.C: {"soundness": 5},
        }
    )

    assert hints == {
        EvaluatorSlot.A: {"soundness": (4, 5)},
        EvaluatorSlot.B: {"soundness": (2, 5)},
        EvaluatorSlot.C: {"soundness": (2, 4)},
    }
