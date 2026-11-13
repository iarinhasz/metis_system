"""Mapa extraído do documento, sem interpretações nem chamadas ao modelo."""

import re
from typing import Literal

from projects.correction.extractor.article import ExtractedArticle
from projects.correction.questions.profile import FrozenModel
from projects.correction.questions.section_roles import Roles, SectionAssignment


class MapSection(FrozenModel):
    id: str
    title: str
    roles: Roles
    first_sentence: str


class MapFigure(FrozenModel):
    id: str
    kind: Literal["figure", "table"]
    label: str
    page: int
    caption: str


class DocumentMap(FrozenModel):
    title: str
    abstract: str
    sections: tuple[MapSection, ...]
    figures: tuple[MapFigure, ...]


def build_document_map(
    article: ExtractedArticle, assignments: tuple[SectionAssignment, ...]
) -> DocumentMap:
    roles = {assignment.section_id: assignment.roles for assignment in assignments}
    if set(roles) != {section.id for section in article.sections}:
        raise ValueError("Toda seção precisa de papéis para montar o mapa.")
    abstract = article.section("abstract")
    return DocumentMap(
        title=article.title,
        abstract=abstract.text if abstract else "",
        sections=tuple(
            MapSection(
                id=section.id,
                title=section.title,
                roles=roles[section.id],
                first_sentence=re.split(r"(?<=[.!?])\s+", section.text.strip(), maxsplit=1)[0],
            )
            for section in article.sections
        ),
        figures=tuple(
            MapFigure(
                id=figure.id,
                kind=figure.kind,
                label=figure.label,
                page=figure.page,
                caption=figure.caption,
            )
            for figure in article.figures
        ),
    )
