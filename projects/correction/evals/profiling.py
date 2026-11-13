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
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.evals.profiling_data import ProfilingCase, ProfilingDataset
from projects.correction.extractor.article import ExtractedArticle
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
    source_sha256: dict[str, str]
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal | None
    unpriced_calls: int
    overall: Scores
    by_area: dict[str, Scores]
    predictions: tuple[Prediction, ...]


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
    article: ExtractedArticle,
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
    cases = dataset.cases[:limit]
    sink = MemoryUsageSink()
    predictions = []
    specs: dict[Role, ModelSpec] = {}
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
            specs[Role.FAST] = factory.models.specs[Role.FAST]
        try:
            if factory is None:
                # Baseline condicional: o tipo de referência é conhecido, o field não é medido.
                paper_type, field = case.labels.paper_type, None
            else:
                assert taxonomy_version is not None
                profile = profile_article(
                    case.article,
                    factory=factory,
                    taxonomy_version=taxonomy_version,
                    max_attempts=max_attempts,
                )
                paper_type, field = profile.paper_type, profile.area_path[1].code
            roles, ambiguous = _roles(
                case.article, paper_type, factory=factory, threshold=confidence_threshold
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
    source = Path(__file__).parents[1] / "questions"
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
        source_sha256={
            name: hashlib.sha256((source / name).read_text(encoding="utf-8").encode()).hexdigest()
            for name in ("profiler.py", "section_roles.py")
        },
        calls=len(sink.calls),
        input_tokens=sum(call.input_tokens for call in sink.calls),
        output_tokens=sum(call.output_tokens for call in sink.calls),
        cost_usd=sum((call.cost_usd or Decimal(0) for call in sink.calls), Decimal(0))
        if all(call.cost_usd is not None for call in sink.calls)
        else None,
        unpriced_calls=sum(call.cost_usd is None for call in sink.calls),
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
