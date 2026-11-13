"""Custos históricos no admin, com PostgreSQL real e sem chamadas a provedores."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from projects.correction.agents.specs import Provider, Role
from projects.correction.agents.usage import LLMUsage
from projects.correction.attempts.costs import budget_status, usd
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import Stage
from projects.correction.metis.config import settings
from projects.correction.queries.attempts.llm_call import CostTotals

pytestmark = pytest.mark.django_db


def usage(
    run: Run,
    cost: str | None,
    *,
    stage: Stage = Stage.EXTRACTION,
    role: Role = Role.VISION,
    agent: str = "describer",
    provider: Provider = Provider.GOOGLE,
    model_id: str = "model-one",
    success: bool = True,
) -> LLMUsage:
    return LLMUsage(
        run_id=str(run.pk),
        stage=stage,
        role=role,
        agent=agent,
        provider=provider,
        model_id=model_id,
        prompt_version="v1",
        input_tokens=10,
        output_tokens=5,
        cached_tokens=0,
        latency_ms=12,
        success=success,
        cost_usd=Decimal(cost) if cost is not None else None,
    )


def test_totals_match_all_calls_and_keep_runs_stages_roles_and_providers_separate(run: Run) -> None:
    other = Run.create(attempt=run.attempt)
    LLMCall.record_usage(usage(run, "0.123456789012"))
    LLMCall.record_usage(usage(run, "0.000000000001", success=False))
    LLMCall.record_usage(usage(run, None, stage=Stage.PROFILING, role=Role.FAST))
    LLMCall.record_usage(usage(other, "0.2", provider=Provider.OPENAI))

    report = LLMCall.cost_report()
    assert report.totals == CostTotals(Decimal("0.323456789013"), 4, 1, 1)
    sections = {section.key: section for section in report.sections}
    by_run = {group.label: group for group in sections["run"].groups}
    assert by_run[str(run.pk)].totals == CostTotals(Decimal("0.123456789013"), 3, 1, 1)
    assert by_run[str(other.pk)].totals == CostTotals(Decimal("0.2"), 1, 0, 0)
    for section in sections.values():
        assert sum(group.totals.cost_usd for group in section.groups) == report.totals.cost_usd
        assert sum(group.totals.calls for group in section.groups) == report.totals.calls
    assert {group.label for group in sections["model"].groups} == {
        "google / model-one",
        "openai / model-one",
    }
    assert {group.label for group in sections["stage"].groups} == {"extraction", "profiling"}
    assert {group.label for group in sections["role"].groups} == {"vision", "fast"}


def test_run_panel_is_isolated_and_warns_without_mutating_the_run(
    run: Run, admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = Run.create(attempt=run.attempt)
    LLMCall.record_usage(usage(run, "0.8"))
    LLMCall.record_usage(usage(run, "0.3", success=False))
    LLMCall.record_usage(usage(other, "9"))
    monkeypatch.setattr(settings, "llm_run_budget_usd", Decimal("1"))
    previous_status = run.status

    response = admin_client.get(reverse("admin:attempts_run_change", args=[run.pk]))

    assert response.status_code == 200
    panel = response.context["cost_panel"]
    assert panel["totals"]["cost"] == "USD 1.10"
    assert panel["totals"]["calls"] == 2
    assert panel["totals"]["failed_calls"] == 1
    assert panel["totals"]["over_budget"]
    assert "Orçamento excedido" in response.content.decode()
    assert 'role="alert"' in response.content.decode()
    assert Run.get_by_id(run.pk).status == previous_status


def test_filters_search_and_pagination_scope_sums_but_not_run_budget(
    run: Run, admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = Run.create(attempt=run.attempt)
    LLMCall.record_usage(usage(run, "0.4", stage=Stage.PROFILING, agent="profiler"))
    LLMCall.record_usage(usage(run, "0.7", stage=Stage.EXTRACTION, agent="profiler"))
    LLMCall.record_usage(usage(other, "8", stage=Stage.PROFILING, agent="other-agent"))
    monkeypatch.setattr(settings, "llm_run_budget_usd", Decimal("1"))
    from projects.correction.attempts.admin import LLMCallAdmin

    monkeypatch.setattr(LLMCallAdmin, "list_per_page", 1)
    url = reverse("admin:attempts_llmcall_changelist")

    searched = admin_client.get(url, {"q": "profiler", "p": "2"})
    assert searched.status_code == 200
    assert len(searched.context["cl"].result_list) == 1
    assert searched.context["cost_panel"]["totals"]["cost"] == "USD 1.10"
    assert searched.context["cost_panel"]["totals"]["calls"] == 2

    filtered = admin_client.get(url, {"q": "profiler", "stage__exact": Stage.PROFILING})
    assert filtered.status_code == 200
    panel = filtered.context["cost_panel"]
    assert panel["totals"]["cost"] == "USD 0.40"
    [group] = next(section["groups"] for section in panel["sections"] if section["key"] == "run")
    assert group["lifetime"]["cost"] == "USD 1.10"
    assert group["lifetime"]["over_budget"]
    assert "Orçamento excedido" in filtered.content.decode()


def test_period_filter_and_daily_groups_use_local_dates(
    run: Run, admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Congela só o relógio usado pelo default de created_at; as gravações e consultas são reais.
    field = LLMCall._meta.get_field("created_at")
    for instant, cost in (
        (datetime(2026, 11, 12, 2, 59, tzinfo=UTC), "0.6"),
        (datetime(2026, 11, 12, 3, 0, tzinfo=UTC), "0.2"),
        (datetime(2026, 11, 13, 3, 0, tzinfo=UTC), "0.8"),
    ):
        with monkeypatch.context() as clock:
            clock.setattr(field, "_get_default", lambda instant=instant: instant)
            LLMCall.record_usage(usage(run, cost))
    monkeypatch.setattr(settings, "llm_run_budget_usd", Decimal("1"))

    with timezone.override("America/Recife"):
        response = admin_client.get(
            reverse("admin:attempts_llmcall_changelist"),
            {"created_at__year": 2026, "created_at__month": 11, "created_at__day": 12},
        )
    assert response.status_code == 200
    panel = response.context["cost_panel"]
    assert panel["totals"]["cost"] == "USD 0.20"
    [day] = next(section["groups"] for section in panel["sections"] if section["key"] == "day")
    assert day["label"] == "2026-11-12"
    [group] = next(section["groups"] for section in panel["sections"] if section["key"] == "run")
    assert group["lifetime"]["cost"] == "USD 1.60"
    assert group["lifetime"]["over_budget"]


def test_empty_unknown_and_zero_costs_have_distinct_meanings(
    run: Run, admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_run_budget_usd", Decimal("1"))
    assert LLMCall.cost_report().totals == CostTotals(Decimal(0), 0, 0, 0)
    LLMCall.record_usage(usage(run, None))
    response = admin_client.get(reverse("admin:attempts_run_change", args=[run.pk]))
    assert "Total parcial" in response.content.decode()
    assert "Indeterminado: há chamadas sem preço" in response.content.decode()
    assert "Dentro do orçamento" not in response.content.decode()
    assert budget_status(CostTotals(Decimal(0), 1, 0, 0), Decimal(1)) == "Dentro do orçamento"
    assert budget_status(CostTotals(Decimal(1), 1, 0, 0), Decimal(1)) == "Dentro do orçamento"
    assert budget_status(CostTotals(Decimal(2), 2, 1, 0), Decimal(1)) == "Orçamento excedido"
    assert budget_status(CostTotals(Decimal(2), 2, 0, 0), None) == "Orçamento não configurado"
    assert usd(Decimal("0.000000000001")) == "USD 0.000000000001"


def test_run_view_permission_does_not_grant_cost_access(
    run: Run, admin_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    LLMCall.record_usage(usage(run, "1.234"))
    monkeypatch.setattr(User, "has_perm", lambda self, perm, obj=None: perm == "attempts.view_run")

    response = admin_client.get(reverse("admin:attempts_run_change", args=[run.pk]))
    assert response.status_code == 200
    assert "cost_panel" not in response.context
    assert "Custos de LLM" not in response.content.decode()
    assert admin_client.get(reverse("admin:attempts_llmcall_changelist")).status_code == 403


def test_cost_dashboard_is_private_and_call_records_stay_read_only(
    run: Run, admin_client: Client, client: Client
) -> None:
    call = LLMCall.record_usage(usage(run, "0.1"))
    assert client.get(reverse("admin:attempts_llmcall_changelist")).status_code == 302
    assert (
        admin_client.post(
            reverse("admin:attempts_llmcall_change", args=[call.pk]), {"cost_usd": "0"}
        ).status_code
        == 403
    )
    assert LLMCall.for_run(run.pk)[0].cost_usd == Decimal("0.1")


def test_group_limit_is_explicit_and_does_not_limit_totals(run: Run) -> None:
    for index in range(102):
        LLMCall.record_usage(usage(run, "0.01", model_id=f"model-{index:03}"))
    report = LLMCall.cost_report(run_id=run.pk)
    section = next(section for section in report.sections if section.key == "model")
    assert section.truncated and len(section.groups) == 100
    assert report.totals == CostTotals(Decimal("1.02"), 102, 0, 0)
