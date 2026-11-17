"""Métricas offline dos relatórios E4 contra rótulos PeerRead curados."""

import hashlib
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

from pydantic import JsonValue

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.specs import ModelSpec, Provider, Role
from projects.correction.agents.usage import LLMUsage
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evals.ab_evaluation_mode import (
    ABManifest,
    _binary_metrics,
    quadratic_weighted_kappa,
    spearman_correlation,
)
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    Metric,
    UsageSummary,
    fingerprint,
)
from projects.correction.evaluation.contracts import Recommendation
from projects.correction.evaluation.report import ReportContent


def _source_hashes() -> dict[str, str]:
    root = Path(__file__).parents[1]
    return {
        f"evals/{Path(__file__).name}": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "evals/ab_evaluation_mode.py": hashlib.sha256(
            (root / "evals" / "ab_evaluation_mode.py").read_bytes()
        ).hexdigest(),
        "evals/peerread_reviews.py": hashlib.sha256(
            (root / "evals" / "peerread_reviews.py").read_bytes()
        ).hexdigest(),
        "evals/contracts.py": hashlib.sha256(
            (root / "evals" / "contracts.py").read_bytes()
        ).hexdigest(),
        "evaluation/contracts.py": hashlib.sha256(
            (root / "evaluation" / "contracts.py").read_bytes()
        ).hexdigest(),
        "evaluation/report.py": hashlib.sha256(
            (root / "evaluation" / "report.py").read_bytes()
        ).hexdigest(),
        "evaluation/aggregation.py": hashlib.sha256(
            (root / "evaluation" / "aggregation.py").read_bytes()
        ).hexdigest(),
    }


def _runtime_seconds(run: Run) -> float | None:
    events = tuple(run.events.all().order_by("created_at", "id"))
    started = next(
        (index for index, event in enumerate(events) if event.to_status == RunStatus.EVALUATING),
        None,
    )
    if started is None:
        return None
    ended = next(
        (
            event.created_at
            for event in events[started + 1 :]
            if event.to_status == RunStatus.EVALUATED
        ),
        None,
    )
    if ended is None:
        return None
    return max(0.0, (ended - events[started].created_at).total_seconds())


def _acceptance_metrics(
    manifest: ABManifest, reports: dict[UUID, ReportContent]
) -> dict[str, dict[str, float | int | None]]:
    labelled = [case for case in manifest.cases if case.human_decision is not None]
    results: dict[str, dict[str, float | int | None]] = {}
    for strategy, positives in (
        ("strict", {Recommendation.ACCEPT}),
        ("potential", {Recommendation.ACCEPT, Recommendation.MINOR}),
    ):
        actual: list[bool] = []
        predicted: list[bool] = []
        for case in labelled:
            report = reports[case.source_run_id]
            if report.recommendation is None or report.needs_human_review:
                continue
            actual.append(case.human_decision == "accepted")
            predicted.append(report.recommendation in positives)
        results[strategy] = _binary_metrics(actual, predicted, labelled=len(labelled))
    return results


