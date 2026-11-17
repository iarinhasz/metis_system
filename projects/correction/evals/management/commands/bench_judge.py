"""Executa o benchmark de erros plantados no juiz E4, somente com --execute."""

from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunPurpose, RunStatus
from projects.correction.evals.judge_benchmark import run_judge_benchmark
from projects.correction.evals.reports import output_path, write_artifact
from projects.correction.evaluation.context import EvaluationContextBuilder
from projects.correction.evaluation.models import FinalReport


class Command(BaseCommand):
    help = "Mede o juiz E4 em um controle válido e em três erros sintéticos plantados."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("source_run_id", type=UUID, help="Run concluído com snapshots E1/E2.")
        parser.add_argument("--execute", action="store_true", help="Chama os juízes configurados.")
        parser.add_argument("--output", type=Path, help="Destino novo para o relatório JSON.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            run = Run.objects.select_related(
                "attempt", "extraction", "question", "final_report"
            ).get(pk=options["source_run_id"], purpose=RunPurpose.EVALUATION)
            if run.status != RunStatus.DONE or FinalReport.for_run(run.pk) is None:
                raise ValueError("O Run de origem precisa estar concluído e ter FinalReport.")
            EvaluationContextBuilder(run).build()
            if not isinstance(run.config_snapshot.get("model_specs"), dict):
                raise ValueError("O Run de origem não tem snapshots de ModelSpec.")
            if not options["execute"]:
                self.stdout.write(
                    "Dry-run: 8 julgamentos sintéticos (4 casos × slots A/B); "
                    "nenhuma chamada ou gravação. Use --execute para chamar os modelos."
                )
                return

            report = run_judge_benchmark(run)
            path = output_path("bench_judge", output=options["output"])
            write_artifact(report, path)
            self.stdout.write(f"Relatório: {path}")
            self.stdout.write(report.model_dump_json(indent=2))
        except (Run.DoesNotExist, OSError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
