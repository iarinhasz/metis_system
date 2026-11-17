"""Mede relatórios E4 contra notas PeerRead e decisões de aprovação curadas."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.evals.ab_evaluation_mode import read_manifest, validate_sources
from projects.correction.evals.reports import output_path, write_artifact
from projects.correction.evals.review_benchmark import build_review_report


class Command(BaseCommand):
    help = "Gera métricas offline dos FinalReports E4 contra rótulos humanos curados."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "manifest", type=Path, help="Manifesto JSON com Runs e rótulos humanos."
        )
        parser.add_argument("--execute", action="store_true", help="Grava um relatório novo.")
        parser.add_argument("--output", type=Path, help="Destino novo em diretório existente.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            manifest, digest = read_manifest(options["manifest"])
            sources = validate_sources(manifest)
            report = build_review_report(manifest, digest, sources)
            if not options["execute"]:
                self.stdout.write(
                    f"Dry-run: {len(manifest.cases)} casos; "
                    f"{report.details['labelled_score_pairs']} pares de notas; "
                    f"{report.details['human_decision_labelled_cases']} decisões rotuladas; "
                    "nenhuma chamada a provedor ou gravação."
                )
                return

            path = output_path("bench_reviews", output=options["output"])
            write_artifact(report, path)
            self.stdout.write(f"Relatório: {path}")
            self.stdout.write(report.model_dump_json(indent=2))
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
