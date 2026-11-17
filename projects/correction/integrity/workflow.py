"""Execução do E3: coleta, detecção, regras determinísticas e relatório persistido."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from agno.workflow import Parallel, Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput
from django.db import close_old_connections, connections
from pydantic import BaseModel, ConfigDict, Field

from projects.correction.agents.factory import AgentFactory
from projects.correction.attempts.models import Run
from projects.correction.extractor.contract import DocumentReference, ExtractedDocument
from projects.correction.integrity.adjudication import (
    AdjudicationBatch,
    adjudicate_pairs,
    lexical_pairs,
)
from projects.correction.integrity.alignment import (
    CitationAlignmentResult,
    check_citation_alignment,
    fetch_open_access_full_text,
)
from projects.correction.integrity.candidates import (
    Candidate,
    CandidateCollection,
    CandidateCollector,
)
from projects.correction.integrity.citation_filter import SimilarityPair
from projects.correction.integrity.consistency import (
    CitationConsistency,
    check_citation_consistency,
)
from projects.correction.integrity.cross_phases import cross_phase_findings
from projects.correction.integrity.embeddings import MAX_CHUNK_WORDS, embed_documents
from projects.correction.integrity.existence import (
    ReferenceExistence,
    check_reference_existence,
)
from projects.correction.integrity.models import IntegrityReport
from projects.correction.integrity.resolution import ReferenceResolution, resolve_references
from projects.correction.integrity.retraction import (
    RetractionFinding,
    find_retracted_references,
)
from projects.correction.integrity.rules import (
    RULES_VERSION,
    FindingRecord,
    FindingSeverity,
    RiskDecision,
    decide_risk,
)
from projects.correction.integrity.semantic import (
    SemanticConfig,
    SemanticOverlap,
    find_semantic_overlaps,
)
from projects.correction.metis.config import settings
from projects.correction.queries.integrity.source_document import SourceChunkInput


class IntegrityNarrative(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    narrative: str = Field(min_length=1, max_length=6000)


class IntegrityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: str
    risk_level: str
    rules_version: str
    finding_count: int
    coverage: dict[str, object]
    reasons: tuple[str, ...]


class IntegrityPhaseOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    findings: tuple[FindingRecord, ...] = ()
    details: dict[str, Any] = Field(default_factory=dict)
    existence: tuple[ReferenceExistence, ...] = ()
    retractions: tuple[RetractionFinding, ...] = ()
    consistency: CitationConsistency | None = None
    alignments: tuple[CitationAlignmentResult, ...] = ()


class PhaseCheckpointStore(Protocol):
    def get_checkpoint(self, run_id: str, phase: str) -> dict[str, Any] | None: ...

    def save_checkpoint(self, run_id: str, phase: str, payload: dict[str, Any]) -> object: ...


class CandidateCollectorLike(Protocol):
    def collect(self, document: ExtractedDocument) -> CandidateCollection: ...


class ReportLike(Protocol):
    @property
    def pk(self) -> object: ...


CandidateResolver = Callable[[tuple[DocumentReference, ...]], tuple[ReferenceResolution, ...]]
SemanticFinder = Callable[[ExtractedDocument], tuple[SemanticOverlap, ...]]
ReportWriter = Callable[..., ReportLike]


def run_integrity(
    run_id: str,
    *,
    factory: AgentFactory,
    candidate_collector: CandidateCollectorLike | None = None,
    reference_resolver: CandidateResolver = resolve_references,
    semantic_finder: SemanticFinder | None = None,
    report_writer: ReportWriter | None = None,
    checkpoint_store: PhaseCheckpointStore | None = None,
) -> IntegrityResult:
    run = Run.get_by_id(run_id)
    if run.extraction is None:
        return _skipped_result(run, report_writer=report_writer, reason="extraction_missing")
    try:
        document = run.extraction.document
    except ValueError:
        return _skipped_result(
            run, report_writer=report_writer, reason="content_sections_unavailable"
        )
    if not document.sections:
        return _skipped_result(
            run, report_writer=report_writer, reason="content_sections_unavailable"
        )
    store = checkpoint_store or _default_checkpoint_store()
    resolutions = _load_or_resolve(run_id, document.references, reference_resolver, store)

    def similarity_phase() -> IntegrityPhaseOutput:
        return _run_similarity_phase(
            document,
            factory=factory,
            candidate_collector=candidate_collector,
            semantic_finder=semantic_finder,
        )

    def citation_phase() -> IntegrityPhaseOutput:
        return _run_citation_phase(document, resolutions, factory=factory)

    phase1, phase2 = _run_parallel_phases(
        run_id,
        store,
        similarity_phase,
        citation_phase,
    )
    if phase2.consistency is None:
        raise RuntimeError("O ramo de citações não produziu consistência.")
    findings = (
        *cross_phase_findings(
            phase1.findings,
            document,
            resolutions,
            phase2.existence,
            phase2.retractions,
            phase2.consistency,
            phase2.alignments,
        ),
        *phase2.findings,
    )
    nonexistent_references = sum(item.status == "not_found" for item in phase2.existence)
    alignment_contradictions = sum(item.label == "CONTRADICTS" for item in phase2.alignments)
    article_text = {"abstract": document.abstract} | {
        section.id: section.text for section in document.sections
    }
    decision = decide_risk(
        findings,
        article_text=article_text,
        nonexistent_references=nonexistent_references,
        alignment_contradictions=alignment_contradictions,
    )
    coverage = _coverage(phase1, phase2, resolutions, document)
    narrative_runner = factory.integrity_narrator(output_schema=IntegrityNarrative)
    narrative_result = narrative_runner.run(_narrative_prompt(decision, findings, coverage))
    narrative_content = narrative_result.content
    if not narrative_result.valid or not isinstance(narrative_content, IntegrityNarrative):
        raise RuntimeError("O narrador de integridade devolveu saída inválida.")

    report: ReportLike
    if report_writer is None:
        report = IntegrityReport.create_with_findings(
            run_id=run.pk,
            risk_level=decision.level.value,
            rules_version=decision.rules_version,
            coverage=coverage,
            narrative=narrative_content.narrative,
            findings=findings,
        )
    else:
        report = report_writer(
            run_id=run.pk,
            risk_level=decision.level.value,
            rules_version=decision.rules_version,
            coverage=coverage,
            narrative=narrative_content.narrative,
            findings=findings,
        )
    _index_submission(run_id, document, run.extraction.sha256)
    return IntegrityResult(
        report_id=str(report.pk),
        risk_level=decision.level.value,
        rules_version=decision.rules_version,
        finding_count=len(findings),
        coverage=coverage,
        reasons=decision.reasons,
    )


def _skipped_result(
    run: Run,
    *,
    report_writer: ReportWriter | None,
    reason: str,
) -> IntegrityResult:
    coverage: dict[str, object] = {
        "checked": False,
        "skipped": True,
        "skip_reason": reason,
        "content_sections": 0,
    }
    narrative = "Verificação de integridade ignorada: não há conteúdo extraído para analisar."
    report: ReportLike
    if report_writer is None:
        report = IntegrityReport.create_with_findings(
            run_id=run.pk,
            risk_level="low",
            rules_version=RULES_VERSION,
            coverage=coverage,
            narrative=narrative,
            findings=(),
        )
    else:
        report = report_writer(
            run_id=run.pk,
            risk_level="low",
            rules_version=RULES_VERSION,
            coverage=coverage,
            narrative=narrative,
            findings=(),
        )
    return IntegrityResult(
        report_id=str(report.pk),
        risk_level="low",
        rules_version=RULES_VERSION,
        finding_count=0,
        coverage=coverage,
        reasons=(reason,),
    )


def _default_checkpoint_store() -> PhaseCheckpointStore:
    from projects.correction.integrity.models import IntegrityPhaseCheckpoint

    return IntegrityPhaseCheckpoint


def _load_or_resolve(
    run_id: str,
    references: tuple[DocumentReference, ...],
    resolver: CandidateResolver,
    store: PhaseCheckpointStore,
) -> tuple[ReferenceResolution, ...]:
    saved = store.get_checkpoint(run_id, "resolution")
    if saved is not None:
        entries = saved.get("resolutions")
        if not isinstance(entries, list):
            raise RuntimeError("O checkpoint da resolução está inválido.")
        return tuple(ReferenceResolution.model_validate(item) for item in entries)
    resolutions = resolver(references)
    if {item.reference_id for item in resolutions} != {item.id for item in references}:
        raise RuntimeError("A resolução não retornou exatamente as referências do manuscrito.")
    store.save_checkpoint(
        run_id,
        "resolution",
        {"resolutions": [item.model_dump(mode="json") for item in resolutions]},
    )
    return resolutions


def _run_similarity_phase(
    document: ExtractedDocument,
    *,
    factory: AgentFactory,
    candidate_collector: CandidateCollectorLike | None,
    semantic_finder: SemanticFinder | None,
) -> IntegrityPhaseOutput:
    collector = candidate_collector or CandidateCollector(
        paid_search_budget=settings.integrity_paid_search_budget
    )
    collection = collector.collect(document)
    lexical = lexical_pairs(document, collection.candidates)
    if semantic_finder is None:

        def find_configured_semantic_overlaps(
            extracted: ExtractedDocument,
        ) -> tuple[SemanticOverlap, ...]:
            return find_semantic_overlaps(
                extracted,
                config=SemanticConfig(
                    nearest_chunks=5,
                    similarity_threshold=settings.integrity_semantic_similarity_threshold,
                ),
            )

        semantic_finder = find_configured_semantic_overlaps
    semantic = semantic_finder(document)
    semantic_candidates, semantic_pairs = _semantic_candidates(semantic)
    candidates = (*collection.candidates, *semantic_candidates)
    pairs = (*lexical, *semantic_pairs)
    batch = adjudicate_pairs(
        document,
        candidates,
        pairs,
        factory=factory,
        top_n=settings.integrity_adjudication_top_n,
        max_workers=settings.integrity_adjudication_workers,
    )
    findings = tuple(
        finding
        for finding in _build_findings(batch, (), document)
        if finding.finding_type.startswith("similarity_")
    )
    return IntegrityPhaseOutput(
        findings=findings,
        details={
            "candidate_sources": [asdict(item) for item in collection.coverage],
            "paid_searches": {
                "used": collection.paid_searches_used,
                "budget": collection.paid_search_budget,
                "provider": "OpenAlex",
            },
            "semantic": {"checked": True, "overlaps": len(semantic)},
            "adjudication": {
                "eligible": sum(item.disposition == "review" for item in batch.assessments),
                "adjudicated": len(batch.adjudicated),
                "excluded": batch.excluded_from_review,
            },
        },
    )


def _run_citation_phase(
    document: ExtractedDocument,
    resolutions: tuple[ReferenceResolution, ...],
    *,
    factory: AgentFactory,
) -> IntegrityPhaseOutput:
    existence = check_reference_existence(
        document.references,
        resolutions,
        factory=factory,
    )
    retractions = find_retracted_references(resolutions)
    consistency = check_citation_consistency(document, resolutions)
    alignments = check_citation_alignment(
        document,
        resolutions,
        factory=factory,
        max_samples=settings.integrity_alignment_sample_size,
        full_text_fetcher=fetch_open_access_full_text,
    )
    hidden_findings = tuple(
        FindingRecord(
            finding_type=(
                "hidden_ai_instruction" if "instruction" in hidden.reasons else "hidden_text"
            ),
            severity="high" if "instruction" in hidden.reasons else "medium",
            target_excerpt=hidden.text,
            rationale=(
                f"Texto oculto na página {hidden.page}; razões: {', '.join(hidden.reasons)}."
            ),
        )
        for hidden in document.hidden_text_findings
    )
    return IntegrityPhaseOutput(
        findings=hidden_findings,
        details={
            "references": {
                "total": len(document.references),
                "resolved": sum(item.status == "ok" for item in existence),
                "not_found": sum(item.status == "not_found" for item in existence),
                "metadata_mismatch": sum(item.status == "metadata_mismatch" for item in existence),
            },
            "retractions": len(retractions),
            "consistency": consistency.model_dump(mode="json"),
            "alignment": {
                "sampled": len(alignments),
                "full_text_used": sum(item.full_text_used for item in alignments),
                "contradictions": sum(item.label == "CONTRADICTS" for item in alignments),
                "insufficient": sum(item.label == "INSUFFICIENT" for item in alignments),
            },
            "hidden_text": {"checked": True, "findings": len(hidden_findings)},
        },
        existence=existence,
        retractions=retractions,
        consistency=consistency,
        alignments=alignments,
    )


@dataclass(frozen=True)
class _PhaseExecutor:
    run_id: str
    phase: str
    store: PhaseCheckpointStore
    operation: Callable[[], IntegrityPhaseOutput]

    def __call__(self, step_input: StepInput) -> StepOutput:
        del step_input
        close_old_connections()
        try:
            saved = self.store.get_checkpoint(self.run_id, self.phase)
            if saved is not None:
                return StepOutput(content=IntegrityPhaseOutput.model_validate(saved))
            result = self.operation()
            self.store.save_checkpoint(
                self.run_id,
                self.phase,
                result.model_dump(mode="json"),
            )
            return StepOutput(content=result)
        except Exception as exc:
            return StepOutput(
                content=None,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            connections.close_all()


def _run_parallel_phases(
    run_id: str,
    store: PhaseCheckpointStore,
    similarity: Callable[[], IntegrityPhaseOutput],
    citations: Callable[[], IntegrityPhaseOutput],
) -> tuple[IntegrityPhaseOutput, IntegrityPhaseOutput]:
    def step(name: str, phase: str, operation: Callable[[], IntegrityPhaseOutput]) -> Step:
        return Step(
            name=name,
            executor=_PhaseExecutor(run_id, phase, store, operation),
            max_retries=0,
            human_review=HumanReview(on_error=OnError.fail),
        )

    branches: Any = [
        step("similarity", "similarity", similarity),
        step("citations", "citations", citations),
    ]
    parallel = Parallel(*branches, name="integrity_phases")
    result = Workflow(
        name="integrity",
        telemetry=False,
        db=None,
        steps=[parallel],
    ).run(input={"run_id": run_id}, run_id=run_id)
    outputs = _flatten_step_outputs(result.step_results or [])
    container = next(
        (output for output in outputs if output.step_name == "integrity_phases"),
        None,
    )
    if container is None or container.steps is None:
        raise RuntimeError("O Parallel do E3 não retornou os ramos esperados.")
    by_name = {output.step_name: output for output in container.steps}
    for name in ("similarity", "citations"):
        output = by_name.get(name)
        if output is None:
            raise RuntimeError(f"O ramo {name} não retornou resultado.")
        if not output.success:
            _raise_phase_error(output.error or f"Falha no ramo {name}.")
    similarity_output = by_name["similarity"].content
    citation_output = by_name["citations"].content
    if not isinstance(similarity_output, IntegrityPhaseOutput) or not isinstance(
        citation_output, IntegrityPhaseOutput
    ):
        raise RuntimeError("Um ramo do E3 retornou saída fora do contrato.")
    return similarity_output, citation_output


def _flatten_step_outputs(
    outputs: Sequence[StepOutput | list[StepOutput]],
) -> list[StepOutput]:
    flattened: list[StepOutput] = []
    for output in outputs:
        flattened.extend(_flatten_step_outputs(output) if isinstance(output, list) else [output])
    return flattened


def _raise_phase_error(error: str) -> None:
    error_type, _, message = error.partition(":")
    short_type = error_type.rsplit(".", 1)[-1]
    if short_type in {
        "TransientStageError",
        "ScholarlyTransientError",
        "LLMUnavailable",
        "InvalidEvaluationOutput",
    }:
        from projects.correction.pipeline.errors import TransientStageError

        raise TransientStageError(message.strip())
    raise RuntimeError(error)


def _semantic_candidates(
    overlaps: Sequence[SemanticOverlap],
) -> tuple[tuple[Candidate, ...], tuple[SimilarityPair, ...]]:
    candidates: dict[tuple[str, str], Candidate] = {}
    pairs: list[SimilarityPair] = []
    for overlap in overlaps:
        candidate = Candidate(
            source="internal_semantic",
            source_id=overlap.source_identifier,
            title=overlap.source_title,
            text=overlap.source_text,
            metadata={"source_document_id": overlap.source_document_id},
        )
        candidates[(candidate.source, candidate.source_id)] = candidate
        pairs.append(
            SimilarityPair(
                section_id=overlap.target_section_id,
                target_start=overlap.target_start,
                target_end=overlap.target_end,
                source_start=overlap.source_start,
                source_end=overlap.source_end,
                target_excerpt=overlap.target_text,
                source_excerpt=overlap.source_text,
                candidate_source=candidate.source,
                candidate_id=candidate.source_id,
                candidate_title=candidate.title,
                similarity=overlap.similarity,
                method="semantic",
            )
        )
    return tuple(candidates.values()), tuple(pairs)


def _build_findings(
    batch: AdjudicationBatch,
    resolutions: Sequence[ReferenceResolution],
    document: ExtractedDocument,
) -> tuple[FindingRecord, ...]:
    records: list[FindingRecord] = []
    judged = {_pair_key(item.pair): item for item in batch.adjudicated}
    for assessment in batch.assessments:
        pair = assessment.pair
        result = judged.get(_pair_key(pair))
        if result is None and assessment.disposition == "review":
            verdict = (
                "verbatim_copy" if pair.method == "lexical" else "paraphrase_without_attribution"
            )
            confidence = 0.0
            rationale = "Par analisado deterministicamente; não estava no orçamento top-N do LLM."
            severity: FindingSeverity = "high" if pair.method == "lexical" else "medium"
        elif result is not None:
            verdict = result.verdict.verdict
            confidence = result.verdict.confidence
            rationale = result.verdict.justification
            severity = _verdict_severity(verdict)
        else:
            verdict = assessment.disposition
            confidence = 1.0
            rationale = assessment.rationale
            severity = "low"
        records.append(
            FindingRecord(
                finding_type=f"similarity_{pair.method}",
                severity=severity,
                verdict=verdict,
                section_id=pair.section_id,
                target_start=pair.target_start,
                target_end=pair.target_end,
                source_start=pair.source_start,
                source_end=pair.source_end,
                target_excerpt=pair.target_excerpt,
                source_excerpt=pair.source_excerpt,
                source_title=pair.candidate_title,
                source_id=pair.candidate_id,
                source_doi=pair.candidate_doi,
                confidence=confidence,
                rationale=rationale,
            )
        )
    for resolution in resolutions:
        if resolution.status == "ok":
            continue
        records.append(
            FindingRecord(
                finding_type=resolution.status,
                severity="medium",
                verdict=resolution.status,
                source_id=resolution.reference_id,
                source_title=resolution.title or "",
                source_doi=resolution.doi,
                rationale="Referência não validada na cascata de provedores.",
            )
        )
    for hidden in document.hidden_text_findings:
        is_instruction = "instruction" in hidden.reasons
        records.append(
            FindingRecord(
                finding_type="hidden_ai_instruction" if is_instruction else "hidden_text",
                severity="high" if is_instruction else "medium",
                target_excerpt=hidden.text,
                rationale=(
                    f"Texto oculto na página {hidden.page}; razões: {', '.join(hidden.reasons)}."
                ),
            )
        )
    return tuple(records)


def _verdict_severity(verdict: str) -> FindingSeverity:
    if verdict == "verbatim_copy":
        return "high"
    if verdict == "paraphrase_without_attribution":
        return "medium"
    return "low"


def _pair_key(pair: SimilarityPair) -> str:
    return pair.model_dump_json()


def _coverage(
    phase1: IntegrityPhaseOutput,
    phase2: IntegrityPhaseOutput,
    resolutions: Sequence[ReferenceResolution],
    document: ExtractedDocument,
) -> dict[str, object]:
    coverage = dict(phase1.details) | dict(phase2.details)
    coverage["references"] = dict(phase2.details.get("references", {})) | {
        "providers": sorted({item.provider for item in resolutions if item.provider})
    }
    coverage["full_text"] = {
        "sampled_claims": len(phase2.alignments),
        "used": sum(item.full_text_used for item in phase2.alignments),
        "allowed_hosts_configured": bool(settings.integrity_full_text_hosts),
        "reason": (
            "Downloads limitados a hosts HTTPS explicitamente permitidos."
            if settings.integrity_full_text_hosts
            else "Nenhum host de texto completo foi explicitamente permitido."
        ),
    }
    coverage["hidden_text"] = {
        "checked": True,
        "findings": len(document.hidden_text_findings),
    }
    coverage["checkpoints"] = {
        "resolution": True,
        "similarity": True,
        "citations": True,
    }
    return coverage


def _narrative_prompt(
    decision: RiskDecision, findings: Sequence[FindingRecord], coverage: dict[str, object]
) -> str:
    compact = [
        {
            "type": item.finding_type,
            "severity": item.severity,
            "verdict": item.verdict,
            "excerpt": item.target_excerpt[:500],
            "source": item.source_title,
        }
        for item in findings
    ]
    return (
        f"Nível decidido pelas regras: {decision.level.value}.\n"
        f"Motivos da regra: {', '.join(decision.reasons) or 'nenhum'}.\n"
        f"Cobertura e limites: {coverage!r}.\n"
        f"Achados: {compact!r}.\n"
        "Redija um resumo factual em português. Não altere o nível nem crie achados."
    )


def _index_submission(run_id: str, document: ExtractedDocument, sha256: str) -> None:
    texts: list[str] = []
    chunk_specs: list[tuple[str, str, str, int, str]] = []
    passages = [("abstract", "Abstract", "abstract", document.abstract)]
    passages.extend(
        (section.id, section.title, section.key or "", section.text)
        for section in document.sections
    )
    for section_id, title, section_key, text in passages:
        words = text.split()
        for _chunk_index, offset in enumerate(range(0, len(words), MAX_CHUNK_WORDS)):
            chunk_text = " ".join(words[offset : offset + MAX_CHUNK_WORDS])
            if not chunk_text:
                continue
            texts.append(chunk_text)
            chunk_specs.append((section_id, title, section_key, len(chunk_specs), chunk_text))
    if not texts:
        return
    embeddings = embed_documents(texts)
    embedded_inputs: list[SourceChunkInput] = []
    for spec, vector in zip(chunk_specs, embeddings, strict=True):
        section_id, title, section_key, chunk_index, text = spec
        embedded_inputs.append(
            SourceChunkInput(
                section_id=section_id,
                section_title=title,
                section_key=section_key,
                chunk_index=chunk_index,
                text=text,
                embedding=vector,
            )
        )
    from projects.correction.integrity.models import SourceDocument

    SourceDocument.import_with_chunks(
        source="metis_submissions",
        source_identifier=sha256,
        title=document.title,
        doi=None,
        authors=list(document.authors),
        metadata={"run_id": run_id, "language": document.language},
        chunks=embedded_inputs,
    )
