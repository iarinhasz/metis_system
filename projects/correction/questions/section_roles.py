"""Títulos conhecidos viram papéis em código; só os ambíguos chegam ao modelo."""

import json
import re
import unicodedata

from pydantic import BaseModel, ConfigDict

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole, SectionRoleChoice
from projects.correction.extractor.article import ExtractedArticle, ExtractedSection

type Roles = tuple[SectionRole, ...]

EMPIRICAL: Roles = (
    SectionRole.INTRODUCTION,
    SectionRole.RELATED_WORK,
    SectionRole.METHOD,
    SectionRole.RESULTS,
    SectionRole.DISCUSSION,
    SectionRole.CONCLUSION,
)
PAPER_ROLES: dict[PaperType, Roles] = {
    PaperType.EMPIRICAL: EMPIRICAL,
    PaperType.METHODS: EMPIRICAL,
    PaperType.THEORETICAL: (
        SectionRole.INTRODUCTION,
        SectionRole.RELATED_WORK,
        SectionRole.DEFINITIONS,
        SectionRole.THEOREMS,
        SectionRole.PROOFS,
        SectionRole.DISCUSSION,
        SectionRole.CONCLUSION,
    ),
    PaperType.REVIEW: (
        SectionRole.INTRODUCTION,
        SectionRole.SCOPE,
        SectionRole.SEARCH_PROTOCOL,
        SectionRole.THEMATIC,
        SectionRole.SYNTHESIS,
        SectionRole.DISCUSSION,
        SectionRole.CONCLUSION,
    ),
    PaperType.CASE_STUDY: (
        SectionRole.CONTEXT,
        SectionRole.CASE_DESCRIPTION,
        SectionRole.ANALYSIS,
        SectionRole.LESSONS,
        SectionRole.CONCLUSION,
    ),
}
TITLES: dict[SectionRole, tuple[str, ...]] = {
    SectionRole.INTRODUCTION: ("introduction", "introducao"),
    SectionRole.RELATED_WORK: ("related work", "trabalhos relacionados", "background"),
    SectionRole.METHOD: (
        "methods",
        "method",
        "methodology",
        "metodo",
        "metodos",
        "metodologia",
        "materiais e metodos",
        "materials and methods",
        "approach",
        "experiments",
        "experimentos",
    ),
    SectionRole.RESULTS: ("results", "resultados"),
    SectionRole.DISCUSSION: ("discussion", "discussao", "limitations", "limitacoes"),
    SectionRole.CONCLUSION: ("conclusion", "conclusions", "conclusao", "conclusoes"),
    SectionRole.DEFINITIONS: ("definitions", "definicoes", "problem formulation", "problema"),
    SectionRole.THEOREMS: ("theorems", "teoremas", "main results", "resultados principais"),
    SectionRole.PROOFS: ("proofs", "proof", "provas", "demonstracoes"),
    SectionRole.SCOPE: ("scope", "escopo"),
    SectionRole.SEARCH_PROTOCOL: ("search protocol", "protocolo de busca", "search strategy"),
    SectionRole.THEMATIC: ("thematic sections", "secoes tematicas"),
    SectionRole.SYNTHESIS: ("synthesis", "sintese"),
    SectionRole.CONTEXT: ("context", "contexto"),
    SectionRole.CASE_DESCRIPTION: ("case description", "descricao do caso", "case presentation"),
    SectionRole.ANALYSIS: ("analysis", "analise"),
    SectionRole.LESSONS: ("lessons", "licoes"),
}


class SectionAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    roles: Roles
    ambiguous: bool = False


def rule_based_roles(
    article: ExtractedArticle, paper_type: PaperType
) -> tuple[SectionAssignment, ...]:
    assignments = []
    for section in article.sections:
        title = "".join(
            char
            for char in unicodedata.normalize("NFKD", section.title.casefold())
            if not unicodedata.combining(char)
        )
        title = re.sub(r"^\s*[\d.()\s]+", "", title)
        roles = tuple(
            role
            for role in PAPER_ROLES[paper_type]
            if any(re.search(rf"\b{re.escape(word)}\b", title) for word in TITLES[role])
        )
        if paper_type is PaperType.THEORETICAL and title in {"results", "resultados"}:
            roles = (SectionRole.THEOREMS,)
        structural = section.key in {"abstract", "references"}
        assignments.append(
            SectionAssignment(
                section_id=section.id,
                roles=roles or (SectionRole.OTHER,),
                ambiguous=not roles and not structural,
            )
        )
    return tuple(assignments)


def classify_role(
    section: ExtractedSection,
    paper_type: PaperType,
    *,
    factory: AgentFactory,
    confidence_threshold: float,
) -> SectionAssignment:
    allowed = (*PAPER_ROLES[paper_type], SectionRole.OTHER)
    result = factory.section_role_classifier(output_schema=SectionRoleChoice).run(
        AgentPayload(
            "Papéis permitidos: " + ", ".join(allowed),
            article=json.dumps(
                {"title": section.title, "excerpt": section.text[:1000]}, ensure_ascii=False
            ),
        )
    )
    choice = result.content
    roles: Roles = (SectionRole.OTHER,)
    if (
        result.valid
        and isinstance(choice, SectionRoleChoice)
        and choice.confidence >= confidence_threshold
        and choice.roles
        and all(role in allowed for role in choice.roles)
        and not (SectionRole.OTHER in choice.roles and len(choice.roles) > 1)
    ):
        roles = tuple(dict.fromkeys(choice.roles))
    return SectionAssignment(section_id=section.id, roles=roles)
