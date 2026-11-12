"""As chamadas no texto das seções, ligadas às entradas da lista de referências. Só código.

Dois estilos:
- **numérico:** `[3]`, `[1, 4]`, `[2–5]`; a ligação é pela marca da entrada (`[3]`, `3.`) ou,
  quando a lista não é numerada, pela posição nela;
- **autor-ano:** "Silva (2020)", "Silva et al. (2020a)", "Silva e Souza (2020)" e, entre
  parênteses, "(Silva, 2020; Souza et al., 2019)"; a ligação é pelo sobrenome do primeiro autor
  e pelo ano. Quando duas entradas têm o mesmo primeiro autor e o mesmo ano, desempata pelo
  segundo autor ("Silva e Souza"), pelo "et al." (três ou mais autores) ou, sem nenhum dos dois,
  pela entrada de autor único.

O estilo do artigo é decidido uma vez: numérico se a lista é numerada ou se as chamadas
numéricas válidas são maioria; senão, autor-ano. Assim um intervalo como "[0, 1]" num artigo
autor-ano não vira citação.

Uma chamada sem entrada correspondente, ou com mais de uma, fica com `reference_id` nulo: a 5.3
usa isso (citação sem entrada na lista). No autor-ano, "Palavra (2020)" sem entrada é descartada,
porque pode não ser citação; já "(Silva, 2020)" e "Silva et al. (2020)" ficam, mesmo sem ligação.
"""

import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from projects.correction.extractor.article import Citation, ExtractedSection, Reference

UPPER: Final = "A-ZÀ-ÖØ-Þ"
SURNAME: Final = rf"[{UPPER}][\w'’\-]+"
YEAR: Final = r"(?:1[6-9]\d{2}|20\d{2})[a-z]?"
NUMERIC: Final = re.compile(
    r"\[(\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?(?:\s*[,;]\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)*\s*)\]"
)
NARRATIVE: Final = re.compile(
    rf"(?P<names>{SURNAME}(?:\s+et\s+al\.?|\s+(?:and|e|&)\s+{SURNAME})?)"
    rf"\s*\((?P<years>{YEAR}(?:\s*[,;]\s*{YEAR})*)\)"
)
PARENTHESIS: Final = re.compile(r"\(([^()]*)\)")
YEAR_IN_TEXT: Final = re.compile(rf"\b{YEAR}\b")
NAME: Final = re.compile(SURNAME)
NUMBER: Final = re.compile(r"\d+")
RANGE: Final = re.compile(r"(\d+)\s*[-–—]\s*(\d+)")
LEADING_WORDS: Final = re.compile(
    r"^(?:e\.g\.|i\.e\.|cf\.|see|see also|ver|veja|por exemplo|como em|as in)[,:]?\s+", re.I
)
STRONG: Final = re.compile(r",|\bet\s+al\b|\band\b|&|\be\b")
SECOND_AUTHOR: Final = re.compile(r"\s(?:and|e|&)\s")
ET_AL: Final = re.compile(r"\bet\s+al\b")
MAX_RANGE: Final = 50
# Fim de frase, menos depois de abreviação comum ("et al.", "e.g.", "Fig.").
SENTENCE_BREAK: Final = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(\[])|\n+")
ABBREVIATIONS: Final = ("al.", "e.g.", "i.e.", "fig.", "eq.", "vs.", "cf.", "no.", "p.")


class Style(StrEnum):
    NUMERIC = "numeric"
    AUTHOR_YEAR = "author_year"


@dataclass(frozen=True)
class _Found:
    """Uma chamada achada no texto, antes da ligação."""

    start: int
    end: int
    marker: str
    numbers: tuple[int, ...] = ()
    names_years: tuple[tuple[str, str], ...] = ()
    # Forma que é citação mesmo sem entrada na lista: "(Silva, 2020)", "Silva et al. (2020)".
    strong: bool = True
    # Para desempatar entradas do mesmo primeiro autor e ano.
    second_surname: str | None = None
    et_al: bool = False


