"""Síntese das observações e checagens de um avaliador por critério."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriteriaSynthesis,
    CriterionSynthesis,
    CrossCheckResult,
    EvaluationMode,
    EvaluatorSlot,
    ItemRef,
    ItemType,
    Observation,
    ReviewState,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import ReviewRound
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.criteria import CriterionConfig, PaperCriteria


class SynthesisCheckpoints(Protocol):
    """Posse e persistência da rodada atual do E4."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def store_state(self, state: ReviewState) -> None: ...


@dataclass(frozen=True)
class SynthesisStep:
    """Sintetiza todos os critérios pendentes do slot em uma chamada e checkpoint."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: SynthesisCheckpoints

    def execute(
        self,
        *,
        refresh: tuple[Criterion, ...] = (),
        mark_changed: bool = False,
    ) -> ReviewState:
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
        observations: tuple[Observation, ...] = tuple(
            item for item in state.observations if set(item.criteria) & set(pending)
        )
        checks: tuple[CrossCheckResult, ...] = tuple(
            item for item in state.cross_checks if set(item.criteria) & set(pending)
        )
        source = {
            "slot": self.slot.value,
            "paper_type": self.context.profile.paper_type.value,
            "criteria": criteria_payload,
            "observations": [item.model_dump(mode="json") for item in observations],
            "cross_checks": [item.model_dump(mode="json") for item in checks],
            "integrity_summary": self.context.integrity_summary,
            "related_works": (
                [item.model_dump(mode="json") for item in self.context.related_works]
                if Criterion.ORIGINALITY in pending
                else []
            ),
        }

        self.checkpoints.assert_owned()
        response = self.factory.synthesizer(
            self.slot.value,
            output_schema=CriteriaSynthesis,
            spec=self.context.evaluator(self.slot).model,
        ).run(
            AgentPayload(
                "Sintetize os itens e critérios fornecidos.",
                article=json.dumps(source, ensure_ascii=False),
            )
        )
        if not response.valid or not isinstance(response.content, CriteriaSynthesis):
            raise InvalidEvaluationOutput("A síntese por critério retornou uma saída inválida.")
        additions = response.content.criteria
        self._validate(additions, pending, config, observations, checks)
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

    @staticmethod
    def _validate(
        additions: tuple[CriterionSynthesis, ...],
        pending: tuple[Criterion, ...],
        config: dict[Criterion, CriterionConfig],
        observations: Sequence[Observation],
        checks: Sequence[CrossCheckResult],
    ) -> None:
        keys = tuple(item.criterion_key for item in additions)
        if len(keys) != len(set(keys)) or set(keys) != set(pending):
            raise InvalidEvaluationOutput(
                "A síntese não retornou exatamente os critérios solicitados."
            )
        obs_by_id = {item.id: item for item in observations}
        checks_by_id = {item.id: item for item in checks}
        for item in additions:
            allowed_grades = config[item.criterion_key].grades
            if item.grade not in allowed_grades:
                raise InvalidEvaluationOutput("A síntese usou nota fora da escala do critério.")
            if item.evidence:
                raise InvalidEvaluationOutput(
                    "A síntese sectioned deve referenciar observações e checagens por id."
                )
            if len(item.observation_ids) != len(set(item.observation_ids)) or any(
                item_id not in obs_by_id or item.criterion_key not in obs_by_id[item_id].criteria
                for item_id in item.observation_ids
            ):
                raise InvalidEvaluationOutput(
                    "A síntese cita observação inexistente ou de outro critério."
                )
            if len(item.check_ids) != len(set(item.check_ids)) or any(
                item_id not in checks_by_id
                or item.criterion_key not in checks_by_id[item_id].criteria
                for item_id in item.check_ids
            ):
                raise InvalidEvaluationOutput(
                    "A síntese cita checagem inexistente ou de outro critério."
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
class RunSynthesisCheckpoints:
    """Adapta a persistência da primeira rodada para a síntese por avaliador."""

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
        if row.ready or row.verdicts.exists():
            raise RunConflict("Não é possível retomar uma rodada já julgada ou finalizada.")
        return row.state

    def store_state(self, state: ReviewState) -> None:
        ReviewRound.store(
            self.run_id,
            self.task_id,
            slot=self.slot,
            round_number=self.round_number,
            mode=EvaluationMode.SECTIONED,
            model_spec=self.model_spec,
            state=state,
        )
