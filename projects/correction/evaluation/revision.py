"""Revisões parciais, réplica e marcação de itens ainda não resolvidos."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    CrossCheckResult,
    EvaluationMode,
    EvaluatorSlot,
    Evidence,
    ItemRef,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    RevisionResponse,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.evaluation.synthesis import RunSynthesisCheckpoints, SynthesisStep
from projects.correction.evaluation.validators import normalize_quote
from projects.correction.evaluation.whole_document import (
    RunWholeDocumentCheckpoints,
    WholeDocumentStep,
)
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict

MAX_REVISION_ROUNDS = 2

logger = logging.getLogger(__name__)


class RevisionCheckpoints(Protocol):
    """Persistência das rodadas anterior e atual de um avaliador."""

    @property
    def round_number(self) -> int: ...

    @property
    def run_id(self) -> str: ...

    @property
    def task_id(self) -> str: ...

    def assert_owned(self) -> None: ...

    def read_previous_state(self) -> ReviewState: ...

    def read_previous_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]: ...

    def read_current_state(self) -> ReviewState | None: ...

    def read_current_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]: ...

    def store_current_state(self, state: ReviewState) -> None: ...

    def carry_forward_valid_verdicts(self, *, excluded: set[tuple[ItemType, str]]) -> None: ...

    def mark_unresolved(self, items: tuple[ItemRef, ...]) -> ReviewState: ...


class SynthesisRefresher(Protocol):
    def refresh(self, criteria: tuple[Criterion, ...]) -> ReviewState: ...


class RevisionPromptBuilder:
    """Cria o pedido restrito ao item recusado e ao contexto documental necessário."""

    @staticmethod
    def build(
        context: EvaluationContext,
        slot: EvaluatorSlot,
        state: ReviewState,
        target: ItemRef,
        verdict: ItemVerdict,
        round_number: int,
    ) -> AgentPayload:
        item = _find_item(state, target)
        sections = _relevant_sections(context, state, target)
        details: dict[str, object] = {
            "slot": slot.value,
            "round_number": round_number,
            "target": target.model_dump(mode="json"),
            "item": item.model_dump(mode="json"),
            "issues": [issue.model_dump(mode="json") for issue in verdict.issues],
            "evaluation_mode": context.evaluation_mode.value,
        }
        if isinstance(item, CriterionSynthesis):
            observations_by_id = {observation.id: observation for observation in state.observations}
            checks_by_id = {check.id: check for check in state.cross_checks}
            details["supporting_items"] = [
                observation.model_dump(mode="json")
                for item_id in item.observation_ids
                if (observation := observations_by_id.get(item_id)) is not None
            ] + [
                check.model_dump(mode="json")
                for item_id in item.check_ids
                if (check := checks_by_id.get(item_id)) is not None
            ]
        if target.item_type is ItemType.CRITERION:
            config = next(
                item
                for item in context.evaluation_config.criteria
                if item.key.value == target.item_key
            )
            details["rubric"] = {
                "label": config.label,
                "question": config.question,
                "allowed_grades": config.grades,
            }
        return AgentPayload(
            json.dumps(details, ensure_ascii=False),
            article=json.dumps(sections, ensure_ascii=False),
        )


@dataclass(frozen=True)
class RevisionStep:
    """Abre uma rodada para itens recusados e reavalia apenas o que foi alterado."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: RevisionCheckpoints
    synthesis_refresher: SynthesisRefresher | None = None
    max_revisions: int | None = None

    def execute(self) -> ReviewState:
        max_revisions = _configured_max_revisions(self.max_revisions)
        if max_revisions < 1 or self.checkpoints.round_number < 2:
            raise ValueError("A revisão precisa de limite positivo e rodada a partir de 2.")
        if self.checkpoints.round_number > max_revisions + 1:
            raise InvalidEvaluationOutput("O limite de revisões deste avaliador foi excedido.")
        self.checkpoints.assert_owned()
        previous = self.checkpoints.read_previous_state()
        previous_verdicts = self.checkpoints.read_previous_verdicts()
        rejected = tuple(
            verdict
            for _, verdict in previous_verdicts.items()
            if verdict.verdict is Verdict.INVALID
        )
        if not rejected:
            return previous

        state = self.checkpoints.read_current_state()
        if state is None:
            state = previous.model_copy(
                update={"unresolved": (), "changed_items": (), "revisions": ()}
            )
            self.checkpoints.store_current_state(state)

        completed = {(item.item_type, item.item_key) for item in state.revisions}
        previous_items = {(item.item_type, item.item_key): item for item in rejected}
        for key, verdict in previous_items.items():
            if key in completed:
                continue
            target = ItemRef(item_type=key[0], item_key=key[1])
            payload = RevisionPromptBuilder.build(
                self.context,
                self.slot,
                state,
                target,
                verdict,
                self.checkpoints.round_number,
            )
            self.checkpoints.assert_owned()
            response = self.factory.reviser(
                self.slot.value,
                target.item_type.value,
                output_schema=RevisionResponse,
                spec=self.context.evaluator(self.slot).model,
            ).run(payload)
            if not response.valid or not isinstance(response.content, RevisionResponse):
                logger.warning("Revisão inválida de %s/%s: item segue recusado.", *key)
                continue
            try:
                state = self._apply_response(state, target, response.content)
            except InvalidEvaluationOutput as exc:
                # Uma revisão fora das regras deixa o item como estava, ainda recusado: depois do
                # limite de revisões ele vira unresolved, em vez de derrubar o E4 inteiro.
                logger.warning("Revisão recusada de %s/%s: %s", *key, exc)
                continue
            self.checkpoints.store_current_state(state)

        affected = _dependent_criteria(previous, state)
        changed = {(item.item_type, item.item_key) for item in state.changed_items}
        pending_refresh = tuple(
            key for key in affected if (ItemType.CRITERION, key.value) not in changed
        )
        if pending_refresh:
            self.checkpoints.assert_owned()
            state = self._refresh_synthesis(pending_refresh)
        excluded = {(item.item_type, item.item_key) for item in state.changed_items}
        self.checkpoints.carry_forward_valid_verdicts(excluded=excluded)
        current = self.checkpoints.read_current_state()
        if current is None:
            raise RunConflict("A rodada de revisão não foi persistida.")
        return current

    def _apply_response(
        self,
        state: ReviewState,
        target: ItemRef,
        response: RevisionResponse,
    ) -> ReviewState:
        if (response.item_type, response.item_key) != (target.item_type, target.item_key):
            raise InvalidEvaluationOutput("A resposta de revisão cita outro item.")
        if any(
            (item.item_type, item.item_key) == (target.item_type, target.item_key)
            for item in state.revisions
        ):
            raise InvalidEvaluationOutput("O item já tem uma resposta nesta rodada.")
        original = _find_item(state, target)
        self._validate_evidence(response.evidence, target, original)

        if response.action == "accept":
            if response.replacement is None:
                raise InvalidEvaluationOutput("A ação accept precisa trazer o item corrigido.")
            replacement = _parse_replacement(target, response.replacement)
            _validate_identity(original, replacement, target)
            if response.evidence:
                replacement = _attach_evidence(replacement, response.evidence, self.context)
        else:
            if response.replacement is not None or not response.evidence:
                raise InvalidEvaluationOutput(
                    "A ação rebut preserva o item e precisa trazer evidência nova."
                )
            existing_evidence = {
                (item.quote, item.section_id) for item in getattr(original, "evidence", ())
            }
            if not any(
                (item.quote, item.section_id) not in existing_evidence for item in response.evidence
            ):
                raise InvalidEvaluationOutput("A réplica precisa acrescentar evidência nova.")
            replacement = _attach_evidence(original, response.evidence, self.context)

        updated = _replace_item(state, target, replacement)
        refs = {(item.item_type, item.item_key): item for item in updated.changed_items}
        refs[(target.item_type, target.item_key)] = target
        revisions = (*updated.revisions, response)
        return updated.model_copy(
            update={"changed_items": tuple(refs.values()), "revisions": revisions}
        )

    def _validate_evidence(
        self,
        evidence: tuple[Evidence, ...],
        target: ItemRef,
        original: object,
    ) -> None:
        sections = {item.id: item.text for item in self.context.article.sections}
        expected_section = original.section_id if isinstance(original, Observation) else None
        for item in evidence:
            text = sections.get(item.section_id)
            if (
                text is None
                or (expected_section is not None and item.section_id != expected_section)
                or normalize_quote(item.quote) not in normalize_quote(text)
            ):
                raise InvalidEvaluationOutput(
                    f"A evidência nova de {target.item_type.value} não foi localizada no artigo."
                )

    def _refresh_synthesis(self, criteria: tuple[Criterion, ...]) -> ReviewState:
        if self.synthesis_refresher is not None:
            return self.synthesis_refresher.refresh(criteria)
        model_spec = self.context.evaluator(self.slot).model
        checkpoints = (
            RunWholeDocumentCheckpoints(
                self.checkpoints.run_id,
                self.checkpoints.task_id,
                self.slot,
                model_spec,
                self.checkpoints.round_number,
            )
            if self.context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT
            else RunSynthesisCheckpoints(
                self.checkpoints.run_id,
                self.checkpoints.task_id,
                self.slot,
                model_spec,
                self.checkpoints.round_number,
            )
        )
        if self.context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT:
            return WholeDocumentStep(
                self.context,
                self.slot,
                self.factory,
                checkpoints,
            ).execute(refresh=criteria, mark_changed=True)
        return SynthesisStep(
            self.context,
            self.slot,
            self.factory,
            checkpoints,
        ).execute(refresh=criteria, mark_changed=True)


