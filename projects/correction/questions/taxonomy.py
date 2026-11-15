"""Normaliza e versiona a árvore; nenhuma escrita ocorre antes da validação completa."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum

from projects.correction.scholarly.openalex import OpenAlexEntity, OpenAlexTaxonomy, OpenAlexTopic


class TaxonomyLevel(StrEnum):
    DOMAIN = "domain"
    FIELD = "field"
    SUBFIELD = "subfield"
    TOPIC = "topic"


@dataclass(frozen=True)
class TaxonomyEntry:
    code: str
    level: TaxonomyLevel
    name: str
    parent_code: str | None


@dataclass(frozen=True)
class TaxonomySnapshot:
    entries: tuple[TaxonomyEntry, ...]
    version: str

    @classmethod
    def from_topics(cls, topics: tuple[OpenAlexTopic, ...]) -> TaxonomySnapshot:
        return cls.from_catalog(OpenAlexTaxonomy(topics=topics))

    @classmethod
    def from_catalog(cls, catalog: OpenAlexTaxonomy) -> TaxonomySnapshot:
        if not catalog.topics:
            raise ValueError("A taxonomia não pode estar vazia.")
        entries: dict[str, TaxonomyEntry] = {}
        topic_codes: set[str] = set()

        def add_path(path: tuple[OpenAlexEntity, ...]) -> str:
            parent = None
            for level, entity in zip(TaxonomyLevel, path, strict=False):
                code = canonical_code(entity.id, level)
                entry = TaxonomyEntry(code, level, entity.display_name, parent)
                if code in entries and entries[code] != entry:
                    raise ValueError(f"Nome ou parentesco divergente para {code}.")
                entries[code] = entry
                parent = code
            return code

        for domain in catalog.domains:
            add_path((domain,))
        for field in catalog.fields:
            add_path((field.domain, field))
        for subfield in catalog.subfields:
            add_path((subfield.domain, subfield.field, subfield))
        for topic in catalog.topics:
            code = add_path((topic.domain, topic.field, topic.subfield, topic))
            if code in topic_codes:
                raise ValueError("A taxonomia contém topics duplicados.")
            topic_codes.add(code)
        ordered = tuple(sorted(entries.values(), key=lambda entry: entry.code))
        payload = json.dumps(
            [asdict(entry) for entry in ordered], ensure_ascii=False, sort_keys=True
        ).encode()
        return cls(ordered, hashlib.sha256(payload).hexdigest())


def canonical_code(value: str, level: TaxonomyLevel) -> str:
    suffix = "T[1-9][0-9]*" if level == TaxonomyLevel.TOPIC else f"{level}s/[1-9][0-9]*"
    if not re.fullmatch(rf"https?://openalex\.org/{suffix}", value):
        raise ValueError(f"Identificador OpenAlex inválido para o nível {level}.")
    return value.replace("http://", "https://", 1)
