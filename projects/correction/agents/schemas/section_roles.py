"""Papéis compartilhados pelos classificadores e pelos passes de avaliação."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from projects.correction.agents.schemas.profiling import Confidence


class SectionRole(StrEnum):
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    DEFINITIONS = "definitions"
    THEOREMS = "theorems"
    PROOFS = "proofs"
    SCOPE = "scope"
    SEARCH_PROTOCOL = "search_protocol"
    THEMATIC = "thematic"
    SYNTHESIS = "synthesis"
    CONTEXT = "context"
    CASE_DESCRIPTION = "case_description"
    ANALYSIS = "analysis"
    LESSONS = "lessons"
    OTHER = "other"


class SectionRoleChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    roles: tuple[SectionRole, ...]
    confidence: Confidence