@dataclass(frozen=True)
class RunRevisionCheckpoints:
    """Checkpoints de revisão com posse do Run e cópia dos vereditos inalterados."""

    run_id: str
    task_id: str
    slot: EvaluatorSlot
    mode: EvaluationMode
    model_spec: ModelSpec
    round_number: int

    def assert_owned(self) -> None:
        Run.for_evaluation(self.run_id, self.task_id)

    def _round(self, number: int) -> ReviewRound | None:
        self.assert_owned()
        row = ReviewRound.objects.filter(
            run_id=self.run_id,
            evaluator_slot=self.slot,
            round_number=number,
        ).first()
        if row is not None and row.mode != self.mode:
            raise RunConflict("O modo da rodada não corresponde ao snapshot do Run.")
        return row

    def read_previous_state(self) -> ReviewState:
        row = self._round(self.round_number - 1)
        if row is None:
            raise RunConflict("A rodada anterior necessária para revisão não existe.")
        return row.state

    def read_previous_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        row = self._round(self.round_number - 1)
        if row is None:
            raise RunConflict("A rodada anterior necessária para revisão não existe.")
        return {
            (ItemType(item.item_type), item.item_key): item.item
            for item in JudgeVerdict.objects.filter(round=row)
        }

    def read_current_state(self) -> ReviewState | None:
        row = self._round(self.round_number)
        if row is None:
            return None
        if row.ready:
            raise RunConflict("Não é possível retomar uma rodada finalizada.")
        return row.state

    def read_current_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        row = self._round(self.round_number)
        if row is None:
            return {}
        return {
            (ItemType(item.item_type), item.item_key): item.item
            for item in JudgeVerdict.objects.filter(round=row)
        }

    def store_current_state(self, state: ReviewState) -> None:
        self.assert_owned()
        ReviewRound.store(
            self.run_id,
            self.task_id,
            slot=self.slot,
            round_number=self.round_number,
            mode=self.mode,
            model_spec=self.model_spec,
            state=state,
        )

    def carry_forward_valid_verdicts(self, *, excluded: set[tuple[ItemType, str]]) -> None:
        previous = self._round(self.round_number - 1)
        current = self._round(self.round_number)
        if previous is None or current is None:
            raise RunConflict("As rodadas necessárias para copiar os vereditos não existem.")
        current_verdicts = self.read_current_verdicts()
        for row in JudgeVerdict.objects.filter(round=previous):
            key = (ItemType(row.item_type), row.item_key)
            if key in excluded or row.verdict != Verdict.VALID or key in current_verdicts:
                continue
            JudgeVerdict.record(
                current.pk,
                self.task_id,
                item=row.item,
                source=VerdictSource(row.source),
                judge_model=ModelSpec.model_validate(row.judge_model)
                if row.judge_model is not None
                else None,
            )

    def mark_unresolved(self, items: tuple[ItemRef, ...]) -> ReviewState:
        row = self._round(self.round_number)
        if row is None:
            raise RunConflict("A rodada a encerrar não existe.")
        updated = ReviewRound.mark_unresolved(row.pk, self.task_id, items)
        return updated.state

    def has_pending_items(self) -> bool:
        state = self.read_current_state()
        if state is None:
            return False
        unresolved = {(item.item_type, item.item_key) for item in state.unresolved}
        return any(
            verdict.verdict is Verdict.INVALID and key not in unresolved
            for key, verdict in self.read_current_verdicts().items()
        )


