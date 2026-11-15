"""Passes do avaliador por seção, com checkpoints para retomar o E4."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    Observation,
    ReviewState,
    SectionObservations,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec
from projects.correction.attempts.models import Run
from projects.correction.evaluation.context import EvaluationContext
from projects.correction.evaluation.models import ReviewRound
from projects.correction.metis.concurrency import bounded_map
from projects.correction.pipeline.errors import InvalidEvaluationOutput
from projects.correction.queries.attempts.run import RunConflict
from projects.correction.questions.document_map import MapSection

MAX_SECTION_CHARS = 24_000


class ReviewCheckpoints(Protocol):
    """Acesso à posse do E4 e ao checkpoint da rodada atual."""

    def assert_owned(self) -> None: ...

    def read_state(self) -> ReviewState: ...

    def store_state(self, state: ReviewState) -> None: ...


@dataclass(frozen=True)
class _SectionResult:
    observations: tuple[Observation, ...]
    error: Exception | None = None


@dataclass(frozen=True)
class SectionPassStep:
    """Avalia as seções de um slot e persiste cada seção concluída."""

    context: EvaluationContext
    slot: EvaluatorSlot
    factory: AgentFactory
    checkpoints: ReviewCheckpoints
    max_workers: int
    max_section_chars: int = MAX_SECTION_CHARS

    def __post_init__(self) -> None:
        if self.max_workers < 1 or self.max_section_chars < 1:
            raise ValueError("Os limites do passe por seção devem ser positivos.")
        article_sections = {section.id for section in self.context.article.sections}
        map_sections = {section.id for section in self.context.document_map.sections}
        if article_sections != map_sections:
            raise ValueError("O mapa e o artigo precisam ter as mesmas seções.")

    def execute(self) -> ReviewState:
        state = self.checkpoints.read_state()
        existing = {
            (observation.section_id, observation.role) for observation in state.observations
        }
        work: tuple[MapSection, ...] = tuple(
            section
            for section in self.context.document_map.sections
            if any(
                role is not SectionRole.OTHER and (section.id, role) not in existing
                for role in section.roles
            )
        )
        results = bounded_map(self._evaluate_section, work, self.max_workers)
        errors: list[Exception] = []
        for result in results:
            if result.observations:
                state = self._merge(state, result.observations)
                self.checkpoints.store_state(state)
            if result.error is not None:
                errors.append(result.error)
        if errors:
            raise errors[0]
        return state

    def _evaluate_section(self, map_section: MapSection) -> _SectionResult:
        section_id = map_section.id
        article_section = next(
            section for section in self.context.article.sections if section.id == section_id
        )
        current_state = self.checkpoints.read_state()
        existing_roles = {
            observation.role
            for observation in current_state.observations
            if observation.section_id == section_id
        }
        observations: list[Observation] = []
        try:
            role_criteria = self._role_criteria()
            for role in map_section.roles:
                if role is SectionRole.OTHER or role in existing_roles:
                    continue
                if role not in role_criteria:
                    raise InvalidEvaluationOutput(
                        "O método não define critérios para um papel atribuído à seção."
                    )
                observations.extend(
                    self._evaluate_role(
                        section_id=section_id,
                        title=map_section.title,
                        role=role,
                        section_text=article_section.text,
                        criteria=role_criteria[role],
                        map_payload=self.context.document_map.model_dump(mode="json"),
                    )
                )
            return _SectionResult(tuple(observations))
        except Exception as exc:
            return _SectionResult(tuple(observations), exc)

    def _role_criteria(self) -> dict[SectionRole, tuple[dict[str, object], ...]]:
        paper_type = self.context.profile.paper_type
        paper_config = next(
            (
                item
                for item in self.context.evaluation_config.paper_types
                if item.paper_type is paper_type
            ),
            None,
        )
        if paper_config is None:
            raise InvalidEvaluationOutput("O método não cobre o tipo de artigo do Run.")
        criterion_config = {item.key: item for item in self.context.evaluation_config.criteria}
        rubric_fields = {field.key: field for field in self.context.question.rubric_fields}
        result: dict[SectionRole, tuple[dict[str, object], ...]] = {}
        for section_criteria in paper_config.sections:
            items: list[dict[str, object]] = []
            for key in section_criteria.criteria:
                config = criterion_config[key]
                rubric = rubric_fields.get(key.value)
                items.append(
                    {
                        "key": key.value,
                        "label": config.label,
                        "question": config.question,
                        "grades": config.grades,
                        "rubric_text": rubric.rubric_text if rubric is not None else None,
                    }
                )
            result[section_criteria.role] = tuple(items)
        return result

    def _evaluate_role(
        self,
        *,
        section_id: str,
        title: str,
        role: SectionRole,
        section_text: str,
        criteria: Sequence[dict[str, object]],
        map_payload: dict[str, object],
    ) -> tuple[Observation, ...]:
        chunks = split_section_text(section_text, max_chars=self.max_section_chars)
        result: list[Observation] = []
        for chunk_index, chunk in enumerate(chunks):
            self.checkpoints.assert_owned()
            prompt = json.dumps(
                {
                    "document_map": map_payload,
                    "target_section": {
                        "id": section_id,
                        "title": title,
                        "role": role.value,
                        "part": chunk_index + 1,
                        "parts": len(chunks),
                    },
                    "criteria": criteria,
                },
                ensure_ascii=False,
            )
            runner = self.factory.section_reviewer(
                self.slot.value,
                role.value,
                output_schema=SectionObservations,
                spec=self.context.evaluator(self.slot).model,
            )
            response = runner.run(AgentPayload(prompt, article=chunk))
            if not response.valid or not isinstance(response.content, SectionObservations):
                raise InvalidEvaluationOutput("O passe por seção retornou uma saída inválida.")
            output = response.content
            allowed_criteria = {item["key"] for item in criteria}
            output_ids = [item.id for item in output.observations]
            if output.section_id != section_id or len(output_ids) != len(set(output_ids)):
                raise InvalidEvaluationOutput(
                    "A saída do passe não corresponde à seção solicitada."
                )
            for observation in output.observations:
                if (
                    observation.section_id != section_id
                    or observation.role is not role
                    or not {criterion.value for criterion in observation.criteria}
                    <= allowed_criteria
                ):
                    raise InvalidEvaluationOutput(
                        "A saída do passe contém seção, papel ou critério incompatível."
                    )
                result.append(
                    observation.model_copy(
                        update={
                            "id": (f"{section_id}:{role.value}:{chunk_index + 1}:{observation.id}")
                        }
                    )
                )
        return tuple(result)

    @staticmethod
    def _merge(state: ReviewState, additions: tuple[Observation, ...]) -> ReviewState:
        observations = {item.id: item for item in state.observations}
        for item in additions:
            current = observations.get(item.id)
            if current is not None and current != item:
                raise InvalidEvaluationOutput(
                    "Ids de observação duplicados com conteúdos distintos."
                )
            observations[item.id] = item
        return ReviewState.model_validate(
            {
                **state.model_dump(mode="python"),
                "observations": tuple(observations.values()),
            }
        )


def split_section_text(text: str, *, max_chars: int = MAX_SECTION_CHARS) -> tuple[str, ...]:
    """Divide texto longo sem atravessar parágrafos quando há uma fronteira disponível.

    As subseções já chegam como seções independentes em ``ExtractedDocument`` e são avaliadas
    separadamente. Aqui dividimos apenas o texto de uma seção que, sozinha, excede o limite.
    Dentro dela, preferimos parágrafos, depois linhas, depois palavras; só cortamos no limite
    exato quando não há fronteira anterior.
    """
    if max_chars < 1:
        raise ValueError("max_chars deve ser positivo.")
    if len(text) <= max_chars:
        return (text,) if text else ()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary <= start:
                boundary = text.rfind("\n", start, end)
            if boundary <= start:
                boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end])
        start = end
    return tuple(chunks)


@dataclass(frozen=True)
class RunReviewCheckpoints:
    """Implementação persistente dos checkpoints da primeira rodada do E4."""

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
