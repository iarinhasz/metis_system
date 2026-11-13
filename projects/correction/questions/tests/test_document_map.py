"""O mapa preserva o texto extraído e omite interpretações das figuras."""

from projects.correction.agents.schemas.profiling import PaperType
from projects.correction.extractor.article import Figure
from projects.correction.questions.document_map import build_document_map
from projects.correction.questions.section_roles import rule_based_roles
from projects.correction.questions.tests.profiling_helpers import article


def test_document_map_snapshot() -> None:
    document = article()
    section = document.sections[0].model_copy(
        update={
            "id": "sec_2",
            "title": "Métodos",
            "key": None,
            "text": "Primeira frase. Segunda frase.",
        }
    )
    document = document.model_copy(
        update={
            "sections": (*document.sections, section),
            "figures": (
                Figure(
                    id="fig_1",
                    kind="table",
                    label="Tabela 1",
                    number="1",
                    page=2,
                    caption="Medições do experimento.",
                    fidelity=1,
                ),
            ),
        }
    )
    output = build_document_map(document, rule_based_roles(document, PaperType.EMPIRICAL))
    assert output.model_dump(mode="json") == {
        "title": document.title,
        "abstract": document.sections[0].text,
        "sections": [
            {
                "id": "sec_1",
                "title": "Resumo",
                "roles": ["other"],
                "first_sentence": document.sections[0].text,
            },
            {
                "id": "sec_2",
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
