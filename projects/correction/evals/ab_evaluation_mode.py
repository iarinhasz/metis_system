"""Runs pareados e métricas A/B para os modos sectioned e whole_document."""

import hashlib
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from django.db import transaction
from pydantic import Field, model_validator

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import EvaluationMode, EvaluatorSlot, Verdict
from projects.correction.agents.specs import Family, ModelSpec, Role
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import RunPurpose, RunStatus, Stage
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    FrozenModel,
    Metric,
    UsageSummary,
    fingerprint,
)
from projects.correction.evaluation.context import EvaluationContextBuilder
from projects.correction.evaluation.contracts import Recommendation
from projects.correction.evaluation.models import FinalReport, ReviewRound
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.pipeline.publishing import publish_stage_on_commit
from projects.correction.questions.criteria import EvaluationConfig

DEFAULT_REPLICATES = 3
MODES = (EvaluationMode.SECTIONED, EvaluationMode.WHOLE_DOCUMENT)


class ABCase(FrozenModel):
    id: str = Field(min_length=1, max_length=255)
    source_run_id: UUID
    human_decision: Literal["accepted", "rejected"] | None = None
    human_scores: dict[Criterion, Annotated[int, Field(strict=True, ge=1, le=5)]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def valid_human_scores(self) -> ABCase:
        if not self.id.strip():
            raise ValueError("O id do caso não pode ser vazio ou conter somente espaços.")
        if any(score not in range(1, 6) for score in self.human_scores.values()):
            raise ValueError("As notas humanas devem estar entre 1 e 5.")
        return self


class ABManifest(FrozenModel):
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    cases: tuple[ABCase, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_cases(self) -> ABManifest:
        ids = tuple(case.id for case in self.cases)
        source_runs = tuple(case.source_run_id for case in self.cases)
        if len(set(ids)) != len(ids) or len(set(source_runs)) != len(source_runs):
            raise ValueError("O manifesto precisa de casos e runs de origem distintos.")
        return self


def read_manifest(path: Path) -> tuple[ABManifest, str]:
    raw = path.read_bytes()
    manifest = ABManifest.model_validate_json(raw)
    return manifest, hashlib.sha256(raw).hexdigest()


def validate_sources(manifest: ABManifest) -> dict[UUID, Run]:
    """Confere que cada origem tem os snapshots e a extração atual exigidos pelo E4."""
    source_ids = tuple(case.source_run_id for case in manifest.cases)
    sources = {
        run.pk: run
        for run in Run.objects.filter(
            pk__in=source_ids, purpose=RunPurpose.EVALUATION
        ).select_related("attempt", "extraction", "question", "final_report")
    }
    if set(sources) != set(source_ids):
        raise ValueError("Cada source_run_id precisa apontar para um Run de avaliação existente.")

    version = extraction_version(ARTICLE_CONFIG)
    question_snapshots: set[str] = set()
    evaluation_configs: set[str] = set()
    for source in sources.values():
        if source.status != RunStatus.DONE or FinalReport.for_run(source.pk) is None:
            raise ValueError("Os runs de origem precisam estar concluídos e ter FinalReport.")
        if source.extraction is None or not source.profile.get("complete"):
            raise ValueError("Os runs de origem precisam dos snapshots completos de E1 e E2.")
        if (
            source.extraction.version != version
            or source.extraction.sha256 != source.attempt.sha256
        ):
            raise ValueError("A amostra precisa usar a extração em cache na versão atual do E1.")
        try:
            EvaluationContextBuilder(source).build()
            question_snapshots.add(fingerprint(source.config_snapshot["question"]))
            config = EvaluationConfig.model_validate(source.config_snapshot["evaluation_config"])
            evaluation_configs.add(fingerprint(config.model_dump(mode="json")))
            if not source.config_snapshot.get("model_specs"):
                raise ValueError("snapshot de modelos ausente")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Um run de origem não tem snapshots completos para o E4.") from exc

    if len(question_snapshots) != 1 or len(evaluation_configs) != 1:
        raise ValueError(
            "Todos os runs de origem precisam usar a mesma Question e configuração de avaliação."
        )

    configurations = {
        fingerprint(source.config_snapshot["model_specs"]) for source in sources.values()
    }
    if len(configurations) != 1:
        raise ValueError("Todos os casos precisam usar os mesmos ModelSpecs nesta comparação.")
    return sources


@transaction.atomic
def create_ab_runs(
    manifest: ABManifest,
    manifest_sha256: str,
    *,
    batch_id: UUID,
    replicates: int = DEFAULT_REPLICATES,
) -> tuple[tuple[Run, ...], bool]:
    """Cria os dois modos para cada caso e réplica, ou devolve o lote já existente."""
    if replicates < 2 or replicates > 10:
        raise ValueError("O número de réplicas deve estar entre 2 e 10.")
    sources = validate_sources(manifest)
    expected = {
        (case.id, mode.value, replicate, str(case.source_run_id))
        for case in manifest.cases
        for mode in MODES
        for replicate in range(1, replicates + 1)
    }
    existing = tuple(
        Run.objects.filter(
            purpose=RunPurpose.AB_TEST,
            config_snapshot__ab_test__batch_id=str(batch_id),
        )
        .select_related("attempt", "extraction")
        .order_by("created_at", "pk")
    )
    if existing:
        actual = {
            (
                item.config_snapshot["ab_test"]["case_id"],
                item.config_snapshot["ab_test"]["mode"],
                item.config_snapshot["ab_test"]["replicate"],
                item.config_snapshot["ab_test"]["source_run_id"],
            )
            for item in existing
        }
        if actual != expected or any(
            item.config_snapshot["ab_test"].get("manifest_sha256") != manifest_sha256
            for item in existing
        ):
            raise ValueError("Este batch_id já foi usado por outro manifesto ou configuração.")
        return existing, False

    created: list[Run] = []
    for case in manifest.cases:
        source = sources[case.source_run_id]
        for mode in MODES:
            for replicate in range(1, replicates + 1):
                snapshot = {
                    **source.config_snapshot,
                    "evaluation_mode": mode.value,
                    "ab_test": {
                        "batch_id": str(batch_id),
                        "manifest_sha256": manifest_sha256,
                        "dataset": manifest.name,
                        "dataset_version": manifest.version,
                        "case_id": case.id,
                        "source_run_id": str(source.pk),
                        "mode": mode.value,
                        "replicate": replicate,
                    },
                }
                run = Run.create(
                    attempt=source.attempt,
                    actor=f"ab_test:{batch_id}",
                    purpose=RunPurpose.AB_TEST,
                    config_snapshot=snapshot,
                    profile=source.profile,
                    question_id=source.question_id,
                    extraction=source.extraction,
                )
                created.append(run)
                publish_stage_on_commit(str(run.pk), Stage.EXTRACTION)
    return tuple(created), True


def batch_runs(batch_id: UUID) -> tuple[Run, ...]:
    return tuple(
        Run.objects.filter(
            purpose=RunPurpose.AB_TEST,
            config_snapshot__ab_test__batch_id=str(batch_id),
        )
        .select_related("attempt", "extraction", "final_report")
        .prefetch_related("review_rounds__verdicts", "llm_calls", "events")
        .order_by("created_at", "pk")
    )


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2
        for position in range(start, end):
            result[ordered[position][0]] = average_rank
        start = end
    return result


def spearman_correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    x, y = _rank(left), _rank(right)
    mean_x, mean_y = statistics.mean(x), statistics.mean(y)
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    denominator = math.sqrt(sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y))
    return covariance / denominator if denominator else None


def quadratic_weighted_kappa(left: list[int], right: list[int], *, scale: int = 5) -> float | None:
    if len(left) != len(right) or not left or scale < 2:
        return None
    size = scale
    observed = [[0 for _ in range(size)] for _ in range(size)]
    for actual, predicted in zip(left, right, strict=True):
        if actual not in range(1, scale + 1) or predicted not in range(1, scale + 1):
            raise ValueError("QWK aceita notas dentro da escala informada.")
        observed[actual - 1][predicted - 1] += 1
    actual_counts = [sum(observed[row]) for row in range(size)]
    predicted_counts = [sum(observed[row][column] for row in range(size)) for column in range(size)]
    total = len(left)
    observed_loss = 0.0
    expected_loss = 0.0
    for actual in range(size):
        for predicted in range(size):
            weight = ((actual - predicted) / (size - 1)) ** 2
            observed_loss += weight * observed[actual][predicted]
            expected_loss += weight * actual_counts[actual] * predicted_counts[predicted] / total
    return 1 - observed_loss / expected_loss if expected_loss else None


def _latest_rounds(run: Run) -> dict[EvaluatorSlot, ReviewRound]:
    latest: dict[EvaluatorSlot, ReviewRound] = {}
    for row in run.review_rounds.all().order_by("evaluator_slot", "-round_number"):
        slot = EvaluatorSlot(row.evaluator_slot)
        latest.setdefault(slot, row)
    if set(latest) != set(EvaluatorSlot) or any(not row.ready for row in latest.values()):
        raise ValueError(f"O Run {run.pk} não tem as três últimas rodadas prontas.")
    return latest


def _valid_grades(row: ReviewRound) -> dict[str, int]:
    verdicts = {
        (item.item_type, item.item_key): Verdict(item.verdict) for item in row.verdicts.all()
    }
    unresolved = {(item.item_type.value, item.item_key) for item in row.state.unresolved}
    return {
        item.criterion_key.value: item.grade
        for item in row.state.criteria
        if verdicts.get(("criterion", item.criterion_key.value)) is Verdict.VALID
        and ("criterion", item.criterion_key.value) not in unresolved
    }


def _binary_metrics(
    actual: list[bool], predicted: list[bool], *, labelled: int
) -> dict[str, float | int | None]:
    tp = sum(a and p for a, p in zip(actual, predicted, strict=True))
    fp = sum(not a and p for a, p in zip(actual, predicted, strict=True))
    tn = sum(not a and not p for a, p in zip(actual, predicted, strict=True))
    fn = sum(a and not p for a, p in zip(actual, predicted, strict=True))
    positive_total, negative_total = tp + fn, tn + fp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / positive_total if positive_total else None
    specificity = tn / negative_total if negative_total else None
    f1 = None
    if precision is not None and recall is not None:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    balanced = (
        (recall + specificity) / 2 if recall is not None and specificity is not None else None
    )
    scored = len(actual)
    return {
        "accuracy": (tp + tn) / scored if scored else None,
        "balanced_accuracy": balanced,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "coverage": scored / labelled if labelled else None,
        "labelled_cases": labelled,
        "scored_cases": scored,
        "abstentions": labelled - scored,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
    }


def _acceptance_metrics(
    mode: EvaluationMode, rows: list[dict[str, Any]], cases: tuple[ABCase, ...]
) -> dict[str, dict[str, float | int | None]]:
    """Compara a recomendação com o veredito humano, votando entre réplicas por artigo."""
    labelled_cases = [case for case in cases if case.human_decision is not None]
    mode_rows = [row for row in rows if row["mode"] == mode.value]
    output: dict[str, dict[str, float | int | None]] = {}
    for strategy, positive_recommendations in (
        ("strict", {Recommendation.ACCEPT.value}),
        ("potential", {Recommendation.ACCEPT.value, Recommendation.MINOR.value}),
    ):
        actual: list[bool] = []
        predicted: list[bool] = []
        for case in labelled_cases:
            case_rows = [row for row in mode_rows if row["case_id"] == case.id]
            votes = []
            for row in case_rows:
                recommendation = row.get("recommendation")
                if recommendation is None or row.get("needs_human_review"):
                    continue
                votes.append(recommendation in positive_recommendations)
            # Réplicas sem recomendação ou com revisão humana sinalizada não votam.
            positive_votes = sum(votes)
            negative_votes = len(votes) - positive_votes
            if max(positive_votes, negative_votes) <= len(case_rows) / 2:
                continue
            actual.append(case.human_decision == "accepted")
            predicted.append(positive_votes > negative_votes)
        output[strategy] = _binary_metrics(actual, predicted, labelled=len(labelled_cases))
    return output


def _mode_metrics(
    mode: EvaluationMode,
    rows: list[dict[str, Any]],
    cases: tuple[ABCase, ...],
) -> tuple[dict[str, Metric], dict[str, Any]]:
    mode_runs = [row for row in rows if row["mode"] == mode.value]
    by_case_slot_criterion: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    disagreements: dict[str, list[float]] = defaultdict(list)
    judge_invalid = judge_total = 0
    grade_rows: list[dict[str, Any]] = []
    for item in mode_runs:
        slot_grades = item["grades"]
        families = item["families"]
        for slot, grades in slot_grades.items():
            for criterion, grade in grades.items():
                by_case_slot_criterion[(item["case_id"], slot, criterion)].append(grade)
        pairs = (("a", "b", "ab"), ("a", "c", "ac"), ("b", "c", "bc"))
        for left, right, pair in pairs:
            relation = ""
            if pair == "ac":
                relation = "_same_family" if families[left] == families[right] else "_cross_family"
            for criterion in slot_grades[left].keys() & slot_grades[right].keys():
                disagreements[f"{pair}{relation}"].append(
                    abs(slot_grades[left][criterion] - slot_grades[right][criterion])
                )
        judge_invalid += item["judge_invalid"]
        judge_total += item["judge_total"]
        grade_rows.append(item)

    repeat_spreads = [
        statistics.pstdev(values) for values in by_case_slot_criterion.values() if len(values) > 1
    ]
    metrics: dict[str, Metric] = {
        f"{mode.value}.intra_evaluator_score_stddev": Metric(
            value=statistics.mean(repeat_spreads) if repeat_spreads else None,
            unit="grade_points",
            direction="lower",
        ),
        f"{mode.value}.judge_invalidation_rate": Metric(
            value=judge_invalid / judge_total if judge_total else None,
            unit="fraction",
            direction="lower",
        ),
    }
    for key, unit in (
        ("ab", "grade_points"),
        ("ac_same_family", "grade_points"),
        ("ac_cross_family", "grade_points"),
        ("bc", "grade_points"),
    ):
        values = disagreements.get(key, [])
        metrics[f"{mode.value}.evaluator_disagreement_{key}_mae"] = Metric(
            value=statistics.mean(values) if values else None,
            unit=unit,
            direction="lower",
        )
    metrics[f"{mode.value}.evaluator_disagreement_mae"] = Metric(
        value=(
            statistics.mean([value for values in disagreements.values() for value in values])
            if disagreements
            else None
        ),
        unit="grade_points",
        direction="lower",
    )

    labels = {case.id: case.human_scores for case in cases}
    human, predictions = [], []
    for case_id in {case.id for case in cases}:
        for criterion in labels[case_id]:
            values = [
                item["grades"][slot][criterion.value]
                for item in grade_rows
                if item["case_id"] == case_id
                for slot in EvaluatorSlot
                if criterion.value in item["grades"][slot.value]
            ]
            if values:
                human.append(float(labels[case_id][criterion]))
                predictions.append(float(statistics.mean(values)))
    rounded = [
        int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) for value in predictions
    ]
    metrics[f"{mode.value}.human_spearman"] = Metric(
        value=spearman_correlation(human, predictions),
        unit="correlation",
        direction="higher",
    )
    metrics[f"{mode.value}.human_qwk"] = Metric(
        value=quadratic_weighted_kappa([int(value) for value in human], rounded),
        unit="coefficient",
        direction="higher",
    )
    acceptance_summaries = _acceptance_metrics(mode, rows, cases)
    for strategy, acceptance_values in acceptance_summaries.items():
        for name in (
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall",
            "specificity",
            "f1",
            "coverage",
        ):
            metrics[f"{mode.value}.{strategy}_acceptance_{name}"] = Metric(
                value=acceptance_values[name],
                unit="fraction",
                direction="higher",
            )
    return metrics, {
        "paired_human_scores": len(human),
        "judge_invalid": judge_invalid,
        "judge_total": judge_total,
        "repeat_score_cells": len(repeat_spreads),
        "acceptance_prediction": acceptance_summaries,
    }


