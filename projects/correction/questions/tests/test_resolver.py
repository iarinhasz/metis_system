"""Todos os degraus do fallback, versão, método, limiar e snapshot independente."""

import json
from copy import deepcopy
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.profile import ArticleProfile, ResolutionScope
from projects.correction.questions.profiler import profile_article
from projects.correction.questions.resolver import resolve_question
from projects.correction.questions.taxonomy import TaxonomyLevel, TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import (
    OTHER_TOPIC,
    article,
    field_answer,
    topic_answer,
)
from projects.correction.scholarly.openalex import OpenAlexTopic

pytestmark = pytest.mark.django_db


@pytest.fixture
def profile(profiling_taxonomy: TaxonomySnapshot) -> ArticleProfile:
    factory = FakeAgentFactory(
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [topic_answer()],
        }
    )
    return profile_article(article(), factory=factory, taxonomy_version=profiling_taxonomy.version)


@pytest.mark.parametrize(
    "level", [TaxonomyLevel.TOPIC, TaxonomyLevel.SUBFIELD, TaxonomyLevel.FIELD, None]
)
def test_every_fallback_level_and_its_path(
    profile: ArticleProfile, level: TaxonomyLevel | None
) -> None:
    nodes = {
        node.level: node
        for node in TaxonomyNode.path_for_topic(
            profile.taxonomy_version, profile.area_path[-1].code
        )
    }
    selected = Question.create(
        name="Perfil da área",
        method="standard",
        taxonomy_node=nodes[level] if level else None,
        is_generic=level is None,
        validated=True,
    )
    if level is not None:
        Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    result = resolve_question(profile, method="standard")
    assert result.question.id == selected.pk and not result.uncertain
    order = [
        ResolutionScope.TOPIC,
        ResolutionScope.SUBFIELD,
        ResolutionScope.FIELD,
        ResolutionScope.GENERIC,
    ]
    last = ResolutionScope(level.value) if level else ResolutionScope.GENERIC
    assert [hop.scope for hop in result.resolution_path] == order[: order.index(last) + 1]
    assert [hop.matched for hop in result.resolution_path] == [False] * (
        len(result.resolution_path) - 1
    ) + [True]


def test_nearest_active_validated_question_wins(profile: ArticleProfile) -> None:
    nodes = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)
    questions = [
        Question.create(name=node.name, method="standard", taxonomy_node=node, validated=True)
        for node in nodes[1:]
    ]
    result = resolve_question(profile, method="standard")
    assert result.question.id == questions[-1].pk
    assert len(result.resolution_path) == 1


@pytest.mark.parametrize("validated,active", [(False, True), (True, False), (False, False)])
def test_drafts_and_inactive_questions_are_skipped(
    profile: ArticleProfile, validated: bool, active: bool
) -> None:
    node = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)[-1]
    Question.create(
        name="Ignorada", method="standard", taxonomy_node=node, validated=validated, active=active
    )
    generic = Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    assert resolve_question(profile, method="standard").question.id == generic.pk


def test_wrong_method_and_unrelated_topic_do_not_match(profile: ArticleProfile) -> None:
    nodes = TaxonomyNode.for_version(profile.taxonomy_version)
    topic = next(node for node in nodes if node.code == OTHER_TOPIC)
    Question.create(name="Outro tópico", method="standard", taxonomy_node=topic, validated=True)
    Question.create(name="Outro método", method="different", is_generic=True, validated=True)
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")


def test_question_from_another_version_does_not_match(
    profile: ArticleProfile, recorded_topics: list[dict[str, Any]]
) -> None:
    changed = deepcopy(recorded_topics)
    changed[0]["display_name"] += " atualizado"
    snapshot = TaxonomySnapshot.from_topics(
        tuple(TypeAdapter(list[OpenAlexTopic]).validate_python(changed))
    )
    TaxonomyNode.import_snapshot(snapshot)
    topic = TaxonomyNode.path_for_topic(snapshot.version, profile.area_path[-1].code)[-1]
    Question.create(name="Outra versão", method="standard", taxonomy_node=topic, validated=True)
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")


def test_low_confidence_goes_directly_to_generic_and_sets_flag(profile: ArticleProfile) -> None:
    topic = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)[-1]
    Question.create(name="Área", method="standard", taxonomy_node=topic, validated=True)
    generic = Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    uncertain = profile.model_copy(update={"confidence": 0.2, "topic_confidence": 0.2})
    result = resolve_question(uncertain, method="standard")
    assert result.uncertain and result.question.id == generic.pk
    assert [hop.scope for hop in result.resolution_path] == [ResolutionScope.GENERIC]


def test_confidence_at_threshold_can_use_the_topic(profile: ArticleProfile) -> None:
    topic = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)[-1]
    selected = Question.create(name="Área", method="standard", taxonomy_node=topic, validated=True)
    result = resolve_question(profile, method="standard", confidence_threshold=profile.confidence)
    assert result.question.id == selected.pk and not result.uncertain


@pytest.mark.parametrize("low", [True, False])
def test_no_available_question_raises_setup_required(profile: ArticleProfile, low: bool) -> None:
    if low:
        profile = profile.model_copy(update={"confidence": 0.1, "topic_confidence": 0.1})
    with pytest.raises(SetupRequired) as raised:
        resolve_question(profile, method="standard")
    assert raised.value.failure_status == "waiting_setup"


def test_domain_question_is_not_a_fallback(profile: ArticleProfile) -> None:
    domain = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)[0]
    Question.create(name="Domain", method="standard", taxonomy_node=domain, validated=True)
    with pytest.raises(SetupRequired):
        resolve_question(profile, method="standard")


def test_snapshot_keeps_rubric_order_newlines_and_json_fields(profile: ArticleProfile) -> None:
    generic = Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    text = "Contexto do domínio.\n\n- Item A\n- Item B\n"
    RubricField.create(
        question=generic, key="second", label="Segundo", rubric_text="Outro.", order=2
    )
    RubricField.create(question=generic, key="first", label="Primeiro", rubric_text=text, order=1)
    result = resolve_question(profile, method="standard")
    snapshot = result.question
    assert snapshot.version == 1 and snapshot.name == generic.name
    assert [field.key for field in snapshot.rubric_fields] == ["first", "second"]
    assert snapshot.rubric_fields[0].rubric_text == text
    generic.name = "Nome alterado em memória"
    assert snapshot.name == "Genérica"
    with pytest.raises(ValidationError):
        snapshot.__setattr__("name", "Tentativa de edição")
    payload = result.model_dump(mode="json")
    assert payload["question"]["id"] == str(generic.pk)
    assert json.loads(result.model_dump_json()) == payload


def test_resolver_has_bounded_queries_even_with_many_rubric_fields(
    profile: ArticleProfile, django_assert_num_queries: Any
) -> None:
    generic = Question.create(name="Genérica", method="standard", is_generic=True, validated=True)
    for index in range(12):
        RubricField.create(
            question=generic, key=f"field-{index}", label="Campo", rubric_text="Texto.", order=index
        )
    with django_assert_num_queries(3):
        result = resolve_question(profile, method="standard")
    assert len(result.question.rubric_fields) == 12


def test_changed_profile_path_is_rejected(profile: ArticleProfile) -> None:
    wrong = profile.model_copy(update={"taxonomy_version": "outra"})
    with pytest.raises(SetupRequired):
        resolve_question(wrong, method="standard")
