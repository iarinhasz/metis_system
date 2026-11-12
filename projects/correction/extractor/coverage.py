"""Confere a seção devolvida pelo modelo contra o texto do próprio PDF, em duas medidas:

- **cobertura:** quanto da prosa do trecho do PDF veio na resposta (o modelo pulou texto?);
- **fidelidade:** quanto da resposta está no trecho do PDF daquela seção (o modelo trouxe texto
  de outra seção ou inventou?).

A referência é o texto do PDF lido aqui (`pdf_text`). Ele tem ruído que o modelo tira de
propósito (cabeçalho e rodapé de página, legendas, tabelas, notas), por isso as medidas não
chegam a 100% e os limites ficam na config.

Como funciona:
1. Tira da referência as linhas que se repetem em boa parte das páginas (cabeçalho e rodapé).
2. Acha na referência, em ordem, o título de cada seção do mapa; o trecho até o título seguinte é
   a versão local da seção. Título não achado deixa a seção sem verificação (`None`).
3. Compara trechos de 20 caracteres do texto só com letras e dígitos, sem acento e sem caixa:
   espaço, hifenização e palavra grudada ("reasonabout") não contam como diferença, e uma nota
   colada no meio de uma frase só derruba os trechos em volta dela.
4. Na cobertura, só conta a prosa do PDF: legenda, tabela e fórmula ficam de fora.
"""

import re
import unicodedata
from collections import Counter
from typing import Final

from projects.correction.extractor.section_map import SectionMap

# Uma linha que aparece em pelo menos esta fração das páginas é cabeçalho ou rodapé.
REPEATED_LINE_SHARE: Final = 0.5
PAGE_NUMBER: Final = re.compile(r"^\s*\d+\.?\s*$")
SENTENCE_END: Final = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(\[])")
CAPTION: Final = re.compile(r"^(figure|fig\.|table|tabela|figura|quadro|algorithm)\s*\d", re.I)
WORD: Final = re.compile(r"[^\W\d_]{2,}")
# Frase de prosa: palavras suficientes e quase só letras (tabela e fórmula têm muito número).
MIN_WORDS: Final = 8
MIN_LETTER_SHARE: Final = 0.75
GRAM_CHARS: Final = 20
# Frase do PDF com menos que isto dos seus trechos na resposta conta como faltando.
SENTENCE_FOUND_SHARE: Final = 0.5


def reference_text(pages: list[str]) -> str:
    """Texto do PDF sem cabeçalho, rodapé e números de página."""
    page_lines = [[line.strip() for line in page.splitlines() if line.strip()] for page in pages]
    counts = Counter(line for lines in page_lines for line in set(lines))
    repeated = (
        {line for line, count in counts.items() if count >= len(pages) * REPEATED_LINE_SHARE}
        if len(pages) > 1
        else set()
    )
    return "\n".join(
        line
        for lines in page_lines
        for line in lines
        if line not in repeated and not PAGE_NUMBER.match(line)
    )


def local_sections(reference: str, section_map: SectionMap) -> dict[str, str | None]:
    """A versão local de cada seção: o trecho da referência entre o título dela e o seguinte."""
    squashed, positions = _squash_with_positions(reference)
    found: dict[str, tuple[int, int]] = {}
    cursor = 0
    for section in section_map.values():
        title = squash(section.title)
        index = _find_title(reference, squashed, positions, title, cursor) if title else -1
        if index >= 0:
            found[section.id] = (positions[index], positions[index + len(title) - 1] + 1)
            cursor = index + len(title)

    starts = sorted(start for start, _ in found.values())
    slices: dict[str, str | None] = {}
    for section_id in section_map:
        if section_id not in found:
            slices[section_id] = None
            continue
        start, body_start = found[section_id]
        end = next((s for s in starts if s > start), len(reference))
        slices[section_id] = reference[body_start:end]
    return slices


