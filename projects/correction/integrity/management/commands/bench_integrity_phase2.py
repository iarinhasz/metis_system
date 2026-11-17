"""Executa benchmarks de referências inventadas e alinhamento de citações."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import JsonValue

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import LLMUsage, MemoryUsageSink
from projects.correction.evals.reports import output_path, write_artifact
from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.alignment import AlignmentJudgment, AlignmentLabel
from projects.correction.integrity.benchmarks_phase2 import (
    AlignmentBenchmarkCase,
    evaluate_alignment_cases,
    evaluate_reference_cases,
    plant_invented_references,
)
from projects.correction.integrity.evals import adapt_phase2_report
from projects.correction.integrity.resolution import resolve_references


class Command(BaseCommand):
    help = "Mede a detecção de referências inventadas ou o alinhamento de citações."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dataset",
            required=True,
            choices=("planted_references", "sciciteval", "citation_integrity"),
        )
        parser.add_argument("--input", type=Path, required=True)
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--plant-count", type=int, default=10)
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--output", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        dataset = options["dataset"]
        source = options["input"]
        limit = options["limit"]
        plant_count = options["plant_count"]
        if not isinstance(source, Path) or not source.is_file():
            raise CommandError("--input deve apontar para um arquivo JSONL existente.")
        if not isinstance(limit, int) or limit < 1:
            raise CommandError("--limit deve ser positivo.")
        if not isinstance(plant_count, int) or plant_count < 0:
            raise CommandError("--plant-count não pode ser negativo.")
        rows = _read_jsonl(source, limit)

        if dataset == "planted_references":
            references = tuple(DocumentReference.model_validate(row) for row in rows)
            reference_cases = plant_invented_references(references, count=plant_count)
            if not reference_cases:
                raise CommandError("O benchmark precisa de referências de entrada.")

            def detect(reference: DocumentReference) -> bool:
                result = resolve_references((reference,))[0]
                return result.status == "ok"

            report = evaluate_reference_cases(reference_cases, detect)
        else:
            alignment_cases = tuple(AlignmentBenchmarkCase.model_validate(row) for row in rows)
            usage_sink = MemoryUsageSink()
            factory = AgentFactory("phase2-benchmark", "integrity_benchmark", usage_sink=usage_sink)
            runner = factory.citation_alignment_judge(output_schema=AlignmentJudgment)

            def judge(claim: str, source_text: str) -> AlignmentLabel:
                result = runner.run(
                    "Classifique o alinhamento entre afirmação e fonte usando apenas "
                    "os rótulos permitidos.\n"
                    f"Afirmação: {claim}\nFonte: {source_text}"
                )
                if not result.valid or not isinstance(result.content, AlignmentJudgment):
                    raise CommandError("O juiz retornou saída inválida durante o benchmark.")
                return result.content.label

            report = evaluate_alignment_cases(dataset, alignment_cases, judge)
        if not options["execute"]:
            self.stdout.write(
                json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
            )
            if options["output"]:
                self.stdout.write("Dry-run: use --execute para gravar o relatório metis.evals.")
            return
        usage: Sequence[LLMUsage] = ()
        model_specs: dict[Role, ModelSpec] = {}
        prompt_versions: dict[str, tuple[str, ...]] = {}
        parameters: dict[str, JsonValue]
        if dataset == "planted_references":
            case_ids = [case.reference.id for case in reference_cases]
            parameters = {
                "limit": limit,
                "plant_count": plant_count,
                "provider_order": ["crossref", "openalex", "semantic_scholar"],
            }
        else:
            case_ids = [f"{dataset}:{index}" for index in range(len(alignment_cases))]
            usage = usage_sink.calls
            model_specs = {Role.ADJUDICATOR: factory.models.specs[Role.ADJUDICATOR]}
            prompt_versions = {
                name: (version,) for name, version in factory.prompt_versions.items()
            }
            parameters = {
                "limit": limit,
                "label_set": [
                    "SUPPORTS",
                    "PARTIAL",
                    "CONTRADICTS",
                    "UNRELATED",
                    "INSUFFICIENT",
                ],
            }
        input_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        try:
            normalized = adapt_phase2_report(
                report,
                dataset_version="operator-jsonl-v1",
                dataset_sha256=input_hash,
                case_ids=case_ids,
                parameters=parameters,
                source_files=(
                    Path(__file__),
                    Path(__file__).parents[2] / "benchmarks_phase2.py",
                    Path(__file__).parents[2] / "evals.py",
                ),
                model_specs=model_specs,
                prompt_versions=prompt_versions,
                calls=usage,
            )
            path = output_path(report.dataset, output=options["output"])
            write_artifact(normalized, path)
        except (OSError, ValueError) as exc:
            raise CommandError("Não foi possível gravar um relatório metis.evals novo.") from exc
        self.stdout.write(normalized.model_dump_json(indent=2))
        self.stdout.write(f"Relatório: {path}")


def _read_jsonl(path: Path, limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CommandError(f"JSONL inválido na linha {line_number}.") from exc
                if not isinstance(value, dict):
                    raise CommandError(f"A linha {line_number} precisa ser um objeto JSON.")
                rows.append(value)
                if len(rows) == limit:
                    break
    except OSError as exc:
        raise CommandError(f"Falha ao ler {path}: {exc}") from exc
    return rows