def find_citations(
    sections: Iterable[ExtractedSection], references: Sequence[Reference]
) -> tuple[Citation, ...]:
    if not references:
        return ()
    texts = [s for s in sections if s.key != "references" and s.text]
    by_number = _references_by_number(references)
    style = _style(texts, references, by_number)

    citations: list[Citation] = []
    for section in texts:
        finder = _numeric if style is Style.NUMERIC else _author_year
        for found in finder(section.text):
            ids = (
                _link_numbers(found, by_number)
                if style is Style.NUMERIC
                else _link_names(found, references)
            )
            if ids is None:
                continue
            sentence = _sentence_around(section.text, found.start, found.end)
            citations.extend(
                Citation(
                    reference_id=reference_id,
                    marker=found.marker,
                    sentence=sentence,
                    section_id=section.id,
                    start=found.start,
                    end=found.end,
                )
                for reference_id in ids
            )
    return tuple(citations)


# --- estilo -----------------------------------------------------------------------------------


def _style(
    sections: Sequence[ExtractedSection],
    references: Sequence[Reference],
    by_number: dict[int, str],
) -> Style:
    numbered = sum(_marker_number(r.marker) is not None for r in references)
    if numbered >= len(references) / 2:
        return Style.NUMERIC
    numeric_hits = sum(
        1
        for section in sections
        for found in _numeric(section.text)
        if any(number in by_number for number in found.numbers)
    )
    author_hits = sum(
        1
        for section in sections
        for found in _author_year(section.text)
        if any(_link_names(found, references) or ())
    )
    return Style.NUMERIC if numeric_hits > author_hits else Style.AUTHOR_YEAR


# --- estilo numérico --------------------------------------------------------------------------


def _numeric(text: str) -> Iterator[_Found]:
    for match in NUMERIC.finditer(text):
        yield _Found(
            start=match.start(),
            end=match.end(),
            marker=match.group(),
            numbers=tuple(_expand(match.group(1))),
        )


def _expand(content: str) -> list[int]:
    numbers: list[int] = []
    for part in re.split(r"[,;]", content):
        if bounds := RANGE.search(part):
            first, last = int(bounds.group(1)), int(bounds.group(2))
            numbers.extend(
                range(first, last + 1) if 0 <= last - first <= MAX_RANGE else (first, last)
            )
        elif number := NUMBER.search(part):
            numbers.append(int(number.group()))
    return numbers


def _references_by_number(references: Sequence[Reference]) -> dict[int, str]:
    """Número → id: pela marca da entrada se a lista é numerada; senão, pela posição."""
    numbered = {
        number: ref.id for ref in references if (number := _marker_number(ref.marker)) is not None
    }
    if len(numbered) >= len(references) / 2:
        return numbered
    return {position: ref.id for position, ref in enumerate(references, start=1)}


def _marker_number(marker: str | None) -> int | None:
    match = NUMBER.search(marker or "")
    return int(match.group()) if match else None


def _link_numbers(found: _Found, by_number: dict[int, str]) -> list[str | None] | None:
    """Ids na ordem dos números; None quando não é citação: nenhum número é de uma entrada, ou
    aparece o 0, que nenhuma lista usa (um intervalo como "[0, 1]")."""
    if 0 in found.numbers:
        return None
    ids = [by_number.get(number) for number in found.numbers]
    return ids if any(ids) else None


# --- estilo autor-ano -------------------------------------------------------------------------


def _author_year(text: str) -> Iterator[_Found]:
    for match in NARRATIVE.finditer(text):
        names = match.group("names")
        surname = NAME.match(names)
        if surname is None:
            continue
        years = YEAR_IN_TEXT.findall(match.group("years"))
        yield _Found(
            start=match.start(),
            end=match.end(),
            marker=match.group(),
            names_years=tuple((surname.group(), year) for year in years),
            strong=bool(STRONG.search(names)),
            second_surname=_coauthors(names)[0],
            et_al=_coauthors(names)[1],
        )
    for match in PARENTHESIS.finditer(text):
        content_start = match.start(1)
        offset = 0
        for item in match.group(1).split(";"):
            item_start = content_start + offset
            offset += len(item) + 1
            found = _parenthetical_item(item, item_start)
            if found is not None:
                yield found


