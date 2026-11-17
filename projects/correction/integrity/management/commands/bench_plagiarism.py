"""Benchmarka detectores com trechos PeerRead sintéticos; LLM é opt-in."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.specs import Role
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.evals.reports import output_path, write_artifact
from projects.correction.extractor.contract import ExtractedDocument
from projects.correction.integrity.benchmarks import (
    BenchmarkReport,
    build_peerread_cases,
    evaluate_cases,
)
from projects.correction.integrity.embeddings import embed_documents, embed_query
from projects.correction.integrity.evals import (
    adapt_plagiarism_report,
)
from projects.correction.integrity.lexical import find_lexical_overlaps
from projects.correction.metis.config import settings


class RewriteOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rewritten_text: str = Field(min_length=1, max_length=12000)


class Command(BaseCommand):
    help = "Mede precisão e recall do detector com trechos sintéticos do PeerRead."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source-dir",
            type=Path,
            default=Path("projects/correction/extractor/tests/fixtures/peerread"),
        )
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--output", type=Path)
        parser.add_argument(
            "--with-llm",
            action="store_true",
            help="Gera exemplos parafraseados/traduzidos; implica chamadas externas pagas.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        source_dir = options["source_dir"]
        limit = options["limit"]
        with_llm = options["with_llm"]
        if not isinstance(source_dir, Path) or not isinstance(limit, int) or limit < 1:
            raise CommandError("--source-dir deve ser um caminho e --limit deve ser positivo.")
        files = sorted(source_dir.glob("*.json"))[:limit]
        if not files:
            raise CommandError(f"Nenhuma fixture PeerRead encontrada em {source_dir}.")
        try:
            documents = [
                ExtractedDocument.model_validate_json(path.read_text(encoding="utf-8"))
                for path in files
            ]
        except (OSError, ValueError) as exc:
            raise CommandError(f"Falha ao carregar fixture PeerRead: {exc}") from exc

        usage_sink = MemoryUsageSink()
        factory = AgentFactory("benchmark", "integrity_benchmark", usage_sink=usage_sink)
        rewrite = self._rewriter(factory) if with_llm else None
        cases = build_peerread_cases(documents, rewrite=rewrite, max_documents=limit)
        if not cases:
            raise CommandError(
                "As fixtures não contêm passagens com o tamanho mínimo do benchmark."
            )
        vectors: dict[str, list[float]] = {}

        def detector(source: str, target: str) -> bool:
            if find_lexical_overlaps(source, target):
                return True
            if source not in vectors:
                vectors[source] = next(iter(embed_documents([source])))
            if target not in vectors:
                vectors[target] = embed_query(target)
            source_vector = vectors[source]
            target_vector = vectors[target]
            return (
                _cosine(source_vector, target_vector)
                >= settings.integrity_semantic_similarity_threshold
            )

        report: BenchmarkReport = evaluate_cases(
            cases,
            detector,
            calibration_values={
                "high_verbatim_sentences": settings.integrity_high_verbatim_sentences,
                "high_paraphrase_fraction": settings.integrity_high_paraphrase_fraction,
                "high_nonexistent_references": settings.integrity_high_nonexistent_references,
                "semantic_similarity_threshold": settings.integrity_semantic_similarity_threshold,
            },
        )
        if not options["execute"]:
            self.stdout.write(
                json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
            )
            if options["output"]:
                self.stdout.write("Dry-run: use --execute para gravar o relatório metis.evals.")
            return
        files = [path for path in files if path.is_file()]
        digest = _dataset_digest(files)
        specs = {Role.ADJUDICATOR: factory.models.specs[Role.ADJUDICATOR]} if with_llm else {}
        prompt_versions = (
            {name: (version,) for name, version in factory.prompt_versions.items()}
            if with_llm
            else {}
        )
        calibration_values: dict[str, JsonValue] = {
            key: value for key, value in report.calibration_values.items()
        }
        try:
            normalized = adapt_plagiarism_report(
                report,
                dataset_version="peerread-fixtures-v1",
                dataset_sha256=digest,
                case_ids=[case.case_id for case in cases],
                parameters={
                    "limit": limit,
                    "with_llm_rewrites": with_llm,
                    "embedding_model": "intfloat/multilingual-e5-large",
                    "embedding_similarity_threshold": (
                        settings.integrity_semantic_similarity_threshold
                    ),
                    "calibration_values": calibration_values,
                },
                source_files=(
                    Path(__file__),
                    Path(__file__).parents[2] / "benchmarks.py",
                    Path(__file__).parents[2] / "evals.py",
                    Path(__file__).parents[2] / "embeddings.py",
                    Path(__file__).parents[2] / "lexical.py",
                ),
                model_specs=specs,
                prompt_versions=prompt_versions,
                calls=usage_sink.calls,
            )
            path = output_path("bench_plagiarism", output=options["output"])
            write_artifact(normalized, path)
        except (OSError, ValueError) as exc:
            raise CommandError("Não foi possível gravar um relatório metis.evals novo.") from exc
        self.stdout.write(normalized.model_dump_json(indent=2))
        self.stdout.write(f"Relatório: {path}")

    @staticmethod
    def _rewriter(
        factory: AgentFactory,
    ) -> Callable[[str, Literal["paraphrase", "translated"]], str]:
        runner = factory.build(
            "plagiarism_benchmark_rewriter",
            Role.ADJUDICATOR,
            RewriteOutput,
        )

        def rewrite(text: str, kind: Literal["paraphrase", "translated"]) -> str:
            result = runner.run(f"Tipo de variante: {kind}\nTrecho:\n{text}")
            if not result.valid or result.content is None:
                raise CommandError("O gerador de variantes devolveu saída inválida.")
            return result.content.rewritten_text

        return rewrite


def _dataset_digest(files: list[Path]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Os embeddings do benchmark têm dimensões diferentes.")
    dot = 0.0
    left_squared_norm = 0.0
    right_squared_norm = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        dot += left_value * right_value
        left_squared_norm += left_value * left_value
        right_squared_norm += right_value * right_value
    left_norm = left_squared_norm**0.5
    right_norm = right_squared_norm**0.5
    if not left_norm or not right_norm:
        return 0.0
    similarity = float(dot / (left_norm * right_norm))
    if similarity < 0:
        return 0.0
    if similarity > 1:
        return 1.0
    return similarity
