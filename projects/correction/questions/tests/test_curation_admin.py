"""Fluxos reais do admin, permissões e proteção da validação em POSTs forjados."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import FakeAgentFactory
from projects.correction.questions.admin import QuestionAdmin
from projects.correction.questions.curation import draft_question
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import FIELD

pytestmark = pytest.mark.django_db


@pytest.fixture
def node(profiling_taxonomy: TaxonomySnapshot) -> TaxonomyNode:
    return next(n for n in TaxonomyNode.for_version(profiling_taxonomy.version) if n.code == FIELD)


@pytest.fixture
def factory(monkeypatch: pytest.MonkeyPatch) -> FakeAgentFactory:
    fake = FakeAgentFactory()
    monkeypatch.setattr(
        "projects.correction.questions.curation.AgentFactory", lambda *a, **kw: fake
    )
    return fake


def action(client: Client, question: Question, name: str) -> Any:
    return client.post(
        reverse("admin:questions_question_changelist"),
        {
            "action": name,
            "_selected_action": [str(question.pk)],
            "index": "0",
        },
        follow=True,
    )


def edit_data(question: Question) -> dict[str, Any]:
    fields = RubricField.for_question(question)
    data: dict[str, Any] = {
        "name": question.name,
        "method": question.method,
        "taxonomy_node": str(question.taxonomy_node_id or ""),
        "revision": question.updated_at.isoformat(),
        "_save": "Salvar",
        "rubric_fields-TOTAL_FORMS": str(len(fields)),
        "rubric_fields-INITIAL_FORMS": str(len(fields)),
        "rubric_fields-MIN_NUM_FORMS": "0",
        "rubric_fields-MAX_NUM_FORMS": "1000",
    }
    if question.is_generic:
        data["is_generic"] = "on"
    for index, field in enumerate(fields):
        data.update(
            {
                f"rubric_fields-{index}-id": str(field.pk),
                f"rubric_fields-{index}-question": str(question.pk),
                f"rubric_fields-{index}-key": field.key,
                f"rubric_fields-{index}-label": field.label,
                f"rubric_fields-{index}-rubric_text": field.rubric_text,
                f"rubric_fields-{index}-order": str(field.order),
            }
        )
    return data


def test_draft_form_creates_editable_inactive_rubric(
    admin_client: Client,
    node: TaxonomyNode,
    factory: FakeAgentFactory,
) -> None:
    url = reverse("admin:questions_question_draft")
    assert admin_client.get(url).status_code == 200 and not factory.calls
    response = admin_client.post(url, {"method": "standard", "taxonomy_node": str(node.pk)})
    assert response.status_code == 302
    [question] = Question.for_curation()
    assert response["Location"] == reverse("admin:questions_question_change", args=[question.pk])
    assert not question.validated and not question.active
    page = admin_client.get(response["Location"])
    assert page.status_code == 200 and b"rubric_fields-0-rubric_text" in page.content


def test_admin_actions_validate_activate_and_deactivate(
    admin_client: Client, factory: FakeAgentFactory
) -> None:
    question = draft_question(method="standard")
    assert action(admin_client, question, "validate_selected").status_code == 200
    assert Question.get_by_id(question.pk).version == 2
    action(admin_client, question, "activate_selected")
    assert Question.get_by_id(question.pk).active
    action(admin_client, question, "deactivate_selected")
    assert not Question.get_by_id(question.pk).active


def test_drafting_action_does_not_edit_the_source_question(
    admin_client: Client, factory: FakeAgentFactory
) -> None:
    source = draft_question(method="standard")
    Question.validate_for_use(source.pk)
    Question.set_active(source.pk, True)
    action(admin_client, source, "draft_selected")
    assert len(Question.for_curation()) == 2
    assert Question.get_by_id(source.pk).active
    assert Question.get_by_id(source.pk).version == 2


@pytest.mark.parametrize("operation", ["edit", "delete"])
def test_inline_changes_remove_approval_and_ignore_forged_status(
    admin_client: Client,
    factory: FakeAgentFactory,
    operation: str,
) -> None:
    question = draft_question(method="standard")
    Question.validate_for_use(question.pk)
    question = Question.set_active(question.pk, True)
    data = edit_data(question)
    data.update({"validated": "on", "active": "on", "version": "999"})
    if operation == "edit":
        data["rubric_fields-0-rubric_text"] = "Novo texto, ainda sem revisão."
    else:
        data["rubric_fields-0-DELETE"] = "on"
    response = admin_client.post(
        reverse("admin:questions_question_change", args=[question.pk]), data
    )
    assert response.status_code == 302
    current = Question.get_by_id(question.pk)
    assert not current.validated and not current.active and current.version == 2
    assert len(RubricField.for_question(current)) == (7 if operation == "edit" else 6)


def test_invalid_inline_cannot_partially_update_question(
    admin_client: Client, factory: FakeAgentFactory
) -> None:
    question = draft_question(method="standard")
    Question.validate_for_use(question.pk)
    question = Question.set_active(question.pk, True)
    data = edit_data(question)
    data["name"] = "Não deve ser salvo"
    data["rubric_fields-0-rubric_text"] = ""
    response = admin_client.post(
        reverse("admin:questions_question_change", args=[question.pk]), data
    )
    assert response.status_code == 200
    current = Question.get_by_id(question.pk)
    assert current.name == question.name and current.active and current.validated


def test_stale_admin_post_does_not_overwrite_another_curator(
    admin_client: Client, factory: FakeAgentFactory
) -> None:
    question = draft_question(method="standard")
    stale = edit_data(question)
    changed = Question.get_by_id(question.pk)
    changed.name = "Outra pessoa já salvou"
    Question.save_curation(changed)
    stale["name"] = "Texto obsoleto"
    response = admin_client.post(
        reverse("admin:questions_question_change", args=[question.pk]), stale, follow=True
    )
    assert response.status_code == 200
    assert "mudou enquanto" in response.content.decode()
    assert Question.get_by_id(question.pk).name == changed.name


def test_missing_add_permission_blocks_drafter(
    admin_client: Client,
    factory: FakeAgentFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(QuestionAdmin, "has_add_permission", lambda *args: False)
    url = reverse("admin:questions_question_draft")
    assert admin_client.get(url).status_code == 403
    assert admin_client.post(url, {"method": "standard"}).status_code == 403
    assert not factory.calls


def test_missing_change_permission_blocks_validation(
    admin_client: Client,
    factory: FakeAgentFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = draft_question(method="standard")
    monkeypatch.setattr(QuestionAdmin, "has_change_permission", lambda *args: False)
    action(admin_client, question, "validate_selected")
    assert not Question.get_by_id(question.pk).validated
    assert (
        admin_client.post(
            reverse("admin:questions_question_change", args=[question.pk]), edit_data(question)
        ).status_code
        == 403
    )


def test_provider_error_is_shown_without_persisting_draft(
    admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeAgentFactory(scripts={"question_drafter": [LLMUnavailable("Provedor indisponível")]})
    monkeypatch.setattr(
        "projects.correction.questions.curation.AgentFactory", lambda *a, **kw: fake
    )
    response = admin_client.post(reverse("admin:questions_question_draft"), {"method": "standard"})
    assert response.status_code == 200
    assert "Provedor indisponível" in response.content.decode()
    assert Question.for_curation() == []


def test_anonymous_user_cannot_draft(client: Client) -> None:
    response = client.post(reverse("admin:questions_question_draft"), {"method": "standard"})
    assert response.status_code == 302 and "/admin/login/" in response["Location"]