def _parenthetical_item(item: str, item_start: int) -> _Found | None:
    stripped = item.strip()
    if not stripped:
        return None
    cleaned = LEADING_WORDS.sub("", stripped)
    lead = len(item) - len(item.lstrip()) + len(stripped) - len(cleaned)
    years = list(YEAR_IN_TEXT.finditer(cleaned))
    if not years:
        return None
    authors_part = cleaned[: years[0].start()]
    surname = NAME.search(authors_part)
    if surname is None:
        return None
    start = item_start + lead
    return _Found(
        start=start,
        end=start + len(cleaned),
        marker=cleaned,
        names_years=tuple((surname.group(), year.group()) for year in years),
        strong=bool(STRONG.search(authors_part)),
        second_surname=_coauthors(authors_part)[0],
        et_al=_coauthors(authors_part)[1],
    )


def _coauthors(names: str) -> tuple[str | None, bool]:
    """O segundo sobrenome de "Silva e Souza" e se a chamada tem "et al."."""
    surnames = NAME.findall(names)
    has_second = bool(SECOND_AUTHOR.search(names)) and len(surnames) > 1
    return (surnames[1] if has_second else None), bool(ET_AL.search(names))


def _link_names(found: _Found, references: Sequence[Reference]) -> list[str | None] | None:
    """Ids na ordem dos anos; None quando a chamada fraca não liga a nada (não é citação)."""
    ids = [
        _match_reference(surname, year, references, found.second_surname, found.et_al)
        for surname, year in found.names_years
    ]
    if not any(ids) and not found.strong:
        return None
    return ids


def _match_reference(
    surname: str,
    year: str,
    references: Sequence[Reference],
    second_surname: str | None = None,
    et_al: bool = False,
) -> str | None:
    key, base, suffix = fold_name(surname).split()[-1:], year[:4], year[4:]
    candidates = [
        ref
        for ref in references
        if ref.authors
        and ref.year
        and surname_key(ref.authors[0]) in key
        and ref.year[:4] == base
        and (not suffix or ref.year[4:] == suffix)
    ]
    if len(candidates) > 1:
        candidates = _break_tie(candidates, second_surname, et_al)
    return candidates[0].id if len(candidates) == 1 else None


def _break_tie(
    candidates: list[Reference], second_surname: str | None, et_al: bool
) -> list[Reference]:
    if second_surname:
        second = fold_name(second_surname).split()[-1:]
        return [r for r in candidates if len(r.authors) > 1 and surname_key(r.authors[1]) in second]
    if et_al:
        return [r for r in candidates if len(r.authors) >= 3]
    return [r for r in candidates if len(r.authors) == 1]


def surname_key(name: str) -> str:
    """O sobrenome do primeiro autor, sem acento e sem caixa: "Silva, A.", "A. Silva",
    "Ana Silva" e "Silva A" viram "silva"."""
    if "," in name:
        surname = name.split(",")[0]
    else:
        tokens = name.replace(".", ". ").split()
        words = [token for token in tokens if not _is_initial(token)]
        if not words:
            surname = tokens[-1] if tokens else ""
        elif not _is_initial(tokens[0]) and all(_is_initial(t) for t in tokens[1:]):
            surname = tokens[0]
        else:
            surname = words[-1]
    folded = fold_name(surname).split()
    return folded[-1] if folded else ""


def _is_initial(token: str) -> bool:
    bare = token.strip(".,-")
    return token.endswith(".") or len(bare) <= 1 or (bare.isupper() and len(bare) <= 3)


def fold_name(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    kept = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", kept).split())


# --- frase da chamada -------------------------------------------------------------------------


def _sentence_around(text: str, start: int, end: int) -> str:
    sentence_start, sentence_end = 0, len(text)
    for boundary in SENTENCE_BREAK.finditer(text):
        before = text[max(0, boundary.start() - 5) : boundary.start()].casefold()
        if "\n" not in boundary.group() and before.endswith(ABBREVIATIONS):
            continue
        if boundary.end() <= start:
            sentence_start = boundary.end()
        elif boundary.start() >= end:
            sentence_end = boundary.start()
            break
    return " ".join(text[sentence_start:sentence_end].split())
