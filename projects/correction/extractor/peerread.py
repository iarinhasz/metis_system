"""Converte exemplos `parsed_pdfs` do PeerRead para o contrato do E1."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from projects.correction.extractor.contract import (
    CitationMention,
    DocumentReference,
    DocumentSection,
    ExtractedDocument,
)


def peerread_to_document(row: dict[str, Any]) -> ExtractedDocument:
    """Converte uma linha do PeerRead sem rede ou chamada a modelo."""
    metadata = row.get("metadata") or {}
    title_value = metadata.get("title") or row.get("name")
    title = ""
    if isinstance(title_value, list):
        title = " ".join(_text(part) for part in title_value if _text(part))
    else:
        title = _text(title_value)
    abstract = _text(metadata.get("abstractText"))

    raw_sections = metadata.get("sections") or []
    sections: list[DocumentSection] = []
    parents: list[tuple[int, str]] = []
    for index, item in enumerate(raw_sections, start=1):
        heading = _text(item.get("heading")) or f"Seção {index}"
        key = _slug(heading)
        if key in {"abstract", "references", "bibliography"}:
            if key == "abstract" and not abstract:
                abstract = _text(item.get("text"))
            continue
        level = _heading_level(heading)
        while parents and parents[-1][0] >= level:
            parents.pop()
        parent_id = parents[-1][1] if parents else None
        # PeerRead não fornece offsets nem páginas para cada seção.
        section_id = f"sec_{len(sections) + 1}"
        sections.append(
            DocumentSection(
                id=section_id,
                title=heading,
                level=level,
                parent_id=parent_id,
                key=key or None,
                text=_text(item.get("text")),
            )
        )
        parents.append((level, section_id))

    if not abstract:
        raise ValueError("O registro PeerRead não tem abstract.")
    if not sections:
        raise ValueError("O registro PeerRead não tem seções de conteúdo.")

    references: list[DocumentReference] = []
    for index, item in enumerate(metadata.get("references") or [], start=1):
        authors = tuple(_text(author) for author in item.get("author") or [] if _text(author))
        ref_title = _text(item.get("title")) or None
        venue = _text(item.get("venue")) or None
        year = item.get("year")
        raw_parts = [part for part in (*authors, ref_title or "", venue or "") if part]
        if year:
            raw_parts.append(str(year))
        raw = ". ".join(raw_parts) or f"Referência PeerRead {index}"
        references.append(
            DocumentReference(
                id=f"ref_{index}",
                raw=raw,
                authors=authors,
                title=ref_title,
                year=str(year) if year else None,
                venue=venue,
            )
        )

    citation_mentions: list[CitationMention] = []
    for item in metadata.get("referenceMentions") or []:
        sentence = _text(item.get("context"))
        if not sentence:
            continue
        matched_section_id = _find_section(sentence, sections)
        if matched_section_id is None:
            continue
        start = next(
            section.text.find(sentence) for section in sections if section.id == matched_section_id
        )
        raw_reference_index = item.get("referenceID")
        try:
            reference_index = int(raw_reference_index)
        except TypeError, ValueError:
            reference_index = -1
        reference_id = (
            f"ref_{reference_index + 1}"
            if not isinstance(raw_reference_index, bool) and 0 <= reference_index < len(references)
            else None
        )
        citation_mentions.append(
            CitationMention(
                reference_id=reference_id,
                sentence=sentence,
                section_id=matched_section_id,
                start_offset=start,
                end_offset=start + len(sentence),
            )
        )

    return ExtractedDocument(
        title=title or _text(row.get("name")) or "Artigo sem título",
        authors=tuple(_text(author) for author in metadata.get("authors") or [] if _text(author)),
        language="en",
        abstract=abstract,
        sections=tuple(sections),
        references=tuple(references),
        citation_mentions=tuple(citation_mentions),
    )


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", plain.casefold()).strip("_")


def _heading_level(heading: str) -> int:
    match = re.match(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+", heading)
    return min(match.group(1).count(".") + 1, 6) if match else 1


def _find_section(sentence: str, sections: list[DocumentSection]) -> str | None:
    candidates = [section for section in sections if sentence in section.text]
    if not candidates:
        return None
    return min(candidates, key=lambda section: section.text.find(sentence)).id
