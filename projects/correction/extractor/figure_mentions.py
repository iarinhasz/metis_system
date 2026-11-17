"""As chamadas às figuras e tabelas no texto das seções, ligadas à lista. Só código.

Reconhece "Fig. 3", "Figure 3a", "Figura 2", "Figures 2 and 3", "Figs. 2–4", "Table 1",
"Tabela A.1" e liga pelo tipo e pelo número do rótulo. Uma chamada a um rótulo que não está na
lista fica com `figure_id` nulo.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Final

from projects.correction.extractor.article import ExtractedSection, Figure, FigureMention
from projects.correction.extractor.citations import sentence_around
from projects.correction.extractor.figures import NUMBER, Kind, kind_of

ITEM: Final = rf"{NUMBER}[a-z]?"
MENTION: Final = re.compile(
    r"\b(?P<word>Figures?|Figs?\.|Figuras?|Tables?|Tabs?\.|Tabelas?|Quadros?)\s*"
    rf"(?P<items>{ITEM}(?:\s*(?:,|and|e|&|[-–—])\s*{ITEM})*)"
)
ITEM_NUMBER: Final = re.compile(NUMBER)
RANGE: Final = re.compile(rf"({NUMBER})[a-z]?\s*[-–—]\s*({NUMBER})")
MAX_RANGE: Final = 20


def find_figure_mentions(
    sections: Iterable[ExtractedSection], figures: Sequence[Figure]
) -> tuple[FigureMention, ...]:
    by_label: dict[tuple[Kind, str], str] = {
        (figure.kind, figure.number): figure.id for figure in figures if figure.number
    }
    mentions: list[FigureMention] = []
    for section in sections:
        if section.key == "references" or not section.text:
            continue
        for match in MENTION.finditer(section.text):
            kind = kind_of(match.group("word"))
            sentence = sentence_around(section.text, match.start(), match.end())
            mentions.extend(
                FigureMention(
                    figure_id=by_label.get((kind, number)),
                    marker=match.group(),
                    sentence=sentence,
                    section_id=section.id,
                    start=match.start(),
                    end=match.end(),
                )
                for number in _numbers(match.group("items"))
            )
    return tuple(mentions)


def _numbers(items: str) -> list[str]:
    """Os números da chamada, com os intervalos inteiros expandidos ("2–4" → 2, 3, 4)."""
    numbers: list[str] = []
    for part in re.split(r"\s*(?:,|\band\b|\be\b|&)\s*", items):
        bounds = RANGE.fullmatch(part.strip())
        if bounds and bounds.group(1).isdigit() and bounds.group(2).isdigit():
            first, last = int(bounds.group(1)), int(bounds.group(2))
            if 0 <= last - first <= MAX_RANGE:
                numbers.extend(str(n) for n in range(first, last + 1))
                continue
        numbers.extend(ITEM_NUMBER.findall(part))
    return list(dict.fromkeys(numbers))
