"""Dry-run por padrão; --execute mede sem gravar objetos do pipeline."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.agents.errors import MissingProviderKey
from projects.correction.evals.profiling import evaluation_report, run_benchmark
from projects.correction.evals.profiling_data import DATASET_PATH, read_dataset
from projects.correction.evals.reports import output_path, write_artifact
from projects.correction.metis.config import settings
from projects.correction.questions.models import TaxonomyNode


class Command(BaseCommand):
    help = "Mede field e papéis; modo rules é local e modo llm usa os provedores configurados."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--file", type=Path, default=DATASET_PATH)
        parser.add_argument("--mode", choices=("rules", "llm"), default="rules")
        parser.add_argument("--limit", type=int, default=30)
        parser.add_argument("--max-attempts", type=int, default=1)
        parser.add_argument("--taxonomy-version")
        parser.add_argument("--output", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        if options["limit"] < 1 or options["max_attempts"] < 1:
            raise CommandError("--limit e --max-attempts precisam ser positivos.")
        try:
            dataset = read_dataset(options["file"])
        except (OSError, ValueError) as exc:
            raise CommandError("Amostra de profiling inválida.") from exc
        self.stdout.write(
            f"dataset: {dataset.version}; casos: {min(options['limit'], len(dataset.cases))}; "
            f"modo: {options['mode']}; rótulos: {dataset.annotation_status}"
        )
        if not options["execute"]:
            self.stdout.write("Dry-run: sem chamadas ou escrita. Use --execute para medir.")
            return
        try:
            destination = output_path("bench_profiling", output=options["output"])
        except (OSError, ValueError) as exc:
            raise CommandError(
                "Escolha um arquivo novo em um diretório existente para o relatório."
            ) from exc
        version = None
        if options["mode"] == "llm":
            version = (
                options["taxonomy_version"]
                or settings.profiling_taxonomy_version
                or TaxonomyNode.latest_version()
            )
            if not version:
                raise CommandError("Carregue a taxonomia antes do benchmark com LLM.")
            required = {case.labels.field for case in dataset.cases[: options["limit"]]}
            available = {node.code for node in TaxonomyNode.fields_for_profiling(version)}
            if not required <= available:
                raise CommandError("A taxonomia não contém todos os fields da amostra.")
        try:
            report = run_benchmark(
                dataset,
                mode=options["mode"],
                taxonomy_version=version,
                limit=options["limit"],
                max_attempts=options["max_attempts"],
                confidence_threshold=settings.profiling_confidence_threshold,
                progress=lambda case_id: self.stderr.write(f"Medindo {case_id}..."),
            )
        except MissingProviderKey as exc:
            raise CommandError(
                "Configure a chave do provedor do papel fast antes da medição."
            ) from exc
        try:
            artifact = evaluation_report(report)
            write_artifact(artifact, destination)
        except (OSError, ValueError) as exc:
            raise CommandError(
                "Não foi possível criar o relatório; confira o caminho e os metadados."
            ) from exc
        self.stdout.write(f"Relatório: {destination}; variante: {artifact.variant_id}")
        summary = report.overall
        field = (
            f"{summary.field_accuracy:.2%}" if summary.field_accuracy is not None else "não medido"
        )
        self.stdout.write(
            f"Field: {field}; papéis: {summary.roles_exact}/{summary.sections} "
            f"({summary.roles_accuracy:.2%}); F1: {summary.roles_micro_f1:.4f}; "
            f"falhas: {summary.failures}; chamadas: {report.calls}."
        )
        if summary.failures:
            raise CommandError("Benchmark com falhas; elas permanecem no denominador do relatório.")
