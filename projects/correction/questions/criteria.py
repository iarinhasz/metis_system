"""Métodos imutáveis com critérios, escala discreta e cobertura por papel de seção."""

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import Field, model_validator

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.questions.curation_errors import CurationError
from projects.correction.questions.profile import FrozenModel
from projects.correction.questions.section_roles import PAPER_ROLES


class CriterionConfig(FrozenModel):
    key: Criterion
    label: str = Field(min_length=1)
    question: str = Field(min_length=1)
    weight: float = Field(default=1, ge=0, allow_inf_nan=False)
    grades: tuple[int, ...] = (1, 2, 3, 4, 5)


class SectionCriteria(FrozenModel):
    role: SectionRole
    criteria: tuple[Criterion, ...] = Field(min_length=1)


class PaperCriteria(FrozenModel):
    paper_type: PaperType
    active: tuple[Criterion, ...] = Field(min_length=1)
    sections: tuple[SectionCriteria, ...]


class EvaluationConfig(FrozenModel):
    method: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    allowed_grades: tuple[int, ...] = (1, 2, 3, 4, 5)
    criteria: tuple[CriterionConfig, ...]
    paper_types: tuple[PaperCriteria, ...]

    @model_validator(mode="after")
    def coherent_method(self) -> EvaluationConfig:
        if (
            not self.allowed_grades
            or tuple(sorted(set(self.allowed_grades))) != self.allowed_grades
        ):
            raise ValueError("A escala deve ser não vazia, única e crescente.")
        keys = tuple(item.key for item in self.criteria)
        if len(set(keys)) != len(keys) or set(keys) != set(Criterion):
            raise ValueError("O método deve definir uma vez cada um dos sete critérios.")
        for item in self.criteria:
            if (
                not item.grades
                or len(set(item.grades)) != len(item.grades)
                or not set(item.grades) <= set(self.allowed_grades)
            ):
                raise ValueError("As notas devem pertencer à escala do método.")
        types = [paper.paper_type for paper in self.paper_types]
        if len(set(types)) != len(types) or set(types) != set(PaperType):
            raise ValueError("O método deve cobrir todos os tipos de artigo.")
        weights = {item.key: item.weight for item in self.criteria}
        for paper in self.paper_types:
            active = set(paper.active)
            roles = [section.role for section in paper.sections]
            if len(active) != len(paper.active) or not active <= set(keys):
                raise ValueError("Critérios ativos inválidos ou repetidos.")
            if sum(weights[key] for key in active) <= 0:
                raise ValueError("Os critérios ativos precisam ter peso total positivo.")
            if len(set(roles)) != len(roles) or set(roles) != set(PAPER_ROLES[paper.paper_type]):
                raise ValueError("O método deve cobrir uma vez cada papel do tipo de artigo.")
            covered: set[Criterion] = set()
            for section in paper.sections:
                if not set(section.criteria) <= active:
                    raise ValueError("Um papel não pode avaliar critérios inativos.")
                covered.update(section.criteria)
            if covered != active:
                raise ValueError("Todo critério ativo deve aparecer em algum papel.")
        return self


QUESTIONS: tuple[tuple[Criterion, str, str], ...] = (
    (Criterion.ORIGINALITY, "Originalidade", "O que é novo em relação ao estado da arte?"),
    (Criterion.SOUNDNESS, "Solidez", "Os métodos e as conclusões se sustentam?"),
    (Criterion.SUBSTANCE, "Substância", "Há experimentos, provas ou análise suficientes?"),
    (Criterion.CLARITY, "Clareza", "O texto é claro e bem organizado?"),
    (Criterion.MEANINGFUL_COMPARISON, "Comparação", "Compara com os trabalhos relevantes?"),
    (Criterion.IMPACT, "Impacto", "Qual a relevância para a área?"),
    (
        Criterion.REPLICABILITY,
        "Reprodutibilidade",
        "Dados, código e parâmetros permitem reproduzir?",
    ),
)
ROLE_CRITERIA: dict[SectionRole, tuple[Criterion, ...]] = {
    SectionRole.INTRODUCTION: (Criterion.ORIGINALITY, Criterion.IMPACT),
    SectionRole.RELATED_WORK: (Criterion.MEANINGFUL_COMPARISON, Criterion.ORIGINALITY),
    SectionRole.METHOD: (Criterion.SOUNDNESS, Criterion.REPLICABILITY),
    SectionRole.RESULTS: (Criterion.SUBSTANCE, Criterion.SOUNDNESS),
    SectionRole.DISCUSSION: (Criterion.SOUNDNESS, Criterion.IMPACT),
    SectionRole.CONCLUSION: (Criterion.IMPACT,),
    SectionRole.DEFINITIONS: (Criterion.SOUNDNESS,),
    SectionRole.THEOREMS: (Criterion.ORIGINALITY, Criterion.SUBSTANCE, Criterion.IMPACT),
    SectionRole.PROOFS: (Criterion.SOUNDNESS, Criterion.SUBSTANCE),
    SectionRole.SCOPE: (Criterion.ORIGINALITY, Criterion.IMPACT),
    SectionRole.SEARCH_PROTOCOL: (Criterion.SOUNDNESS, Criterion.REPLICABILITY),
    SectionRole.THEMATIC: (Criterion.SUBSTANCE, Criterion.MEANINGFUL_COMPARISON),
    SectionRole.SYNTHESIS: (Criterion.SOUNDNESS, Criterion.IMPACT, Criterion.MEANINGFUL_COMPARISON),
    SectionRole.CONTEXT: (Criterion.ORIGINALITY, Criterion.IMPACT),
    SectionRole.CASE_DESCRIPTION: (Criterion.SUBSTANCE, Criterion.REPLICABILITY),
    SectionRole.ANALYSIS: (Criterion.SOUNDNESS, Criterion.MEANINGFUL_COMPARISON),
    SectionRole.LESSONS: (Criterion.IMPACT, Criterion.ORIGINALITY),
}


def _paper_rules(paper_type: PaperType) -> PaperCriteria:
    active = tuple(
        key
        for key in Criterion
        if not (paper_type is PaperType.THEORETICAL and key is Criterion.REPLICABILITY)
    )
    return PaperCriteria(
        paper_type=paper_type,
        active=active,
        sections=tuple(
            SectionCriteria(
                role=role,
                criteria=(*ROLE_CRITERIA[role], Criterion.CLARITY),
            )
            for role in PAPER_ROLES[paper_type]
        ),
    )


# Padrões de desenvolvimento; pesos uniformes e escala 1–5 aguardam calibração no M3.
STANDARD = EvaluationConfig(
    method="standard",
    criteria=tuple(
        CriterionConfig(key=key, label=label, question=question)
        for key, label, question in QUESTIONS
    ),
    paper_types=tuple(_paper_rules(paper_type) for paper_type in PaperType),
)
METHODS: Mapping[str, EvaluationConfig] = MappingProxyType({STANDARD.method: STANDARD})


def get_method(name: str) -> EvaluationConfig:
    if name not in METHODS:
        raise CurationError("Método de avaliação não registrado.")
    return METHODS[name]
