"""Síntese das observações e checagens de um avaliador por critério."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final, Protocol

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

SYNTHESIS_ATTEMPTS: Final = 2


def _cleaned(
    items: Sequence[CriterionSynthesis],
    pending: tuple[Criterion, ...],
    config: dict[Criterion, CriterionConfig],
    observations: Sequence[Observation],
    checks: Sequence[CrossCheckResult],
) -> list[CriterionSynthesis]:
    """As sínteses aproveitáveis da resposta, uma por critério pedido.

    Sai o critério não pedido ou repetido e a nota fora da escala (o critério volta a faltar).
    Das que ficam, saem as citações do texto (no modo por seção, a síntese cita as observações
    e as checagens pelo id) e os ids que não existem ou são de outro critério.
    """
    obs_by_id = {item.id: item for item in observations}
    checks_by_id = {item.id: item for item in checks}
    kept: dict[Criterion, CriterionSynthesis] = {}
    for item in items:
        key = item.criterion_key
        if key not in pending or key in kept or item.grade not in config[key].grades:
            continue
        kept[key] = item.model_copy(
            update={
                "evidence": (),
                "observation_ids": tuple(
                    dict.fromkeys(
                        i
                        for i in item.observation_ids
                        if i in obs_by_id and key in obs_by_id[i].criteria
                    )
                ),
                "check_ids": tuple(
                    dict.fromkeys(
                        i
                        for i in item.check_ids
                        if i in checks_by_id and key in checks_by_id[i].criteria
                    )
                ),
            }
        )
    return list(kept.values())


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

        observations: tuple[Observation, ...] = tuple(
            item for item in state.observations if set(item.criteria) & set(pending)
        )
        checks: tuple[CrossCheckResult, ...] = tuple(
            item for item in state.cross_checks if set(item.criteria) & set(pending)
        )
        # Com modelos reais, a resposta vem quase certa: um critério repetido ou faltando,
        # citações do texto no lugar dos ids, um id que não existe. O código limpa o que dá e
        # pede de novo só os critérios que faltaram, uma vez, como o E1 faz com as seções.
        additions: dict[Criterion, CriterionSynthesis] = {}
        missing = pending
        for _ in range(SYNTHESIS_ATTEMPTS):
            hint = (
                ""
                if missing == pending
                else " Faltaram estes critérios na resposta anterior: "
                + ", ".join(key.value for key in missing)
                + "."
            )
            source = self._source(missing, config, rubric_fields, observations, checks)
            self.checkpoints.assert_owned()
            response = self.factory.synthesizer(
                self.slot.value,
                output_schema=CriteriaSynthesis,
                spec=self.context.evaluator(self.slot).model,
            ).run(
                AgentPayload(
                    "Sintetize os itens e critérios fornecidos." + hint,
                    article=json.dumps(source, ensure_ascii=False),
                )
            )
            if response.valid and isinstance(response.content, CriteriaSynthesis):
                for item in _cleaned(
                    response.content.criteria, missing, config, observations, checks
                ):
                    additions.setdefault(item.criterion_key, item)
            missing = tuple(key for key in pending if key not in additions)
            if not missing:
                break
        if missing:
            names = ", ".join(key.value for key in missing)
            raise InvalidEvaluationOutput(f"A síntese não trouxe os critérios: {names}.")
        additions_in_order = tuple(additions[key] for key in pending)
        updated = self._merge(state, additions_in_order, replace_existing=bool(refresh))
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

    def _source(
        self,
        pending: tuple[Criterion, ...],
        config: dict[Criterion, CriterionConfig],
        rubric_fields: dict[str, Any],
        observations: Sequence[Observation],
        checks: Sequence[CrossCheckResult],
    ) -> dict[str, object]:
        return {
            "slot": self.slot.value,
            "paper_type": self.context.profile.paper_type.value,
            "criteria": [
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
            ],
            "observations": [
                item.model_dump(mode="json")
                for item in observations
                if set(item.criteria) & set(pending)
            ],
            "cross_checks": [
                item.model_dump(mode="json") for item in checks if set(item.criteria) & set(pending)
            ],
            "integrity_summary": self.context.integrity_summary,
            "related_works": (
                [item.model_dump(mode="json") for item in self.context.related_works]
                if Criterion.ORIGINALITY in pending
                else []
            ),
        }

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