def coverage(local: str | None, extracted: str) -> float | None:
    """Fração da prosa do trecho local que está na resposta; None quando não há o que verificar
    (título não achado ou trecho sem prosa)."""
    if local is None:
        return None
    expected = set().union(*(_grams(sentence) for sentence in prose_sentences(local)))
    if not expected:
        return None
    return len(expected & _grams(extracted)) / len(expected)


def fidelity(local: str | None, extracted: str) -> float | None:
    """Fração da resposta que está no trecho local da seção; None quando não há o que verificar
    (título não achado ou resposta vazia)."""
    if local is None:
        return None
    produced = _grams(extracted)
    if not produced:
        return None
    return len(produced & _grams(local)) / len(produced)


def text_coverage(expected: str, produced: str) -> float | None:
    """Fração do texto esperado que está no produzido, sem o filtro de prosa (para listas,
    como a de referências); None quando o esperado não tem o que comparar."""
    grams = _grams(expected)
    if not grams:
        return None
    return len(grams & _grams(produced)) / len(grams)


def uncovered_paragraphs(text: str, produced: str, limit: int) -> list[str]:
    """Os primeiros parágrafos de `text` que não estão em `produced`."""
    grams_produced = _grams(produced)
    missing = []
    for paragraph in (p.strip() for p in text.split("\n\n")):
        grams = _grams(paragraph)
        if grams and len(grams & grams_produced) < SENTENCE_FOUND_SHARE * len(grams):
            missing.append(paragraph)
            if len(missing) == limit:
                break
    return missing


def missing_sentences(local: str | None, extracted: str, limit: int) -> list[str]:
    """As primeiras frases de prosa do trecho local que não vieram na resposta."""
    if local is None:
        return []
    produced = _grams(extracted)
    missing = []
    for sentence in prose_sentences(local):
        grams = _grams(sentence)
        if grams and len(grams & produced) < SENTENCE_FOUND_SHARE * len(grams):
            missing.append(sentence)
            if len(missing) == limit:
                break
    return missing


def prose_sentences(text: str) -> list[str]:
    flat = " ".join(text.split())
    return [s for s in SENTENCE_END.split(flat) if _is_prose(s)]


def squash(text: str) -> str:
    """Só letras e dígitos, sem acento e sem caixa."""
    return "".join(char for original in text for char in _fold(original) if char.isalnum())


def _grams(text: str) -> set[str]:
    squashed = squash(text)
    return {squashed[i : i + GRAM_CHARS] for i in range(len(squashed) - GRAM_CHARS + 1)}


def _is_prose(sentence: str) -> bool:
    if CAPTION.match(sentence):
        return False
    visible = [char for char in sentence if not char.isspace()]
    letters = sum(char.isalpha() for char in visible)
    return len(WORD.findall(sentence)) >= MIN_WORDS and letters >= MIN_LETTER_SHARE * len(visible)


def _find_title(
    reference: str, squashed: str, positions: list[int], title: str, cursor: int
) -> int:
    """Posição do título, preferindo a ocorrência que começa uma linha: a primeira ocorrência
    pode ser o título citado no texto ("como mostra a Seção 3 Método")."""
    first = index = squashed.find(title, cursor)
    while index >= 0:
        start = positions[index]
        if not reference[reference.rfind("\n", 0, start) + 1 : start].strip():
            return index
        index = squashed.find(title, index + 1)
    return first


def _squash_with_positions(text: str) -> tuple[str, list[int]]:
    """O texto só com letras e dígitos e, para cada caractere dele, a posição no original."""
    kept = [
        (folded, index)
        for index, char in enumerate(text)
        for folded in _fold(char)
        if folded.isalnum()
    ]
    return "".join(char for char, _ in kept), [index for _, index in kept]


def _fold(char: str) -> str:
    """O caractere sem acento e sem caixa; pode virar mais de um (`ß` → `ss`)."""
    decomposed = unicodedata.normalize("NFKD", char).casefold()
    return "".join(c for c in decomposed if not unicodedata.combining(c))
