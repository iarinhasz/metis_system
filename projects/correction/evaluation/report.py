"""Relatório tipado e render Markdown; a narrativa não escreve na agregação."""

import html
import re
from decimal import Decimal
from uuid import UUID

from projects.correction.agents.schemas.consolidation import MetaPoint, MetaReview
from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    CrossCheckResult,
    EvaluatorSlot,
    ItemType,
    Observation,
    Verdict,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import ModelSpec
from projects.correction.evaluation.contracts import (
    Aggregation,
    AggregationPolicy,
    CriterionScore,
    Recommendation,
    ReviewedSlot,
    item_id,
)
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.questions.criteria import EvaluationConfig
from projects.correction.questions.profile import FrozenModel, QuestionSnapshot

type EvidenceItem = Observation | CrossCheckResult | CriterionSynthesis


class ReportObservation(FrozenModel):
    id: str
    evaluator_slot: EvaluatorSlot
    observation: Observation
    unresolved: bool


class ReportSection(FrozenModel):
    id: str
    title: str
    roles: tuple[SectionRole, ...]
    observations: tuple[ReportObservation, ...]


class IntegritySummary(FrozenModel):
    status: str = "not_checked"
    risk_level: str | None = None
    findings: tuple[str, ...] = ()
    coverage: dict[str, bool] = {"integrity_stage_implemented": False}


class FigureIssues(FrozenModel):
    id: str
    label: str
    page: int
    issues: tuple[str, ...]


class ReportVersions(FrozenModel):
    model_specs: dict[str, ModelSpec]
    prompt_versions: dict[str, tuple[str, ...]]
    mode: str
    review_rounds: dict[str, int]
    evaluation_config: EvaluationConfig
    evaluation_config_origin: str
    question: QuestionSnapshot
    taxonomy_version: str
    extraction_version: str
    policy: AggregationPolicy


class ReportContent(FrozenModel):
    schema_version: int = 1
    run_id: UUID
    title: str
    recommendation: Recommendation | None
    total_score: Decimal | None
    agreement: Decimal | None
    needs_human_review: bool
    criteria: tuple[CriterionScore, ...]
    sections: tuple[ReportSection, ...]
    strengths: tuple[MetaPoint, ...]
    weaknesses: tuple[MetaPoint, ...]
    suggestions: tuple[MetaPoint, ...]
    evidence: dict[str, EvidenceItem]
    integrity: IntegritySummary
    figures: tuple[FigureIssues, ...]
    versions: ReportVersions
    unresolved: tuple[str, ...]
    warnings: tuple[str, ...]


def reference_catalog(
    reviews: tuple[ReviewedSlot, ...], aggregation: Aggregation
) -> dict[str, EvidenceItem]:
    """Somente votos incluídos e evidências válidas ficam disponíveis para a narrativa."""
    catalog: dict[str, EvidenceItem] = {}
    included = {
        (score.criterion_key, vote.slot) for score in aggregation.criteria for vote in score.votes
    }
    for review in reviews:
        pending = {(item.item_type, item.item_key) for item in review.state.unresolved}
        valid = {
            (item.item_type, item.item_key)
            for item in review.verdicts
            if item.verdict == Verdict.VALID
        } - pending
        for synthesis in review.state.criteria:
            if (synthesis.criterion_key, review.slot) not in included:
                continue
            catalog[item_id(review.slot, ItemType.CRITERION, synthesis.criterion_key)] = synthesis
            for observation in review.state.observations:
                if (
                    observation.id in synthesis.observation_ids
                    and (ItemType.OBSERVATION, observation.id) in valid
                ):
                    catalog[item_id(review.slot, ItemType.OBSERVATION, observation.id)] = (
                        observation
                    )
            for check in review.state.cross_checks:
                if check.id in synthesis.check_ids and (ItemType.CHECK, check.id) in valid:
                    catalog[item_id(review.slot, ItemType.CHECK, check.id)] = check
    return catalog


def validate_meta_review(
    review: MetaReview, references: dict[str, EvidenceItem], active: set[Criterion]
) -> tuple[MetaReview, int]:
    dropped = 0
    fields: dict[str, tuple[MetaPoint, ...]] = {}
    for name in ("strengths", "weaknesses", "suggestions"):
        points = []
        for point in getattr(review, name):
            if set(point.evidence_ids) <= references.keys() and set(point.criterion_keys) <= active:
                points.append(point)
            else:
                dropped += 1
        fields[name] = tuple(points)
    return MetaReview(**fields), dropped


