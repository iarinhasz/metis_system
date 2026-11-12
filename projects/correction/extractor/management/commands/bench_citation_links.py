"""Mede a ligação citação ↔ referência contra o PeerRead (etapa 1.10).

Roda o extractor inteiro (chamadas ao Gemini) em PDFs do PeerRead que têm o gabarito
(`parsed_pdfs`) e compara com ele (ver extractor/citation_bench.py). Em dry-run, só lista os
artigos escolhidos; com --execute, chama o modelo e grava o relatório em
dataset_project/processed/bench_citation_links/<data e hora>/, junto com cada artigo extraído,
para os desacordos serem olhados à mão.
"""

import json
from dataclasses import asdict
from itertools import zip_longest
from pathlib import Path
from typing import Any, Final

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from projects.correction.extractor.article import ExtractedArticle
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.citation_bench import GoldPaper, PaperScore, score_paper, totals
from projects.correction.extractor.citations import find_citations
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.service import extract_article
from projects.correction.extractor.session import INLINE_LIMIT_BYTES
from projects.correction.pipeline.errors import StageError

DEFAULT_VENUES: Final = ("iclr_2017", "acl_2017", "conll_2016")
DEFAULT_DATA: Final = "dataset_project/raw/PeerRead-master/data"
REPORTS: Final = "dataset_project/processed/bench_citation_links"
MIN_MENTIONS: Final = 5


class Command(BaseCommand):
    help = "Mede a ligação citação ↔ referência contra o PeerRead (dry-run sem --execute)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=10, help="Quantos artigos medir.")
        parser.add_argument("--venues", nargs="+", default=list(DEFAULT_VENUES))
        parser.add_argument("--data", default=None, help=f"Pasta do PeerRead ({DEFAULT_DATA}).")
        parser.add_argument(
            "--papers", nargs="+", default=None, help="Só estes artigos (ex.: 316)."
        )
        parser.add_argument("--execute", action="store_true", help="Chama o modelo e mede.")
        parser.add_argument(
            "--rescore",
            default=None,
            help="Pasta de uma medição anterior: recalcula com os artigos salvos, sem o modelo.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        root = Path(settings.BASE_DIR).parents[1]
        data = Path(options["data"]) if options["data"] else root / DEFAULT_DATA
        if not data.is_dir():
            raise CommandError(f"Pasta do PeerRead não encontrada: {data}")
        papers = choose_papers(data, options["venues"], options["limit"], options["papers"])
        if options["rescore"]:
            self._rescore(Path(options["rescore"]), papers)
            return
        for pdf, gold in papers:
            venue = pdf.parents[2].name
            self.stdout.write(f"{venue}/{gold.name}: {len(gold.mentions)} chamadas no gabarito")
        if not options["execute"]:
            self.stdout.write("Dry-run: nenhum modelo foi chamado. Use --execute para medir.")
            return

        run_dir = root / REPORTS / f"{timezone.now():%Y%m%d-%H%M%S}"
        run_dir.mkdir(parents=True, exist_ok=True)
        scores: list[PaperScore] = []
        for pdf, gold in papers:
            name = f"{pdf.parents[2].name}/{gold.name}"
            try:
                article = extract_article(pdf.read_bytes())
            except StageError as exc:
                self.stdout.write(f"{name}: falhou ({type(exc).__name__}: {exc})")
                continue
            (run_dir / f"{name.replace('/', '_')}.json").write_text(
                article.model_dump_json(indent=2), encoding="utf-8"
            )
            score = score_paper(article, gold)
            score.name = name
            scores.append(score)
            self.stdout.write(_line(score))

        self._report(run_dir, scores)

    def _rescore(self, run_dir: Path, papers: list[tuple[Path, GoldPaper]]) -> None:
        scores = []
        for pdf, gold in papers:
            name = f"{pdf.parents[2].name}/{gold.name}"
            saved = run_dir / f"{name.replace('/', '_')}.json"
            if not saved.is_file():
                continue
            article = ExtractedArticle.model_validate_json(saved.read_text())
            # As citações saem só de código: recalcula com a versão atual de citations.py.
            article = article.model_copy(
                update={"citations": find_citations(article.sections, article.references)}
            )
            score = score_paper(article, gold)
            score.name = name
            scores.append(score)
            self.stdout.write(_line(score))
        self._report(run_dir, scores)

    def _report(self, run_dir: Path, scores: list[PaperScore]) -> None:
        summary = totals(scores)
        report = run_dir / "report.json"
        report.write_text(
            json.dumps(
                {
                    "extractor_version": extraction_version(ARTICLE_CONFIG),
                    "totals": summary,
                    "papers": [asdict(score) for score in scores],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.stdout.write(json.dumps(summary, ensure_ascii=False))
        self.stdout.write(f"Relatório: {report}")


def choose_papers(
    data: Path, venues: list[str], limit: int, names: list[str] | None = None
) -> list[tuple[Path, GoldPaper]]:
    """Alterna entre as venues, na ordem dos nomes, só com artigos que têm PDF que vai inline
    ao modelo e pelo menos MIN_MENTIONS chamadas no gabarito; com `names`, só esses."""
    per_venue = [list(_papers_of(data / venue)) for venue in venues]
    chosen = [paper for group in zip_longest(*per_venue) for paper in group if paper is not None]
    if names:
        chosen = [paper for paper in chosen if paper[1].name in names]
    return chosen[:limit]


def _papers_of(venue: Path) -> list[tuple[Path, GoldPaper]]:
    papers = []
    for gold_path in sorted(venue.glob("*/parsed_pdfs/*.pdf.json")):
        pdf = gold_path.parents[1] / "pdfs" / gold_path.name.removesuffix(".json")
        if not pdf.is_file() or pdf.stat().st_size > INLINE_LIMIT_BYTES:
            continue
        gold = GoldPaper.from_json(gold_path)
        if len(gold.mentions) >= MIN_MENTIONS:
            papers.append((pdf, gold))
    return papers


def _line(score: PaperScore) -> str:
    def share(part: int, whole: int) -> str:
        return f"{part}/{whole}" + (f" ({part / whole:.0%})" if whole else "")

    return (
        f"{score.name}: recall {share(score.mentions_found, score.mentions_judgeable)} · "
        f"precisão {share(score.citations_correct, score.citations_judgeable)} · "
        f"inconsistentes no gabarito {score.mentions_inconsistent} · "
        f"sem julgamento {score.citations_unjudgeable} · "
        f"referências casadas {share(score.references_matched, score.references_gold)} · "
        f"citações sem ligação {score.citations_unlinked}"
    )
