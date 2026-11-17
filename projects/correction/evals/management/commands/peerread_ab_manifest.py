"""Gera manifesto A/B a partir dos Runs atuais da amostra PeerRead."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunPurpose, RunStatus
from projects.correction.evals.ab_evaluation_mode import ABCase, ABManifest, validate_sources
from projects.correction.evals.reports import output_path

DEFAULT_CANDIDATES = Path(__file__).parents[2] / "data" / "peerread_iclr2017_test_candidates.json"


class Command(BaseCommand):
    help = "Monta um manifesto A/B PeerRead com Runs concluídos e snapshots atuais."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
        parser.add_argument("--output", type=Path, help="Destino novo para o manifesto JSON.")
        parser.add_argument(
            "--execute", action="store_true", help="Grava o manifesto; sem isso apenas valida."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            data = json.loads(options["candidates"].read_text(encoding="utf-8"))
            cases = []
            for candidate in data["cases"]:
                matching_runs = list(
                    Run.objects.filter(
                        purpose=RunPurpose.EVALUATION,
                        status=RunStatus.DONE,
                        attempt__article__external_id=candidate["source_run_external_id"],
                        attempt__sha256=candidate["pdf_sha256"],
                    ).order_by("pk")
                )
                if len(matching_runs) != 1:
                    raise ValueError(
                        f"{candidate['id']}: esperado exatamente um Run concluído para o PDF; "
                        f"encontrados {len(matching_runs)}."
                    )
                cases.append(
                    ABCase(
                        id=candidate["id"],
                        source_run_id=matching_runs[0].pk,
                        human_decision=candidate["human_decision"],
                    )
                )

            manifest = ABManifest(name=data["name"], version=data["version"], cases=tuple(cases))
            validate_sources(manifest)
            if not options["execute"]:
                self.stdout.write(
                    f"Dry-run: manifesto válido com {len(manifest.cases)} artigos; "
                    "nenhum arquivo gravado."
                )
                return

            path = output_path("peerread_ab_manifest", output=options["output"])
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(manifest.model_dump_json(indent=2) + "\n")
            self.stdout.write(f"Manifesto: {path}")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