def build_report(
    *,
    run_id: UUID,
    article: ExtractedDocument,
    reviews: tuple[ReviewedSlot, ...],
    aggregation: Aggregation,
    meta: MetaReview,
    section_roles: dict[str, tuple[SectionRole, ...]],
    versions: ReportVersions,
    warnings: tuple[str, ...] = (),
) -> ReportContent:
    sections = []
    unresolved = tuple(
        item_id(review.slot, item.item_type, item.item_key)
        for review in reviews
        for item in review.state.unresolved
    )
    for section in article.sections:
        observations = []
        for review in reviews:
            valid = {
                (item.item_type, item.item_key)
                for item in review.verdicts
                if item.verdict == Verdict.VALID
            }
            for observation in review.state.observations:
                if observation.section_id != section.id:
                    continue
                ref = item_id(review.slot, ItemType.OBSERVATION, observation.id)
                observations.append(
                    ReportObservation(
                        id=ref,
                        evaluator_slot=review.slot,
                        observation=observation,
                        unresolved=ref in unresolved
                        or (ItemType.OBSERVATION, observation.id) not in valid,
                    )
                )
        sections.append(
            ReportSection(
                id=section.id,
                title=section.title,
                roles=section_roles.get(section.id, (SectionRole.OTHER,)),
                observations=tuple(observations),
            )
        )
    return ReportContent(
        run_id=run_id,
        title=article.title,
        recommendation=aggregation.recommendation,
        total_score=aggregation.total_score,
        agreement=aggregation.agreement,
        needs_human_review=aggregation.needs_human_review or bool(unresolved) or bool(warnings),
        criteria=aggregation.criteria,
        sections=tuple(sections),
        strengths=meta.strengths,
        weaknesses=meta.weaknesses,
        suggestions=meta.suggestions,
        evidence=reference_catalog(reviews, aggregation),
        integrity=IntegritySummary(),
        figures=tuple(
            FigureIssues(
                id=figure.id, label=figure.label, page=figure.page, issues=figure.description.issues
            )
            for figure in article.figures
            if figure.description and figure.description.issues
        ),
        versions=versions,
        unresolved=unresolved,
        warnings=tuple(
            dict.fromkeys((*warnings, "integrity_not_checked", "recommendation_bands_uncalibrated"))
        ),
    )


def _escape(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", html.escape(text))


def render_markdown(report: ReportContent) -> str:
    def number(value: Decimal | None) -> str:
        return f"{value:.2f}" if value is not None else "indisponível"

    lines = [
        f"# {_escape(report.title)}",
        "",
        f"Run: `{report.run_id}`",
        "",
        f"Recomendação: **{report.recommendation or 'revisão humana necessária'}**",
        f"Nota ponderada: **{number(report.total_score)}** · "
        f"Concordância: **{number(report.agreement)}**",
        "",
        f"Revisão humana sinalizada: {'sim' if report.needs_human_review else 'não'}",
        "",
        "## Critérios",
        "",
    ]
    for score in report.criteria:
        lines += [
            f"### {_escape(score.label)}",
            "",
            f"Nota: {number(score.grade)} · Dispersão: {number(score.dispersion)} · "
            f"Votos válidos: {len(score.votes)}",
            "",
        ]
        for vote in score.votes:
            lines.append(
                f"- {vote.slot.upper()} (rodada {vote.round_number}, nota {vote.grade}): "
                f"{_escape(vote.justification)}"
            )
        for excluded in score.excluded:
            lines.append(f"- Voto excluído de {excluded.slot.upper()}: `{excluded.reason}`")
        lines.append("")
    for name, title in (
        ("strengths", "Pontos fortes"),
        ("weaknesses", "Pontos fracos"),
        ("suggestions", "Sugestões"),
    ):
        lines += [f"## {title}", ""]
        for point in getattr(report, name):
            lines.append(
                f"- {_escape(point.text)} [{', '.join(_escape(ref) for ref in point.evidence_ids)}]"
            )
        lines.append("")
    lines += ["## Seções", ""]
    for section in report.sections:
        lines += [f"### {_escape(section.title)}", ""]
        for item in section.observations:
            flag = " [unresolved]" if item.unresolved else ""
            lines.append(f"- {_escape(item.id)}{flag}: {_escape(item.observation.statement)}")
        lines.append("")
    lines += ["## Evidências", ""]
    for ref, evidence_item in report.evidence.items():
        if isinstance(evidence_item, Observation):
            description = evidence_item.statement
        elif isinstance(evidence_item, CriterionSynthesis):
            description = evidence_item.justification
        else:
            description = f"{evidence_item.kind}: {evidence_item.verdict}"
        lines.append(f"- {_escape(ref)}: {_escape(description)}")
        for evidence in evidence_item.evidence:
            lines.append(f"  - {_escape(evidence.section_id)}: {_escape(evidence.quote)}")
    lines += [
        "",
        "## Integridade",
        "",
        "Ainda não verificada: o E3 permanece pass-through.",
        "",
        "## Figuras",
        "",
    ]
    for figure in report.figures:
        lines.append(
            f"- {_escape(figure.label)} (página {figure.page}): {_escape('; '.join(figure.issues))}"
        )
    lines += [
        "",
        "## Versões",
        "",
        f"Question: `{report.versions.question.id}` v{report.versions.question.version}",
        f"Taxonomia: `{report.versions.taxonomy_version}`",
        f"Modo: `{report.versions.mode}` · Agregação: `{report.versions.policy.version}`",
        "",
    ]
    for role, spec in report.versions.model_specs.items():
        lines.append(f"- {_escape(role)}: {_escape(spec.provider)} / {_escape(spec.model_id)}")
    for agent, hashes in report.versions.prompt_versions.items():
        lines.append(f"- Prompt {_escape(agent)}: {', '.join(hashes)}")
    if report.unresolved:
        lines += ["", "## Itens pendentes", "", *(f"- {_escape(ref)}" for ref in report.unresolved)]
    if report.warnings:
        messages = {
            "integrity_not_checked": "A integridade ainda não foi verificada.",
            "recommendation_bands_uncalibrated": (
                "As faixas de recomendação são provisórias e aguardam calibração."
            ),
            "meta_review_invalid_schema": (
                "A narrativa não pôde ser validada e precisa de revisão humana."
            ),
            "no_valid_evidence_for_meta_review": "Não há evidência válida para gerar a narrativa.",
        }
        lines += ["", "## Avisos", ""]
        for warning in report.warnings:
            message = (
                f"Foram removidos {warning.split(':')[-1]} pontos sem referências válidas."
                if warning.startswith("meta_points_dropped:")
                else messages.get(warning, warning)
            )
            lines.append(f"- {_escape(message)}")
    return "\n".join(lines) + "\n"
