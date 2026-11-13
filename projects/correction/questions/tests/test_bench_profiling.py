"""Métricas, isolamento dos rótulos e contratos do comando; nenhum provedor externo."""

import json
from collections import Counter
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pydantic import ValidationError

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Role
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.evals.profiling import Prediction, evaluation_report, run_benchmark, scores
from projects.correction.evals.profiling_data import read_dataset
from projects.correction.questions.management.commands.load_taxonomy import read_catalog
from projects.correction.questions.models import Question, TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomySnapshot


def test_bundled_sample_has_thirty_unique_licensed_articles_and_complete_labels() -> None:
    dataset = read_dataset()
    assert Counter(case.area for case in dataset.cases) == {
        "computing": 10,
        "physics": 10,
        "medicine": 10,
    }
    assert sum(len(case.article.sections) - 1 for case in dataset.cases) == 152
    assert "human review pending" in dataset.annotation_status
    assert all(case.article.authors and case.source.license_notice for case in dataset.cases)


def test_duplicate_articles_and_missing_section_labels_are_rejected() -> None:
    data = read_dataset().model_dump(mode="json")
    data["cases"].append(data["cases"][0])
    with pytest.raises(ValidationError, match="repetidos"):
        type(read_dataset()).model_validate(data)
    data["cases"].pop()
    data["cases"][0]["labels"]["section_roles"].pop("sec_1")
    with pytest.raises(ValidationError, match="rótulo"):
        type(read_dataset()).model_validate(data)


def test_multilabel_scores_ignore_structural_sections_and_penalize_missing_predictions() -> None:
    case = read_dataset().cases[0]
    # Este caso tem cinco seções científicas e uma seção suplementar, além do abstract.
    partial = Prediction(
        case_id=case.id, field=case.labels.field, section_roles={"sec_4": (SectionRole.RESULTS,)}
    )
    result = scores((case,), (partial,), mode="llm")
    assert result.field_accuracy == 1 and result.sections == 6 and result.roles_exact == 0
    assert result.roles_micro_precision == 1 and result.roles_micro_recall == 1 / 7
    failed = scores((case,), (Prediction(case_id=case.id, error="InvalidProfile"),), mode="llm")
    assert failed.field_accuracy == 0 and failed.roles_accuracy == 0 and failed.failures == 1
    with pytest.raises(ValueError):
        scores((case,), (), mode="llm")


def test_rules_report_has_no_field_claim_no_calls_and_no_database_access() -> None:
    report = run_benchmark(read_dataset(), mode="rules")
    assert report.overall.articles == 30 and report.overall.sections == 152
    assert report.overall.field_accuracy is None and report.calls == 0
    assert report.model_specs == {} and report.cost_usd == 0
    assert 0 < report.overall.roles_accuracy < 1
    assert len(report.dataset_sha256) == 64 and len(report.by_area) == 3


def test_command_is_dry_run_by_default_and_protects_existing_reports(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    output = StringIO()
    call_command("bench_profiling", mode="llm", output=path, stdout=output)
    assert "Dry-run" in output.getvalue() and not path.exists()
    call_command("bench_profiling", execute=True, output=path, stdout=StringIO(), stderr=StringIO())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["format"] == "metis.evals"
    assert saved["metrics"]["overall.field_accuracy"]["value"] is None
    with pytest.raises(CommandError, match="arquivo novo"):
        call_command("bench_profiling", execute=True, output=path, stdout=StringIO())
    with pytest.raises(CommandError, match="positivos"):
        call_command("bench_profiling", limit=0)


@pytest.mark.django_db
def test_llm_path_uses_both_profiler_steps_and_never_supplies_reference_labels() -> None:
    snapshot = TaxonomySnapshot.from_catalog(
        read_catalog(Path(__file__).parent / "data" / "initial_taxonomy.json")
    )
    TaxonomyNode.import_snapshot(snapshot)
    dataset = read_dataset()
    first = dataset.cases[0]
    topic = next(
        node for node in TaxonomyNode.topics_for_field(snapshot.version, first.labels.field)
    )
    factories = []

    def build(case_id: str, sink: MemoryUsageSink) -> FakeAgentFactory:
        factory = FakeAgentFactory(
            case_id,
            "bench_profiling",
            usage_sink=sink,
            scripts={
                "profiler_field": [
                    {
                        "field": first.labels.field,
                        "paper_type": "methods",
                        "language": "en",
                        "keywords": [],
                        "confidence": 0.9,
                    }
                ],
                "profiler_topic": [
                    {
                        "topic": topic.code,
                        "subfield": topic.parent.code if topic.parent else "",
                        "secondary_areas": [],
                        "confidence": 0.9,
                    }
                ],
                "section_role_classifier": [{"roles": ["other"], "confidence": 0.9}],
            },
        )
        factories.append(factory)
        return factory

    report = run_benchmark(
        dataset, mode="llm", taxonomy_version=snapshot.version, limit=1, factory_builder=build
    )
    assert report.overall.field_accuracy == 1 and report.calls >= 2
    assert report.model_specs and report.prompt_versions and report.input_tokens > 0
    exported = evaluation_report(report)
    assert {"profiler_field", "profiler_topic"} <= exported.prompt_versions.keys()
    assert exported.model_specs == report.model_specs
    assert report.taxonomy_version == snapshot.version and Question.for_curation() == []
    calls = factories[0].calls
    assert [call.name for call in calls[:2]] == ["profiler_field", "profiler_topic"]
    for call in calls[:2]:
        assert call.payload.article is not None
        assert set(json.loads(call.payload.article)) == {"title", "abstract", "keywords"}

    captured: list[MemoryUsageSink] = []

    def drift(case_id: str, sink: MemoryUsageSink) -> FakeAgentFactory:
        factory = build(case_id, sink)
        if captured:
            factory.models.specs[Role.FAST] = factory.models.specs[Role.FAST].model_copy(
                update={"model_id": "changed-during-benchmark"}
            )
            factory.prompt_templates["profiler_field"] = "Changed prompt."
        captured.append(sink)
        return factory

    consistent = run_benchmark(
        dataset, mode="llm", taxonomy_version=snapshot.version, limit=2, factory_builder=drift
    )
    assert consistent.model_specs[Role.FAST] == report.model_specs[Role.FAST]
    assert {call.model_id for call in captured[0].calls} == {report.model_specs[Role.FAST].model_id}
    assert len(consistent.named_prompt_versions["profiler_field"]) == 1

    def down(case_id: str, sink: MemoryUsageSink) -> FakeAgentFactory:
        return FakeAgentFactory(
            case_id,
            "bench_profiling",
            usage_sink=sink,
            scripts={"profiler_field": [LLMUnavailable("private provider text")]},
        )

    failed = run_benchmark(
        dataset, mode="llm", taxonomy_version=snapshot.version, limit=1, factory_builder=down
    )
    assert failed.overall.failures == 1 and failed.overall.field_accuracy == 0
    assert "private provider text" not in failed.model_dump_json()
