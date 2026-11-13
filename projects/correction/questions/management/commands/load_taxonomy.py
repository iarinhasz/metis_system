"""Carga da taxonomia OpenAlex: dry-run por padrão, escrita atômica com --execute."""

import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import TypeAdapter, ValidationError

from projects.correction.metis.config import settings
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomyLevel, TaxonomySnapshot
from projects.correction.scholarly.openalex import (
    OpenAlexClient,
    OpenAlexTaxonomy,
    OpenAlexTopic,
    TopicPage,
)


class Command(BaseCommand):
    help = "Confere a taxonomia OpenAlex; só grava com --execute."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--execute", action="store_true", help="Grava a árvore no banco.")
        parser.add_argument(
            "--file", type=Path, help="JSON local: lista de topics ou resposta completa da API."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            catalog = (
                read_catalog(options["file"])
                if options["file"] is not None
                else OpenAlexClient(api_key=settings.openalex_api_key).taxonomy()
            )
            snapshot = TaxonomySnapshot.from_catalog(catalog)
        except HTTPError as exc:
            raise CommandError(
                f"OpenAlex respondeu HTTP {exc.code}; nenhuma escrita foi feita."
            ) from None
        except URLError:
            raise CommandError(
                "Não foi possível consultar o OpenAlex; nenhuma escrita foi feita."
            ) from None
        except OSError, ValueError, ValidationError:
            raise CommandError(
                "Taxonomia inválida ou incompleta; nenhuma escrita foi feita."
            ) from None
        counts = Counter(entry.level for entry in snapshot.entries)
        self.stdout.write(f"taxonomy_version: {snapshot.version}")
        self.stdout.write("; ".join(f"{level}: {counts[level]}" for level in TaxonomyLevel))
        if not options["execute"]:
            self.stdout.write("Dry-run: nenhuma escrita. Use --execute para gravar.")
            return
        TaxonomyNode.import_snapshot(snapshot)
        self.stdout.write(self.style.SUCCESS(f"Taxonomia disponível: {len(snapshot.entries)} nós."))


def read_topics(path: Path) -> tuple[OpenAlexTopic, ...]:
    return read_catalog(path).topics


def read_catalog(path: Path) -> OpenAlexTaxonomy:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "meta" in data:
            page = TopicPage.model_validate(data)
            if page.meta.count != len(page.results):
                raise ValueError("O arquivo contém só uma página da taxonomia.")
            return OpenAlexTaxonomy(topics=tuple(page.results))
        return OpenAlexTaxonomy.model_validate(data)
    return OpenAlexTaxonomy(topics=tuple(TypeAdapter(list[OpenAlexTopic]).validate_python(data)))
