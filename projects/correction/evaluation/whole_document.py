"""Avaliação do artigo inteiro em uma única chamada por slot."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Protocol

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

SYNTHESIS_ATTEMPTS: Final = 2


def _cleaned(
    items: Sequence[CriterionSynthesis],
    pending: tuple[Criterion, ...],
    config: dict[Criterion, CriterionConfig],
    section_ids: set[str],
) -> list[CriterionSynthesis]:
    """As sínteses aproveitáveis, uma por critério pedido.

    Sai o critério não pedido ou repetido e a nota fora da escala. Das que ficam, saem os ids
    de itens (este modo cita o texto direto) e as evidências de seções que não existem; a que
    fica sem nenhuma evidência não vale, e o critério volta a faltar.
    """
    kept: dict[Criterion, CriterionSynthesis] = {}
    for item in items:
        key = item.criterion_key
        if key not in pending or key in kept or item.grade not in config[key].grades:
            continue
        evidence = tuple(e for e in item.evidence if e.section_id in section_ids)
        if evidence:
            kept[key] = item.model_copy(
                update={"observation_ids": (), "check_ids": (), "evidence": evidence}
            )
    return list(kept.values())


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

        # Como na síntese por seção: limpa o que dá e pede de novo só o que faltou, uma vez.
        section_ids = {section.id for section in self.context.article.sections}
        additions: dict[Criterion, CriterionSynthesis] = {}
        missing = pending
        for _ in range(SYNTHESIS_ATTEMPTS):
            prompt_data: dict[str, object] = {
                "slot": self.slot.value,
                "paper_type": self.context.profile.paper_type.value,
                "criteria": [
                    {
                        "key": key.value,
                        "label": config[key].label,
                        "question": config[key].question,
                        "allowed_grades": config[key].grades,
                        "rubric_text": (
                            rubric_fields[key.value].rubric_text
                            if key.value in rubric_fields
                            else None
                        ),
                    }
                    for key in missing
                ],
            }
            if missing != pending:
                prompt_data["missing_in_previous_answer"] = [key.value for key in missing]
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
            if response.valid and isinstance(response.content, CriteriaSynthesis):
                for item in _cleaned(response.content.criteria, missing, config, section_ids):
                    additions.setdefault(item.criterion_key, item)
            missing = tuple(key for key in pending if key not in additions)
            if not missing:
                break
        if missing:
            names = ", ".join(key.value for key in missing)
            raise InvalidEvaluationOutput(f"A avaliação whole_document não trouxe: {names}.")
        updated = self._merge(
            state, tuple(additions[key] for key in pending), replace_existing=bool(refresh)
        )
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
