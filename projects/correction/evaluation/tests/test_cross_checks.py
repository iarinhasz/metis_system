"""Checagens entre seções com payloads restritos e retomada por tipo."""

import json

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.evaluation import (
    CrossCheckResult,
    EvaluatorSlot,
    ReviewState,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role, development_spec
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.cross_checks import (
    CROSS_CHECK_KINDS,
    CrossCheckStep,
    RunCrossCheckCheckpoints,
)
from projects.correction.evaluation.tests.test_context import _context_run
from projects.correction.extractor.contract import DocumentFigure, DocumentSection
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.document_map import MapSection


class FakeCheckpoints:
    def __init__(self, state: ReviewState | None = None) -> None:
        self.state = state or ReviewState()
        self.writes = 0
        self.ownership_checks = 0

    def assert_owned(self) -> None:
        self.ownership_checks += 1

    def read_state(self) -> ReviewState:
        self.assert_owned()
        return self.state

    def store_state(self, state: ReviewState) -> None:
        self.assert_owned()
        self.state = state
        self.writes += 1


def _context() -> EvaluationContext:
    context = EvaluationContextBuilder(_context_run()).build()
    sections = (
        DocumentSection(
            id="sec_intro",
            title="Introdução",
            level=1,
            parent_id=None,
            key=None,
            text="Prometemos avaliar uma nova abordagem.",
        ),
        DocumentSection(
            id="sec_method",
            title="Método",
            level=1,
            parent_id=None,
            key=None,
            text="Aplicamos um protocolo experimental.",
        ),
        DocumentSection(
            id="sec_results",
            title="Resultados",
            level=1,
            parent_id=None,
            key=None,
            text="A Figura 1 compara os resultados.",
        ),
        DocumentSection(
            id="sec_discussion",
            title="Discussão",
            level=1,
            parent_id=None,
            key=None,
            text="A Figura 1 explica por que os resultados sustentam parcialmente a promessa.",
        ),
        DocumentSection(
            id="sec_conclusion",
            title="Conclusão",
            level=1,
            parent_id=None,
            key=None,
            text="Concluímos que a abordagem é promissora.",
        ),
        DocumentSection(
            id="sec_other",
            title="Apêndice",
            level=1,
            parent_id=None,
            key=None,
            text="Conteúdo auxiliar que não participa das checagens.",
        ),
    )
    role_by_id = {
        "sec_intro": SectionRole.INTRODUCTION,
        "sec_method": SectionRole.METHOD,
        "sec_results": SectionRole.RESULTS,
        "sec_discussion": SectionRole.DISCUSSION,
        "sec_conclusion": SectionRole.CONCLUSION,
        "sec_other": SectionRole.OTHER,
    }
    map_sections = tuple(
        MapSection(
            id=section.id,
            title=section.title,
            roles=(role_by_id[section.id],),
            first_sentence=section.text,
        )
        for section in sections
    )
    figures = (
        DocumentFigure(
            id="fig-1",
            kind="figure",
            label="Figura 1",
            page=4,
            caption="Comparação entre os resultados.",
            section_id="sec_results",
            offset=0,
            description={
                "figure_class": "chart",
                "description": "Comparação de desempenho entre os grupos.",
                "data_read": ["Grupo A: 0.8", "Grupo B: 0.7"],
                "supports_claims": True,
                "support_rationale": "As barras mostram a diferença descrita.",
                "issues": [],
                "table_markdown": None,
            },
        ),
    )
    article = context.article.model_copy(update={"sections": sections, "figures": figures})
    document_map = context.document_map.model_copy(update={"sections": map_sections})
    return context.model_copy(update={"article": article, "document_map": document_map})


def _result(kind: str, *, section_id: str, item_id: str) -> dict[str, object]:
    criterion = {
        "claims_vs_results": "soundness",
        "method_vs_question": "replicability",
        "figure_vs_text": "substance",
    }[kind]
    return {
        "id": item_id,
        "kind": kind,
        "verdict": "inconsistent",
        "evidence": [{"quote": "Trecho citado no artigo.", "section_id": section_id}],
        "criteria": [criterion],
        "severity": "minor",
    }


def _step(
    *,
    factory: FakeAgentFactory | None = None,
    checkpoints: FakeCheckpoints | None = None,
) -> tuple[CrossCheckStep, FakeAgentFactory, FakeCheckpoints]:
    selected_factory = factory or FakeAgentFactory()
    selected_checkpoints = checkpoints or FakeCheckpoints()
    return (
        CrossCheckStep(
            context=_context(),
            slot=EvaluatorSlot.A,
            factory=selected_factory,
            checkpoints=selected_checkpoints,
            max_workers=1,
        ),
        selected_factory,
        selected_checkpoints,
    )


def test_each_cross_check_receives_only_its_relevant_sections_and_is_resumable() -> None:
    factory = FakeAgentFactory(
        scripts={
            "cross_checker": [
                _result("claims_vs_results", section_id="sec_results", item_id="claims"),
                _result("method_vs_question", section_id="sec_method", item_id="method"),
                _result("figure_vs_text", section_id="sec_results", item_id="figure"),
            ]
        }
    )
    step, factory, checkpoints = _step(factory=factory)

    state = step.execute()
    assert [check.kind for check in state.cross_checks] == list(CROSS_CHECK_KINDS)
    assert [check.id for check in state.cross_checks] == [
        "claims_vs_results:claims",
        "method_vs_question:method",
        "figure_vs_text:figure",
    ]

    claims = json.loads(factory.calls[0].payload.article or "{}")
    assert {section["id"] for section in claims["sections"]} == {
        "sec_intro",
        "sec_results",
        "sec_discussion",
        "sec_conclusion",
    }
    assert claims["abstract"] == _context().article.abstract
    assert claims["figures"] == []

    method = json.loads(factory.calls[1].payload.article or "{}")
    assert {section["id"] for section in method["sections"]} == {"sec_intro", "sec_method"}
    assert method["abstract"] == _context().article.abstract
    assert method["figures"] == []

    figure = json.loads(factory.calls[2].payload.article or "{}")
    assert [section["id"] for section in figure["sections"]] == [
        "sec_results",
        "sec_discussion",
    ]
    assert [item["id"] for item in figure["figures"]] == ["fig-1"]
    assert figure["abstract"] is None

    assert len(factory.calls) == 3 and checkpoints.writes == 3
    assert step.execute() == state
    assert len(factory.calls) == 3 and checkpoints.writes == 3


def test_cross_check_without_both_sides_is_skipped() -> None:
    context = _context()
    one_section = MapSection(
        id=context.article.sections[0].id,
        title="Introdução",
        roles=(SectionRole.INTRODUCTION,),
        first_sentence="Prometemos avaliar uma nova abordagem.",
    )
    article = context.article.model_copy(
        update={"sections": (context.article.sections[0],), "figures": ()}
    )
    document_map = context.document_map.model_copy(update={"sections": (one_section,)})
    context = context.model_copy(update={"article": article, "document_map": document_map})
    factory = FakeAgentFactory()
    checkpoints = FakeCheckpoints()
    step = CrossCheckStep(
        context=context,
        slot=EvaluatorSlot.A,
        factory=factory,
        checkpoints=checkpoints,
        max_workers=1,
    )

    assert step.execute() == ReviewState()
    assert factory.calls == [] and checkpoints.writes == 0


def test_cross_check_rejects_result_for_wrong_kind_or_unrequested_section() -> None:
    factory = FakeAgentFactory(
        scripts={
            "cross_checker": [
                _result("claims_vs_results", section_id="sec_other", item_id="wrong-section")
            ]
        }
    )
    step, _, _ = _step(factory=factory)

    with pytest.raises(InvalidEvaluationOutput, match="seção fora do pedido"):
        step.execute()


@pytest.mark.django_db
def test_cross_check_checkpoint_persists_and_refuses_stale_owner(run: Run) -> None:
    task_id = "e4-cross-check"
    Run.objects.filter(pk=run.pk).update(status=RunStatus.EVALUATING, current_task_id=task_id)
    checkpoints = RunCrossCheckCheckpoints(
        run_id=str(run.pk),
        task_id=task_id,
        slot=EvaluatorSlot.A,
        model_spec=development_spec(Role.EVALUATOR_A),
    )
    state = ReviewState(
        cross_checks=(
            CrossCheckResult.model_validate(
                _result("claims_vs_results", section_id="sec_results", item_id="claims")
            ),
        )
    )

    assert checkpoints.read_state() == ReviewState()
    checkpoints.store_state(state)
    assert checkpoints.read_state() == state

    Run.objects.filter(pk=run.pk).update(current_task_id="replacement-task")
    with pytest.raises(RunConflict, match="perdeu a posse"):
        checkpoints.read_state()
