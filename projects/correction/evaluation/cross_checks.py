"""Checagens iniciais entre seções, com entrada restrita e checkpoints retomáveis."""

import json
from dataclasses import dataclass
from typing import Literal, Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CrossCheckResult,
    EvaluationMode,
    EvaluatorSlot,
    ReviewState,
)
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import ReviewRound
from projects.correction.metis.concurrency import bounded_map
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.document_map import MapSection

type CrossCheckKind = Literal["claims_vs_results", "method_vs_question", "figure_vs_text"]

CROSS_CHECK_KINDS: tuple[CrossCheckKind, ...] = (
    "claims_vs_results",
    "method_vs_question",
    "figure_vs_text",
)

_CLAIM_AND_EVIDENCE_ROLES: dict[PaperType, tuple[tuple[SectionRole, ...], ...]] = {
    PaperType.EMPIRICAL: (
        (SectionRole.INTRODUCTION, SectionRole.CONCLUSION),
        (SectionRole.RESULTS, SectionRole.DISCUSSION),
    ),
    PaperType.METHODS: (
        (SectionRole.INTRODUCTION, SectionRole.CONCLUSION),
        (SectionRole.RESULTS, SectionRole.DISCUSSION),
    ),
    PaperType.THEORETICAL: (
        (SectionRole.INTRODUCTION, SectionRole.CONCLUSION),
        (SectionRole.THEOREMS, SectionRole.PROOFS, SectionRole.DISCUSSION),
    ),
    PaperType.REVIEW: (
        (SectionRole.INTRODUCTION, SectionRole.SCOPE, SectionRole.CONCLUSION),
        (SectionRole.THEMATIC, SectionRole.SYNTHESIS, SectionRole.DISCUSSION),
    ),
    PaperType.CASE_STUDY: (
        (SectionRole.CONTEXT, SectionRole.CASE_DESCRIPTION, SectionRole.CONCLUSION),
        (SectionRole.ANALYSIS, SectionRole.LESSONS),
    ),
}
_QUESTION_AND_METHOD_ROLES: dict[PaperType, tuple[tuple[SectionRole, ...], ...]] = {
    PaperType.EMPIRICAL: (
        (SectionRole.INTRODUCTION,),
        (SectionRole.METHOD,),
    ),
    PaperType.METHODS: (
        (SectionRole.INTRODUCTION,),
        (SectionRole.METHOD,),
    ),
    PaperType.THEORETICAL: (
        (SectionRole.INTRODUCTION,),
        (SectionRole.DEFINITIONS, SectionRole.THEOREMS, SectionRole.PROOFS),
    ),
    PaperType.REVIEW: (
        (SectionRole.INTRODUCTION, SectionRole.SCOPE),
        (SectionRole.SEARCH_PROTOCOL,),
    ),
    PaperType.CASE_STUDY: (
        (SectionRole.CONTEXT,),
        (SectionRole.CASE_DESCRIPTION, SectionRole.ANALYSIS),
    ),
}
_CHECK_CRITERIA: dict[CrossCheckKind, tuple[Criterion, ...]] = {
    "claims_vs_results": (Criterion.SOUNDNESS, Criterion.SUBSTANCE, Criterion.IMPACT),
    "method_vs_question": (Criterion.SOUNDNESS, Criterion.REPLICABILITY),
    "figure_vs_text": (Criterion.SUBSTANCE, Criterion.SOUNDNESS, Criterion.CLARITY),
}


