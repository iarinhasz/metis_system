"""Cadeia de validação determinística das saídas de cada avaliador."""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import ValidationError

from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    Evidence,
    Issue,
    ItemType,
    ItemVerdict,
    ReviewState,
    Verdict,
)
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.pipeline.errors import InvalidEvaluationOutput

type IssueCategory = Literal[
    "ungrounded", "factual_error", "contradiction", "rubric_mismatch", "off_topic"
]


@dataclass(frozen=True)
class _Finding:
    item_type: ItemType
    item_key: str
    issue: Issue


class _OutputValidator(Protocol):
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]: ...


def normalize_quote(value: str) -> str:
    """Normaliza espaços e hifenização de fim de linha sem alterar palavras."""
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("\u00ad", "")
    normalized = re.sub(r"(?<=[\w])[-‐‑‒–—]\s*(?:\r\n|\r|\n)+\s*(?=[\w])", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_words(value: str) -> str:
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _finding(
    item_type: ItemType,
    item_key: str,
    *,
    category: IssueCategory,
    excerpt: str,
    reason: str,
) -> _Finding:
    return _Finding(
        item_type,
        item_key,
        Issue(category=category, excerpt=excerpt[:20_000] or "saída", reason=reason),
    )


class _GradeValidator:
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]:
        scales = {item.key: item.grades for item in context.evaluation_config.criteria}
        return tuple(
            _finding(
                ItemType.CRITERION,
                item.criterion_key.value,
                category="rubric_mismatch",
                excerpt=f"nota {item.grade}",
                reason="A nota não pertence à escala permitida para este critério.",
            )
            for item in state.criteria
            if item.grade not in scales[item.criterion_key]
        )


class _CriteriaCompletenessValidator:
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]:
        paper = next(
            item
            for item in context.evaluation_config.paper_types
            if item.paper_type is context.profile.paper_type
        )
        active = set(paper.active)
        present = {item.criterion_key for item in state.criteria}
        missing = active - present
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise InvalidEvaluationOutput(f"Faltam sínteses para os critérios ativos: {names}.")
        return tuple(
            _finding(
                ItemType.CRITERION,
                item.criterion_key.value,
                category="rubric_mismatch",
                excerpt=item.criterion_key.value,
                reason="O critério não está ativo para o tipo de artigo deste Run.",
            )
            for item in state.criteria
            if item.criterion_key not in active
        )


class _EvidenceValidator:
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]:
        sections = {item.id: item.text for item in context.article.sections}
        findings: list[_Finding] = []

        def check(
            item_type: ItemType,
            item_key: str,
            evidence: Evidence,
            *,
            expected_section: str | None = None,
        ) -> None:
            text = sections.get(evidence.section_id)
            if text is None:
                reason = "A evidência aponta para uma seção inexistente no documento."
            elif expected_section is not None and evidence.section_id != expected_section:
                reason = "A evidência da observação precisa pertencer à própria seção."
            elif normalize_quote(evidence.quote) not in normalize_quote(text):
                reason = "O trecho citado não existe na seção indicada do documento."
            else:
                return
            findings.append(
                _finding(
                    item_type,
                    item_key,
                    category="ungrounded",
                    excerpt=evidence.quote,
                    reason=reason,
                )
            )

        for observation in state.observations:
            for evidence in observation.evidence:
                check(
                    ItemType.OBSERVATION,
                    observation.id,
                    evidence,
                    expected_section=observation.section_id,
                )
        for check_result in state.cross_checks:
            for evidence in check_result.evidence:
                check(ItemType.CHECK, check_result.id, evidence)
        for criterion in state.criteria:
            if context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT:
                if not criterion.evidence:
                    findings.append(
                        _finding(
                            ItemType.CRITERION,
                            criterion.criterion_key.value,
                            category="ungrounded",
                            excerpt=criterion.justification,
                            reason="A síntese whole_document precisa de evidência direta.",
                        )
                    )
                for evidence in criterion.evidence:
                    check(ItemType.CRITERION, criterion.criterion_key.value, evidence)
            elif criterion.evidence:
                findings.append(
                    _finding(
                        ItemType.CRITERION,
                        criterion.criterion_key.value,
                        category="ungrounded",
                        excerpt=criterion.evidence[0].quote,
                        reason="No modo sectioned, a síntese deve apontar para itens por ID.",
                    )
                )
        observation_sections = {item.id: item.section_id for item in state.observations}
        for revision in state.revisions:
            for evidence in revision.evidence:
                check(
                    revision.item_type,
                    revision.item_key,
                    evidence,
                    expected_section=(
                        observation_sections.get(revision.item_key)
                        if revision.item_type is ItemType.OBSERVATION
                        else None
                    ),
                )
        return tuple(findings)


