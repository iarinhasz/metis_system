"""Catálogo inicial revisável; carregar nunca aprova ou substitui a curadoria."""

from pathlib import Path

from pydantic import Field, model_validator

from projects.correction.agents.schemas.curation import DraftQuestion
from projects.correction.questions.criteria import get_method
from projects.correction.questions.models import Question, TaxonomyNode
from projects.correction.questions.profile import FrozenModel
from projects.correction.questions.taxonomy import TaxonomyLevel, canonical_code

INITIAL_QUESTIONS = Path(__file__).parent / "data" / "initial_questions.json"


class InitialQuestion(FrozenModel):
    field_code: str | None
    draft: DraftQuestion

    @model_validator(mode="after")
    def field_identifier(self) -> InitialQuestion:
        if self.field_code is not None:
            canonical_code(self.field_code, TaxonomyLevel.FIELD)
        return self


class InitialCatalog(FrozenModel):
    version: int = Field(ge=1)
    method: str
    questions: tuple[InitialQuestion, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_scopes(self) -> InitialCatalog:
        get_method(self.method)
        codes = [item.field_code for item in self.questions]
        if len(set(codes)) != len(codes) or codes.count(None) != 1:
            raise ValueError("O catálogo precisa de uma genérica e escopos únicos.")
        return self


def prepare_initial_questions(
    taxonomy_version: str, *, path: Path = INITIAL_QUESTIONS
) -> tuple[InitialCatalog, tuple[tuple[DraftQuestion, TaxonomyNode | None], ...]]:
    catalog = InitialCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    fields = {node.code: node for node in TaxonomyNode.fields_for_profiling(taxonomy_version)}
    missing = {item.field_code for item in catalog.questions if item.field_code} - fields.keys()
    if missing:
        raise ValueError("A versão da taxonomia não contém todos os fields do catálogo inicial.")
    return catalog, tuple(
        (item.draft, fields[item.field_code] if item.field_code else None)
        for item in catalog.questions
    )


def seed_initial_questions(
    taxonomy_version: str, *, path: Path = INITIAL_QUESTIONS
) -> tuple[tuple[Question, bool], ...]:
    catalog, items = prepare_initial_questions(taxonomy_version, path=path)
    return Question.store_initial_drafts(items, method=catalog.method)
