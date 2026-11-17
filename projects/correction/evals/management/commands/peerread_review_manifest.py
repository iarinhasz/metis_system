"""Anexa notas PeerRead agregadas a um manifesto de Runs já preparado."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.evals.ab_evaluation_mode import ABCase, ABManifest, read_manifest
from projects.correction.evals.peerread_reviews import read_peerread_scores
from projects.correction.evals.reports import output_path, write_artifact

DEFAULT_CANDIDATES = Path(__file__).parents[2] / "data" / "peerread_iclr2017_test_candidates.json"


class Command(BaseCommand):
    help = "Prepara rótulos PeerRead: decisão binária e mediana das notas por critério."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "manifest", type=Path, help="Manifesto com source_run_id já resolvidos."
        )
        parser.add_argument("reviews_dir", type=Path, help="Diretório com <peerread_id>.json.")
        parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
        parser.add_argument("--execute", action="store_true", help="Grava um manifesto novo.")
        parser.add_argument("--output", type=Path, help="Destino novo em diretório existente.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            manifest, _ = read_manifest(options["manifest"])
            catalog = json.loads(options["candidates"].read_text(encoding="utf-8"))
            by_id = {item["id"]: item for item in catalog["cases"]}
            if set(case.id for case in manifest.cases) - by_id.keys():
                raise ValueError("O manifesto contém casos fora do catálogo PeerRead informado.")

            cases = []
            labelled_scores = 0
            unlabelled_cases = 0
            for case in manifest.cases:
                candidate = by_id[case.id]
                if case.human_decision != candidate["human_decision"]:
                    raise ValueError(f"{case.id}: decisão humana diverge do catálogo fixado.")
                scores = read_peerread_scores(
                    options["reviews_dir"] / f"{candidate['peerread_id']}.json"
                )
                labelled_scores += len(scores)
                unlabelled_cases += not bool(scores)
                cases.append(
                    ABCase(
                        id=case.id,
                        source_run_id=case.source_run_id,
                        human_decision=case.human_decision,
                        human_scores=scores,
                    )
                )

            enriched = ABManifest(
                name=manifest.name,
                version=f"{manifest.version}-peerread-{catalog['upstream']['revision'][:7]}",
                cases=tuple(cases),
            )
            if not options["execute"]:
                if options["output"]:
                    raise ValueError("--output exige --execute.")
                self.stdout.write(
                    f"Dry-run: {len(cases)} casos; {labelled_scores} notas humanas agregadas; "
                    f"{unlabelled_cases} casos sem notas numéricas; nenhum arquivo gravado."
                )
                return

            path = output_path("peerread_review_manifest", output=options["output"])
            write_artifact(enriched, path)
            self.stdout.write(f"Manifesto: {path}")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
