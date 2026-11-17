"""Julgamento cruzado das saídas dos avaliadores, com persistência por item."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    ItemRef,
    ItemType,
    ItemVerdict,
    JudgeReport,
    ReviewState,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext, divergence_hints
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict


class JudgeCheckpoints(Protocol):
    """Checkpoint de uma rodada do avaliador e leitura de divergências entre slots."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]: ...

    def read_slot_grades(self) -> Mapping[EvaluatorSlot, Mapping[str, int]]: ...

    def record(self, item: ItemVerdict, judge_model: ModelSpec) -> None: ...


@dataclass(frozen=True)
class JudgeStep:
    """Julga apenas itens sem veredito; apontamentos do validador não são reenviados."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: JudgeCheckpoints

    def execute(self) -> tuple[ItemVerdict, ...]:
        self.checkpoints.assert_owned()
        state = self.checkpoints.read_state()
        existing = self.checkpoints.read_verdicts()
        items = _state_items(state)
        pending = tuple(
            ItemRef(item_type=item_type, item_key=item_key)
            for item_type, item_key in items
            if (item_type, item_key) not in existing
        )
        if not pending:
            return ()

        evaluator_spec = self.context.evaluator(self.slot).model
        judge_spec = self.factory.models.judge_for(evaluator_spec)
        slot_grades = {
            slot.value: grades for slot, grades in self.checkpoints.read_slot_grades().items()
        }
        hints = divergence_hints(slot_grades).get(self.slot, {})
        request = {
            "slot": self.slot.value,
            "review": state.model_dump(mode="json"),
            "items_to_judge": [item.model_dump(mode="json") for item in pending],
            "divergence_hints": hints,
        }
        payload = AgentPayload(
            json.dumps(request, ensure_ascii=False),
            article=self.context.article.model_dump_json(),
        )
        self.checkpoints.assert_owned()
        verdicts = _normalized(self._run(payload), pending)
        invalid_excerpts = _invalid_excerpts(verdicts, items)
        missing = [key for key in _expected_keys(pending) if key not in verdicts]
        if invalid_excerpts or missing:
            correction = {
                "original_request": request,
                "excerpt_errors": invalid_excerpts,
                "missing_items": [
                    {"item_type": item_type.value, "item_key": item_key}
                    for item_type, item_key in sorted(missing)
                ],
            }
            self.checkpoints.assert_owned()
            verdicts |= _normalized(
                self._run(
                    AgentPayload(
                        json.dumps(correction, ensure_ascii=False),
                        article=self.context.article.model_dump_json(),
                    )
                ),
                pending,
            )

        cleaned = _discard_invalid_excerpts(verdicts, pending, items)
        for item in cleaned:
            self.checkpoints.record(item, judge_spec)
        return cleaned

    def _run(self, payload: AgentPayload) -> JudgeReport:
        result = self.factory.judge(
            self.context.evaluator(self.slot).model,
            output_schema=JudgeReport,
        ).run(payload)
        if not result.valid or not isinstance(result.content, JudgeReport):
            raise InvalidEvaluationOutput("O juiz retornou uma saída inválida.")
        return result.content


def _state_items(state: ReviewState) -> dict[tuple[ItemType, str], str]:
    items: dict[tuple[ItemType, str], str] = {}
    for observation in state.observations:
        items[(ItemType.OBSERVATION, observation.id)] = "\n".join(
            (
                observation.kind,
                observation.statement,
                observation.severity,
                *(evidence.quote for evidence in observation.evidence),
            )
        )
    for check in state.cross_checks:
        items[(ItemType.CHECK, check.id)] = "\n".join(
            (
                check.kind,
                check.verdict,
                check.severity,
                *(evidence.quote for evidence in check.evidence),
            )
        )
    for synthesis in state.criteria:
        items[(ItemType.CRITERION, synthesis.criterion_key.value)] = "\n".join(
            (
                f"nota {synthesis.grade}",
                synthesis.justification,
                *(evidence.quote for evidence in synthesis.evidence),
            )
        )
    for revision in state.revisions:
        key = (revision.item_type, revision.item_key)
        if key in items and revision.evidence:
            items[key] = "\n".join(
                (items[key], *(evidence.quote for evidence in revision.evidence))
            )
    return items


type Verdicts = dict[tuple[ItemType, str], ItemVerdict]


def _normalized(report: JudgeReport, pending: tuple[ItemRef, ...]) -> Verdicts:
    """Os vereditos aproveitáveis, um por item pedido.

    Com modelos reais, o juiz repete ou inventa itens, aponta problemas num item que diz válido
    ou recusa sem dizer por quê; antes, qualquer desses casos derrubava o E4. Fica o primeiro
    veredito de cada item pedido, e o válido perde os apontamentos. A recusa sem justificativa
    vira válida em `_discard_invalid_excerpts`: sem o motivo, o avaliador não tem o que corrigir.
    """
    expected = _expected_keys(pending)
    verdicts: Verdicts = {}
    for item in report.items:
        key = (item.item_type, item.item_key)
        if key in expected and key not in verdicts:
            verdicts[key] = (
                item.model_copy(update={"issues": ()}) if item.verdict is Verdict.VALID else item
            )
    return verdicts


def _expected_keys(pending: tuple[ItemRef, ...]) -> set[tuple[ItemType, str]]:
    return {(item.item_type, item.item_key) for item in pending}


def _invalid_excerpts(
    verdicts: Verdicts,
    item_texts: dict[tuple[ItemType, str], str],
) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "item_type": item.item_type.value,
            "item_key": item.item_key,
            "excerpt": issue.excerpt,
        }
        for key, item in verdicts.items()
        for issue in item.issues
        if issue.excerpt not in item_texts[key]
    )


def _discard_invalid_excerpts(
    verdicts: Verdicts,
    pending: tuple[ItemRef, ...],
    item_texts: dict[tuple[ItemType, str], str],
) -> tuple[ItemVerdict, ...]:
    """Um veredito por item pedido: o item que o juiz não devolveu, ou que recusou sem um
    apontamento conferido no texto do item, fica válido."""
    cleaned: list[ItemVerdict] = []
    for ref in pending:
        key = (ref.item_type, ref.item_key)
        item = verdicts.get(key) or ItemVerdict(
            item_type=ref.item_type, item_key=ref.item_key, verdict=Verdict.VALID
        )
        valid_issues = tuple(issue for issue in item.issues if issue.excerpt in item_texts[key])
        cleaned.append(
            item.model_copy(
                update={
                    "verdict": Verdict.INVALID if valid_issues else Verdict.VALID,
                    "issues": valid_issues,
                }
            )
        )
    return tuple(cleaned)


@dataclass(frozen=True)
class RunJudgeCheckpoints:
    """Checkpoints persistentes e validação de posse para o julgamento da rodada."""

    run_id: str
    task_id: str
    slot: EvaluatorSlot
    mode: EvaluationMode = EvaluationMode.SECTIONED
    round_number: int = 1

    def assert_owned(self) -> None:
        Run.for_evaluation(self.run_id, self.task_id)

    def _round(self) -> ReviewRound:
        self.assert_owned()
        row = ReviewRound.objects.filter(
            run_id=self.run_id,
            evaluator_slot=self.slot,
            round_number=self.round_number,
        ).first()
        if row is None:
            raise RunConflict("A rodada ainda não existe para este avaliador.")
        if row.mode != self.mode:
            raise RunConflict("O modo da rodada não corresponde ao snapshot do Run.")
        if row.ready:
            raise RunConflict("Não é possível julgar uma rodada já finalizada.")
        return row

    def read_state(self) -> ReviewState:
        return self._round().state

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        row = self._round()
        return {
            (ItemType(item.item_type), item.item_key): item.item
            for item in JudgeVerdict.objects.filter(round=row)
        }

    def read_slot_grades(self) -> Mapping[EvaluatorSlot, Mapping[str, int]]:
        self._round()
        result: dict[EvaluatorSlot, dict[str, int]] = {}
        for row in ReviewRound.objects.filter(run_id=self.run_id, round_number=self.round_number):
            result[EvaluatorSlot(row.evaluator_slot)] = {
                item.criterion_key.value: item.grade for item in row.state.criteria
            }
        return result

    def record(self, item: ItemVerdict, judge_model: ModelSpec) -> None:
        row = self._round()
        JudgeVerdict.record(
            row.pk,
            self.task_id,
            item=item,
            source=VerdictSource.JUDGE,
            judge_model=judge_model,
        )
