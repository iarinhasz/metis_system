"""Bootstrap atômico e repetível, com o mesmo fluxo humano de aprovação do admin."""

import json
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.questions.management.commands.load_taxonomy import read_catalog
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.seeds import (
    INITIAL_QUESTIONS,
    prepare_initial_questions,
    seed_initial_questions,
)
from projects.correction.questions.taxonomy import TaxonomySnapshot

pytestmark = pytest.mark.django_db


@pytest.fixture
def initial_taxonomy() -> TaxonomySnapshot:
    path = Path(__file__).parent / "data" / "initial_taxonomy.json"
    snapshot = TaxonomySnapshot.from_catalog(read_catalog(path))
    TaxonomyNode.import_snapshot(snapshot)
    return snapshot


def test_dry_run_and_missing_taxonomy_do_not_create_questions(
    initial_taxonomy: TaxonomySnapshot,
) -> None:
    output = StringIO()
    call_command("seed_questions", taxonomy_version=initial_taxonomy.version, stdout=output)
    assert "Dry-run" in output.getvalue()
    assert Question.for_curation() == []
    with pytest.raises(CommandError, match="inválido"):
        call_command("seed_questions", execute=True, taxonomy_version="missing", stdout=StringIO())
    assert Question.for_curation() == []


def test_loads_four_drafts_with_seven_criteria_then_preserves_human_edits(
    initial_taxonomy: TaxonomySnapshot,
) -> None:
    call_command(
        "seed_questions", taxonomy_version=initial_taxonomy.version, execute=True, stdout=StringIO()
    )
    before = Question.for_curation()
    assert len(before) == 4 and sum(question.is_generic for question in before) == 1
    for question in before:
        assert not question.validated and not question.active and question.version == 1
        assert {field.key for field in RubricField.for_question(question)} == set(Criterion)
    generic = next(question for question in before if question.is_generic)
    generic.name = "Curadoria humana"
    Question.save_curation(generic)
    [field, *_] = RubricField.for_question(generic)
    field.rubric_text = "Texto revisado pelo curador."
    RubricField.save_curation(field)
    Question.validate_for_use(generic.pk)
    Question.set_active(generic.pk, True)
    updated = Question.get_by_id(generic.pk)
    timestamps = {q.pk: q.updated_at for q in Question.for_curation()}
    assert all(not created for _, created in seed_initial_questions(initial_taxonomy.version))
    assert {q.pk: q.updated_at for q in Question.for_curation()} == timestamps
    actual = Question.get_by_id(generic.pk)
    assert actual.name == "Curadoria humana" and actual.version == updated.version
    assert actual.validated and actual.active
    assert RubricField.for_question(actual)[0].rubric_text == "Texto revisado pelo curador."


def test_unknown_catalog_scope_aborts_before_the_generic_is_created(
    initial_taxonomy: TaxonomySnapshot, tmp_path: Path
) -> None:
    data = json.loads(INITIAL_QUESTIONS.read_text(encoding="utf-8"))
    data["questions"][-1]["field_code"] = "https://openalex.org/fields/999"
    path = tmp_path / "seeds.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="fields"):
        seed_initial_questions(initial_taxonomy.version, path=path)
    assert Question.for_curation() == []


def test_database_validation_failure_rolls_back_earlier_drafts(
    initial_taxonomy: TaxonomySnapshot,
) -> None:
    catalog, items = prepare_initial_questions(initial_taxonomy.version)
    broken = items[1][0].model_copy(update={"name": "x" * 256})
    with pytest.raises(ValidationError):
        Question.store_initial_drafts((items[0], (broken, items[1][1])), method=catalog.method)
    assert Question.for_curation() == []


@pytest.mark.django_db(transaction=True)
def test_concurrent_loads_do_not_duplicate_empty_generic_scope(
    initial_taxonomy: TaxonomySnapshot,
) -> None:
    def load(_: int) -> tuple[Any, ...]:
        close_old_connections()
        try:
            return tuple(
                question.pk for question, _ in seed_initial_questions(initial_taxonomy.version)
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.map(load, range(2))
    assert first == second and len(Question.for_curation()) == 4
