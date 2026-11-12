"""O mapa das seções: os títulos da chamada 1 num dict ordenado, com nível, pai e a chave das
seções que a config procura pelo nome (`abstract`, `references`)."""

import re
from typing import Final

from pydantic import BaseModel, ConfigDict

from projects.correction.extractor.config import DocumentConfig, normalize_label
from projects.correction.extractor.schemas import HeadingScan

# Numeração na frente do título: "2.1 ", "IV. ", "A.1 ", "3) ".
NUMBERING: Final = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLCDM]+|[A-Z](?:\.\d+)*)[.):]?\s+")
TRAILING_PUNCTUATION: Final = " .:;—–-"


class MappedSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    level: int
    parent_id: str | None
    # Chave da seção da config que o título nomeia; None para as demais.
    key: str | None


type SectionMap = dict[str, MappedSection]


def build_section_map(scan: HeadingScan, config: DocumentConfig) -> SectionMap:
    keys_by_label = {
        normalize_label(label): definition.key
        for definition in config.all_sections
        for label in definition.labels
    }
    section_map: SectionMap = {}
    open_sections: list[MappedSection] = []
    used_keys: set[str] = set()

    for heading in scan.headings:
        title = " ".join(heading.title.split())
        if not title:
            continue
        while open_sections and open_sections[-1].level >= heading.level:
            open_sections.pop()
        key = keys_by_label.get(_comparable(title))
        if key in used_keys:
            key = None  # a primeira seção com o nome fica com a chave
        section = MappedSection(
            id=f"sec_{len(section_map) + 1}",
            title=title,
            level=heading.level,
            parent_id=open_sections[-1].id if open_sections else None,
            key=key,
        )
        if key is not None:
            used_keys.add(key)
        section_map[section.id] = section
        open_sections.append(section)
    return section_map


def missing_required(section_map: SectionMap, config: DocumentConfig) -> tuple[str, ...]:
    found = {section.key for section in section_map.values()}
    return tuple(d.key for d in config.required_sections if d.key not in found)


def section_target(section_map: SectionMap, section_id: str) -> str:
    """Como a chamada 2 nomeia a seção: o título e a seção de que ela faz parte, que desfaz a
    dúvida quando dois títulos se repetem ("Bubble Sort." em 3.2 e em 4.1)."""
    section = section_map[section_id]
    parent = section_map.get(section.parent_id) if section.parent_id else None
    inside = f', dentro da seção "{parent.title}"' if parent is not None else ""
    return f'"{section.title}"{inside}'


def section_end(section_map: SectionMap, section_id: str) -> str:
    """Onde a seção termina: no título seguinte do mapa ou no fim do documento."""
    ids = list(section_map)
    position = ids.index(section_id)
    if position + 1 < len(ids):
        return f'no título "{section_map[ids[position + 1]].title}"'
    return "no fim do documento"


def _comparable(title: str) -> str:
    return normalize_label(NUMBERING.sub("", title)).strip(TRAILING_PUNCTUATION)
