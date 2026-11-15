import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from projects.correction.evals.comparison import compare_reports
from projects.correction.evals.profiling_data import read_dataset
from projects.correction.evals.reports import output_path, read_report, write_artifact
from projects.correction.evals.tests.helpers import changed, report


def test_immutable_utf8_files_and_default_destinations(tmp_path: Path) -> None:
    original = changed(report(), notes=("Medição científica.",))
    first = output_path("synthetic", directory=tmp_path / "results")
    second = output_path("synthetic", directory=tmp_path / "results")
    assert first != second and first.parent.is_dir()
    write_artifact(original, first)
    before = first.read_bytes()
    assert read_report(first) == original and "científica" in first.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_artifact(original, first)
    assert first.read_bytes() == before
    with pytest.raises(ValueError):
        output_path("synthetic", output=first)
    with pytest.raises(ValueError):
        output_path("../outside", directory=tmp_path)


def test_historical_profiling_baseline_can_be_compared_without_rewriting_it(tmp_path: Path) -> None:
    legacy = Path(__file__).parents[1] / "data" / "baseline_rules.json"
    before = legacy.read_bytes()
    baseline = read_report(legacy)
    exported = tmp_path / "converted.json"
    write_artifact(baseline, exported)
    candidate = read_report(exported)
    comparison = compare_reports(baseline, candidate)
    assert baseline.notes and comparison.comparable
    assert all(metric.delta in {0, None} for metric in comparison.metrics.values())
    assert legacy.read_bytes() == before


def test_compare_command_does_not_write_by_default_and_rejects_wrong_inputs(tmp_path: Path) -> None:
    left, right, output = (tmp_path / name for name in ("left.json", "right.json", "delta.json"))
    write_artifact(report(), left)
    write_artifact(report(), right)
    call_command("compare_evals", left, right, output=output, stdout=StringIO())
    assert not output.exists()
    call_command("compare_evals", left, right, execute=True, output=output, stdout=StringIO())
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["comparable"] and saved["baseline_report"] == report().report_id
    with pytest.raises(CommandError, match="arquivo novo"):
        call_command("compare_evals", left, right, execute=True, output=output, stdout=StringIO())
    bad = tmp_path / "bad.json"
    write_artifact(changed(report(), parameters={"other": True}), bad)
    with pytest.raises(CommandError, match="incompatíveis"):
        call_command("compare_evals", left, bad, stdout=StringIO())
    bad.write_text('{"format":"metis.evals","schema_version":99}', encoding="utf-8")
    with pytest.raises(CommandError, match="válidos"):
        call_command("compare_evals", left, bad, stdout=StringIO())


def test_profiling_execute_uses_shared_output_directory_and_dry_run_leaves_it_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from projects.correction.evals import reports
    from projects.correction.questions.management.commands import bench_profiling

    destination = tmp_path / "results"
    monkeypatch.setattr(
        bench_profiling,
        "output_path",
        lambda name, **kw: reports.output_path(name, directory=destination, **kw),
    )
    call_command("bench_profiling", stdout=StringIO())
    assert not destination.exists()
    call_command("bench_profiling", execute=True, limit=1, stdout=StringIO(), stderr=StringIO())
    [path] = list(destination.glob("*.json"))
    artifact = read_report(path)
    assert artifact.dataset.case_ids == (read_dataset().cases[0].id,)
    assert artifact.parameters["mode"] == "rules" and artifact.usage.calls == 0
