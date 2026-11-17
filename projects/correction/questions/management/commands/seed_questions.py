"""Prepara a Question genérica e três áreas para revisão no admin."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from projects.correction.metis.config import settings
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.seeds import (
    INITIAL_QUESTIONS,
    prepare_initial_questions,
    seed_initial_questions,
)


class Command(BaseCommand):
    help = "Carrega Questions iniciais como rascunhos; revisão e ativação ficam no admin."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--file", type=Path, default=INITIAL_QUESTIONS)
        parser.add_argument("--taxonomy-version")

    def handle(self, *args: Any, **options: Any) -> None:
        version = (
            options["taxonomy_version"]
            or settings.profiling_taxonomy_version
            or TaxonomyNode.latest_version()
        )
        if not version:
            raise CommandError("Carregue a taxonomia com load_taxonomy antes das Questions.")
        try:
            catalog, items = prepare_initial_questions(version, path=options["file"])
            self.stdout.write(f"catalog_version: {catalog.version}; taxonomy_version: {version}")
            for draft, node in items:
                self.stdout.write(f"{node.code if node else 'generic'}: {draft.name}")
            if not options["execute"]:
                self.stdout.write("Dry-run: nenhuma escrita. Use --execute para criar rascunhos.")
                return
            results = seed_initial_questions(version, path=options["file"])
        except (OSError, ValueError) as exc:
            raise CommandError("Catálogo inicial inválido; nenhuma escrita foi feita.") from exc
        for question, created in results:
            state = "criada" if created else "preservada"
            self.stdout.write(f"Question {state}: {question.pk} ({question.name})")
        self.stdout.write("Revise, valide e ative as Questions em /admin/questions/question/.")
