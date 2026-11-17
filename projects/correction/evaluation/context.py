"""Contexto congelado que os três avaliadores recebem para um Run."""

from collections.abc import Mapping
from typing import Any

from pydantic import Field, JsonValue

from projects.correction.agents.schemas.evaluation import EvaluationMode, EvaluatorSlot
from projects.correction.agents.specs import Family, ModelSpec, Role
from projects.correction.attempts.models import Run
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.criteria import EvaluationConfig, get_method
from projects.correction.questions.document_map import DocumentMap
from projects.correction.questions.profile import ArticleProfile, FrozenModel, QuestionSnapshot


class RelatedWork(FrozenModel):
    """Obra relacionada disponível para contextualizar a avaliação de originalidade."""

    title: str
    authors: tuple[str, ...] = ()
    year: str | None = None
    venue: str | None = None
    doi: str | None = None
    abstract: str | None = None


class EvaluatorContext(FrozenModel):
    """Entradas comuns e imutáveis de um dos slots A, B ou C."""

    slot: EvaluatorSlot
    model: ModelSpec


class EvaluationContext(FrozenModel):
    """Dados estáveis compartilhados pelos passos de avaliação de um Run."""

    article: ExtractedDocument
    profile: ArticleProfile
    question: QuestionSnapshot
    document_map: DocumentMap
    evaluation_config: EvaluationConfig
    evaluation_mode: EvaluationMode = EvaluationMode.SECTIONED
    evaluators: tuple[EvaluatorContext, ...] = Field(min_length=3, max_length=3)
    integrity_summary: dict[str, JsonValue] = Field(default_factory=dict)
    related_works: tuple[RelatedWork, ...] = ()

    def evaluator(self, slot: EvaluatorSlot | str) -> EvaluatorContext:
        selected = EvaluatorSlot(slot)
        return next(item for item in self.evaluators if item.slot is selected)


