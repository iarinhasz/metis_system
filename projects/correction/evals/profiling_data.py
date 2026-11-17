"""Contrato da amostra: entrada do profiler separada dos rótulos de referência."""

from pathlib import Path

from pydantic import Field, model_validator

from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.extractor.article import ExtractedArticle
from projects.correction.questions.profile import FrozenModel
from projects.correction.questions.section_roles import PAPER_ROLES
from projects.correction.questions.taxonomy import TaxonomyLevel, canonical_code

DATASET_PATH = Path(__file__).parent / "data" / "profiling.json"


class ArticleSource(FrozenModel):
    doi: str = Field(min_length=1)
    openalex_id: str = Field(pattern=r"^https://openalex.org/W[1-9][0-9]*$")
    url: str = Field(pattern=r"^https://")
    license: str = Field(min_length=1)
    license_notice: str = Field(min_length=1)
    xml_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    year: int = Field(ge=1900)


class ProfileLabels(FrozenModel):
    field: str
    paper_type: PaperType
    section_roles: dict[str, tuple[SectionRole, ...]]

    @model_validator(mode="after")
    def valid_roles(self) -> ProfileLabels:
        canonical_code(self.field, TaxonomyLevel.FIELD)
        allowed = {*PAPER_ROLES[self.paper_type], SectionRole.OTHER}
        for roles in self.section_roles.values():
            if (
                not roles
                or len(set(roles)) != len(roles)
                or not set(roles) <= allowed
                or (SectionRole.OTHER in roles and len(roles) > 1)
            ):
                raise ValueError("Papéis de referência incompatíveis com o tipo de artigo.")
        return self


class ProfilingCase(FrozenModel):
    id: str = Field(min_length=1)
    area: str = Field(min_length=1)
    source: ArticleSource
    article: ExtractedArticle
    labels: ProfileLabels

    @model_validator(mode="after")
    def complete_labels(self) -> ProfilingCase:
        ids = [section.id for section in self.article.sections]
        abstract = self.article.section("abstract")
        if not self.article.title.strip() or abstract is None or not abstract.text.strip():
            raise ValueError("O caso precisa de título e abstract.")
        if len(ids) != len(set(ids)) or set(ids) != self.labels.section_roles.keys():
            raise ValueError("Cada seção precisa de um id único e um rótulo.")
        if self.labels.section_roles[abstract.id] != (SectionRole.OTHER,):
            raise ValueError("O abstract é estrutural, com papel other.")
        return self


class ProfilingDataset(FrozenModel):
    version: str = Field(min_length=1)
    retrieved_on: str
    annotation_status: str
    field_label_source: str
    role_label_source: str
    sampling: str
    cases: tuple[ProfilingCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_articles(self) -> ProfilingDataset:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("A amostra contém ids de artigos repetidos.")
        if len({case.source.doi.casefold() for case in self.cases}) != len(self.cases):
            raise ValueError("A amostra contém DOIs repetidos.")
        return self


def read_dataset(path: Path = DATASET_PATH) -> ProfilingDataset:
    return ProfilingDataset.model_validate_json(path.read_text(encoding="utf-8"))
