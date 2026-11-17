"""Benchmark do juiz E4 com erros controlados em revisões sintéticas."""

import hashlib
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    EvaluatorSlot,
    Evidence,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    Verdict,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec, Role, validate_catalog
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    Metric,
    UsageSummary,
    fingerprint,
)
from projects.correction.evaluation.context import EvaluationContextBuilder
from projects.correction.evaluation.judge import JudgeCheckpoints, JudgeStep
from projects.correction.evaluation.models import FinalReport
from projects.correction.extractor.contract import DocumentSection, ExtractedDocument

_TITLE = "Controlled evaluation sample"
_RESULTS_SECTION = "results"
_DISCUSSION_SECTION = "discussion"
_RESULTS_QUOTE = "Measured accuracy was 87%; baseline accuracy was 91%."
_DISCUSSION_QUOTE = (
    "The model achieved 87 percent accuracy, compared with 91 percent for the baseline."
)


class _MemoryCheckpoints(JudgeCheckpoints):
    def __init__(self, state: ReviewState) -> None:
        self.state = state
        self.writes: list[ItemVerdict] = []

    def assert_owned(self) -> None:
        return None

    def read_state(self) -> ReviewState:
        return self.state

    def read_verdicts(self) -> dict[tuple[ItemType, str], ItemVerdict]:
        return {}

    def read_slot_grades(self) -> dict[EvaluatorSlot, dict[str, int]]:
        return {}

    def record(self, item: ItemVerdict, judge_model: ModelSpec) -> None:
        self.writes.append(item)


def _article() -> ExtractedDocument:
    return ExtractedDocument(
        title=_TITLE,
        language="en",
        abstract="The experiment compares a proposed method with a baseline.",
        sections=(
            DocumentSection(
                id=_RESULTS_SECTION,
                title="Results",
                level=1,
                text=_RESULTS_QUOTE,
            ),
            DocumentSection(
                id=_DISCUSSION_SECTION,
                title="Discussion",
                level=1,
                text=(f"{_DISCUSSION_QUOTE} The proposed method did not improve on the baseline."),
            ),
        ),
    )


def _observation(
    key: str,
    *,
    statement: str,
    quote: str,
    section_id: str = _RESULTS_SECTION,
    criterion: Criterion = Criterion.SOUNDNESS,
) -> Observation:
    return Observation(
        id=key,
        section_id=section_id,
        role=SectionRole.RESULTS,
        kind="weakness",
        statement=statement,
        evidence=(Evidence(quote=quote, section_id=section_id),),
        criteria=(criterion,),
        severity="major",
        confidence=0.95,
    )


def _scenarios() -> tuple[tuple[str, str | None, ReviewState], ...]:
    valid = _observation(
        "obs-valid",
        statement="The proposed method performed below the baseline.",
        quote=_RESULTS_QUOTE,
    )
    fabricated = _observation(
        "obs-fabricated-quote",
        statement="The proposed method reached 99 percent accuracy.",
        quote="The proposed method reached 99 percent accuracy.",
    )
    wrong_location = _observation(
        "obs-wrong-section",
        statement="The method's accuracy was lower than the baseline.",
        quote=_DISCUSSION_QUOTE,
    )
    contradictory = ReviewState(
        observations=(valid,),
        criteria=(
            CriterionSynthesis(
                criterion_key=Criterion.SOUNDNESS,
                grade=5,
                justification=(
                    "The method soundly demonstrates a major improvement, reaching 99 percent "
                    "accuracy over the 91 percent baseline."
                ),
                observation_ids=(valid.id,),
                confidence=0.95,
            ),
        ),
    )
    return (
        ("control_valid", None, ReviewState(observations=(valid,))),
        ("fabricated_quote", "obs-fabricated-quote", ReviewState(observations=(fabricated,))),
        (
            "quote_in_wrong_section",
            "obs-wrong-section",
            ReviewState(observations=(wrong_location,)),
        ),
        (
            "grade_contradicts_evidence",
            "criterion:soundness",
            contradictory,
        ),
    )


