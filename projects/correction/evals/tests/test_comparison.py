from datetime import timedelta

import pytest

from projects.correction.agents.specs import Role
from projects.correction.evals.comparison import compare_reports
from projects.correction.evals.contracts import Metric
from projects.correction.evals.tests.helpers import changed, report


def test_model_parameters_prompts_and_code_identify_variants_but_time_does_not() -> None:
    original = report()
    spec = original.model_specs[Role.FAST].model_copy(update={"params": {"temperature": 0.1}})
    for candidate in (
        changed(original, model_specs={Role.FAST: spec}),
        changed(original, prompt_versions={"classifier": ("d" * 64,)}),
        changed(original, source_sha256={"runner.py": "e" * 64}),
    ):
        assert candidate.variant_id != original.variant_id
        assert compare_reports(original, candidate).comparable
    later = changed(original, created_at=original.created_at + timedelta(seconds=1))
    assert later.variant_id == original.variant_id and later.report_id != original.report_id
    # A ordem das chaves e das versões registradas não cria uma variante diferente.
    first = changed(original, prompt_versions={"classifier": ("b" * 64, "d" * 64)})
    second = changed(original, prompt_versions={"classifier": ("d" * 64, "b" * 64)})
    assert first.variant_id == second.variant_id


def test_deltas_keep_nulls_and_respect_metric_direction() -> None:
    original = report()
    metrics = original.metrics | {
        "accuracy": Metric(value=0.75, unit="fraction", direction="higher"),
        "failures": Metric(value=0, unit="count", direction="lower"),
    }
    comparison = compare_reports(original, changed(original, metrics=metrics, failures=0))
    assert comparison.comparable
    assert comparison.metrics["accuracy"].delta == 0.25
    assert comparison.metrics["accuracy"].improved
    assert comparison.metrics["failures"].delta == -1 and comparison.metrics["failures"].improved
    assert comparison.metrics["unmeasured"].delta is None


@pytest.mark.parametrize(
    "change", ["benchmark", "version", "dataset", "cohort", "policy", "unit", "direction"]
)
def test_incompatible_executions_have_no_metric_deltas(change: str) -> None:
    original = report()
    overrides: dict[str, object] = {}
    if change == "benchmark":
        overrides["benchmark"] = "other"
    elif change == "version":
        overrides["benchmark_version"] = "2"
    elif change in {"dataset", "cohort"}:
        dataset = original.dataset.model_dump()
        if change == "dataset":
            dataset["sha256"] = "d" * 64
        else:
            dataset["case_ids"] = ("b", "a")
        overrides["dataset"] = dataset
    elif change == "policy":
        overrides["parameters"] = {"limit": 3}
    else:
        overrides["metrics"] = original.metrics | {
            "accuracy": Metric(
                value=0.5,
                unit="percent" if change == "unit" else "fraction",
                direction="lower" if change == "direction" else "higher",
            ),
        }
    result = compare_reports(original, changed(original, **overrides))
    assert not result.comparable and result.reasons and result.metrics == {}


def test_boolean_and_numeric_parameters_do_not_silently_compare_as_equal() -> None:
    baseline = changed(report(), parameters={"policy": 1})
    candidate = changed(report(), parameters={"policy": True})
    assert baseline.comparison_key != candidate.comparison_key
    assert not compare_reports(baseline, candidate).comparable
