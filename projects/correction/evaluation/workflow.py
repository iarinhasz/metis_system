"""E5 com passos Agno, checkpoints duráveis e posse verificada antes das escritas."""

import json
from dataclasses import dataclass
from typing import Any

from agno.workflow import Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput
from pydantic import TypeAdapter

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.prompts import template
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.consolidation import MetaReview
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec, Role, validate_catalog
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.evaluation.aggregation import aggregate
from projects.correction.evaluation.contracts import (
    Aggregation,
    AggregationPolicy,
    ConsolidationResult,
    ReviewedSlot,
)
from projects.correction.evaluation.models import FinalReport, ReviewRound
from projects.correction.evaluation.report import (
    ReportContent,
    ReportVersions,
    build_report,
    reference_catalog,
    validate_meta_review,
)
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.criteria import EvaluationConfig, get_method
from projects.correction.questions.profile import QuestionSnapshot

REVIEWS = TypeAdapter(tuple[ReviewedSlot, ...])
SECTION_ROLES = TypeAdapter(dict[str, tuple[SectionRole, ...]])


@dataclass(frozen=True)
class Dependencies:
    run_id: str
    task_id: str
    factory: AgentFactory

    def read(self) -> Run:
        return Run.for_consolidation(self.run_id, self.task_id)

    def store(self, key: str, value: Any) -> None:
        Run.checkpoint_consolidation(self.run_id, self.task_id, key, value)

    def reviews(self) -> tuple[ReviewedSlot, ...]:
        return REVIEWS.validate_python(self.read().consolidation["reviews"])

    def aggregation(self) -> Aggregation:
        return Aggregation.model_validate(self.read().consolidation["aggregation"])


@dataclass(frozen=True)
class AggregateStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        saved = run.consolidation.get("aggregation")
        if saved is not None:
            result = Aggregation.model_validate(saved)
        else:
            result = aggregate(
                self.deps.reviews(),
                EvaluationConfig.model_validate(run.config_snapshot["evaluation_config"]),
                PaperType(run.profile["classification"]["paper_type"]),
                policy=AggregationPolicy.model_validate(
                    run.config_snapshot["consolidation"]["policy"]
                ),
            )
            self.deps.store("aggregation", result.model_dump(mode="json"))
        return StepOutput(content=result)


