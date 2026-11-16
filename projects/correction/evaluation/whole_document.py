"""Avaliação do artigo inteiro em uma única chamada por slot."""

import json
from dataclasses import dataclass
from typing import Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriteriaSynthesis,
    CriterionSynthesis,
    EvaluationMode,
    EvaluatorSlot,
    ItemRef,
    ItemType,
    ReviewState,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import ReviewRound
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.criteria import CriterionConfig, PaperCriteria


class WholeDocumentCheckpoints(Protocol):
    """Posse e persistência da rodada atual do E4."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def store_state(self, state: ReviewState) -> None: ...


@dataclass(frozen=True)
class WholeDocumentStep:
    """Avalia todos os critérios pendentes lendo o artigo inteiro numa chamada."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: WholeDocumentCheckpoints

    def execute(
        self,
        *,
        refresh: tuple[Criterion, ...] = (),
        mark_changed: bool = False,
    ) -> ReviewState:
        if self.context.evaluation_mode is not EvaluationMode.WHOLE_DOCUMENT:
            raise InvalidEvaluationOutput("WholeDocumentStep exige o modo whole_document.")
        state = self.checkpoints.read_state()
        paper = self._paper_criteria()
        active = tuple(paper.active)
        config = {item.key: item for item in self.context.evaluation_config.criteria}
        rubric_fields = {item.key: item for item in self.context.question.rubric_fields}
        existing = {item.criterion_key for item in state.criteria}
        if not existing <= set(active):
            raise InvalidEvaluationOutput("A rodada contém síntese de critério inativo.")
        if refresh and (not set(refresh) <= existing or not set(refresh) <= set(active)):
            raise InvalidEvaluationOutput("Só é possível atualizar sínteses ativas existentes.")
        pending = refresh or tuple(key for key in active if key not in existing)
        if not pending:
            return state

        criteria_payload = [
            {
                "key": key.value,
                "label": config[key].label,
                "question": config[key].question,
                "allowed_grades": config[key].grades,
                "rubric_text": (
                    rubric_fields[key.value].rubric_text if key.value in rubric_fields else None
                ),
            }
            for key in pending
        ]
        prompt_data = {
            "slot": self.slot.value,
            "paper_type": self.context.profile.paper_type.value,
            "criteria": criteria_payload,
        }
        self.checkpoints.assert_owned()
        response = self.factory.whole_document_reviewer(
            self.slot.value,
            output_schema=CriteriaSynthesis,
            spec=self.context.evaluator(self.slot).model,
        ).run(
            AgentPayload(
                json.dumps(prompt_data, ensure_ascii=False),
                article=self.context.article.model_dump_json(),
            )
        )
        if not response.valid or not isinstance(response.content, CriteriaSynthesis):
            raise InvalidEvaluationOutput("A avaliação whole_document retornou saída inválida.")
        additions = response.content.criteria
        self._validate(additions, pending, config)
        updated = self._merge(state, additions, replace_existing=bool(refresh))
        if mark_changed:
            changed = {(item.item_type, item.item_key): item for item in updated.changed_items}
            changed.update(
                {
                    (ItemType.CRITERION, key.value): ItemRef(
                        item_type=ItemType.CRITERION,
                        item_key=key.value,
                    )
                    for key in pending
                }
            )
            updated = updated.model_copy(update={"changed_items": tuple(changed.values())})
        self.checkpoints.store_state(updated)
        return updated

    def _paper_criteria(self) -> PaperCriteria:
        paper = next(
            (
                item
                for item in self.context.evaluation_config.paper_types
                if item.paper_type is self.context.profile.paper_type
            ),
            None,
        )
        if paper is None:
            raise InvalidEvaluationOutput("O método não cobre o tipo de artigo do Run.")
        return paper

    def _validate(
        self,
        additions: tuple[CriterionSynthesis, ...],
        pending: tuple[Criterion, ...],
        config: dict[Criterion, CriterionConfig],
    ) -> None:
        keys = tuple(item.criterion_key for item in additions)
        if len(keys) != len(set(keys)) or set(keys) != set(pending):
            raise InvalidEvaluationOutput(
                "A avaliação whole_document não retornou exatamente os critérios solicitados."
            )
        section_ids = {section.id for section in self.context.article.sections}
        for item in additions:
            if item.grade not in config[item.criterion_key].grades:
                raise InvalidEvaluationOutput("A síntese usou nota fora da escala do critério.")
            if item.observation_ids or item.check_ids:
                raise InvalidEvaluationOutput(
                    "O modo whole_document deve citar evidências diretas, não ids de itens."
                )
            if not item.evidence or any(
                evidence.section_id not in section_ids for evidence in item.evidence
            ):
                raise InvalidEvaluationOutput(
                    "A síntese precisa citar evidências em seções existentes do artigo."
                )

    @staticmethod
    def _merge(
        state: ReviewState,
        additions: tuple[CriterionSynthesis, ...],
        *,
        replace_existing: bool = False,
    ) -> ReviewState:
        criteria = {item.criterion_key: item for item in state.criteria}
        for item in additions:
            previous = criteria.get(item.criterion_key)
            if previous is not None and previous != item and not replace_existing:
                raise InvalidEvaluationOutput(
                    "Critério duplicado com sínteses de conteúdos distintos."
                )
            criteria[item.criterion_key] = item
        return ReviewState.model_validate(
            {
                **state.model_dump(mode="python"),
                "criteria": tuple(criteria[key] for key in sorted(criteria, key=lambda v: v.value)),
            }
        )


@dataclass(frozen=True)
class RunWholeDocumentCheckpoints:
    """Checkpoints da rodada whole_document, com validação de modo e posse."""

    run_id: str
    task_id: str
    slot: EvaluatorSlot
    model_spec: ModelSpec
    round_number: int = 1

    def assert_owned(self) -> None:
        Run.for_evaluation(self.run_id, self.task_id)

    def read_state(self) -> ReviewState:
        self.assert_owned()
        row = ReviewRound.objects.filter(
            run_id=self.run_id,
            evaluator_slot=self.slot,
            round_number=self.round_number,
        ).first()
        if row is None:
            return ReviewState()
        if row.mode != EvaluationMode.WHOLE_DOCUMENT:
            raise RunConflict("O modo da rodada não corresponde ao snapshot do Run.")
        if row.ready or row.verdicts.exists():
            raise RunConflict("Não é possível retomar uma rodada já julgada ou finalizada.")
        return row.state

    def store_state(self, state: ReviewState) -> None:
        ReviewRound.store(
            self.run_id,
            self.task_id,
            slot=self.slot,
            round_number=self.round_number,
            mode=EvaluationMode.WHOLE_DOCUMENT,
            model_spec=self.model_spec,
            state=state,
        )
