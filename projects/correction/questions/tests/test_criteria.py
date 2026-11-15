"""O método importa completo e recusa escalas, pesos e coberturas incoerentes."""

import pytest
from pydantic import ValidationError

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.questions.criteria import STANDARD, EvaluationConfig, get_method


def test_standard_covers_active_criteria_and_roles() -> None:
    assert get_method("standard") is STANDARD
    assert {item.key for item in STANDARD.criteria} == set(Criterion)
    for paper in STANDARD.paper_types:
        assert {key for section in paper.sections for key in section.criteria} == set(paper.active)
        assert all(section.criteria for section in paper.sections)
        assert (Criterion.REPLICABILITY in paper.active) == (
            paper.paper_type != PaperType.THEORETICAL
        )
    with pytest.raises(ValidationError):
        STANDARD.__setattr__("method", "alterado")


@pytest.mark.parametrize("kind", ["grade", "weight", "nan", "missing_role", "missing_criterion"])
def test_invalid_configuration_is_rejected(kind: str) -> None:
    data = STANDARD.model_dump(mode="json")
    if kind == "grade":
        data["criteria"][0]["grades"] = [6]
    elif kind in {"weight", "nan"}:
        data["criteria"][0]["weight"] = -1 if kind == "weight" else float("nan")
    elif kind == "missing_role":
        data["paper_types"][0]["sections"].pop()
    else:
        data["criteria"].pop()
    with pytest.raises(ValidationError):
        EvaluationConfig.model_validate(data)


def test_unknown_method_is_refused() -> None:
    with pytest.raises(ValueError, match="não registrado"):
        get_method("inventado")
