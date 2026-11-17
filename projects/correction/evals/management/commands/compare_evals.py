"""Comparação local de relatórios existentes; gravação somente com --execute."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.evals.comparison import compare_reports
from projects.correction.evals.reports import output_path, read_report, write_artifact


class Command(BaseCommand):
    help = "Compara uma referência e um candidato, conferindo a compatibilidade da medição."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("baseline", type=Path)
        parser.add_argument("candidate", type=Path)
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--output", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            comparison = compare_reports(
                read_report(options["baseline"]), read_report(options["candidate"])
            )
        except (OSError, ValueError) as exc:
            raise CommandError("Não foi possível ler relatórios válidos para comparar.") from exc
        self.stdout.write(comparison.model_dump_json(indent=2))
        if options["execute"]:
            try:
                path = output_path("comparison", output=options["output"])
                write_artifact(comparison, path)
            except (OSError, ValueError) as exc:
                raise CommandError(
                    "Não foi possível criar um arquivo novo para a comparação."
                ) from exc
            self.stdout.write(f"Comparação: {path}")
        elif options["output"]:
            self.stdout.write("Dry-run: use --execute para gravar a comparação.")
        if not comparison.comparable:
            raise CommandError("Relatórios incompatíveis: " + "; ".join(comparison.reasons) + ".")
