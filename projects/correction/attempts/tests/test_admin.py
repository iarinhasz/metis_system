"""Testes dos botões do gate e do reprocessamento na página do run, no admin."""

import pytest
from django.test import Client
from django.urls import reverse

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import LLMUnavailable
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.stages import (
    EvaluationStage,
    IntegrityStage,
    StageContext,
    StageOutcome,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.usefixtures("eager_celery")]


def change_url(run: Run) -> str:
    return reverse("admin:attempts_run_change", args=[run.pk])


def action_url(run: Run) -> str:
    return reverse("admin:attempts_run_action", args=[run.pk])


def high_risk(self: IntegrityStage, ctx: StageContext) -> StageOutcome:
    return StageOutcome(payload={"risk": "high"}, halt=True)


def llm_down(self: EvaluationStage, ctx: StageContext) -> StageOutcome:
    raise LLMUnavailable("429 do provedor")


def evaluated(self: EvaluationStage, ctx: StageContext) -> StageOutcome:
    return StageOutcome()


def test_gate_shows_decision_buttons_and_continue_reaches_done(
    admin_client: Client, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(IntegrityStage, "execute", high_risk)
    publish_stage(str(run.pk), Stage.EXTRACTION)

    page = admin_client.get(change_url(run)).content.decode()
    assert 'value="continue"' in page
    assert 'value="close"' in page
    assert 'value="recover"' not in page

    response = admin_client.post(action_url(run), {"action": "continue"})

    assert response.status_code == 302
    assert response["Location"] == change_url(run)
    assert Run.get_by_id(run.pk).status == RunStatus.DONE
    decision = next(e for e in RunEvent.for_run(run.pk) if e.to_status == "integrity_checked")
    assert decision.actor == "admin:admin"


def test_close_ends_the_run(
    admin_client: Client, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(IntegrityStage, "execute", high_risk)
    publish_stage(str(run.pk), Stage.EXTRACTION)

    admin_client.post(action_url(run), {"action": "close"})

    assert Run.get_by_id(run.pk).status == RunStatus.CLOSED_BY_REVIEWER


def test_failed_run_shows_reprocess_and_resumes(
    admin_client: Client, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "stage_max_retries", 1)
    monkeypatch.setattr(EvaluationStage, "execute", llm_down)
    publish_stage(str(run.pk), Stage.EXTRACTION)

    page = admin_client.get(change_url(run)).content.decode()
    assert 'value="recover"' in page
    assert 'value="continue"' not in page

    monkeypatch.setattr(EvaluationStage, "execute", evaluated)
    admin_client.post(action_url(run), {"action": "recover"})

    assert Run.get_by_id(run.pk).status == RunStatus.DONE


def test_running_run_shows_no_action_buttons(admin_client: Client, run: Run) -> None:
    page = admin_client.get(change_url(run)).content.decode()

    assert 'name="action"' not in page


def test_action_outside_gate_is_refused_with_a_message(admin_client: Client, run: Run) -> None:
    response = admin_client.post(action_url(run), {"action": "continue"}, follow=True)

    assert "O run não está aguardando revisão humana." in response.content.decode()
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED


def test_anonymous_user_cannot_act(client: Client, run: Run) -> None:
    response = client.post(action_url(run), {"action": "close"})

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
    assert Run.get_by_id(run.pk).status == RunStatus.RECEIVED


def test_action_url_only_accepts_post(admin_client: Client, run: Run) -> None:
    assert admin_client.get(action_url(run)).status_code == 405
