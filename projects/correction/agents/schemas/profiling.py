"""Contratos do profiler e schemas fechados montados a partir da taxonomia escolhida."""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import GenericAlias
from typing import Annotated, Any, cast

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
from pydantic_core import PydanticCustomError

Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False, examples=[0.9])]


class PaperType(StrEnum):
    EMPIRICAL = "empirical"
    THEORETICAL = "theoretical"
    REVIEW = "review"
    METHODS = "methods"
    CASE_STUDY = "case_study"


class FieldChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    paper_type: PaperType
    language: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", examples=["pt"])
    keywords: tuple[str, ...]
    confidence: Confidence


class TopicChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subfield: str
    topic: str
    secondary_areas: tuple[str, ...]
    confidence: Confidence


def _codes(values: Sequence[str]) -> type[StrEnum]:
    if not values:
        raise ValueError("Um enum do profiler precisa de pelo menos uma opção.")
    return cast(
        type[StrEnum],
        StrEnum("TaxonomyCode", {f"CODE_{index}": value for index, value in enumerate(values)}),
    )


def field_choice_schema(fields: Sequence[str]) -> type[FieldChoice]:
    return create_model("ClosedFieldChoice", __base__=FieldChoice, field=(_codes(fields), ...))


def topic_choice_schema(
    topic_parents: Mapping[str, str], fields: Sequence[str]
) -> type[TopicChoice]:
    parents = dict(topic_parents)

    def coherent_subfield(choice: TopicChoice) -> TopicChoice:
        if parents[choice.topic] != choice.subfield:
            raise PydanticCustomError(
                "topic_subfield_mismatch", "O topic deve pertencer ao subfield informado."
            )
        return choice

    definitions: dict[str, Any] = {
        "topic": (_codes(tuple(parents)), ...),
        "subfield": (_codes(tuple(dict.fromkeys(parents.values()))), ...),
        "secondary_areas": (GenericAlias(tuple, (_codes(fields), Ellipsis)), ...),
    }
    validators: dict[str, Any] = {
        "coherent_subfield": model_validator(mode="after")(coherent_subfield)
    }
    return create_model(
        "ClosedTopicChoice",
        __base__=TopicChoice,
        __validators__=validators,
        **definitions,
    )