def _source_hashes() -> dict[str, str]:
    root = Path(__file__).parents[1]
    prompt = root / "agents" / "prompts" / "judge.md"
    files = {
        f"evals/{Path(__file__).name}": Path(__file__),
        "evaluation/judge.py": root / "evaluation" / "judge.py",
        "evaluation/context.py": root / "evaluation" / "context.py",
        "agents/factory.py": root / "agents" / "factory.py",
        "agents/schemas/evaluation.py": root / "agents" / "schemas" / "evaluation.py",
        "agents/prompts/judge.md": prompt,
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def _set_model_specs(factory: AgentFactory, run: Run) -> None:
    raw_specs = run.config_snapshot.get("model_specs")
    if not isinstance(raw_specs, dict):
        raise ValueError("O Run de origem não tem snapshots de ModelSpec.")
    factory.models.specs = validate_catalog(
        {Role(role): ModelSpec.model_validate(value) for role, value in raw_specs.items()}
    )


def _classify(items: tuple[ItemVerdict, ...]) -> dict[str, str]:
    return {f"{item.item_type.value}:{item.item_key}": item.verdict.value for item in items}


def run_judge_benchmark(run: Run) -> EvaluationReport:
    if run.status != RunStatus.DONE or FinalReport.for_run(run.pk) is None:
        raise ValueError("O Run de origem precisa estar concluído e ter FinalReport.")
    context = EvaluationContextBuilder(run).build().model_copy(update={"article": _article()})
    fixture_cases = _scenarios()
    sink = MemoryUsageSink()
    outcomes: list[dict[str, Any]] = []
    binary_rows: list[tuple[bool, bool | None, str]] = []
    failures = 0
    model_specs: dict[Role, ModelSpec] = {}
    prompt_versions: dict[str, set[str]] = defaultdict(set)

    # Slots A e B exercitam ambos os provedores de juiz cruzado.
    for slot in (EvaluatorSlot.A, EvaluatorSlot.B):
        for scenario, expected_invalid, state in fixture_cases:
            case_id = f"{scenario}:{slot.value}"
            checkpoints = _MemoryCheckpoints(state)
            factory = AgentFactory(
                run_id=f"bench_judge:{run.pk}:{case_id}",
                stage=Stage.EVALUATION.value,
                usage_sink=sink,
            )
            _set_model_specs(factory, run)
            judge_role = factory.models.judge_role(context.evaluator(slot).model)
            judge_spec = factory.models.judge_for(context.evaluator(slot).model)
            model_specs[judge_role] = judge_spec
            actual: dict[str, str] = {}
            error_type = None
            try:
                judged = JudgeStep(context, slot, factory, checkpoints).execute()
                actual = _classify(judged)
            except Exception as exc:
                failures += 1
                error_type = type(exc).__name__
            prompt_versions.update(
                {name: {version} for name, version in factory.prompt_versions.items()}
            )

            expected_items = {
                f"observation:{observation.id}" for observation in state.observations
            } | {f"criterion:{item.criterion_key.value}" for item in state.criteria}
            target = (
                f"observation:{expected_invalid}"
                if expected_invalid and not expected_invalid.startswith("criterion:")
                else expected_invalid
            )
            for item_key in expected_items:
                expected_bad = item_key == target
                predicted_bad = actual.get(item_key) == Verdict.INVALID.value
                binary_rows.append(
                    (expected_bad, predicted_bad if item_key in actual else None, scenario)
                )
            outcomes.append(
                {
                    "case_id": case_id,
                    "scenario": scenario,
                    "evaluator_slot": slot.value,
                    "judge_provider": (
                        factory.models.judge_for(context.evaluator(slot).model).provider.value
                    ),
                    "expected_invalid_item": target,
                    "judged": actual,
                    "error": error_type,
                }
            )

    expected_invalid_count = sum(expected for expected, _, _ in binary_rows)
    true_positive = sum(expected and predicted is True for expected, predicted, _ in binary_rows)
    false_negative = sum(
        expected and predicted is not True for expected, predicted, _ in binary_rows
    )
    false_positive = sum(
        not expected and predicted is True for expected, predicted, _ in binary_rows
    )
    true_negative = sum(
        not expected and predicted is False for expected, predicted, _ in binary_rows
    )
    judged_items = sum(predicted is not None for _, predicted, _ in binary_rows)
    total_items = len(binary_rows)
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else None
    )
    recall = true_positive / expected_invalid_count if expected_invalid_count else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
        if precision is not None and recall is not None
        else None
    )
    false_positive_rate = (
        false_positive / (false_positive + true_negative)
        if false_positive + true_negative
        else None
    )
    metrics = {
        "bench_judge.injection_recall": Metric(value=recall, unit="fraction", direction="higher"),
        "bench_judge.invalid_precision": Metric(
            value=precision, unit="fraction", direction="higher"
        ),
        "bench_judge.invalid_f1": Metric(value=f1, unit="fraction", direction="higher"),
        "bench_judge.false_positive_rate": Metric(
            value=false_positive_rate, unit="fraction", direction="lower"
        ),
        "bench_judge.coverage": Metric(
            value=judged_items / total_items if total_items else None,
            unit="fraction",
            direction="higher",
        ),
    }
    for scenario, _, _ in fixture_cases:
        scenario_rows = [row for row in binary_rows if row[2] == scenario]
        expected = sum(row[0] for row in scenario_rows)
        found = sum(row[0] and row[1] is True for row in scenario_rows)
        metrics[f"bench_judge.{scenario}_recall"] = Metric(
            value=found / expected if expected else None,
            unit="fraction",
            direction="higher",
        )

    fixture_payload = {
        "version": "1",
        "title": _TITLE,
        "sections": {
            _RESULTS_SECTION: _RESULTS_QUOTE,
            _DISCUSSION_SECTION: _DISCUSSION_QUOTE,
        },
        "cases": [
            {
                "name": name,
                "expected_invalid": expected_invalid,
                "review": state.model_dump(mode="json"),
            }
            for name, expected_invalid, state in fixture_cases
        ],
    }
    calls = sink.calls
    return EvaluationReport(
        benchmark="bench_judge",
        benchmark_version="1",
        created_at=datetime.now(UTC),
        dataset=DatasetIdentity(
            name="synthetic_judge_error_injection",
            version="1",
            sha256=fingerprint(fixture_payload),
            case_ids=tuple(str(item["case_id"]) for item in outcomes),
        ),
        parameters={
            "metric_protocol": "bench-judge-v1",
            "slots": [EvaluatorSlot.A.value, EvaluatorSlot.B.value],
            "judge_roles": cast(JsonValue, sorted(role.value for role in model_specs)),
            "expected_errors": cast(
                JsonValue,
                [
                    "fabricated_quote",
                    "quote_in_wrong_section",
                    "grade_contradicts_evidence",
                ],
            ),
        },
        model_specs=model_specs,
        prompt_versions={
            name: tuple(sorted(versions)) for name, versions in prompt_versions.items()
        },
        source_sha256=_source_hashes(),
        metrics=metrics,
        failures=failures,
        usage=UsageSummary.from_calls(calls),
        details={
            "source_run_id": str(run.pk),
            "judged_items": judged_items,
            "total_items": total_items,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
            "mean_provider_latency_ms": (
                statistics.mean(call.latency_ms for call in calls) if calls else None
            ),
            "cases": cast(JsonValue, outcomes),
        },
        notes=(
            "As quatro situações são sintéticas: um controle válido e três erros plantados. "
            "O relatório mede o comportamento do juiz nos casos controlados, não sua precisão "
            "em artigos reais.",
            "Erros de execução contam como falha e como erro não detectado para o recall.",
        ),
    )
