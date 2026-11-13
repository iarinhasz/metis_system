"""Saídas imutáveis do E2, serializáveis para o profile e o config_snapshot do Run."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from projects.correction.agents.schemas.profiling import Confidence, PaperType
from projects.correction.questions.taxonomy import TaxonomyLevel


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AreaNode(FrozenModel):
    code: str
    level: TaxonomyLevel
    name: str


class ArticleProfile(FrozenModel):
    taxonomy_version: str
    area_path: tuple[AreaNode, AreaNode, AreaNode, AreaNode]
    field_confidence: Confidence
    topic_confidence: Confidence
    confidence: Confidence
    paper_type: PaperType
    language: str
    keywords: tuple[str, ...]
    # Fields da mesma versão, para os casos interdisciplinares.
    secondary_areas: tuple[AreaNode, ...]

    @model_validator(mode="after")
    def ordered_path(self) -> ArticleProfile:
        if tuple(node.level for node in self.area_path) != tuple(TaxonomyLevel):
            raise ValueError("O caminho deve seguir domain, field, subfield, topic.")
        if self.confidence != min(self.field_confidence, self.topic_confidence):
            raise ValueError("A confiança do perfil deve ser a menor dos dois passos.")
        return self


class RubricFieldSnapshot(FrozenModel):
    id: UUID
    key: str
    label: str
    rubric_text: str
    order: int = Field(ge=0)


class QuestionSnapshot(FrozenModel):
    id: UUID
    version: int = Field(ge=1)
    name: str
    method: str
    is_generic: bool
    taxonomy_node_code: str | None
    taxonomy_version: str | None
    rubric_fields: tuple[RubricFieldSnapshot, ...]


class ResolutionScope(StrEnum):
    TOPIC = "topic"
    SUBFIELD = "subfield"
    FIELD = "field"
    GENERIC = "generic"


class ResolutionHop(FrozenModel):
    scope: ResolutionScope
    code: str | None
    matched: bool


class ResolvedQuestion(FrozenModel):
    question: QuestionSnapshot
    taxonomy_version: str
    resolution_path: tuple[ResolutionHop, ...]
    uncertain: bool
