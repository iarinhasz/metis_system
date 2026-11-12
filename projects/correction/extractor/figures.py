"""A lista de figuras e tabelas, com a legenda conferida contra o texto do PDF.

Uma chamada com o PDF devolve rótulo, tipo, página e legenda de cada figura e tabela. O código
confere contra o texto do PDF lido pelo pypdf:
- **legenda:** precisa estar no texto (fidelidade); a que não está é descartada;
- **cobertura:** as linhas que começam como legenda ("Figure 3:", "Tabela 2.") mostram quais
  rótulos existem; o que faltar na resposta volta como dica numa nova tentativa.
Sem texto do PDF (escaneado), a lista fica como o modelo devolveu, sem conferência.
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

from projects.correction.extractor.article import Figure
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.coverage import fidelity
from projects.correction.extractor.errors import InvalidModelAnswer
from projects.correction.extractor.prompts import load_prompt, render_prompt
from projects.correction.extractor.schemas import FigureScan, ScannedFigure
from projects.correction.extractor.session import DocumentSession

type Kind = Literal["figure", "table"]

# "3", "12", "A1", "A.1", "2.4": letra de apêndice opcional, com ou sem ponto.
NUMBER: Final = r"(?:[A-Z]\.?)?\d+(?:\.\d+)*"
CAPTION_LINE: Final = re.compile(
    rf"(?m)^\s*(?P<word>Figures?|Figs?\.|Figuras?|Tables?|Tabelas?|Quadros?)\s+(?P<number>{NUMBER})"
    r"\s*[:.]"
)
LABEL_NUMBER: Final = re.compile(NUMBER)
QUOTE_CHARS: Final = 160
QUOTES_IN_HINT: Final = 3


def label_number(label: str) -> str | None:
    """O número do rótulo: "Figure 3" → "3", "Table A.1" → "A.1", "Fig. 3a" → "3"."""
    match = LABEL_NUMBER.search(label)
    return match.group() if match else None


def kind_of(word: str) -> Kind:
    return "table" if word.casefold().startswith(("tab", "quadro")) else "figure"


@dataclass(frozen=True)
class _Listed:
    kept: tuple[ScannedFigure, ...]
    foreign: tuple[ScannedFigure, ...]
    missing: tuple[tuple[Kind, str], ...]

    @property
    def score(self) -> float:
        total = len(self.kept) + len(self.foreign) + len(self.missing)
        return len(self.kept) / total if total else 1.0

    @property
    def passes(self) -> bool:
        return not self.foreign and not self.missing


def scan_figures(
    session: DocumentSession, config: DocumentConfig, reference: str | None
) -> tuple[Figure, ...]:
    expected = _caption_labels(reference)
    best: _Listed | None = None
    hint = ""
    for _ in range(config.check_retries + 1):
        try:
            answer = session.ask(config.figures_prompt + hint, FigureScan)
        except InvalidModelAnswer:
            continue  # tentativa falha; a lista de figuras não derruba a extração
        listed = _check(answer, reference, expected, config)
        if best is None or listed.score > best.score:
            best = listed
        if listed.passes:
            break
        hint = _retry_hint(listed)
    if best is None:
        return ()
    return tuple(
        Figure(
            id=f"fig_{index}",
            kind=entry.kind,
            label=" ".join(entry.label.split()),
            number=label_number(entry.label),
            page=entry.page,
            caption=" ".join(entry.caption.split()),
            fidelity=fidelity(reference, entry.caption),
        )
        # Pela página (ordenação estável): o modelo às vezes lista na ordem em que são citadas.
        for index, entry in enumerate(sorted(best.kept, key=lambda e: e.page), start=1)
    )


def _caption_labels(reference: str | None) -> set[tuple[Kind, str]]:
    if reference is None:
        return set()
    return {
        (kind_of(match.group("word")), match.group("number"))
        for match in CAPTION_LINE.finditer(reference)
    }


def _check(
    answer: FigureScan,
    reference: str | None,
    expected: set[tuple[Kind, str]],
    config: DocumentConfig,
) -> _Listed:
    entries = [entry for entry in answer.figures if entry.caption.strip()]
    if reference is None:
        return _Listed(tuple(entries), (), ())
    kept = tuple(
        entry
        for entry in entries
        if (fidelity(reference, entry.caption) or 0.0) >= config.min_fidelity
    )
    foreign = tuple(entry for entry in entries if entry not in kept)
    found = {(entry.kind, label_number(entry.label)) for entry in kept}
    missing = tuple(sorted(label for label in expected if label not in found))
    return _Listed(kept, foreign, missing)


def _retry_hint(listed: _Listed) -> str:
    hints = []
    if listed.missing:
        names = "\n".join(
            f"- {'Tabela' if kind == 'table' else 'Figura'} {number}"
            for kind, number in listed.missing
        )
        hints.append(render_prompt(load_prompt("retry_figures_missing"), missing=names))
    if listed.foreign:
        quoted = "\n".join(
            f"- «{' '.join(entry.caption.split())[:QUOTE_CHARS]}»"
            for entry in listed.foreign[:QUOTES_IN_HINT]
        )
        hints.append(render_prompt(load_prompt("retry_figures_foreign"), foreign=quoted))
    return "".join(f"\n\n{hint}" for hint in hints)