@dataclass(frozen=True)
class MetaReviewStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        if saved := run.consolidation.get("meta"):
            return StepOutput(content=MetaReview.model_validate(saved["review"]))
        aggregation = self.deps.aggregation()
        catalog = reference_catalog(self.deps.reviews(), aggregation)
        active = {score.criterion_key for score in aggregation.criteria}
        progress = run.consolidation.get("meta_progress", {"attempts": 0, "candidate": None})
        attempts = progress["attempts"]
        candidate = (
            MetaReview.model_validate(progress["candidate"])
            if progress["candidate"] is not None
            else None
        )
        warnings: tuple[str, ...] = ()
        if not catalog:
            candidate = MetaReview()
            warnings = ("no_valid_evidence_for_meta_review",)
        while catalog:
            if candidate is not None:
                cleaned, dropped = validate_meta_review(candidate, catalog, active)
                if not dropped:
                    candidate = cleaned
                    break
                if attempts >= 2:
                    candidate = cleaned
                    warnings = (f"meta_points_dropped:{dropped}",)
                    break
            elif attempts >= 2:
                candidate = MetaReview()
                warnings = ("meta_review_invalid_schema",)
                break
            self.deps.read()  # Não inicia outra chamada se a task já perdeu a posse.
            prompt = "Redija somente a narrativa; use apenas os ids do catálogo validado."
            if attempts:
                prompt += (
                    " A resposta anterior tinha schema inválido ou referências desconhecidas;"
                    " corrija usando somente as opções fornecidas."
                )
            result = self.deps.factory.meta_reviewer(output_schema=MetaReview).run(
                AgentPayload(
                    prompt,
                    article=json.dumps(
                        {
                            "aggregation": aggregation.model_dump(mode="json"),
                            "reference_catalog": {
                                ref: item.model_dump(mode="json") for ref, item in catalog.items()
                            },
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            attempts += 1
            candidate = (
                result.content if result.valid and isinstance(result.content, MetaReview) else None
            )
            self.deps.store(
                "meta_progress",
                {
                    "attempts": attempts,
                    "candidate": candidate.model_dump(mode="json") if candidate else None,
                },
            )
        assert candidate is not None
        self.deps.store("meta", {"review": candidate.model_dump(mode="json"), "warnings": warnings})
        return StepOutput(content=candidate)


@dataclass(frozen=True)
class ValidateMetaReviewStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        review = MetaReview.model_validate(self.deps.read().consolidation["meta"]["review"])
        aggregation = self.deps.aggregation()
        _, dropped = validate_meta_review(
            review,
            reference_catalog(self.deps.reviews(), aggregation),
            {item.criterion_key for item in aggregation.criteria},
        )
        if dropped:
            raise RuntimeError("A meta-revisão persistida contém referências não validadas.")
        return StepOutput(content=review)


@dataclass(frozen=True)
class BuildFinalReportStep:
    deps: Dependencies

    def __call__(self, step_input: StepInput) -> StepOutput:
        run = self.deps.read()
        assert run.extraction is not None
        reviews = self.deps.reviews()
        snapshot = run.config_snapshot
        calls = LLMCall.for_run(run.pk)
        prompts: dict[str, set[str]] = {
            name: {version} for name, version in snapshot.get("prompt_versions", {}).items()
        }
        for call in calls:
            prompts.setdefault(call.agent, set()).add(call.prompt_version)
        specs = {
            name: ModelSpec.model_validate(value) for name, value in snapshot["model_specs"].items()
        }
        specs.update({f"evaluator_{review.slot}": review.model_spec for review in reviews})
        content = build_report(
            run_id=run.pk,
            article=run.extraction.article,
            reviews=reviews,
            aggregation=self.deps.aggregation(),
            meta=MetaReview.model_validate(run.consolidation["meta"]["review"]),
            section_roles=SECTION_ROLES.validate_python(run.consolidation["section_roles"]),
            versions=ReportVersions(
                model_specs=specs,
                prompt_versions={key: tuple(sorted(values)) for key, values in prompts.items()},
                mode=reviews[0].mode,
                review_rounds={review.slot: review.round_number for review in reviews},
                evaluation_config=EvaluationConfig.model_validate(snapshot["evaluation_config"]),
                evaluation_config_origin=snapshot["consolidation"]["evaluation_config_origin"],
                question=QuestionSnapshot.model_validate(snapshot["question"]),
                taxonomy_version=snapshot["taxonomy_version"],
                extraction_version=run.extraction.version,
                policy=AggregationPolicy.model_validate(snapshot["consolidation"]["policy"]),
            ),
            warnings=tuple(run.consolidation["meta"]["warnings"]),
        )
        row = FinalReport.store(run.pk, self.deps.task_id, content)
        stored = ReportContent.model_validate(row.content)
        return StepOutput(
            content=ConsolidationResult(
                report_id=row.pk,
                recommendation=stored.recommendation,
                needs_human_review=stored.needs_human_review,
            )
        )


def build_workflow(run_id: str, task_id: str, *, factory: AgentFactory) -> Workflow:
    run = Run.for_consolidation(run_id, task_id)
    if not run.consolidation:
        reviews = ReviewRound.latest_for_consolidation(run_id)
        if not reviews:
            raise SetupRequired(
                "O E5 precisa das últimas rodadas finalizadas dos avaliadores A, B e C."
            )
        if (
            run.extraction is None
            or not run.profile.get("complete")
            or "question" not in run.config_snapshot
        ):
            raise SetupRequired("O E5 precisa da extração e do perfil com Question em snapshot.")
        method = run.config_snapshot.get("method", "standard")
        config_data = run.config_snapshot.get("evaluation_config")
        config = EvaluationConfig.model_validate(config_data) if config_data else get_method(method)
        paper_type = PaperType(run.profile["classification"]["paper_type"])
        active = set(
            next(paper.active for paper in config.paper_types if paper.paper_type == paper_type)
        )
        if len({review.mode for review in reviews}) != 1 or any(
            {item.criterion_key for item in review.state.criteria} != active for review in reviews
        ):
            raise SetupRequired("As rodadas precisam do mesmo modo e de todos os critérios ativos.")
        sections = {section.id for section in run.extraction.article.sections}
        if any(
            observation.section_id not in sections
            for review in reviews
            for observation in review.state.observations
        ):
            raise SetupRequired("A revisão contém uma seção que não pertence à extração.")
        QuestionSnapshot.model_validate(run.config_snapshot["question"])
        specs = run.config_snapshot.get("model_specs") or {
            role.value: spec.model_dump(mode="json") for role, spec in factory.models.specs.items()
        }
        policy = AggregationPolicy()
        run = Run.initialize_consolidation(
            run_id,
            task_id,
            snapshot={
                "evaluation_config": config.model_dump(mode="json"),
                "model_specs": specs,
                "consolidation": {
                    "policy": policy.model_dump(mode="json"),
                    "evaluation_config_origin": "evaluation_snapshot"
                    if config_data
                    else "registry_at_consolidation",
                    "prompt_template": template("meta_reviewer"),
                },
            },
            inputs={
                "reviews": REVIEWS.dump_python(reviews, mode="json"),
                "section_roles": {
                    item["section_id"]: item["roles"] for item in run.profile["section_roles"]
                },
            },
        )
    snapshot = run.config_snapshot
    factory.models.specs = validate_catalog(
        {
            Role(role): ModelSpec.model_validate(value)
            for role, value in snapshot["model_specs"].items()
        }
    )
    factory.prompt_templates = {"meta_reviewer": snapshot["consolidation"]["prompt_template"]}
    factory.on_prompt = lambda name, version: Run.record_consolidation_prompt(
        run_id, task_id, name, version
    )
    deps = Dependencies(run_id, task_id, factory)

    def step(name: str, executor: Any) -> Step:
        return Step(
            name=name,
            executor=executor,
            max_retries=0,
            human_review=HumanReview(on_error=OnError.fail),
        )

    return Workflow(
        name="consolidation",
        telemetry=False,
        db=None,
        steps=[
            step("aggregate", AggregateStep(deps)),
            step("meta_review", MetaReviewStep(deps)),
            step("validate_meta_review", ValidateMetaReviewStep(deps)),
            step("build_report", BuildFinalReportStep(deps)),
        ],
    )


def run_consolidation(run_id: str, task_id: str, *, factory: AgentFactory) -> ConsolidationResult:
    Run.for_consolidation(run_id, task_id)
    if existing := FinalReport.for_run(run_id):
        saved = ReportContent.model_validate(existing.content)
        return ConsolidationResult(
            report_id=existing.pk,
            recommendation=saved.recommendation,
            needs_human_review=saved.needs_human_review,
        )
    result = build_workflow(run_id, task_id, factory=factory).run(
        input={"run_id": run_id}, run_id=task_id
    )
    if not isinstance(result.content, ConsolidationResult):
        raise RuntimeError("O E5 não terminou com um relatório final completo.")
    return result.content
