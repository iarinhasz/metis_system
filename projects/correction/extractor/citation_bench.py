"""Compara a ligação citação ↔ referência do extractor com o gabarito do PeerRead.

O gabarito são os `parsed_pdfs` do PeerRead (science-parse): a lista de referências e as chamadas
no texto (`referenceMentions`), cada uma com o índice da referência, a frase e a posição da
chamada nela.

Como compara:
1. Casa as nossas referências com as do gabarito pelo título (sem acento, caixa e pontuação).
   O gabarito às vezes repete a mesma obra em duas entradas; uma referência nossa casa com
   todas as entradas de título praticamente igual ao da mais parecida.
2. Uma chamada do gabarito foi achada quando uma citação nossa aponta para a referência casada
   com a dela e está na mesma frase: as frases se sobrepõem pelo menos pela metade, ou a nossa
   contém a vizinhança da chamada no gabarito (40 caracteres antes e depois do marcador), porque
   o science-parse às vezes recorta do fim de uma frase até a seguinte.
3. **Recall:** chamadas do gabarito achadas, entre as julgáveis: as que têm a referência casada
   e são consistentes.
4. **Precisão:** citações nossas que batem com uma chamada válida do gabarito, entre as
   julgáveis. Uma citação nossa fica sem julgamento quando bate com uma chamada inválida do
   gabarito, quando está dentro de um grupo que o gabarito ligou a uma obra só, ou quando a
   referência dela não aparece em nenhuma chamada válida do gabarito (ele não cobre aquela obra).
   É errada só quando o gabarito cobre a referência e nenhuma chamada válida dele está na frase.

O science-parse também erra, de dois jeitos que dá para reconhecer sem olhar à mão:
- **chamada inconsistente:** o texto da própria chamada não traz o sobrenome e o ano da
  referência a que o gabarito a ligou ("Pathak et al. (2010)" ligada a um artigo de Hamm, 2016),
  ou os offsets dela não fazem sentido no contexto (marcador com centenas de caracteres ou sem
  número, como um parágrafo inteiro ligado a uma referência só). Ela sai da conta do recall;
- **grupo ligado a uma referência só:** em "(Dwork et al., 2006b; Dwork, 2011)" o gabarito tem
  uma chamada, ligada só a uma das obras.
O resto dos desacordos precisa ser olhado à mão numa amostra antes de virar meta.
"""

import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Final

from projects.correction.extractor.article import ExtractedArticle, Reference
from projects.correction.extractor.citations import fold_name, surname_key
from projects.correction.extractor.coverage import squash, text_coverage

TITLE_SIMILARITY: Final = 0.85
# Entradas do gabarito com títulos assim parecidos são a mesma obra repetida.
DUPLICATE_SIMILARITY: Final = 0.95
SENTENCE_OVERLAP: Final = 0.5
NEIGHBORHOOD_CHARS: Final = 40
MAX_MARKER_CHARS: Final = 80
YEAR: Final = re.compile(r"\d{4}")


@dataclass(frozen=True)
class GoldMention:
    reference_index: int
    context: str
    # O texto da chamada na frase ("Pathak et al. (2010)") e onde ele está no contexto.
    marker: str = ""
    start: int = 0
    end: int = 0

    @property
    def neighborhood(self) -> str:
        """A chamada com o que vem logo antes e logo depois dela no contexto."""
        if self.end <= self.start:
            return self.context
        return self.context[max(0, self.start - NEIGHBORHOOD_CHARS) : self.end + NEIGHBORHOOD_CHARS]


@dataclass(frozen=True)
class GoldPaper:
    name: str
    reference_titles: tuple[str, ...]
    mentions: tuple[GoldMention, ...]
    # Sobrenome do primeiro autor e ano de cada referência do gabarito, para a consistência.
    reference_keys: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_json(cls, path: Path) -> GoldPaper:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        metadata = data["metadata"]
        references = metadata["references"]
        return cls(
            name=path.name.removesuffix(".pdf.json"),
            reference_titles=tuple(ref.get("title") or "" for ref in references),
            mentions=tuple(
                GoldMention(
                    reference_index=m["referenceID"],
                    context=m["context"],
                    **_located_marker(m),
                )
                for m in metadata["referenceMentions"]
            ),
            reference_keys=tuple(
                (
                    surname_key(ref["author"][0]) if ref.get("author") else "",
                    str(ref.get("year") or ""),
                )
                for ref in references
            ),
        )

    def is_consistent(self, mention: GoldMention) -> bool:
        """O texto da chamada traz o sobrenome e o ano da referência a que o gabarito a ligou.
        Marcador implausível (offsets fora do lugar) não tem como conferir: inconsistente.
        Chamada numérica ("[3]") ou referência sem os dados conta como consistente."""
        if not mention.marker:
            return False
        if not any(char.isalpha() for char in mention.marker) or not self.reference_keys:
            return True
        surname, year = self.reference_keys[mention.reference_index]
        if not surname or not year:
            return True
        marker = fold_name(mention.marker)
        return surname in marker.split() and year in YEAR.findall(mention.marker)


@dataclass
class PaperScore:
    name: str
    references_gold: int = 0
    references_ours: int = 0
    references_matched: int = 0
    mentions_gold: int = 0
    mentions_inconsistent: int = 0
    mentions_judgeable: int = 0
    mentions_found: int = 0
    citations_judgeable: int = 0
    citations_unjudgeable: int = 0
    citations_correct: int = 0
    citations_unlinked: int = 0
    # Chamadas do gabarito que não achamos e citações nossas que não bateram, para olhar à mão.
    misses: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)


