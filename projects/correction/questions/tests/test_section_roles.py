"""As regras evitam chamadas pagas e os casos duvidosos ficam em other."""

import pytest

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.questions.section_roles import classify_role, rule_based_roles
from projects.correction.questions.tests.profiling_helpers import article


@pytest.mark.parametrize("title", ["Materiais e métodos", "Methods", "2. Approach"])
def test_method_titles(title: str) -> None:
    document = article()
    section = document.sections[0].model_copy(update={"title": title, "key": None})
    document = document.model_copy(update={"sections": (section,)})
    [assignment] = rule_based_roles(document, PaperType.EMPIRICAL)
    assert assignment.roles == (SectionRole.METHOD,) and not assignment.ambiguous


def test_combined_title_has_two_roles() -> None:
    document = article()
    section = document.sections[0].model_copy(update={"title": "Experimentos e resultados"})
    [assignment] = rule_based_roles(
        document.model_copy(update={"sections": (section,)}), PaperType.EMPIRICAL
    )
    assert assignment.roles == (SectionRole.METHOD, SectionRole.RESULTS)


@pytest.mark.parametrize(
    "answer",
    [
        {"roles": ["method"], "confidence": 0.9},
        {"roles": ["method"], "confidence": 0.2},
        {"roles": ["proofs"], "confidence": 0.9},
        {"roles": ["inventado"], "confidence": 0.9},
        {"roles": ["other", "method"], "confidence": 0.9},
    ],
)
def test_unknown_title_only_accepts_confident_roles_of_the_paper_type(
    answer: dict[str, object],
) -> None:
    document = article()
    section = document.sections[0].model_copy(update={"title": "Nossa proposta", "key": None})
    [assignment] = rule_based_roles(
        document.model_copy(update={"sections": (section,)}), PaperType.EMPIRICAL
    )
    assert assignment.ambiguous
    factory = FakeAgentFactory(scripts={"section_role_classifier": [answer]})
    result = classify_role(section, PaperType.EMPIRICAL, factory=factory, confidence_threshold=0.7)
    assert result.roles == (
        (SectionRole.METHOD,)
        if answer["confidence"] == 0.9 and answer["roles"] == ["method"]
        else (SectionRole.OTHER,)
    )
    assert not result.ambiguous


def test_theoretical_results_have_theorem_role() -> None:
    document = article()
    section = document.sections[0].model_copy(update={"title": "Resultados", "key": None})
    [assignment] = rule_based_roles(
        document.model_copy(update={"sections": (section,)}), PaperType.THEORETICAL
    )
    assert assignment.roles == (SectionRole.THEOREMS,)