class EvaluationContextBuilder:
    """Valida e combina os snapshots do E1/E2 com a configuração do E4."""

    def __init__(
        self,
        run: Run,
        *,
        integrity_summary: Mapping[str, JsonValue] | None = None,
        related_works: tuple[RelatedWork, ...] = (),
        evaluation_mode: EvaluationMode | None = None,
    ) -> None:
        self.run = run
        self.integrity_summary = dict(integrity_summary or {})
        self.related_works = related_works
        self.evaluation_mode = evaluation_mode

    def _selected_mode(self) -> EvaluationMode:
        snapshot_mode = self.run.config_snapshot.get("evaluation_mode")
        if snapshot_mode is not None:
            try:
                return EvaluationMode(snapshot_mode)
            except (TypeError, ValueError) as exc:
                raise SetupRequired("O modo de avaliação do Run não é válido.") from exc
        if self.evaluation_mode is not None:
            return self.evaluation_mode
        from projects.correction.metis.config import settings

        return settings.evaluation_mode

    def snapshot(self) -> dict[str, Any]:
        """Configuração versionada pelo Run antes da primeira chamada do E4."""
        run = self.run
        if run.extraction is None:
            raise SetupRequired("O contexto de avaliação precisa da extração do E1.")
        question_data = run.config_snapshot.get("question")
        if not question_data:
            raise SetupRequired("O contexto de avaliação precisa do snapshot da Question.")
        question = QuestionSnapshot.model_validate(question_data)
        method = run.config_snapshot.get("method", question.method)
        if method != question.method:
            raise SetupRequired("O método da Question não corresponde ao método do Run.")
        config_data = run.config_snapshot.get("evaluation_config")
        try:
            config = (
                EvaluationConfig.model_validate(config_data) if config_data else get_method(method)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SetupRequired("O método de avaliação do Run não está configurado.") from exc
        if config.method != question.method:
            raise SetupRequired("O método da Question difere da configuração de avaliação.")
        raw_specs = run.config_snapshot.get("model_specs")
        if not isinstance(raw_specs, dict):
            raise SetupRequired("O Run não tem o snapshot dos modelos do E2.")
        specs = {
            slot.value: ModelSpec.model_validate(raw_specs[role.value]).model_dump(mode="json")
            for slot, role in (
                (EvaluatorSlot.A, Role.EVALUATOR_A),
                (EvaluatorSlot.B, Role.EVALUATOR_B),
                (EvaluatorSlot.C, Role.EVALUATOR_C),
            )
            if role.value in raw_specs
        }
        if len(specs) != 3:
            raise SetupRequired("O snapshot precisa definir os modelos dos slots A, B e C.")
        return {
            "evaluation_config": config.model_dump(mode="json"),
            "evaluation_models": specs,
            "evaluation_mode": self._selected_mode().value,
        }

    def build(self) -> EvaluationContext:
        run = self.run
        if run.extraction is None:
            raise SetupRequired("O contexto de avaliação precisa da extração do E1.")
        if not run.profile.get("complete"):
            raise SetupRequired("O contexto de avaliação precisa do perfil completo do E2.")

        snapshot = run.config_snapshot
        try:
            article = run.extraction.document
            profile = ArticleProfile.model_validate(run.profile["classification"])
            question = QuestionSnapshot.model_validate(snapshot["question"])
            document_map = DocumentMap.model_validate(run.profile["document_map"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SetupRequired("O Run não tem os snapshots válidos de E1 e E2.") from exc

        method = snapshot.get("method", question.method)
        if method != question.method:
            raise SetupRequired("O método da Question não corresponde ao método do Run.")
        config_data = snapshot.get("evaluation_config")
        try:
            evaluation_config = (
                EvaluationConfig.model_validate(config_data) if config_data else get_method(method)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SetupRequired("O método de avaliação do Run não está configurado.") from exc

        raw_specs = snapshot.get("evaluation_models") or snapshot.get("model_specs")
        if not isinstance(raw_specs, dict):
            raise SetupRequired("O Run não tem o snapshot dos modelos do E2.")
        slots = (
            (EvaluatorSlot.A, EvaluatorSlot.A.value, Role.EVALUATOR_A),
            (EvaluatorSlot.B, EvaluatorSlot.B.value, Role.EVALUATOR_B),
            (EvaluatorSlot.C, EvaluatorSlot.C.value, Role.EVALUATOR_C),
        )
        try:
            evaluators = tuple(
                EvaluatorContext(
                    slot=slot,
                    model=ModelSpec.model_validate(
                        raw_specs.get(slot_key, raw_specs.get(role.value))
                    ),
                )
                for slot, slot_key, role in slots
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SetupRequired(
                "O snapshot precisa definir os modelos dos slots A, B e C."
            ) from exc
        if evaluators[0].model.family is not Family.GPT:
            raise SetupRequired("O slot A precisa usar a família GPT.")
        if evaluators[1].model.family is not Family.GEMINI:
            raise SetupRequired("O slot B precisa usar a família Gemini.")

        if question.method != evaluation_config.method:
            raise SetupRequired("O método da Question difere da configuração de avaliação.")
        if profile.paper_type not in {item.paper_type for item in evaluation_config.paper_types}:
            raise SetupRequired("O tipo de artigo não está coberto pelo método de avaliação.")

        return EvaluationContext(
            article=article,
            profile=profile,
            question=question,
            document_map=document_map,
            evaluation_config=evaluation_config,
            evaluation_mode=self._selected_mode(),
            evaluators=evaluators,
            integrity_summary=self.integrity_summary,
            related_works=self.related_works,
        )


def divergence_hints(
    grades_by_slot: Mapping[EvaluatorSlot | str, Mapping[str, int]],
) -> dict[EvaluatorSlot, dict[str, tuple[int, ...]]]:
    """Expõe diferenças de nota para o juiz sem interpretá-las como erro."""
    normalized = {EvaluatorSlot(slot): dict(grades) for slot, grades in grades_by_slot.items()}
    hints: dict[EvaluatorSlot, dict[str, tuple[int, ...]]] = {}
    for slot, grades in normalized.items():
        other_slots = [other for other in normalized if other is not slot]
        slot_hints: dict[str, tuple[int, ...]] = {}
        for criterion, grade in grades.items():
            other_grades = tuple(
                normalized[other][criterion]
                for other in other_slots
                if criterion in normalized[other]
            )
            if other_grades and any(other_grade != grade for other_grade in other_grades):
                slot_hints[criterion] = other_grades
        hints[slot] = slot_hints
    return hints
