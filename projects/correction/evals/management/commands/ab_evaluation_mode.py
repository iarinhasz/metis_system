"""Executa e relata a comparação pareada dos modos de avaliação."""

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.evals.ab_evaluation_mode import (
    DEFAULT_REPLICATES,
    batch_runs,
    build_report,
    create_ab_runs,
    read_manifest,
    validate_sources,
)
from projects.correction.evals.reports import output_path, write_artifact


class Command(BaseCommand):
    help = "Prepara, executa ou relata o benchmark A/B do modo de avaliação."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("manifest", type=Path, help="Manifesto JSON da amostra pareada.")
        action = parser.add_mutually_exclusive_group()
        action.add_argument("--execute", action="store_true", help="Cria Runs e inicia chamadas.")
        action.add_argument("--report", action="store_true", help="Relata um lote concluído.")
        parser.add_argument("--batch-id", type=UUID, help="UUID do lote ou idempotência.")
        parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
        parser.add_argument("--output", type=Path, help="Destino novo para o relatório JSON.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            manifest, digest = read_manifest(options["manifest"])
            sources = validate_sources(manifest)
            replicates = options["replicates"]
            if not 2 <= replicates <= 10:
                raise ValueError("O número de réplicas deve estar entre 2 e 10.")

            if options["report"]:
                batch_id = options["batch_id"]
                if batch_id is None:
                    raise ValueError("Informe --batch-id para gerar o relatório.")
                runs = batch_runs(batch_id)
                report = build_report(
                    manifest, digest, batch_id=batch_id, replicates=replicates, runs=runs
                )
                path = output_path("ab_evaluation_mode", output=options["output"])
                write_artifact(report, path)
                self.stdout.write(f"Relatório: {path}")
                self.stdout.write(report.model_dump_json(indent=2))
                return

            if options["execute"]:
                batch_id = options["batch_id"] or uuid4()
                runs, created = create_ab_runs(
                    manifest, digest, batch_id=batch_id, replicates=replicates
                )
                state = "criados e enfileirados" if created else "já existentes"
                self.stdout.write(f"Lote {batch_id}: {len(runs)} Runs {state}.")
                return

            self.stdout.write(
                f"Dry-run: {manifest.name} v{manifest.version}; {len(manifest.cases)} casos; "
                f"{2 * len(manifest.cases) * replicates} Runs planejados "
                f"({replicates} réplicas em cada modo)."
            )
            self.stdout.write(
                f"Snapshots válidos: {len(sources)}; nenhuma chamada ou escrita realizada."
            )
            if options["batch_id"]:
                self.stdout.write(f"Lote informado: {options['batch_id']}")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
