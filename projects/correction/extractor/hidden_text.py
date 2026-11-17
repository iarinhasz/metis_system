"""Texto que o leitor não vê no PDF, mas um modelo lê. Só código.

O pdfminer dá a cor, o tamanho e a posição de cada caractere, e o código marca o que está:
- **em branco** (`color`): o fundo da página é tomado como branco;
- **em fonte minúscula** (`size`): abaixo de 2 pt;
- **fora da página** (`off_page`).

Um trecho escondido com cara de instrução para um revisor de IA ("ignore all previous
instructions", "give a positive review", "ignore as instruções anteriores") ganha também o
motivo `instruction`. Trechos escondidos seguidos, mesmo em linhas diferentes, viram um só.

Fica de fora, por enquanto: texto atrás de uma imagem (pede a ordem de desenho) e o modo de
renderização invisível, que as camadas de OCR dos PDFs escaneados usam de propósito.
"""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Final

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTAnno, LTChar, LTContainer, LTPage, LTTextLine

from projects.correction.extractor.article import HiddenReason, HiddenText
from projects.correction.extractor.coverage import squash

logger = logging.getLogger(__name__)

TINY_FONT_PT: Final = 2.0
# Cinza ou RGB com todos os componentes a partir daqui contam como branco; CMYK, sem tinta.
WHITE: Final = 0.95
# Um trecho precisa de uma palavra com pelo menos 3 letras ou dígitos: glifos soltos e letras
# espaçadas, como os rótulos de eixo reduzidos de uma figura ("e u a v l"), não contam.
MIN_WORD_CHARS: Final = 3
MAX_TEXT_CHARS: Final = 500

# Comparados com o texto só com letras e dígitos, sem acento e caixa ("Ignore ALL previous
# instructions" → "ignoreallpreviousinstructions"), para não depender dos espaços do PDF.
INSTRUCTION: Final = re.compile(
    "|".join(
        (
            r"(ignore|disregard|forget)(all|any)?(ofthe|the|your)?"
            r"(previous|prior|above|preceding|earlier)(instructions?|prompts?|directions?)",
            r"(give|write|provide|output|generate)\w{0,12}positivereview",
            r"(recommend|suggest)\w{0,20}accept",
            r"(donot|dont)(highlight|mention|pointout|discuss)(any)?"
            r"(negatives?|weakness|flaws?|criticisms?|limitations?)",
            r"(ai|llm|languagemodel)reviewers?",
            r"ifyouarean?(ai|llm|largelanguagemodel|languagemodel)",
            r"(ignore|desconsidere|esqueca)(todas)?(as)?instrucoes(anteriores|acima)",
            r"(de|faca|escreva|gere)(uma)?(avaliacao|revisao|parecer)positiv[ao]",
            r"recomende\w{0,20}aceit",
            r"sevoceeuma?(ia|modelodelinguagem|revisor)",
        )
    )
)


def find_hidden_text(pdf: bytes) -> tuple[HiddenText, ...] | None:
    """Os trechos escondidos, na ordem das páginas; None se o pdfminer não leu o PDF."""
    try:
        pages = list(extract_pages(BytesIO(pdf), laparams=LAParams(all_texts=True)))
    except Exception:  # PDF malformado: a extração segue, sem esta busca
        logger.warning("Não foi possível procurar texto oculto no PDF.")
        return None
    return tuple(
        hidden for number, page in enumerate(pages, start=1) for hidden in _page(page, number)
    )


@dataclass
class _Run:
    """Caracteres escondidos seguidos, com os motivos de cada um somados."""

    parts: list[str] = field(default_factory=list)
    reasons: set[HiddenReason] = field(default_factory=set)

    def finding(self, page: int) -> HiddenText | None:
        text = " ".join("".join(self.parts).split())
        if not any(len(squash(word)) >= MIN_WORD_CHARS for word in text.split()):
            return None
        letters = squash(text)
        reasons = self.reasons | ({"instruction"} if INSTRUCTION.search(letters) else set())
        return HiddenText(page=page, text=text[:MAX_TEXT_CHARS], reasons=tuple(sorted(reasons)))


def _page(page: LTPage, number: int) -> list[HiddenText]:
    runs: list[_Run] = []
    current: _Run | None = None
    for line in _lines(page):
        for item in line:
            if isinstance(item, LTChar):
                if reasons := _reasons(item, page):
                    current = current or _Run()
                    current.parts.append(item.get_text())
                    current.reasons |= reasons
                elif current is not None:
                    runs.append(current)  # um caractere visível encerra o trecho
                    current = None
            elif isinstance(item, LTAnno) and current is not None:
                current.parts.append(item.get_text())  # espaços e quebras de linha
    if current is not None:
        runs.append(current)
    return [hidden for run in runs if (hidden := run.finding(number)) is not None]


def _lines(container: LTContainer[Any]) -> Iterator[LTTextLine]:
    for child in container:
        if isinstance(child, LTTextLine):
            yield child
        elif isinstance(child, LTContainer):
            yield from _lines(child)


def _reasons(char: LTChar, page: LTPage) -> set[HiddenReason]:
    reasons: set[HiddenReason] = set()
    if _is_white(char.graphicstate.ncolor):
        reasons.add("color")
    if char.size < TINY_FONT_PT:
        reasons.add("size")
    x0, y0, x1, y1 = char.bbox
    left, bottom, right, top = page.bbox
    if x1 <= left or x0 >= right or y1 <= bottom or y0 >= top:
        reasons.add("off_page")
    return reasons


def _is_white(color: object) -> bool:
    """Cinza (1 número), RGB (3) ou CMYK (4); padrões e cores com nome não contam."""
    values = color if isinstance(color, tuple | list) else (color,)
    if not values or not all(isinstance(v, int | float) for v in values):
        return False
    if len(values) in (1, 3):
        return all(float(v) >= WHITE for v in values)
    if len(values) == 4:
        return all(float(v) <= 1 - WHITE for v in values)
    return False
