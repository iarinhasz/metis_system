"""Execução do E3: coleta, detecção, regras determinísticas e relatório persistido."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.agents.factory import AgentFactory
from projects.correction.attempts.models import Run
from projects.correction.extractor.contract import DocumentReference, ExtractedDocument
from projects.correction.integrity.adjudication import (
    AdjudicationBatch,
    adjudicate_pairs,
    lexical_pairs,
)
from projects.correction.integrity.candidates import (
    Candidate,
    CandidateCollection,
    CandidateCollector,
)
from projects.correction.integrity.citation_filter import SimilarityPair
from projects.correction.integrity.embeddings import MAX_CHUNK_WORDS, embed_documents
from projects.correction.integrity.models import IntegrityReport
from projects.correction.integrity.resolution import ReferenceResolution, resolve_references
from projects.correction.integrity.rules import (
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
) -> IntegrityResult:
    run = Run.get_by_id(run_id)
    if run.extraction is None:
        raise ValueError(f"O run {run_id} não tem uma extração para verificar.")
    document = run.extraction.document

    resolutions = reference_resolver(document.references)
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
    findings = _build_findings(batch, resolutions, document)
    nonexistent_references = sum(item.status == "not_found" for item in resolutions)
    article_text = {"abstract": document.abstract} | {
        section.id: section.text for section in document.sections
    }
    decision = decide_risk(
        findings,
        article_text=article_text,
        nonexistent_references=nonexistent_references,
    )
    coverage = _coverage(collection, resolutions, semantic, batch, document)
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
    collection: CandidateCollection,
    resolutions: Sequence[ReferenceResolution],
    semantic: Sequence[SemanticOverlap],
    batch: AdjudicationBatch,
    document: ExtractedDocument,
) -> dict[str, object]:
    return {
        "candidate_sources": [asdict(item) for item in collection.coverage],
        "paid_searches": {
            "used": collection.paid_searches_used,
            "budget": collection.paid_search_budget,
            "provider": "OpenAlex",
        },
        "references": {
            "total": len(document.references),
            "resolved": sum(item.status == "ok" for item in resolutions),
            "not_found": sum(item.status == "not_found" for item in resolutions),
            "metadata_mismatch": sum(item.status == "metadata_mismatch" for item in resolutions),
            "providers": sorted({item.provider for item in resolutions if item.provider}),
        },
        "semantic": {"checked": True, "overlaps": len(semantic)},
        "adjudication": {
            "eligible": sum(item.disposition == "review" for item in batch.assessments),
            "adjudicated": len(batch.adjudicated),
            "excluded": batch.excluded_from_review,
        },
        "hidden_text": {
            "checked": True,
            "findings": len(document.hidden_text_findings),
        },
        "full_text": {
            "available": False,
            "reason": (
                "Fontes OA são identificadas, mas a extração/indexação remota "
                "de PDFs não foi executada."
            ),
        },
    }


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