def build_review_report(
    manifest: ABManifest,
    manifest_sha256: str,
    sources: dict[UUID, Run],
) -> EvaluationReport:
    if not any(case.human_scores or case.human_decision for case in manifest.cases):
        raise ValueError("O manifesto precisa conter notas humanas ou vereditos de aprovação.")

    reports: dict[UUID, ReportContent] = {}
    modes: set[str] = set()
    model_snapshots: set[str] = set()
    prompt_versions: dict[str, set[str]] = defaultdict(set)
    model_specs: dict[Role, ModelSpec] = {}
    all_calls: list[LLMCall] = []
    runtimes: list[float] = []
    for case in manifest.cases:
        run = sources[case.source_run_id]
        report = ReportContent.model_validate(run.final_report.content)
        reports[run.pk] = report
        modes.add(report.versions.mode)
        model_snapshots.add(
            fingerprint(
                {
                    role: spec.model_dump(mode="json")
                    for role, spec in report.versions.model_specs.items()
                }
            )
        )
        for role, spec in report.versions.model_specs.items():
            model_specs[Role(role)] = spec
        for name, hashes in report.versions.prompt_versions.items():
            prompt_versions[name].update(hashes)
        all_calls.extend(
            call
            for call in run.llm_calls.all()
            if call.stage in {Stage.EVALUATION, Stage.CONSOLIDATION}
        )
        runtime = _runtime_seconds(run)
        if runtime is not None:
            runtimes.append(runtime)

    if len(modes) != 1:
        raise ValueError("Todos os Runs precisam usar o mesmo modo de avaliação.")
    if len(model_snapshots) != 1:
        raise ValueError(
            "Os relatórios precisam registrar os mesmos ModelSpecs efetivamente usados."
        )

    pairs: dict[Criterion, tuple[list[float], list[float]]] = {
        criterion: ([], []) for criterion in Criterion
    }
    case_details = []
    unmatched_human_score_entries = 0
    for case in manifest.cases:
        report = reports[case.source_run_id]
        predicted = {score.criterion_key: score.grade for score in report.criteria}
        compared: dict[str, float] = {}
        unmatched: list[str] = []
        for criterion, human_score in case.human_scores.items():
            grade = predicted.get(criterion)
            if grade is None:
                unmatched.append(criterion.value)
                unmatched_human_score_entries += 1
                continue
            human_values, model_values = pairs[criterion]
            human_values.append(float(human_score))
            model_values.append(float(grade))
            compared[criterion.value] = float(grade)
        case_details.append(
            {
                "case_id": case.id,
                "source_run_id": str(case.source_run_id),
                "human_decision": case.human_decision,
                "prediction": {
                    "recommendation": report.recommendation.value
                    if report.recommendation
                    else None,
                    "needs_human_review": report.needs_human_review,
                    "criteria": compared,
                },
                "human_scores_without_model_grade": unmatched,
            }
        )

    all_human = [value for humans, _ in pairs.values() for value in humans]
    all_predicted = [value for _, predictions in pairs.values() for value in predictions]
    metrics: dict[str, Metric] = {
        "bench_reviews.human_spearman": Metric(
            value=spearman_correlation(all_human, all_predicted),
            unit="correlation",
            direction="higher",
        ),
        "bench_reviews.human_qwk": Metric(
            value=quadratic_weighted_kappa(
                [int(value) for value in all_human],
                [
                    int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                    for value in all_predicted
                ],
            ),
            unit="coefficient",
            direction="higher",
        ),
    }
    for criterion, (humans, predictions) in pairs.items():
        rounded = [
            int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            for value in predictions
        ]
        metrics[f"bench_reviews.{criterion.value}.spearman"] = Metric(
            value=spearman_correlation(humans, predictions),
            unit="correlation",
            direction="higher",
        )
        metrics[f"bench_reviews.{criterion.value}.qwk"] = Metric(
            value=quadratic_weighted_kappa([int(value) for value in humans], rounded),
            unit="coefficient",
            direction="higher",
        )

    acceptance = _acceptance_metrics(manifest, reports)
    for strategy, scores in acceptance.items():
        for name in (
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall",
            "specificity",
            "f1",
            "coverage",
        ):
            metrics[f"bench_reviews.{strategy}_acceptance_{name}"] = Metric(
                value=scores[name], unit="fraction", direction="higher"
            )

    usage = UsageSummary.from_calls(
        [
            LLMUsage(
                run_id=str(call.run_id),
                stage=call.stage,
                role=Role(call.role),
                agent=call.agent,
                provider=Provider(call.provider),
                model_id=call.model,
                prompt_version=call.prompt_version,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                cached_tokens=call.cached_tokens,
                cache_write_tokens=call.cache_write_tokens,
                reasoning_tokens=call.reasoning_tokens,
                latency_ms=call.latency_ms,
                success=call.success,
                error=call.error or None,
                cost_usd=call.cost_usd,
            )
            for call in all_calls
        ]
    )
    dataset_labels = {
        "name": manifest.name,
        "version": manifest.version,
        "cases": [
            {
                "id": case.id,
                "human_decision": case.human_decision,
                "human_scores": {
                    criterion.value: score for criterion, score in case.human_scores.items()
                },
            }
            for case in manifest.cases
        ],
    }
    return EvaluationReport(
        benchmark="bench_reviews",
        benchmark_version="1",
        created_at=datetime.now(UTC),
        dataset=DatasetIdentity(
            name=manifest.name,
            version=manifest.version,
            sha256=fingerprint(dataset_labels),
            case_ids=tuple(case.id for case in manifest.cases),
        ),
        parameters={
            "mode": next(iter(modes)),
            "metric_protocol": "bench-reviews-v1",
            "human_score_policy": "curated_article_level_integer_scores",
            "acceptance_abstention": "missing_recommendation_or_needs_human_review",
        },
        model_specs=model_specs,
        prompt_versions={name: tuple(sorted(hashes)) for name, hashes in prompt_versions.items()},
        source_sha256=_source_hashes(),
        metrics=metrics,
        usage=usage,
        details={
            "source_manifest_sha256": manifest_sha256,
            "labelled_score_pairs": len(all_human),
            "unmatched_human_score_entries": unmatched_human_score_entries,
            "human_decision_labelled_cases": sum(
                case.human_decision is not None for case in manifest.cases
            ),
            "acceptance_prediction": cast(JsonValue, acceptance),
            "runtime_seconds_per_article": statistics.mean(runtimes) if runtimes else None,
            "measured_runtimes": len(runtimes),
            "cases": cast(JsonValue, case_details),
        },
        notes=(
            "Notas humanas por artigo devem ser curadas antes da comparação; o benchmark não lê "
            "pareceres nem envia rótulos aos modelos.",
            "QWK arredonda a nota prevista para o inteiro mais próximo, com empate para cima.",
            "A previsão binária usa o veredito PeerRead; casos com revisão humana ou sem "
            "recomendação são abstenções.",
        ),
    )
