"""Contrato agnóstico de provedor para documentos científicos extraídos (M1.1)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class DocumentSection(ContractModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: int = Field(ge=1)
    parent_id: str | None = None
    key: str | None = None
    text: str
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> DocumentSection:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset e end_offset devem ser informados juntos.")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset < self.start_offset
        ):
            raise ValueError("end_offset não pode ser menor que start_offset.")
        if (self.start_page is None) != (self.end_page is None):
            raise ValueError("start_page e end_page devem ser informados juntos.")
        if (
            self.start_page is not None
            and self.end_page is not None
            and self.end_page < self.start_page
        ):
            raise ValueError("end_page não pode ser menor que start_page.")
        return self


class DocumentReference(ContractModel):
    id: str = Field(min_length=1)
    raw: str = Field(min_length=1)
    marker: str | None = None
    authors: tuple[str, ...] = ()
    title: str | None = None
    year: str | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None


class DocumentFigureDescription(ContractModel):
    figure_class: str
    description: str
    data_read: tuple[str, ...] = ()
    supports_claims: bool | None = None
    support_rationale: str = ""
    issues: tuple[str, ...] = ()
    table_markdown: str | None = None


class CitationMention(ContractModel):
    reference_id: str | None = None
    marker: str | None = None
    sentence: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> CitationMention:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("Os offsets da citação devem ser informados juntos.")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset < self.start_offset
        ):
            raise ValueError("end_offset não pode ser menor que start_offset.")
        return self


class DocumentFigure(ContractModel):
    id: str = Field(min_length=1)
    kind: Literal["figure", "table"]
    label: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    caption: str = Field(min_length=1)
    section_id: str | None = None
    offset: int | None = Field(default=None, ge=0)
    description: DocumentFigureDescription | None = None


class ExtractedDocument(ContractModel):
    """Representação validada do artigo, sem dependência de extrator ou provedor de LLM."""

    contract_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    title: str = Field(min_length=1)
    authors: tuple[str, ...] = ()
    language: str = Field(min_length=2, max_length=3, pattern=r"^[a-z]{2,3}$")
    abstract: str = Field(min_length=1)
    sections: tuple[DocumentSection, ...] = Field(min_length=1)
    references: tuple[DocumentReference, ...] = ()
    citation_mentions: tuple[CitationMention, ...] = ()
    figures: tuple[DocumentFigure, ...] = ()

    @model_validator(mode="after")
    def validate_relations(self) -> ExtractedDocument:
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Os ids das seções devem ser únicos.")
        known_sections = set(section_ids)
        earlier_sections: set[str] = set()
        section_by_id = {section.id: section for section in self.sections}
        for section in self.sections:
            if section.parent_id is not None:
                if section.parent_id not in known_sections:
                    raise ValueError(f"Seção pai inexistente: {section.parent_id}.")
                if section.parent_id not in earlier_sections:
                    raise ValueError("A seção pai precisa aparecer antes da seção filha.")
                parent = section_by_id[section.parent_id]
                if parent.level >= section.level:
                    raise ValueError("O nível da seção filha deve ser maior que o do pai.")
            elif section.level != 1:
                raise ValueError("Seção sem pai deve estar no nível 1.")
            earlier_sections.add(section.id)

        reference_ids = [reference.id for reference in self.references]
        if len(reference_ids) != len(set(reference_ids)):
            raise ValueError("Os ids das referências devem ser únicos.")
        known_references = set(reference_ids)
        for citation in self.citation_mentions:
            if citation.section_id not in known_sections:
                raise ValueError(f"Seção da citação inexistente: {citation.section_id}.")
            if citation.reference_id is not None and citation.reference_id not in known_references:
                raise ValueError(f"Referência da citação inexistente: {citation.reference_id}.")
            if citation.end_offset is not None and citation.end_offset > len(
                section_by_id[citation.section_id].text
            ):
                raise ValueError("O offset da citação ultrapassa o texto da seção.")

        figure_ids = [figure.id for figure in self.figures]
        if len(figure_ids) != len(set(figure_ids)):
            raise ValueError("Os ids de figuras e tabelas devem ser únicos.")
        for figure in self.figures:
            if figure.section_id is not None and figure.section_id not in known_sections:
                raise ValueError(f"Seção da figura inexistente: {figure.section_id}.")
            if figure.offset is not None and figure.section_id is None:
                raise ValueError("Figura com offset precisa indicar a seção correspondente.")
            if (
                figure.offset is not None
                and figure.section_id is not None
                and figure.offset > len(section_by_id[figure.section_id].text)
            ):
                raise ValueError("O offset da figura ultrapassa o texto da seção.")

        if not self.abstract:
            raise ValueError("O artigo precisa ter abstract.")
        return self

    def render_for_llm(
        self, section_id: str | None = None, *, max_chars: int = 24_000
    ) -> tuple[str, ...]:
        """Renderiza o artigo em blocos, preservando seções e colocando figuras junto ao texto.

        Se `section_id` for informado, inclui a seção e suas descendentes. Blocos longos são
        separados primeiro por seção/subseção e, quando necessário, por parágrafo.
        """
        if max_chars < 256:
            raise ValueError("max_chars precisa ser pelo menos 256.")
        selected = self._section_ids(section_id)
        figures_by_section: dict[str, list[DocumentFigure]] = defaultdict(list)
        for figure in self.figures:
            if figure.section_id is not None and figure.section_id in selected:
                figures_by_section[figure.section_id].append(figure)

        rendered: list[str] = []
        for section in self.sections:
            if section.id not in selected:
                continue
            heading = "#" * min(section.level + 1, 6)
            body = self._render_section_text(section, figures_by_section[section.id])
            rendered.append(f"{heading} {section.title}\n{body}".strip())

        if section_id is None and self.references:
            references = "\n".join(f"- {reference.raw}" for reference in self.references)
            rendered.append(f"## Referências\n{references}")
        unplaced_figures = [figure for figure in self.figures if figure.section_id is None]
        if section_id is None and unplaced_figures:
            visuals = "\n".join(
                f"[{('FIGURA' if figure.kind == 'figure' else 'TABELA')} "
                f"{figure.label}: {figure.caption}]"
                for figure in unplaced_figures
            )
            rendered.append(f"## Figuras e tabelas\n{visuals}")

        header = f"# {self.title}\n\nAutores: {', '.join(self.authors)}\n\n{self.abstract}\n\n"
        payload_limit = max_chars - len(header)
        if payload_limit < 64:
            raise ValueError("max_chars é pequeno demais para incluir os metadados do artigo.")
        payloads: list[str] = []
        current = ""
        for block in rendered:
            if len(current) + len(block) + 2 <= payload_limit:
                current = f"{current}\n\n{block}" if current else block
                continue
            if current:
                payloads.append(current)
            if len(block) <= payload_limit:
                current = block
                continue
            pieces = self._split_long_block(block, payload_limit)
            payloads.extend(pieces[:-1])
            current = pieces[-1]
        if current:
            payloads.append(current)
        return tuple(f"{header}{payload}" for payload in payloads) or (header.rstrip(),)

    def _section_ids(self, section_id: str | None) -> set[str]:
        if section_id is None:
            return {section.id for section in self.sections}
        sections = {section.id: section for section in self.sections}
        if section_id not in sections:
            raise ValueError(f"Seção inexistente: {section_id}.")
        selected = {section_id}
        for section in self.sections:
            parent_id = section.parent_id
            while parent_id is not None:
                if parent_id in selected:
                    selected.add(section.id)
                    break
                parent_id = sections[parent_id].parent_id
        return selected

    @staticmethod
    def _render_section_text(section: DocumentSection, figures: list[DocumentFigure]) -> str:
        body = section.text
        insertions: list[tuple[int, str]] = []
        for figure in figures:
            if figure.offset is not None and figure.offset <= len(body):
                label = "FIGURA" if figure.kind == "figure" else "TABELA"
                insertions.append(
                    (figure.offset, f"\n[{label} {figure.label}: {figure.caption}]\n")
                )
        for offset, text in sorted(insertions, reverse=True):
            body = f"{body[:offset]}{text}{body[offset:]}"
        unpositioned = [figure for figure in figures if figure.offset is None]
        if unpositioned:
            body = "\n\n".join(
                [body]
                + [
                    f"[{('FIGURA' if figure.kind == 'figure' else 'TABELA')} "
                    f"{figure.label}: {figure.caption}]"
                    for figure in unpositioned
                ]
            )
        return body

    @staticmethod
    def _split_long_block(block: str, max_chars: int) -> list[str]:
        heading, separator, body = block.partition("\n")
        if not separator:
            return [block[index : index + max_chars] for index in range(0, len(block), max_chars)]
        paragraphs = re.split(r"\n\s*\n", body)
        chunks: list[str] = []
        current = heading
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current != heading:
                chunks.append(current)
            if len(paragraph) + len(heading) + 2 > max_chars:
                available = max_chars - len(heading) - 2
                chunks.extend(
                    f"{heading}\n\n{paragraph[index : index + available]}"
                    for index in range(0, len(paragraph), available)
                )
                current = heading
            else:
                current = f"{heading}\n\n{paragraph}"
        if current != heading:
            chunks.append(current)
        return chunks or [heading]