@dataclass(frozen=True)
class MarkUnresolvedStep:
    """Marca como unresolved os itens que continuam inválidos após o limite."""

    checkpoints: RevisionCheckpoints
    max_revisions: int | None = None

    def execute(self) -> tuple[ItemRef, ...]:
        max_revisions = _configured_max_revisions(self.max_revisions)
        self.checkpoints.assert_owned()
        state = self.checkpoints.read_current_state()
        if state is None:
            return ()
        existing = {(item.item_type, item.item_key) for item in state.unresolved}
        verdicts = self.checkpoints.read_current_verdicts()
        invalid = tuple(
            key
            for key, verdict in verdicts.items()
            if verdict.verdict is Verdict.INVALID and key not in existing
        )
        if self.checkpoints.round_number < max_revisions + 1:
            if invalid:
                raise InvalidEvaluationOutput("Ainda há rodadas de revisão permitidas.")
            return state.unresolved
        items = tuple(ItemRef(item_type=key[0], item_key=key[1]) for key in invalid)
        if items:
            state = self.checkpoints.mark_unresolved(items)
        return state.unresolved


def has_pending_items(checkpoints: RevisionCheckpoints) -> bool:
    """Consulta o banco/checkpoint da rodada atual; não depende do output do Loop."""
    if isinstance(checkpoints, RunRevisionCheckpoints):
        return checkpoints.has_pending_items()
    state = checkpoints.read_current_state()
    if state is None:
        return False
    unresolved = {(item.item_type, item.item_key) for item in state.unresolved}
    return any(
        verdict.verdict is Verdict.INVALID and key not in unresolved
        for key, verdict in checkpoints.read_current_verdicts().items()
    )


