"""O mapa preserva o texto extraído e omite interpretações das figuras."""

from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.extractor.contract import DocumentFigure
from projects.correction.questions.document_map import build_document_map
from projects.correction.questions.section_roles import rule_based_roles
from projects.correction.questions.tests.profiling_helpers import document


def test_document_map_snapshot() -> None:
    manuscript = document()
    section = manuscript.sections[0].model_copy(
        update={
            "id": "sec_3",
            "title": "Métodos",
            "key": None,
            "text": "Primeira frase. Segunda frase.",
        }
    )
    manuscript = manuscript.model_copy(
        update={
            "sections": (*manuscript.sections, section),
            "figures": (
                DocumentFigure(
                    id="fig_1",
                    kind="table",
                    label="Tabela 1",
                    page=2,
                    caption="Medições do experimento.",
                ),
            ),
        }
    )
    output = build_document_map(manuscript, rule_based_roles(manuscript, PaperType.EMPIRICAL))
    assert output.model_dump(mode="json") == {
        "title": manuscript.title,
        "abstract": manuscript.abstract,
        "sections": [
            {
                "id": "sec_2",
                "title": "Introdução",
                "roles": ["introduction"],
                "first_sentence": "Texto do corpo para os testes.",
            },
            {
                "id": "sec_3",
                "title": "Métodos",
                "roles": ["method"],
                "first_sentence": "Primeira frase.",
            },
        ],
        "figures": [
            {
                "id": "fig_1",
                "kind": "table",
                "label": "Tabela 1",
                "page": 2,
                "caption": "Medições do experimento.",
            }
        ],
    }