class _InternalReferencesValidator:
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]:
        observations = {item.id: item for item in state.observations}
        checks = {item.id: item for item in state.cross_checks}
        findings: list[_Finding] = []
        for item in state.criteria:
            key = item.criterion_key.value
            if context.evaluation_mode is EvaluationMode.WHOLE_DOCUMENT:
                if item.observation_ids or item.check_ids:
                    findings.append(
                        _finding(
                            ItemType.CRITERION,
                            key,
                            category="ungrounded",
                            excerpt=key,
                            reason=(
                                "O modo whole_document usa evidências diretas, não IDs internos."
                            ),
                        )
                    )
                continue
            if len(item.observation_ids) != len(set(item.observation_ids)):
                findings.append(
                    _finding(
                        ItemType.CRITERION,
                        key,
                        category="ungrounded",
                        excerpt=key,
                        reason="A síntese repete IDs de observação.",
                    )
                )
            if len(item.check_ids) != len(set(item.check_ids)):
                findings.append(
                    _finding(
                        ItemType.CRITERION,
                        key,
                        category="ungrounded",
                        excerpt=key,
                        reason="A síntese repete IDs de checagem.",
                    )
                )
            for item_id in item.observation_ids:
                if (
                    item_id not in observations
                    or item.criterion_key not in observations[item_id].criteria
                ):
                    findings.append(
                        _finding(
                            ItemType.CRITERION,
                            key,
                            category="ungrounded",
                            excerpt=item_id,
                            reason=(
                                "A síntese cita observação ausente ou não associada ao critério."
                            ),
                        )
                    )
            for item_id in item.check_ids:
                if item_id not in checks or item.criterion_key not in checks[item_id].criteria:
                    findings.append(
                        _finding(
                            ItemType.CRITERION,
                            key,
                            category="ungrounded",
                            excerpt=item_id,
                            reason="A síntese cita checagem ausente ou não associada ao critério.",
                        )
                    )
        return tuple(findings)


class _JustificationValidator:
    def validate(self, state: ReviewState, context: EvaluationContext) -> tuple[_Finding, ...]:
        questions = {item.key: item.question for item in context.evaluation_config.criteria}
        return tuple(
            _finding(
                ItemType.CRITERION,
                item.criterion_key.value,
                category="rubric_mismatch",
                excerpt=item.justification,
                reason="A justificativa está vazia ou apenas repete a pergunta do critério.",
            )
            for item in state.criteria
            if not item.justification.strip()
            or _normalize_words(item.justification)
            == _normalize_words(questions[item.criterion_key])
        )


class ValidatorChain:
    """Valida o schema e executa regras puras, agrupando falhas por item."""

    def __init__(self, context: EvaluationContext) -> None:
        self.context = context
        self.validators: tuple[_OutputValidator, ...] = (
            _GradeValidator(),
            _CriteriaCompletenessValidator(),
            _EvidenceValidator(),
            _InternalReferencesValidator(),
            _JustificationValidator(),
        )

    def validate(self, candidate: object) -> tuple[ItemVerdict, ...]:
        try:
            state = ReviewState.model_validate(candidate)
        except (TypeError, ValueError, ValidationError) as exc:
            raise InvalidEvaluationOutput("A rodada persistida não respeita o schema E4.") from exc
        grouped: dict[tuple[ItemType, str], list[Issue]] = defaultdict(list)
        for validator in self.validators:
            for finding in validator.validate(state, self.context):
                issues = grouped[(finding.item_type, finding.item_key)]
                if finding.issue not in issues:
                    issues.append(finding.issue)
        return tuple(
            ItemVerdict(
                item_type=item_type,
                item_key=item_key,
                verdict=Verdict.INVALID,
                issues=tuple(issues),
            )
            for (item_type, item_key), issues in grouped.items()
        )


class ValidationCheckpoints(Protocol):
    """Leitura e gravação auditável dos vereditos da rodada atual."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> object: ...

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]: ...

    def record(self, item: ItemVerdict) -> None: ...


@dataclass(frozen=True)
class ValidateStep:
    """Executa validadores sem LLM e checkpointa apenas os itens recusados."""

    context: EvaluationContext
    checkpoints: ValidationCheckpoints

    def execute(self) -> tuple[ItemVerdict, ...]:
        self.checkpoints.assert_owned()
        invalid = ValidatorChain(self.context).validate(self.checkpoints.read_state())
        existing = self.checkpoints.read_verdicts()
        pending = tuple(item for item in invalid if (item.item_type, item.item_key) not in existing)
        for item in pending:
            self.checkpoints.record(item)
        return pending


@dataclass(frozen=True)
class RunValidationCheckpoints:
    """Adapta o armazenamento de vereditos à rodada 1 do avaliador."""

    run_id: str
    task_id: str
    slot: EvaluatorSlot
    mode: EvaluationMode
    round_number: int = 1

    def assert_owned(self) -> None:
        from projects.correction.attempts.models import Run

        Run.for_evaluation(self.run_id, self.task_id)

    def _round(self) -> ReviewRound:
        from projects.correction.queries.attempts.run import RunConflict

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
            raise RunConflict("Não é possível validar uma rodada já finalizada.")
        return row

    def read_state(self) -> object:
        from projects.correction.agents.schemas.evaluation import ReviewState

        row = self._round()
        return {name: getattr(row, name) for name in ReviewState.model_fields}

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        row = self._round()
        return {
            (ItemType(item.item_type), item.item_key): item.item
            for item in JudgeVerdict.objects.filter(round=row)
        }

    def record(self, item: ItemVerdict) -> None:
        from projects.correction.agents.schemas.evaluation import VerdictSource

        row = self._round()
        JudgeVerdict.record(
            row.pk,
            self.task_id,
            item=item,
            source=VerdictSource.VALIDATOR,
        )
