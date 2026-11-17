"""E2 síncrono: passos Agno com checkpoints no Run e posse conferida a cada gravação."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from agno.workflow import Condition, Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput
from pydantic import TypeAdapter

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.prompts import template
from projects.correction.agents.schemas.profiling import FieldChoice
from projects.correction.agents.specs import ModelSpec, Role, validate_catalog
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunPurpose
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.document_map import DocumentMap, build_document_map
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.profile import (
    ArticleProfile,
    FrozenModel,
    QuestionSnapshot,
    ResolvedQuestion,
)
from projects.correction.questions.profiler import classify_field, classify_topic
from projects.correction.questions.resolver import resolve_question
from projects.correction.questions.section_roles import (
    SectionAssignment,
    classify_role,
    rule_based_roles,
)

ROLES = TypeAdapter(tuple[SectionAssignment, ...])
PROMPTS = ("profiler_field", "profiler_topic", "section_role_classifier")


class ProfilingResult(FrozenModel):
    question_id: UUID
    taxonomy_version: str
    uncertain: bool


@dataclass(frozen=True)
class Dependencies:
    run_id: str
    task_id: str
    factory: AgentFactory
    article: ExtractedDocument
    snapshot: dict[str, Any]

    def read(self) -> Run:
        return Run.for_profiling(self.run_id, self.task_id)

    def store(self, key: str, value: Any, *, question_id: UUID | None = None) -> None:
        Run.checkpoint_profile(
            self.run_id,
            self.task_id,
            key,
            value,
            question_id=question_id,
            prompt_versions=self.factory.prompt_versions,
        )

    @property
    def version(self) -> str:
        return str(self.snapshot["taxonomy_version"])

    @property
    def attempts(self) -> int:
        return int(self.snapshot["profiling"]["max_attempts"])

    @property
    def threshold(self) -> float:
        return float(self.snapshot["profiling"]["confidence_threshold"])


def _output[T](step_input: StepInput, name: str, expected: type[T]) -> T:
    previous = step_input.get_step_output(name)
    if previous is None or not previous.success or not isinstance(previous.content, expected):
        raise RuntimeError(f"O passo {name} não entregou a saída tipada esperada.")
    return previous.content


@dataclass(frozen=True)
class ClassifyFieldStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        saved = self.deps.read().profile.get("field_choice")
        if saved is not None:
            choice = FieldChoice.model_validate(saved)
        else:
            choice = classify_field(
                self.deps.article,
                factory=self.deps.factory,
                taxonomy_version=self.deps.version,
                max_attempts=self.deps.attempts,
            )
            self.deps.store("field_choice", choice.model_dump(mode="json"))
        return StepOutput(content=choice)


@dataclass(frozen=True)
class ClassifyTopicStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        saved = self.deps.read().profile.get("classification")
        if saved is not None:
            profile = ArticleProfile.model_validate(saved)
        else:
            field = _output(step_input, "classify_field", FieldChoice)
            profile = classify_topic(
                self.deps.article,
                field,
                factory=self.deps.factory,
                taxonomy_version=self.deps.version,
                max_attempts=self.deps.attempts,
            )
            self.deps.store("classification", profile.model_dump(mode="json"))
        return StepOutput(content=profile)


@dataclass(frozen=True)
class ResolveQuestionStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        saved = run.profile.get("resolution")
        if saved is not None:
            resolved = ResolvedQuestion.model_validate(saved)
        else:
            profile = _output(step_input, "classify_topic", ArticleProfile)
            if run.purpose == RunPurpose.RUBRIC_CHECK:
                draft = self.deps.snapshot.get("question")
                if not draft:
                    raise SetupRequired("O rubric check precisa do snapshot da Question rascunho.")
                question = QuestionSnapshot.model_validate(draft)
                if question.method != self.deps.snapshot["method"]:
                    raise SetupRequired("O método do rascunho difere do método do Run.")
                resolved = ResolvedQuestion(
                    question=question,
                    taxonomy_version=self.deps.version,
                    resolution_path=(),
                    uncertain=profile.confidence < self.deps.threshold,
                )
            else:
                resolved = resolve_question(
                    profile,
                    method=self.deps.snapshot["method"],
                    confidence_threshold=self.deps.threshold,
                )
            self.deps.store(
                "resolution", resolved.model_dump(mode="json"), question_id=resolved.question.id
            )
        return StepOutput(content=resolved)


@dataclass(frozen=True)
class RuleBasedRolesStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        saved = self.deps.read().profile.get("section_roles")
        if saved is not None:
            roles = ROLES.validate_python(saved)
        else:
            profile = _output(step_input, "classify_topic", ArticleProfile)
            roles = rule_based_roles(self.deps.article, profile.paper_type)
            self.deps.store("section_roles", ROLES.dump_python(roles, mode="json"))
        return StepOutput(content=roles)


@dataclass(frozen=True)
class HasAmbiguousRoles:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> bool:
        run = self.deps.read()
        return any(role.ambiguous for role in ROLES.validate_python(run.profile["section_roles"]))


@dataclass(frozen=True)
class ClassifyRolesStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        roles = list(ROLES.validate_python(run.profile["section_roles"]))
        profile = _output(step_input, "classify_topic", ArticleProfile)
        sections = {section.id: section for section in self.deps.article.sections}
        for index, role in enumerate(roles):
            if role.ambiguous:
                self.deps.read()  # Verifica a posse antes de abrir outra chamada paga.
                roles[index] = classify_role(
                    sections[role.section_id],
                    profile.paper_type,
                    factory=self.deps.factory,
                    confidence_threshold=self.deps.threshold,
                )
                self.deps.store("section_roles", ROLES.dump_python(tuple(roles), mode="json"))
        return StepOutput(content=tuple(roles))


@dataclass(frozen=True)
class DocumentMapStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        saved = run.profile.get("document_map")
        if saved is not None:
            document_map = DocumentMap.model_validate(saved)
        else:
            roles = ROLES.validate_python(run.profile["section_roles"])
            if any(role.ambiguous for role in roles):
                raise RuntimeError("Há papéis pendentes antes de montar o mapa.")
            document_map = build_document_map(self.deps.article, roles)
            self.deps.store("document_map", document_map.model_dump(mode="json"))
        return StepOutput(content=document_map)


@dataclass(frozen=True)
class PersistProfileStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        resolved = _output(step_input, "resolve_question", ResolvedQuestion)
        _output(step_input, "document_map", DocumentMap)
        self.deps.store("complete", True)
        return StepOutput(
            content=ProfilingResult(
                question_id=resolved.question.id,
                taxonomy_version=resolved.taxonomy_version,
                uncertain=resolved.uncertain,
            )
        )


def build_workflow(run_id: str, task_id: str, *, factory: AgentFactory) -> Workflow:
    run = Run.for_profiling(run_id, task_id)
    if run.extraction is None:
        raise SetupRequired("O E2 precisa da extração do E1 ligada ao Run.")
    if "profiling" not in run.config_snapshot:
        version = settings.profiling_taxonomy_version or TaxonomyNode.latest_version()
        if not version:
            raise SetupRequired("Carregue uma versão da taxonomia antes de executar o E2.")
        run = Run.initialize_profiling(
            run_id,
            task_id,
            {
                "taxonomy_version": version,
                "method": run.config_snapshot.get("method", settings.evaluation_method),
                "profiling": {
                    "max_attempts": settings.profiling_max_attempts,
                    "confidence_threshold": settings.profiling_confidence_threshold,
                },
                "model_specs": {
                    role.value: spec.model_dump(mode="json")
                    for role, spec in factory.models.specs.items()
                },
                "prompt_templates": {name: template(name) for name in PROMPTS},
                "prompt_versions": {},
            },
        )
    snapshot = run.config_snapshot
    factory.models.specs = validate_catalog(
        {
            Role(role): ModelSpec.model_validate(spec)
            for role, spec in snapshot["model_specs"].items()
        }
    )
    factory.prompt_templates = dict(snapshot["prompt_templates"])
    factory.on_prompt = lambda name, version: Run.record_profiling_prompt(
        run_id, task_id, name, version
    )
    # initialize_profiling devolve o model travado, sem select_related.
    extraction = Run.for_profiling(run_id, task_id).extraction
    assert extraction is not None
    deps = Dependencies(run_id, task_id, factory, extraction.document, snapshot)

    def step(name: str, executor: Any) -> Step:
        return Step(
            name=name,
            executor=executor,
            max_retries=0,
            human_review=HumanReview(on_error=OnError.fail),
        )

    return Workflow(
        name="profiling",
        telemetry=False,
        db=None,
        steps=[
            step("classify_field", ClassifyFieldStep(deps)),
            step("classify_topic", ClassifyTopicStep(deps)),
            step("resolve_question", ResolveQuestionStep(deps)),
            step("section_roles", RuleBasedRolesStep(deps)),
            Condition(
                name="ambiguous_roles",
                evaluator=HasAmbiguousRoles(deps),
                human_review=HumanReview(on_error=OnError.fail),
                steps=[step("classify_roles", ClassifyRolesStep(deps))],
            ),
            step("document_map", DocumentMapStep(deps)),
            step("persist", PersistProfileStep(deps)),
        ],
    )


def run_profiling(run_id: str, task_id: str, *, factory: AgentFactory) -> ProfilingResult:
    result = build_workflow(run_id, task_id, factory=factory).run(
        input={"run_id": run_id}, run_id=task_id
    )
    if not isinstance(result.content, ProfilingResult):
        raise RuntimeError("O workflow E2 não terminou com um perfil completo.")
    return result.content
