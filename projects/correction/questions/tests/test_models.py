"""As Questions e rubricas preservam o contexto e recusam estados ambíguos."""

from pathlib import Path

import pytest
from django.core.exceptions import ValidationError

from projects.correction.questions.management.commands.load_taxonomy import read_topics
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomyLevel, TaxonomySnapshot

pytestmark = pytest.mark.django_db


@pytest.fixture
def node(taxonomy_file: Path) -> TaxonomyNode:
    snapshot = TaxonomySnapshot.from_topics(read_topics(taxonomy_file))
    TaxonomyNode.import_snapshot(snapshot)
    return next(
        n for n in TaxonomyNode.for_version(snapshot.version) if n.level == TaxonomyLevel.FIELD
    )


def test_generic_and_area_questions_start_as_drafts(node: TaxonomyNode) -> None:
    generic = Question.create(name="Genérica", method="standard", is_generic=True)
    area = Question.create(name="Física", method="standard", taxonomy_node=node)
    assert generic.taxonomy_node is None and generic.is_generic
    assert area.taxonomy_node == node and not area.is_generic
    assert not area.validated and area.active and area.version == 1
    assert generic.pk.version == area.pk.version == 7


def test_generic_flag_and_node_must_agree(node: TaxonomyNode) -> None:
    with pytest.raises(ValidationError):
        Question.create(name="Inválida", method="standard", is_generic=True, taxonomy_node=node)
    with pytest.raises(ValidationError):
        Question.create(name="Inválida", method="standard")


def test_only_one_active_validated_question_per_scope_and_method(node: TaxonomyNode) -> None:
    for scope_node, generic in ((None, True), (node, False)):
        Question.create(
            name="Validada",
            method="standard",
            validated=True,
            taxonomy_node=scope_node,
            is_generic=generic,
        )
        Question.create(
            name="Rascunho", method="standard", taxonomy_node=scope_node, is_generic=generic
        )
        with pytest.raises(ValidationError):
            Question.create(
                name="Ambígua",
                method="standard",
                validated=True,
                taxonomy_node=scope_node,
                is_generic=generic,
            )


def test_version_zero_is_invalid() -> None:
    question = Question(name="Genérica", method="standard", is_generic=True, version=0)
    with pytest.raises(ValidationError):
        question.full_clean()


def test_rubric_fields_preserve_lines_and_have_unique_keys(node: TaxonomyNode) -> None:
    question = Question.create(name="Área", method="standard", taxonomy_node=node)
    text = "Primeira linha.\n\n- Checklist A\n- Checklist B\n"
    second = RubricField.create(
        question=question, key="noise", label="Ruído", rubric_text=text, order=2
    )
    first = RubricField.create(
        question=question, key="design", label="Desenho", rubric_text="Contexto.", order=1
    )
    fields = RubricField.for_question(question)
    assert [field.pk for field in fields] == [first.pk, second.pk]
    assert fields[1].rubric_text == text
    with pytest.raises(ValidationError):
        RubricField.create(question=question, key="noise", label="Outro", rubric_text="Texto.")


def test_node_validation_rejects_wrong_parent_level_and_version(node: TaxonomyNode) -> None:
    invalid = TaxonomyNode(
        code="https://openalex.org/T10001",
        level=TaxonomyLevel.TOPIC,
        name="Topic",
        parent=node,
        taxonomy_version=node.taxonomy_version,
    )
    with pytest.raises(ValidationError, match="nível anterior"):
        invalid.clean()
    invalid.level = TaxonomyLevel.SUBFIELD
    invalid.code = "https://openalex.org/subfields/3107"
    invalid.taxonomy_version = "outra-versão"
    with pytest.raises(ValidationError, match="mesma versão"):
        invalid.clean()
