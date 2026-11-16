"""Workflows E4 e E5 com passos Agno e checkpoints duráveis."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agno.workflow import Condition, Loop, Parallel, Step, Steps, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput
from django.db import close_old_connections, connections
from pydantic import TypeAdapter

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.prompts import template
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.consolidation import MetaReview
from projects.correction.agents.schemas.evaluation import (
    EvaluationMode,
    EvaluatorSlot,
    ItemType,
)
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec, Role, validate_catalog
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.evaluation.aggregation import aggregate
from projects.correction.evaluation.context import EvaluationContext, EvaluationContextBuilder
from projects.correction.evaluation.contracts import (
    Aggregation,
    AggregationPolicy,
    ConsolidationResult,
    ReviewedSlot,
)
from projects.correction.evaluation.cross_checks import CrossCheckStep, RunCrossCheckCheckpoints
from projects.correction.evaluation.judge import JudgeStep, RunJudgeCheckpoints
from projects.correction.evaluation.models import FinalReport, JudgeVerdict, ReviewRound
from projects.correction.evaluation.report import (
    ReportContent,
    ReportVersions,
    build_report,
    reference_catalog,
    validate_meta_review,
)
from projects.correction.evaluation.revision import (
    MarkUnresolvedStep,
    RevisionStep,
    RunRevisionCheckpoints,
)
from projects.correction.evaluation.revision import (
    has_pending_items as has_pending_revision_items,
)
from projects.correction.evaluation.section_pass import RunReviewCheckpoints, SectionPassStep
from projects.correction.evaluation.synthesis import RunSynthesisCheckpoints, SynthesisStep
from projects.correction.evaluation.validators import RunValidationCheckpoints, ValidateStep
from projects.correction.evaluation.whole_document import (
    RunWholeDocumentCheckpoints,
    WholeDocumentStep,
)
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import InvalidEvaluationOutput, SetupRequired
from projects.correction.questions.criteria import EvaluationConfig, get_method
from projects.correction.questions.profile import QuestionSnapshot

REVIEWS = TypeAdapter(tuple[ReviewedSlot, ...])
SECTION_ROLES = TypeAdapter(dict[str, tuple[SectionRole, ...]])


@dataclass(frozen=True)
class EvaluationDependencies:
    run_id: str
    task_id: str
    context: EvaluationContext
    factory: AgentFactory

    def latest_round(self, slot: EvaluatorSlot) -> ReviewRound | None:
        return (
            ReviewRound.objects.filter(run_id=self.run_id, evaluator_slot=slot)
            .order_by("-round_number")
            .first()
        )

    def revision_checkpoints(
        self, slot: EvaluatorSlot, round_number: int
    ) -> RunRevisionCheckpoints:
        return RunRevisionCheckpoints(
            self.run_id,
            self.task_id,
            slot,
            self.context.evaluation_mode,
            self.context.evaluator(slot).model,
            round_number,
        )

    def has_revision_work(self) -> bool:
        for slot in EvaluatorSlot:
            row = self.latest_round(slot)
            if row is None or row.ready:
                continue
            if row.round_number > 1 and not _round_is_judged(row):
                return True
            if row.round_number <= settings.max_revision_rounds:
                checkpoints = self.revision_checkpoints(slot, row.round_number)
                if has_pending_revision_items(checkpoints):
                    return True
        return False


def _round_item_keys(row: ReviewRound) -> set[tuple[ItemType, str]]:
    state = row.state
    return (
        {(ItemType.OBSERVATION, item.id) for item in state.observations}
        | {(ItemType.CHECK, item.id) for item in state.cross_checks}
        | {(ItemType.CRITERION, item.criterion_key.value) for item in state.criteria}
    )


def _round_is_judged(row: ReviewRound) -> bool:
    verdict_keys = {
        (ItemType(item.item_type), item.item_key) for item in JudgeVerdict.objects.filter(round=row)
    }
    return _round_item_keys(row) <= verdict_keys


def _failed_step_names(outputs: Sequence[StepOutput | list[StepOutput]]) -> list[str]:
    failed: list[str] = []
    for output in outputs:
        if isinstance(output, list):
            failed.extend(_failed_step_names(output))
        elif not output.success:
            failed.append(output.step_name or "unknown")
    return failed


def _has_revision_work(deps: EvaluationDependencies) -> bool:
    """Inclui rodadas parciais para que um retry retome revisão, validação e julgamento."""
    close_old_connections()
    try:
        return deps.has_revision_work()
    finally:
        connections.close_all()


def no_pending_items(deps: EvaluationDependencies) -> bool:
    return not _has_revision_work(deps)


@dataclass(frozen=True)
class EvaluationExecutor:
    deps: EvaluationDependencies
    slot: EvaluatorSlot
    action: str
    round_number: int = 1

    def __call__(self, step_input: StepInput) -> StepOutput:
        close_old_connections()
        try:
            return self._execute(step_input)
        finally:
            connections.close_all()

    def _execute(self, step_input: StepInput) -> StepOutput:
        context, factory = self.deps.context, self.deps.factory
        model = context.evaluator(self.slot).model
        mode = context.evaluation_mode
        result: object
        latest = self.deps.latest_round(self.slot)
        if self.action in {"section_pass", "cross_checks", "synthesis", "whole_document"}:
            if latest is not None and (latest.ready or latest.verdicts.exists()):
                return StepOutput(content=latest.state)
        if self.action in {"validate", "judge"} and self.round_number == 1:
            if latest is not None and latest.round_number == 1 and latest.ready:
                return StepOutput(content=latest.state)
        if self.action == "section_pass":
            result = SectionPassStep(
                context,
                self.slot,
                factory,
                RunReviewCheckpoints(self.deps.run_id, self.deps.task_id, self.slot, model, mode),
                settings.llm_max_concurrency,
            ).execute()
        elif self.action == "cross_checks":
            result = CrossCheckStep(
                context,
                self.slot,
                factory,
                RunCrossCheckCheckpoints(self.deps.run_id, self.deps.task_id, self.slot, model),
                settings.llm_max_concurrency,
            ).execute()
        elif self.action == "synthesis":
            result = SynthesisStep(
                context,
                self.slot,
                factory,
                RunSynthesisCheckpoints(self.deps.run_id, self.deps.task_id, self.slot, model),
            ).execute()
        elif self.action == "whole_document":
            result = WholeDocumentStep(
                context,
                self.slot,
                factory,
                RunWholeDocumentCheckpoints(self.deps.run_id, self.deps.task_id, self.slot, model),
            ).execute()
        elif self.action == "validate":
            result = ValidateStep(
                context,
                RunValidationCheckpoints(
                    self.deps.run_id,
                    self.deps.task_id,
                    self.slot,
                    mode,
                    self.round_number,
                ),
            ).execute()
        elif self.action == "judge":
            result = JudgeStep(
                context,
                self.slot,
                factory,
                RunJudgeCheckpoints(
                    self.deps.run_id,
                    self.deps.task_id,
                    self.slot,
                    mode,
                    self.round_number,
                ),
            ).execute()
        elif self.action == "revision_cycle":
            result = self._revision_cycle()
        elif self.action == "mark_unresolved":
            row = self.deps.latest_round(self.slot)
            result = (
                row.state.unresolved
                if row is not None and row.ready
                else MarkUnresolvedStep(
                    self.deps.revision_checkpoints(self.slot, row.round_number)
                ).execute()
                if row is not None
                else ()
            )
        elif self.action == "finalize":
            row = self.deps.latest_round(self.slot)
            if row is None:
                raise SetupRequired("O E4 terminou sem criar rodadas para os três avaliadores.")
            result = ReviewRound.finalize(row.pk, self.deps.task_id)
        else:
            raise ValueError(f"Ação de workflow E4 desconhecida: {self.action}.")
        return StepOutput(content=result)

    def _revision_cycle(self) -> ReviewRound | None:
        row = self.deps.latest_round(self.slot)
        if row is None or row.ready:
            return row
        if row.round_number > 1 and not _round_is_judged(row):
            round_number = row.round_number
        elif row.round_number <= settings.max_revision_rounds and has_pending_revision_items(
            self.deps.revision_checkpoints(self.slot, row.round_number)
        ):
            round_number = row.round_number + 1
        else:
            return row

        checkpoints = self.deps.revision_checkpoints(self.slot, round_number)
        RevisionStep(self.deps.context, self.slot, self.deps.factory, checkpoints).execute()
        ValidateStep(
            self.deps.context,
            RunValidationCheckpoints(
                self.deps.run_id,
                self.deps.task_id,
                self.slot,
                self.deps.context.evaluation_mode,
                round_number,
            ),
        ).execute()
        JudgeStep(
            self.deps.context,
            self.slot,
            self.deps.factory,
            RunJudgeCheckpoints(
                self.deps.run_id,
                self.deps.task_id,
                self.slot,
                self.deps.context.evaluation_mode,
                round_number,
            ),
        ).execute()
        return ReviewRound.objects.get(
            run_id=self.deps.run_id,
            evaluator_slot=self.slot,
            round_number=round_number,
        )


def build_evaluation_workflow(
    run_id: str,
    task_id: str,
    context: EvaluationContext,
    *,
    factory: AgentFactory,
) -> Workflow:
    deps = EvaluationDependencies(run_id, task_id, context, factory)

    def step(name: str, executor: Any) -> Step:
        return Step(
            name=name,
            executor=executor,
            max_retries=0,
            human_review=HumanReview(on_error=OnError.fail),
        )

    def parallel(name: str, branches: list[Any]) -> Parallel:
        branch_args: Any = branches
        return Parallel(*branch_args, name=name)

    def evaluator(slot: EvaluatorSlot) -> Steps:
        names = (
            ("section_pass", "cross_checks", "synthesis")
            if context.evaluation_mode is EvaluationMode.SECTIONED
            else ("whole_document",)
        )
        return Steps(
            name=f"evaluator_{slot.value}",
            steps=[
                step(f"{action}_{slot.value}", EvaluationExecutor(deps, slot, action))
                for action in names
            ],
        )

    slots = tuple(EvaluatorSlot)
    initial_evaluators = parallel("evaluators", [evaluator(slot) for slot in slots])
    validations = parallel(
        "validate_evaluators",
        [
            step(f"validate_{slot.value}", EvaluationExecutor(deps, slot, "validate"))
            for slot in slots
        ],
    )
    judges = parallel(
        "judge_evaluators",
        [step(f"judge_{slot.value}", EvaluationExecutor(deps, slot, "judge")) for slot in slots],
    )
    revision_loop = Loop(
        steps=[
            parallel(
                "revision_cycles",
                [
                    step(
                        f"revision_cycle_{slot.value}",
                        EvaluationExecutor(deps, slot, "revision_cycle"),
                    )
                    for slot in slots
                ],
            )
        ],
        name="revision_loop",
        max_iterations=settings.max_revision_rounds,
        end_condition=lambda _: no_pending_items(deps),
    )
    revisions = Condition(
        steps=[revision_loop],
        evaluator=lambda _: _has_revision_work(deps),
        name="needs_revision",
        human_review=HumanReview(on_error=OnError.fail),
    )
    unresolved = parallel(
        "mark_unresolved",
        [
            step(
                f"mark_unresolved_{slot.value}",
                EvaluationExecutor(deps, slot, "mark_unresolved"),
            )
            for slot in slots
        ],
    )
    finalize = parallel(
        "finalize_rounds",
        [
            step(f"finalize_{slot.value}", EvaluationExecutor(deps, slot, "finalize"))
            for slot in slots
        ],
    )
    return Workflow(
        name="evaluation",
        telemetry=False,
        db=None,
        steps=[initial_evaluators, validations, judges, revisions, unresolved, finalize],
    )


def run_evaluation(run_id: str, task_id: str, *, factory: AgentFactory) -> dict[str, Any]:
    run = Run.for_evaluation(run_id, task_id)
    builder = EvaluationContextBuilder(run)
    Run.initialize_evaluation(run_id, task_id, builder.snapshot())
    run = Run.for_evaluation(run_id, task_id)
    context = EvaluationContextBuilder(run).build()
    factory.models.specs = validate_catalog(
        {
            Role(role): ModelSpec.model_validate(value)
            for role, value in run.config_snapshot["model_specs"].items()
        }
    )
    result = build_evaluation_workflow(run_id, task_id, context, factory=factory).run(
        input={"run_id": run_id}, run_id=task_id
    )
    reviews = ReviewRound.latest_for_consolidation(run_id)
    if len(reviews) != len(EvaluatorSlot):
        errors = _failed_step_names(result.step_results or [])
        raise InvalidEvaluationOutput(
            "O workflow E4 não finalizou as rodadas de todos os slots "
            f"(status={result.status}; passos incompletos={errors})."
        )
    return {
        "evaluators": [item.slot.value for item in reviews],
        "review_rounds": {item.slot.value: item.round_number for item in reviews},
        "workflow_status": str(result.status),
    }


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
            article=run.extraction.document,
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
        sections = {section.id for section in run.extraction.document.sections}
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