def score_paper(article: ExtractedArticle, gold: GoldPaper) -> PaperScore:
    matched = match_references(article.references, gold.reference_titles)
    score = PaperScore(
        name=gold.name,
        references_gold=len(gold.reference_titles),
        references_ours=len(article.references),
        references_matched=len(set().union(*matched.values())),
        mentions_gold=len(gold.mentions),
        citations_unlinked=sum(c.reference_id is None for c in article.citations),
    )
    ours = [
        (matched[c.reference_id], c.sentence, c.marker)
        for c in article.citations
        if c.reference_id is not None and c.reference_id in matched
    ]
    used: set[int] = set()
    judgeable_indexes: set[int] = set().union(*matched.values())
    invalid: list[GoldMention] = []
    covered: set[int] = set()
    for mention in gold.mentions:
        if mention.reference_index not in judgeable_indexes:
            continue
        if not gold.is_consistent(mention):
            score.mentions_inconsistent += 1
            invalid.append(mention)
            continue
        covered.add(mention.reference_index)
        score.mentions_judgeable += 1
        hit = next(
            (
                position
                for position, (index, sentence, _) in enumerate(ours)
                if position not in used
                and mention.reference_index in index
                and _same_sentence(sentence, mention)
            ),
            None,
        )
        if hit is None:
            score.misses.append(f"{mention.marker} | {mention.context[:160]}")
        else:
            used.add(hit)
            score.mentions_found += 1

    for position, (index, sentence, marker) in enumerate(ours):
        if position in used:
            score.citations_correct += 1
        elif (
            not index & covered
            or _inside_a_gold_mention(marker, sentence, gold)
            or any(m.reference_index in index and _same_sentence(sentence, m) for m in invalid)
        ):
            score.citations_unjudgeable += 1
        else:
            score.extras.append(f"{marker} | {sentence[:160]}")
    score.citations_judgeable = len(ours) - score.citations_unjudgeable
    return score


def match_references(
    ours: Sequence[Reference], gold_titles: Sequence[str]
) -> dict[str, frozenset[int]]:
    """Nossa referência → índices do gabarito, pelo título: a entrada mais parecida (uma para
    cada referência nossa) e as repetições dela no gabarito."""
    pairs = sorted(
        (
            (SequenceMatcher(None, _title_key(ref.title), _title_key(title)).ratio(), ref.id, index)
            for ref in ours
            if ref.title
            for index, title in enumerate(gold_titles)
            if title
        ),
        reverse=True,
    )
    matched: dict[str, int] = {}
    taken: set[int] = set()
    for similarity, ref_id, index in pairs:
        if similarity < TITLE_SIMILARITY:
            break
        if ref_id not in matched and index not in taken:
            matched[ref_id] = index
            taken.add(index)
    keys = [_title_key(title) for title in gold_titles]
    return {
        ref_id: frozenset(
            other
            for other, key in enumerate(keys)
            if key and SequenceMatcher(None, keys[index], key).ratio() >= DUPLICATE_SIMILARITY
        )
        for ref_id, index in matched.items()
    }


def totals(scores: Sequence[PaperScore]) -> dict[str, float | int]:
    judgeable = sum(s.mentions_judgeable for s in scores)
    citations = sum(s.citations_judgeable for s in scores)
    references_gold = sum(s.references_gold for s in scores)
    return {
        "papers": len(scores),
        "recall": sum(s.mentions_found for s in scores) / judgeable if judgeable else 0.0,
        "precision": sum(s.citations_correct for s in scores) / citations if citations else 0.0,
        "references_matched": (
            sum(s.references_matched for s in scores) / references_gold if references_gold else 0.0
        ),
        "mentions_gold": sum(s.mentions_gold for s in scores),
        "mentions_judgeable": judgeable,
        "mentions_inconsistent": sum(s.mentions_inconsistent for s in scores),
        "citations_judgeable": citations,
        "citations_unjudgeable": sum(s.citations_unjudgeable for s in scores),
        "citations_unlinked": sum(s.citations_unlinked for s in scores),
    }


def _inside_a_gold_mention(marker: str, sentence: str, gold: GoldPaper) -> bool:
    ours = squash(marker)
    return bool(ours) and any(
        ours in squash(mention.marker) and _same_sentence(sentence, mention)
        for mention in gold.mentions
    )


def _located_marker(mention: dict[str, Any]) -> dict[str, Any]:
    """O marcador recortado pelos offsets, se for plausível; senão, desconhecido."""
    start, end = mention.get("startOffset", 0), mention.get("endOffset", 0)
    marker = mention["context"][start:end]
    plausible = 0 < len(marker) <= MAX_MARKER_CHARS and any(c.isdigit() for c in marker)
    return {"marker": marker, "start": start, "end": end} if plausible else {}


def _same_sentence(sentence: str, mention: GoldMention) -> bool:
    """As frases se sobrepõem pela metade, ou a vizinhança da chamada está na nossa frase."""
    shorter, longer = sorted((sentence, mention.context), key=len)
    overlap = text_coverage(shorter, longer)
    if overlap is not None and overlap >= SENTENCE_OVERLAP:
        return True
    if not mention.marker:
        return False
    near = text_coverage(mention.neighborhood, sentence)
    return near is not None and near >= SENTENCE_OVERLAP


def _title_key(title: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", title or "").casefold()
    bare = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", bare).split())
