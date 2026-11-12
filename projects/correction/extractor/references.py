"""A lista de referências separada em campos pelo modelo e conferida contra o texto da seção.

A chamada vai só com o texto da seção de referências, já extraído e conferido; o modelo devolve
cada entrada com o texto cru e os campos. O código confere: entrada que não está no texto é
descartada, e o conjunto precisa cobrir o texto. Reprovada, a chamada é refeita com uma dica,
como nas seções (ver section_answer.py).
"""

from dataclasses import dataclass
from typing import Final

from projects.correction.extractor.article import Reference
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.coverage import fidelity, text_coverage, uncovered_paragraphs
from projects.correction.extractor.errors import InvalidModelAnswer
from projects.correction.extractor.prompts import load_prompt, render_prompt
from projects.correction.extractor.schemas import ParsedReference, ParsedReferences
from projects.correction.extractor.session import DocumentSession

QUOTE_CHARS: Final = 200
QUOTES_IN_HINT: Final = 2


@dataclass(frozen=True)
class _Parsed:
    kept: tuple[ParsedReference, ...]
    foreign: tuple[ParsedReference, ...]
    coverage: float | None

    @property
    def score(self) -> float:
        total = len(self.kept) + len(self.foreign)
        kept_share = len(self.kept) / total if total else 0.0
        return min(kept_share, 1.0 if self.coverage is None else self.coverage)

    def passes(self, config: DocumentConfig) -> bool:
        enough = self.coverage is None or self.coverage >= config.min_coverage
        return bool(self.kept) and not self.foreign and enough


def parse_references(
    session: DocumentSession, config: DocumentConfig, text: str
) -> tuple[Reference, ...]:
    prompt = render_prompt(config.references_prompt, references=text)
    best: _Parsed | None = None
    hint = ""
    invalid: InvalidModelAnswer | None = None
    for _ in range(config.check_retries + 1):
        try:
            answer = session.ask(prompt + hint, ParsedReferences, with_document=False)
        except InvalidModelAnswer as exc:
            invalid = exc  # conta como tentativa falha, como nas seções
            continue
        parsed = _check(answer, text, config)
        if best is None or parsed.score > best.score:
            best = parsed
        if parsed.passes(config):
            break
        hint = _retry_hint(parsed, text)
    if best is None:
        assert invalid is not None
        raise invalid
    if not best.kept:
        raise InvalidModelAnswer("O modelo não devolveu nenhuma referência que esteja na lista.")
    return tuple(
        Reference(id=f"ref_{index}", **_cleaned(entry).model_dump())
        for index, entry in enumerate(best.kept, start=1)
    )


def _check(answer: ParsedReferences, text: str, config: DocumentConfig) -> _Parsed:
    entries = [entry for entry in answer.references if entry.raw.strip()]
    kept = tuple(e for e in entries if (fidelity(text, e.raw) or 0.0) >= config.min_fidelity)
    foreign = tuple(e for e in entries if e not in kept)
    coverage = text_coverage(text, "\n".join(entry.raw for entry in kept))
    return _Parsed(kept, foreign, coverage)


def _retry_hint(parsed: _Parsed, text: str) -> str:
    hints = []
    if parsed.foreign:
        listed = "\n".join(f"- {_quote(e.raw)}" for e in parsed.foreign[:QUOTES_IN_HINT])
        hints.append(render_prompt(load_prompt("retry_references_foreign"), foreign=listed))
    produced = "\n".join(entry.raw for entry in parsed.kept)
    if missing := uncovered_paragraphs(text, produced, limit=QUOTES_IN_HINT):
        listed = "\n".join(f"- {_quote(paragraph)}" for paragraph in missing)
        hints.append(render_prompt(load_prompt("retry_references_missing"), missing=listed))
    return "".join(f"\n\n{hint}" for hint in hints)


def _cleaned(entry: ParsedReference) -> ParsedReference:
    """Espaços normalizados e campos vazios como nulos."""

    def tidy(value: str | None) -> str | None:
        flat = " ".join(value.split()) if value else ""
        return flat or None

    return ParsedReference(
        raw=" ".join(entry.raw.split()),
        marker=tidy(entry.marker),
        authors=tuple(name for name in (tidy(a) for a in entry.authors) if name),
        title=tidy(entry.title),
        year=tidy(entry.year),
        venue=tidy(entry.venue),
        doi=tidy(entry.doi),
        arxiv_id=tidy(entry.arxiv_id),
    )


def _quote(text: str) -> str:
    flat = " ".join(text.split())
    cut = "…" if len(flat) > QUOTE_CHARS else ""
    return f"«{flat[:QUOTE_CHARS]}{cut}»"