def no_pending_items(checkpoints: RevisionCheckpoints) -> bool:
    return not has_pending_items(checkpoints)


def _configured_max_revisions(value: int | None) -> int:
    if value is not None:
        return value
    from projects.correction.metis.config import settings

    return settings.max_revision_rounds


def _find_item(
    state: ReviewState, ref: ItemRef
) -> Observation | CrossCheckResult | CriterionSynthesis:
    candidates: list[Observation | CrossCheckResult | CriterionSynthesis]
    if ref.item_type is ItemType.OBSERVATION:
        candidates = [item for item in state.observations if item.id == ref.item_key]
    elif ref.item_type is ItemType.CHECK:
        candidates = [item for item in state.cross_checks if item.id == ref.item_key]
    else:
        candidates = [item for item in state.criteria if item.criterion_key.value == ref.item_key]
    if len(candidates) != 1:
        raise InvalidEvaluationOutput("A rodada não contém exatamente o item a revisar.")
    return candidates[0]


def _parse_replacement(
    target: ItemRef,
    replacement: Observation | CrossCheckResult | CriterionSynthesis,
) -> Observation | CrossCheckResult | CriterionSynthesis:
    """Valida de novo contra o tipo do alvo: na união, o modelo pode ter casado outro tipo."""
    data = replacement.model_dump(mode="python")
    try:
        if target.item_type is ItemType.OBSERVATION:
            return Observation.model_validate(data)
        if target.item_type is ItemType.CHECK:
            return CrossCheckResult.model_validate(data)
        return CriterionSynthesis.model_validate(data)
    except (TypeError, ValueError) as exc:
        raise InvalidEvaluationOutput("A substituição não respeita o schema do item.") from exc