def _source_hashes() -> dict[str, str]:
    root = Path(__file__).parents[1]
    evaluation = root / "evaluation"
    agents = root / "agents"
    files = [
        evaluation / name
        for name in (
            "aggregation.py",
            "context.py",
            "contracts.py",
            "cross_checks.py",
            "judge.py",
            "models.py",
            "report.py",
            "revision.py",
            "section_pass.py",
            "synthesis.py",
            "validators.py",
            "whole_document.py",
            "workflow.py",
        )
    ]
    files.extend(
        agents / name
        for name in (
            "factory.py",
            "runner.py",
            "specs.py",
            "schemas/criteria.py",
            "schemas/evaluation.py",
            "usage.py",
        )
    )
    files.append(root / "questions" / "criteria.py")
    prompts = agents / "prompts"
    files.extend(
        prompts / name
        for name in (
            "cross_checker.md",
            "judge.md",
            "meta_reviewer.md",
            "reviser.md",
            "synthesizer.md",
            "whole_document_reviewer.md",
        )
    )
    files.extend(sorted((prompts / "sections").glob("*.md")))
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    } | {"evals/ab_evaluation_mode.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def build_report(
    manifest: ABManifest,
    manifest_sha256: str,
    *,
    batch_id: UUID,
    replicates: int,
    runs: tuple[Run, ...],
) -> EvaluationReport:
    expected = len(manifest.cases) * len(MODES) * replicates
    if len(runs) != expected:
        raise ValueError(f"O lote tem {len(runs)} runs; eram esperados {expected}.")
    expected_batch = str(batch_id)
    expected_manifest_cases = {str(case.source_run_id): case.id for case in manifest.cases}
    expected_pairs = {
        (case.id, mode.value, replicate)
        for case in manifest.cases
        for mode in MODES
        for replicate in range(1, replicates + 1)
    }
    actual_pairs: set[tuple[str, str, int]] = set()
    for run in runs:
        metadata = run.config_snapshot.get("ab_test", {})
        if (
            metadata.get("batch_id") != expected_batch
            or metadata.get("manifest_sha256") != manifest_sha256
            or metadata.get("source_run_id") not in expected_manifest_cases
            or metadata.get("case_id") != expected_manifest_cases[metadata.get("source_run_id")]
            or run.purpose != RunPurpose.AB_TEST
        ):
            raise ValueError("O lote informado não corresponde a este manifesto.")
        actual_pairs.add((metadata.get("case_id"), metadata.get("mode"), metadata.get("replicate")))
    if actual_pairs != expected_pairs:
        raise ValueError("O lote tem casos, modos ou réplicas duplicados/ausentes.")
    incomplete = [run for run in runs if run.status != RunStatus.DONE]
    if incomplete:
        states = ", ".join(
            f"{run.status}={sum(item.status == run.status for item in incomplete)}"
            for run in incomplete
        )
        raise ValueError(f"Ainda há runs sem relatório final: {states}.")
    if any(FinalReport.for_run(run.pk) is None for run in runs):
        raise ValueError("Todos os runs do lote precisam ter FinalReport.")

    cases_by_source = {str(case.source_run_id): case for case in manifest.cases}
    details: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    all_calls: list[LLMCall] = []
    runtimes: dict[str, list[float]] = defaultdict(list)
    model_specs: dict[Role, ModelSpec] = {}
    prompt_versions: dict[str, set[str]] = defaultdict(set)
    for run in runs:
        metadata = run.config_snapshot["ab_test"]
        case = cases_by_source[metadata["source_run_id"]]
        mode = EvaluationMode(metadata["mode"])
        latest = _latest_rounds(run)
        slot_grades: dict[str, dict[str, int]] = {}
        families: dict[str, Family] = {}
        for slot, review in latest.items():
            spec = ModelSpec.model_validate(review.model_spec)
            families[slot.value] = spec.family
            slot_grades[slot.value] = _valid_grades(review)
        aggregate_rows.append(
            {
                "case_id": case.id,
                "mode": mode.value,
                "replicate": metadata["replicate"],
                "grades": slot_grades,
                "families": families,
                "judge_invalid": sum(
                    item.source == "judge" and item.verdict == Verdict.INVALID
                    for review in run.review_rounds.all()
                    for item in review.verdicts.all()
                ),
                "judge_total": sum(
                    item.source == "judge"
                    for review in run.review_rounds.all()
                    for item in review.verdicts.all()
                ),
                "recommendation": run.final_report.recommendation,
                "needs_human_review": bool(run.final_report.content.get("needs_human_review")),
            }
        )
        calls = [
            item
            for item in run.llm_calls.all()
            if item.stage in {Stage.EVALUATION, Stage.CONSOLIDATION}
        ]
        all_calls.extend(calls)
        for role, raw_spec in run.config_snapshot["model_specs"].items():
            model_specs[Role(role)] = ModelSpec.model_validate(raw_spec)
        for name, raw_version in run.config_snapshot.get("prompt_versions", {}).items():
            if not isinstance(raw_version, str):
                raise ValueError(f"A versão do prompt {name} não é uma string válida.")
            if len(raw_version) == 64 and all(char in "0123456789abcdef" for char in raw_version):
                prompt_versions[name].add(raw_version)
            else:
                prompt_versions[name].add(hashlib.sha256(raw_version.encode()).hexdigest())
        events = run.events.all().order_by("created_at", "id")
        started = next(
            (event.created_at for event in events if event.to_status == RunStatus.EVALUATING), None
        )
        ended = next(
            (event.created_at for event in events if event.to_status == RunStatus.EVALUATED), None
        )
        if started is not None and ended is not None:
            runtimes[mode.value].append(max(0.0, (ended - started).total_seconds()))
        details.append(
            {
                "case_id": case.id,
                "source_run_id": metadata["source_run_id"],
                "run_id": str(run.pk),
                "mode": mode.value,
                "replicate": metadata["replicate"],
                "grades": slot_grades,
                "families": {slot: family.value for slot, family in families.items()},
            }
        )

    metrics: dict[str, Metric] = {}
    summaries: dict[str, Any] = {}
    invalid_count = sum(row["judge_invalid"] for row in aggregate_rows)
    total_judgments = sum(row["judge_total"] for row in aggregate_rows)
    for mode in MODES:
        mode_metrics, summary = _mode_metrics(mode, aggregate_rows, manifest.cases)
        metrics.update(mode_metrics)
        durations = runtimes[mode.value]
        metrics[f"{mode.value}.runtime_seconds_per_article"] = Metric(
            value=statistics.mean(durations) if durations else None,
            unit="seconds",
            direction="lower",
        )
        mode_runs = [row for row in runs if row.config_snapshot["ab_test"]["mode"] == mode.value]
        mode_calls = [
            call
            for run in mode_runs
            for call in run.llm_calls.all()
            if call.stage in {Stage.EVALUATION, Stage.CONSOLIDATION}
        ]
        known_cost = sum((call.cost_usd or Decimal(0) for call in mode_calls), Decimal(0))
        unpriced = sum(call.cost_usd is None for call in mode_calls)
        denominator = len(manifest.cases) * replicates
        metrics[f"{mode.value}.cost_usd_per_article"] = Metric(
            value=(None if unpriced else float(known_cost / denominator)),
            unit="USD/article",
            direction="lower",
        )
        summaries[mode.value] = {
            **summary,
            "run_count": len(mode_runs),
            "known_cost_usd": str(known_cost),
            "unpriced_calls": unpriced,
            "measured_runtimes": len(durations),
        }

    usage = UsageSummary(
        calls=len(all_calls),
        input_tokens=sum(call.input_tokens for call in all_calls),
        output_tokens=sum(call.output_tokens for call in all_calls),
        cached_tokens=sum(call.cached_tokens for call in all_calls),
        cache_write_tokens=sum(call.cache_write_tokens for call in all_calls),
        reasoning_tokens=sum(call.reasoning_tokens for call in all_calls),
        cost_usd=(
            None
            if any(call.cost_usd is None for call in all_calls)
            else sum((call.cost_usd or Decimal(0) for call in all_calls), Decimal(0))
        ),
        known_cost_usd=sum((call.cost_usd or Decimal(0) for call in all_calls), Decimal(0)),
        unpriced_calls=sum(call.cost_usd is None for call in all_calls),
    )
    source_sha256 = _source_hashes()
    prompt_versions["e4_prompt_catalog"].update(
        source_sha256[key] for key in source_sha256 if key.startswith("agents/prompts/")
    )
    return EvaluationReport(
        benchmark="ab_evaluation_mode",
        benchmark_version="2",
        created_at=datetime.now(UTC),
        dataset=DatasetIdentity(
            name=manifest.name,
            version=manifest.version,
            sha256=manifest_sha256,
            case_ids=tuple(case.id for case in manifest.cases),
        ),
        parameters={
            "batch_id": str(batch_id),
            "replicates": replicates,
            "modes": [mode.value for mode in MODES],
            "metric_protocol": "ab-evaluation-mode-v2",
            "acceptance_prediction": {
                "strict_positive": [Recommendation.ACCEPT.value],
                "potential_positive": [Recommendation.ACCEPT.value, Recommendation.MINOR.value],
                "abstain_when": "recommendation_missing_or_needs_human_review",
                "replicate_rule": "strict_majority_of_all_replicates",
            },
            "paired_runs": True,
        },
        model_specs=model_specs,
        prompt_versions={
            name: tuple(sorted(versions)) for name, versions in prompt_versions.items()
        },
        source_sha256=source_sha256,
        metrics=metrics,
        failures=0,
        usage=usage,
        details={
            "batch_id": str(batch_id),
            "replicates": replicates,
            "modes": summaries,
            "judge_invalidation_rate": (
                invalid_count / total_judgments if total_judgments else None
            ),
            "judge_invalid": invalid_count,
            "judge_total": total_judgments,
            "cases": details,
            "human_labelled_cases": sum(bool(case.human_scores) for case in manifest.cases),
            "human_score_entries": sum(len(case.human_scores) for case in manifest.cases),
            "human_decision_labelled_cases": sum(
                case.human_decision is not None for case in manifest.cases
            ),
        },
        notes=(
            "A correlação humana usa a média das notas válidas de slots e réplicas "
            "por caso/critério.",
            "A previsão de aprovação usa o veredito binário do dataset; resultados estritos e "
            "potenciais são reportados separadamente. O desempenho depende de rótulos humanos "
            "e não implica calibração fora da amostra.",
            "QWK arredonda essa média para a nota inteira mais próxima, com empate para cima.",
            "O custo por artigo fica nulo quando uma chamada da variante não tem preço conhecido.",
        ),
    )
