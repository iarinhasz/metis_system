"""Mede regras locais ou o profiler real sem gravar Runs nem ler os rótulos no agente."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.prompts import template
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.evals.contracts import (
    DatasetIdentity,
    EvaluationReport,
    Metric,
    UsageSummary,
)
from projects.correction.evals.profiling_data import ProfilingCase, ProfilingDataset
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.extractor.document_adapter import to_extracted_document
from projects.correction.pipeline.errors import StageError
from projects.correction.questions.profile import FrozenModel
from projects.correction.questions.profiler import profile_article
from projects.correction.questions.section_roles import classify_role, rule_based_roles

type Mode = Literal["rules", "llm"]
type Roles = dict[str, tuple[SectionRole, ...]]
type FactoryBuilder = Callable[[str, MemoryUsageSink], AgentFactory]


class Prediction(FrozenModel):
    case_id: str
    field: str | None = None
    paper_type: PaperType | None = None
    section_roles: Roles = Field(default_factory=dict)
    ambiguous_sections: tuple[str, ...] = ()
    error: str | None = None


class Scores(FrozenModel):
    articles: int
    failures: int
    field_correct: int | None
    field_accuracy: float | None
    sections: int
    roles_exact: int
    roles_accuracy: float
    roles_micro_precision: float
    roles_micro_recall: float
    roles_micro_f1: float
    ambiguous_sections: int


class BenchmarkReport(FrozenModel):
    schema_version: int = 1
    created_at: str
    mode: Mode
    dataset_version: str
    dataset_sha256: str
    annotation_status: str
    taxonomy_version: str | None
    max_attempts: int
    confidence_threshold: float
    model_specs: dict[Role, ModelSpec]
    prompt_versions: tuple[str, ...]
    named_prompt_versions: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    source_sha256: dict[str, str]
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal | None
    unpriced_calls: int
    overall: Scores
    by_area: dict[str, Scores]
    predictions: tuple[Prediction, ...]
    usage: UsageSummary | None = None


def scores(
    cases: tuple[ProfilingCase, ...], predictions: tuple[Prediction, ...], *, mode: Mode
) -> Scores:
    by_id = {prediction.case_id: prediction for prediction in predictions}
    if len(by_id) != len(predictions) or set(by_id) != {case.id for case in cases}:
        raise ValueError("Cada artigo precisa de uma previsão, inclusive quando falha.")
    correct = exact = total = tp = fp = fn = failures = ambiguous = 0
    for case in cases:
        prediction = by_id[case.id]
        correct += prediction.field == case.labels.field
        failures += prediction.error is not None
        ambiguous += len(prediction.ambiguous_sections)
        # Abstract/referências não inflacionam o acerto dos papéis científicos.
        for section in case.article.sections:
            if section.key in {"abstract", "references"}:
                continue
            expected = set(case.labels.section_roles[section.id])
            actual = set(prediction.section_roles.get(section.id, ()))
            total += 1
            exact += actual == expected
            tp += len(expected & actual)
            fp += len(actual - expected)
            fn += len(expected - actual)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return Scores(
        articles=len(cases),
        failures=failures,
        field_correct=correct if mode == "llm" else None,
        field_accuracy=correct / len(cases) if mode == "llm" else None,
        sections=total,
        roles_exact=exact,
        roles_accuracy=exact / total if total else 0,
        roles_micro_precision=precision,
        roles_micro_recall=recall,
        roles_micro_f1=2 * precision * recall / (precision + recall) if precision + recall else 0,
        ambiguous_sections=ambiguous,
    )


def _roles(
    article: ExtractedDocument,
    paper_type: PaperType,
    *,
    factory: AgentFactory | None,
    threshold: float,
) -> tuple[Roles, tuple[str, ...]]:
    assignments = rule_based_roles(article, paper_type)
    ambiguous = tuple(item.section_id for item in assignments if item.ambiguous)
    sections = {section.id: section for section in article.sections}
    if factory is not None:
        assignments = tuple(
            classify_role(
                sections[item.section_id],
                paper_type,
                factory=factory,
                confidence_threshold=threshold,
            )
            if item.ambiguous
            else item
            for item in assignments
        )
    return {item.section_id: item.roles for item in assignments}, ambiguous


def run_benchmark(
    dataset: ProfilingDataset,
    *,
    mode: Mode,
    taxonomy_version: str | None = None,
    limit: int = 30,
    max_attempts: int = 1,
    confidence_threshold: float = 0.7,
    factory_builder: FactoryBuilder | None = None,
    progress: Callable[[str], None] | None = None,
) -> BenchmarkReport:
    if limit < 1 or max_attempts < 1 or not 0 <= confidence_threshold <= 1:
        raise ValueError("Limites e limiar do benchmark inválidos.")
    if mode == "llm" and not taxonomy_version:
        raise ValueError("O benchmark com LLM precisa de uma versão da taxonomia.")
    source = Path(__file__).parents[1] / "questions"
    source_hashes = {
        name: hashlib.sha256((source / name).read_text(encoding="utf-8").encode()).hexdigest()
        for name in ("profiler.py", "section_roles.py")
    } | {
        f"evals/{name}": hashlib.sha256(
            (Path(__file__).parent / name).read_text(encoding="utf-8").encode()
        ).hexdigest()
        for name in ("profiling.py", "profiling_data.py")
    }
    cases = dataset.cases[:limit]
    sink = MemoryUsageSink()
    predictions = []
    specs: dict[Role, ModelSpec] = {}
    templates: dict[str, str] | None = None
    for case in cases:
        if progress is not None:
            progress(case.id)
        factory = None
        paper_type = None
        field = None
        if mode == "llm":
            factory = (
                factory_builder(case.id, sink)
                if factory_builder
                else AgentFactory(case.id, "bench_profiling", usage_sink=sink)
            )
            if not specs:
                specs[Role.FAST] = factory.models.specs[Role.FAST].model_copy(deep=True)
                templates = {
                    name: factory.prompt_templates.get(name, template(name))
                    for name in ("profiler_field", "profiler_topic", "section_role_classifier")
                }
            # Todas as amostras usam a mesma configuração, mesmo em factories distintas.
            factory.models.specs[Role.FAST] = specs[Role.FAST]
            assert templates is not None
            factory.prompt_templates = dict(templates)
        try:
            if factory is None:
                # Baseline condicional: o tipo de referência é conhecido, o field não é medido.
                paper_type, field = case.labels.paper_type, None
            else:
                assert taxonomy_version is not None
                document = to_extracted_document(case.article)
                profile = profile_article(
                    document,
                    factory=factory,
                    taxonomy_version=taxonomy_version,
                    max_attempts=max_attempts,
                )
                paper_type, field = profile.paper_type, profile.area_path[1].code
            roles, ambiguous = _roles(
                to_extracted_document(case.article),
                paper_type,
                factory=factory,
                threshold=confidence_threshold,
            )
            predictions.append(
                Prediction(
                    case_id=case.id,
                    field=field,
                    paper_type=paper_type,
                    section_roles=roles,
                    ambiguous_sections=ambiguous,
                )
            )
        except (LLMUnavailable, StageError) as exc:
            predictions.append(
                Prediction(
                    case_id=case.id, field=field, paper_type=paper_type, error=type(exc).__name__
                )
            )
    measured = tuple(predictions)
    usage = UsageSummary.from_calls(sink.calls)
    return BenchmarkReport(
        created_at=datetime.now(UTC).isoformat(),
        mode=mode,
        dataset_version=dataset.version,
        dataset_sha256=hashlib.sha256(dataset.model_dump_json().encode()).hexdigest(),
        annotation_status=dataset.annotation_status,
        taxonomy_version=taxonomy_version,
        max_attempts=max_attempts,
        confidence_threshold=confidence_threshold,
        model_specs=specs,
        prompt_versions=tuple(sorted({call.prompt_version for call in sink.calls})),
        named_prompt_versions={
            name: tuple(sorted({call.prompt_version for call in sink.calls if call.agent == name}))
            for name in sorted({call.agent for call in sink.calls})
        },
        source_sha256=source_hashes,
        calls=usage.calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=usage.cost_usd,
        unpriced_calls=usage.unpriced_calls,
        usage=usage,
        overall=scores(cases, measured, mode=mode),
        by_area={
            area: scores(
                tuple(case for case in cases if case.area == area),
                tuple(
                    p
                    for p in measured
                    if p.case_id in {case.id for case in cases if case.area == area}
                ),
                mode=mode,
            )
            for area in sorted({case.area for case in cases})
        },
        predictions=measured,
    )


def evaluation_report(report: BenchmarkReport, *, legacy: bool = False) -> EvaluationReport:
    """Adapta a medição de profiling para o contrato compartilhado das evals."""
    if report.schema_version != 1:
        raise ValueError("Versão de relatório de profiling não suportada.")
    metrics = {}
    for prefix, group in [
        ("overall", report.overall),
        *[(f"area.{name}", group) for name, group in report.by_area.items()],
    ]:
        for name, value in group.model_dump().items():
            is_ratio = name.endswith(("accuracy", "precision", "recall", "f1"))
            direction = (
                "higher"
                if is_ratio
                else "lower"
                if name in {"failures", "ambiguous_sections"}
                else "informational"
            )
            metrics[f"{prefix}.{name}"] = Metric(
                value=value, unit="fraction" if is_ratio else "count", direction=direction
            )
    return EvaluationReport(
        benchmark="bench_profiling",
        benchmark_version="profiling-1",
        created_at=report.created_at,
        dataset=DatasetIdentity(
            name="profiling",
            version=report.dataset_version,
            sha256=report.dataset_sha256,
            case_ids=tuple(item.case_id for item in report.predictions),
        ),
        parameters={
            "mode": report.mode,
            "max_attempts": report.max_attempts,
            "confidence_threshold": report.confidence_threshold,
            "taxonomy_version": report.taxonomy_version,
            "annotation_status": report.annotation_status,
        },
        model_specs=report.model_specs,
        prompt_versions=report.named_prompt_versions
        or ({"legacy_rendered": report.prompt_versions} if report.prompt_versions else {}),
        source_sha256=report.source_sha256,
        metrics=metrics,
        failures=report.overall.failures,
        usage=report.usage
        or UsageSummary(
            calls=report.calls,
            input_tokens=report.input_tokens,
            output_tokens=report.output_tokens,
            cost_usd=report.cost_usd,
            known_cost_usd=report.cost_usd,
            unpriced_calls=report.unpriced_calls,
        ),
        details={"predictions": [item.model_dump(mode="json") for item in report.predictions]},
        notes=("Relatório legado: preserva apenas os hashes e contadores disponíveis no original.",)
        if legacy
        else (),
    )
