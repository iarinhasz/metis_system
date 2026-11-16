"""Executa benchmarks de referências inventadas e alinhamento de citações."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.agents.factory import AgentFactory
from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.alignment import AlignmentJudgment, AlignmentLabel
from projects.correction.integrity.benchmarks_phase2 import (
    AlignmentBenchmarkCase,
    evaluate_alignment_cases,
    evaluate_reference_cases,
    plant_invented_references,
)
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

            def detect(reference: DocumentReference) -> bool:
                result = resolve_references((reference,))[0]
                return result.status == "ok"

            report = evaluate_reference_cases(reference_cases, detect)
        else:
            alignment_cases = tuple(AlignmentBenchmarkCase.model_validate(row) for row in rows)
            factory = AgentFactory("phase2-benchmark", "integrity")
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
        self.stdout.write(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))


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