class CrossCheckCheckpoints(Protocol):
    """Interface de posse e persistência compartilhada com os passes por seção."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def store_state(self, state: ReviewState) -> None: ...


@dataclass(frozen=True)
class _CheckInput:
    kind: CrossCheckKind
    sections: tuple[MapSection, ...]
    include_abstract: bool
    figure_ids: tuple[str, ...] = ()

    @property
    def section_ids(self) -> frozenset[str]:
        return frozenset(section.id for section in self.sections)


@dataclass(frozen=True)
class _CheckExecution:
    result: CrossCheckResult | None
    error: Exception | None = None


@dataclass(frozen=True)
class CrossCheckStep:
    """Executa as checagens aplicáveis para um avaliador e salva cada resultado."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: CrossCheckCheckpoints
    max_workers: int

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError("max_workers deve ser positivo.")
        article_sections = {section.id for section in self.context.article.sections}
        map_sections = {section.id for section in self.context.document_map.sections}
        if article_sections != map_sections:
            raise ValueError("O mapa e o artigo precisam ter as mesmas seções.")

    def execute(self) -> ReviewState:
        state = self.checkpoints.read_state()
        existing = {check.kind for check in state.cross_checks}
        pending = tuple(
            candidate
            for kind in CROSS_CHECK_KINDS
            if kind not in existing
            if (candidate := self._input_for(kind)) is not None
        )
        results = bounded_map(self._evaluate, pending, self.max_workers)
        errors: list[Exception] = []
        for execution in results:
            if execution.result is not None:
                state = self._merge(state, execution.result)
                self.checkpoints.store_state(state)
            if execution.error is not None:
                errors.append(execution.error)
        if errors:
            raise errors[0]
        return state

    def _input_for(self, kind: CrossCheckKind) -> _CheckInput | None:
        sections = self.context.document_map.sections
        paper_type = self.context.profile.paper_type

        if kind == "claims_vs_results":
            claim_roles, evidence_roles = _CLAIM_AND_EVIDENCE_ROLES[paper_type]
            claims = tuple(section for section in sections if set(section.roles) & set(claim_roles))
            results = tuple(
                section for section in sections if set(section.roles) & set(evidence_roles)
            )
            if not results or (not claims and not self.context.article.abstract.strip()):
                return None
            selected_ids = {section.id for section in (*claims, *results)}
            return _CheckInput(
                kind,
                tuple(section for section in sections if section.id in selected_ids),
                include_abstract=True,
            )

        if kind == "method_vs_question":
            question_roles, method_roles = _QUESTION_AND_METHOD_ROLES[paper_type]
            question_sections = tuple(
                section for section in sections if set(section.roles) & set(question_roles)
            )
            method_sections = tuple(
                section for section in sections if set(section.roles) & set(method_roles)
            )
            if not method_sections or (
                not question_sections and not self.context.article.abstract.strip()
            ):
                return None
            selected_ids = {section.id for section in (*question_sections, *method_sections)}
            return _CheckInput(
                kind,
                tuple(section for section in sections if section.id in selected_ids),
                include_abstract=True,
            )

        article_sections = {section.id: section for section in self.context.article.sections}
        figures_by_id = {figure.id: figure for figure in self.context.article.figures}
        figure_sections = {
            figure.section_id for figure in figures_by_id.values() if figure.section_id is not None
        }
        for figure in figures_by_id.values():
            label = figure.label.casefold()
            figure_sections.update(
                section.id
                for section in article_sections.values()
                if label and label in section.text.casefold()
            )
        figure_input_sections = tuple(
            section for section in sections if section.id in figure_sections
        )
        figure_ids = tuple(
            figure.id
            for figure in self.context.article.figures
            if figure.section_id in {section.id for section in figure_input_sections}
            or (
                figure.section_id is None
                and any(
                    figure.label.casefold() in article_sections[section.id].text.casefold()
                    for section in figure_input_sections
                )
            )
        )
        if not figure_input_sections or not figure_ids:
            return None
        return _CheckInput(
            kind, figure_input_sections, include_abstract=False, figure_ids=figure_ids
        )

    def _evaluate(self, check_input: _CheckInput) -> _CheckExecution:
        try:
            self.checkpoints.assert_owned()
            criteria = tuple(
                criterion
                for criterion in _CHECK_CRITERIA[check_input.kind]
                if criterion in self._active_criteria()
            )
            if not criteria:
                return _CheckExecution(None)
            article_sections = {section.id: section for section in self.context.article.sections}
            figures = {figure.id: figure for figure in self.context.article.figures}
            data = {
                "abstract": self.context.article.abstract if check_input.include_abstract else None,
                "sections": [
                    {
                        "id": section.id,
                        "title": section.title,
                        "roles": [role.value for role in section.roles],
                        "text": article_sections[section.id].text,
                    }
                    for section in check_input.sections
                ],
                "figures": [
                    figures[figure_id].model_dump(mode="json")
                    for figure_id in check_input.figure_ids
                ],
            }
            prompt = json.dumps(
                {
                    "kind": check_input.kind,
                    "criteria": [criterion.value for criterion in criteria],
                },
                ensure_ascii=False,
            )
            response = self.factory.cross_checker(
                self.slot.value,
                check_input.kind,
                output_schema=CrossCheckResult,
                spec=self.context.evaluator(self.slot).model,
            ).run(AgentPayload(prompt, article=json.dumps(data, ensure_ascii=False)))
            if not response.valid or not isinstance(response.content, CrossCheckResult):
                raise InvalidEvaluationOutput("A checagem entre seções retornou saída inválida.")
            result = response.content
            if (
                result.kind != check_input.kind
                or not set(result.criteria) <= set(criteria)
                or any(item.section_id not in check_input.section_ids for item in result.evidence)
            ):
                raise InvalidEvaluationOutput(
                    "A checagem retornou tipo, critério ou seção fora do pedido."
                )
            return _CheckExecution(
                result.model_copy(update={"id": f"{check_input.kind}:{result.id}"})
            )
        except Exception as exc:
            return _CheckExecution(None, exc)

    def _active_criteria(self) -> frozenset[Criterion]:
        paper = next(
            item
            for item in self.context.evaluation_config.paper_types
            if item.paper_type is self.context.profile.paper_type
        )
        return frozenset(paper.active)

    @staticmethod
    def _merge(state: ReviewState, addition: CrossCheckResult) -> ReviewState:
        checks = {item.id: item for item in state.cross_checks}
        previous = checks.get(addition.id)
        if previous is not None and previous != addition:
            raise InvalidEvaluationOutput("Ids de checagem duplicados com conteúdos distintos.")
        checks[addition.id] = addition
        return ReviewState.model_validate(
            {
                **state.model_dump(mode="python"),
                "cross_checks": tuple(checks.values()),
            }
        )


@dataclass(frozen=True)
class RunCrossCheckCheckpoints:
    """Adapta a persistência da primeira rodada para as checagens entre seções."""

    run_id: str
    task_id: str
    slot: EvaluatorSlot
    model_spec: ModelSpec

    def assert_owned(self) -> None:
        Run.for_evaluation(self.run_id, self.task_id)

    def read_state(self) -> ReviewState:
        self.assert_owned()
        row = ReviewRound.objects.filter(
            run_id=self.run_id,
            evaluator_slot=self.slot,
            round_number=1,
        ).first()
        if row is None:
            return ReviewState()
        if row.ready or row.verdicts.exists():
            raise RunConflict("Não é possível retomar uma rodada já julgada ou finalizada.")
        return row.state

    def store_state(self, state: ReviewState) -> None:
        ReviewRound.store(
            self.run_id,
            self.task_id,
            slot=self.slot,
            round_number=1,
            mode=EvaluationMode.SECTIONED,
            model_spec=self.model_spec,
            state=state,
        )