def _validate_identity(
    original: Observation | CrossCheckResult | CriterionSynthesis,
    replacement: Observation | CrossCheckResult | CriterionSynthesis,
    target: ItemRef,
) -> None:
    if type(original) is not type(replacement):
        raise InvalidEvaluationOutput("A substituição mudou o tipo do item revisado.")
    if isinstance(original, Observation) and isinstance(replacement, Observation):
        if (
            replacement.id != original.id
            or replacement.section_id != original.section_id
            or replacement.role is not original.role
        ):
            raise InvalidEvaluationOutput("A substituição mudou a identidade da observação.")
    elif isinstance(original, CrossCheckResult) and isinstance(replacement, CrossCheckResult):
        if replacement.id != original.id or replacement.kind is not original.kind:
            raise InvalidEvaluationOutput("A substituição mudou a identidade da checagem.")
    elif isinstance(original, CriterionSynthesis) and isinstance(replacement, CriterionSynthesis):
        if replacement.criterion_key.value != target.item_key:
            raise InvalidEvaluationOutput("A substituição mudou o critério da síntese.")


def _attach_evidence(
    item: Observation | CrossCheckResult | CriterionSynthesis,
    evidence: tuple[Evidence, ...],
    context: EvaluationContext,
) -> Observation | CrossCheckResult | CriterionSynthesis:
    if isinstance(item, CriterionSynthesis) and context.evaluation_mode is EvaluationMode.SECTIONED:
        return item
    combined = {(entry.quote, entry.section_id): entry for entry in item.evidence}
    combined.update({(entry.quote, entry.section_id): entry for entry in evidence})
    return item.model_copy(update={"evidence": tuple(combined.values())})


def _replace_item(
    state: ReviewState,
    ref: ItemRef,
    replacement: Observation | CrossCheckResult | CriterionSynthesis,
) -> ReviewState:
    data: dict[str, Any] = state.model_dump(mode="python")
    if ref.item_type is ItemType.OBSERVATION:
        if not isinstance(replacement, Observation):
            raise InvalidEvaluationOutput("Substituição incompatível com observação.")
        replacement_data = replacement.model_dump(mode="python")
        data["observations"] = [
            replacement_data if item["id"] == ref.item_key else item
            for item in data["observations"]
        ]
    elif ref.item_type is ItemType.CHECK:
        if not isinstance(replacement, CrossCheckResult):
            raise InvalidEvaluationOutput("Substituição incompatível com checagem.")
        replacement_data = replacement.model_dump(mode="python")
        data["cross_checks"] = [
            replacement_data if item["id"] == ref.item_key else item
            for item in data["cross_checks"]
        ]
    else:
        if not isinstance(replacement, CriterionSynthesis):
            raise InvalidEvaluationOutput("Substituição incompatível com síntese.")
        replacement_data = replacement.model_dump(mode="python")
        data["criteria"] = [
            replacement_data if item["criterion_key"].value == ref.item_key else item
            for item in data["criteria"]
        ]
    return ReviewState.model_validate(data)


def _dependent_criteria(previous: ReviewState, current: ReviewState) -> tuple[Criterion, ...]:
    refs = {
        (item.item_type, item.item_key)
        for item in current.changed_items
        if item.item_type in {ItemType.OBSERVATION, ItemType.CHECK}
    }
    affected = {
        item.criterion_key
        for state in (previous, current)
        for item in state.criteria
        if any((ItemType.OBSERVATION, item_id) in refs for item_id in item.observation_ids)
        or any((ItemType.CHECK, item_id) in refs for item_id in item.check_ids)
    }
    return tuple(sorted(affected, key=lambda key: key.value))


def _relevant_sections(
    context: EvaluationContext,
    state: ReviewState,
    target: ItemRef,
) -> list[dict[str, object]]:
    all_sections = {section.id: section for section in context.article.sections}
    ids: set[str] = set()
    item = _find_item(state, target)
    if isinstance(item, Observation):
        ids.add(item.section_id)
    elif isinstance(item, CrossCheckResult):
        ids.update(evidence.section_id for evidence in item.evidence)
    elif context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT:
        ids.update(all_sections)
    else:
        observations = {value.id: value for value in state.observations}
        checks = {value.id: value for value in state.cross_checks}
        for observation_id in item.observation_ids:
            if observation_id in observations:
                ids.add(observations[observation_id].section_id)
        for check_id in item.check_ids:
            if check_id in checks:
                ids.update(evidence.section_id for evidence in checks[check_id].evidence)
    if not ids:
        ids.update(all_sections)
    return [
        section.model_dump(mode="json") for section in context.article.sections if section.id in ids
    ]
