from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import EvaluationMode, EvaluatorSlot
from projects.correction.agents.specs import Family, Role, development_spec
from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import RunPurpose, RunStatus, Stage
from projects.correction.evals.ab_evaluation_mode import (
    MODES,
    ABCase,
    ABManifest,
    _acceptance_metrics,
    _mode_metrics,
    build_report,
    create_ab_runs,
    quadratic_weighted_kappa,
    spearman_correlation,
    validate_sources,
)
from projects.correction.evaluation.models import FinalReport
from projects.correction.evaluation.tests.helpers import record_review, review
from projects.correction.questions.criteria import STANDARD


def test_rank_correlations_handle_ties_and_unmeasured_values() -> None:
    assert spearman_correlation([1, 2, 2, 4], [2, 3, 3, 5]) == pytest.approx(1)
    assert spearman_correlation([1, 1], [2, 3]) is None
    assert spearman_correlation([1], [1]) is None
    assert quadratic_weighted_kappa([1, 2, 3], [1, 2, 3]) == pytest.approx(1)
    assert quadratic_weighted_kappa([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert quadratic_weighted_kappa([], []) is None


def test_manifest_rejects_duplicate_ids_and_non_integer_or_out_of_range_scores() -> None:
    case = {"id": "paper", "source_run_id": str(uuid4())}
    with pytest.raises(ValidationError):
        ABManifest.model_validate({"name": "sample", "version": "1", "cases": [case, case]})
    with pytest.raises(ValidationError):
        ABCase.model_validate(
            {"id": "paper", "source_run_id": str(uuid4()), "human_scores": {"clarity": 6}}
        )
    with pytest.raises(ValidationError):
        ABCase.model_validate(
            {
                "id": "paper",
                "source_run_id": str(uuid4()),
                "human_scores": {"clarity": "4"},
            }
        )


def test_acceptance_prediction_reports_strict_and_potential_views_and_abstentions() -> None:
    case_accepted = ABCase(id="accepted-paper", source_run_id=uuid4(), human_decision="accepted")
    case_rejected = ABCase(id="rejected-paper", source_run_id=uuid4(), human_decision="rejected")
    rows = []
    for case, recommendations in (
        (case_accepted, ["minor", "accept", "accept"]),
        (case_rejected, ["reject", None, "reject"]),
    ):
        for replicate, recommendation in enumerate(recommendations, start=1):
            rows.append(
                {
                    "case_id": case.id,
                    "mode": EvaluationMode.SECTIONED.value,
                    "replicate": replicate,
                    "recommendation": recommendation,
                    "needs_human_review": recommendation is None,
                }
            )

    metrics = _acceptance_metrics(EvaluationMode.SECTIONED, rows, (case_accepted, case_rejected))

    assert metrics["strict"]["accuracy"] == 1
    assert metrics["strict"]["coverage"] == 1
    assert metrics["strict"]["abstentions"] == 0
    assert metrics["potential"]["accuracy"] == 1
    assert metrics["potential"]["true_positive"] == 1


def test_acceptance_prediction_abstains_when_replicas_do_not_reach_majority() -> None:
    case = ABCase(id="paper", source_run_id=uuid4(), human_decision="accepted")
    rows = [
        {
            "case_id": case.id,
            "mode": EvaluationMode.SECTIONED.value,
            "recommendation": value,
            "needs_human_review": value is None,
        }
        for value in ("accept", "reject", None)
    ]

    metrics = _acceptance_metrics(EvaluationMode.SECTIONED, rows, (case,))

    assert metrics["strict"]["coverage"] == 0
    assert metrics["strict"]["abstentions"] == 1


def test_binary_human_verdict_works_without_criterion_scores() -> None:
    case = ABCase(id="paper", source_run_id=uuid4(), human_decision="rejected")
    rows = [
        {
            "case_id": case.id,
            "mode": EvaluationMode.SECTIONED.value,
            "replicate": replicate,
            "grades": {slot.value: {} for slot in EvaluatorSlot},
            "families": {slot.value: Family.GPT for slot in EvaluatorSlot},
            "judge_invalid": 0,
            "judge_total": 0,
            "recommendation": "reject",
            "needs_human_review": False,
        }
        for replicate in (1, 2, 3)
    ]

    metrics, _ = _mode_metrics(EvaluationMode.SECTIONED, rows, (case,))

    assert metrics["sectioned.human_spearman"].value is None
    assert metrics["sectioned.human_qwk"].value is None
    assert metrics["sectioned.strict_acceptance_accuracy"].value == 1


def test_mode_metrics_report_repetition_agreement_judging_and_human_alignment() -> None:
    case = ABCase(
        id="paper",
        source_run_id=uuid4(),
        human_scores={Criterion.SOUNDNESS: 4, Criterion.CLARITY: 2},
    )
    rows = []
    for replicate, soundness_a in enumerate((3, 4, 5), start=1):
        rows.append(
            {
                "case_id": case.id,
                "mode": EvaluationMode.SECTIONED.value,
                "replicate": replicate,
                "grades": {
                    "a": {"soundness": soundness_a, "clarity": 2},
                    "b": {"soundness": soundness_a, "clarity": 2},
                    "c": {"soundness": 4, "clarity": 2},
                },
                "families": {
                    "a": Family.GPT,
                    "b": Family.GEMINI,
                    "c": Family.GPT,
                },
                "judge_invalid": int(replicate == 1),
                "judge_total": 2,
            }
        )

    metrics, summary = _mode_metrics(EvaluationMode.SECTIONED, rows, (case,))

    assert metrics["sectioned.evaluator_disagreement_ab_mae"].value == 0
    assert metrics["sectioned.evaluator_disagreement_ac_same_family_mae"].value == pytest.approx(
        1 / 3
    )
    assert metrics["sectioned.evaluator_disagreement_ac_cross_family_mae"].value is None
    assert metrics["sectioned.judge_invalidation_rate"].value == pytest.approx(1 / 6)
    assert metrics["sectioned.human_spearman"].value == pytest.approx(1)
    assert metrics["sectioned.human_qwk"].value == pytest.approx(1)
    assert summary["repeat_score_cells"] == 6


@pytest.mark.django_db
def test_create_ab_runs_is_paired_idempotent_and_preserves_source_snapshots(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    run.profile = {"complete": True, "classification": {"paper_type": "empirical"}}
    run.config_snapshot = {"model_specs": {"fast": {"model_id": "fake"}}}
    run.save(update_fields=["profile", "config_snapshot"])
    manifest = ABManifest(
        name="sample",
        version="1",
        cases=(ABCase(id="paper", source_run_id=run.pk),),
    )
    digest = "a" * 64
    batch_id = uuid4()
    monkeypatch.setattr(
        "projects.correction.evals.ab_evaluation_mode.validate_sources",
        lambda _: {run.pk: run},
    )
    publish = Mock()
    monkeypatch.setattr(
        "projects.correction.evals.ab_evaluation_mode.publish_stage_on_commit", publish
    )

    created, is_new = create_ab_runs(manifest, digest, batch_id=batch_id, replicates=2)

    assert is_new
    assert len(created) == 2 * len(MODES) == publish.call_count
    assert {item.purpose for item in created} == {RunPurpose.AB_TEST}
    assert {item.config_snapshot["evaluation_mode"] for item in created} == {
        mode.value for mode in MODES
    }
    assert all(
        item.profile == run.profile and item.extraction_id == run.extraction_id for item in created
    )

    repeated, is_new = create_ab_runs(manifest, digest, batch_id=batch_id, replicates=2)

    assert not is_new
    assert {item.pk for item in repeated} == {item.pk for item in created}
    assert publish.call_count == len(created)

    with pytest.raises(ValueError, match="outro manifesto"):
        create_ab_runs(manifest, "b" * 64, batch_id=batch_id, replicates=2)


@pytest.mark.django_db
def test_validate_sources_rejects_missing_or_unfinished_source_runs(run: Run) -> None:
    manifest = ABManifest(
        name="sample",
        version="1",
        cases=(ABCase(id="paper", source_run_id=run.pk),),
    )
    with pytest.raises(ValueError, match="concluídos"):
        validate_sources(manifest)

    missing = ABManifest(
        name="sample",
        version="1",
        cases=(ABCase(id="missing", source_run_id=uuid4()),),
    )
    with pytest.raises(ValueError, match="existente"):
        validate_sources(missing)


@pytest.mark.django_db
def test_build_report_requires_complete_paired_batch_and_records_variants(run: Run) -> None:
    batch_id = uuid4()
    case = ABCase(
        id="paper",
        source_run_id=uuid4(),
        human_scores={Criterion.SOUNDNESS: 4},
        human_decision="accepted",
    )
    manifest = ABManifest(name="sample", version="1", cases=(case,))
    digest = "a" * 64
    runs = []
    for mode in MODES:
        for replicate in range(1, 4):
            item = Run.create(
                attempt=run.attempt,
                purpose=RunPurpose.AB_TEST,
                config_snapshot={
                    "ab_test": {
                        "batch_id": str(batch_id),
                        "manifest_sha256": digest,
                        "source_run_id": str(case.source_run_id),
                        "case_id": case.id,
                        "mode": mode.value,
                        "replicate": replicate,
                    },
                    "evaluation_config": STANDARD.model_dump(mode="json"),
                    "model_specs": {
                        Role.FAST.value: development_spec(Role.FAST).model_dump(mode="json")
                    },
                    "prompt_versions": {"profiler": "b" * 64},
                },
            )
            Run.objects.filter(pk=item.pk).update(
                status=RunStatus.EVALUATING,
                stage=Stage.EVALUATION,
                current_task_id="e4",
            )
            for slot in EvaluatorSlot:
                record_review(item, review(slot, 4))
            RunEvent.objects.create(
                run=item,
                event_type=RunEvent.EventType.TRANSITION,
                to_status=RunStatus.EVALUATING,
                stage=Stage.EVALUATION,
                event_key=f"{item.pk}:evaluating",
            )
            RunEvent.objects.create(
                run=item,
                event_type=RunEvent.EventType.TRANSITION,
                to_status=RunStatus.EVALUATED,
                stage=Stage.EVALUATION,
                event_key=f"{item.pk}:evaluated",
            )
            Run.objects.filter(pk=item.pk).update(status=RunStatus.DONE, current_task_id=None)
            recommendation = "accept" if mode is EvaluationMode.SECTIONED else "minor"
            FinalReport.objects.create(
                run=item,
                recommendation=recommendation,
                content={"needs_human_review": False},
                markdown="",
            )
            runs.append(Run.objects.get(pk=item.pk))

    report = build_report(
        manifest,
        digest,
        batch_id=batch_id,
        replicates=3,
        runs=tuple(runs),
    )

    assert report.benchmark == "ab_evaluation_mode"
    assert report.metrics["sectioned.intra_evaluator_score_stddev"].value == 0
    assert report.metrics["whole_document.intra_evaluator_score_stddev"].value == 0
    assert report.metrics["sectioned.strict_acceptance_accuracy"].value == 1
    assert report.metrics["whole_document.strict_acceptance_accuracy"].value == 0
    assert report.metrics["whole_document.potential_acceptance_accuracy"].value == 1
    assert report.details["human_decision_labelled_cases"] == 1
    assert report.prompt_versions["profiler"] == ("b" * 64,)
    judge_total = report.details["judge_total"]
    assert isinstance(judge_total, int) and judge_total > 0
    assert report.usage.calls == 0
