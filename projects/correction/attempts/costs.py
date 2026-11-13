"""Apresentação dos custos históricos e do orçamento de alerta no admin."""

from decimal import Decimal
from typing import Any

from django.urls import reverse
from django.utils import timezone

from projects.correction.queries.attempts.llm_call import CostReport, CostTotals


def usd(value: Decimal) -> str:
    """Preserva até as 12 casas registradas, sem esconder consumos menores que um centavo."""
    whole, _, fraction = format(value, ".12f").partition(".")
    return f"USD {whole}.{fraction.rstrip('0').ljust(2, '0')}"


def budget_status(totals: CostTotals, budget: Decimal | None) -> str:
    if budget is None:
        return "Orçamento não configurado"
    if totals.cost_usd > budget:
        return "Orçamento excedido"
    if totals.unpriced_calls:
        return "Indeterminado: há chamadas sem preço"
    return "Dentro do orçamento"


def cost_panel(report: CostReport, budget: Decimal | None, *, single_run: bool) -> dict[str, Any]:
    def summary(totals: CostTotals) -> dict[str, Any]:
        return {
            "cost": usd(totals.cost_usd),
            "calls": totals.calls,
            "failed_calls": totals.failed_calls,
            "unpriced_calls": totals.unpriced_calls,
            "budget_status": budget_status(totals, budget),
            "over_budget": budget is not None and totals.cost_usd > budget,
        }

    sections = []
    for section in report.sections:
        groups = []
        for group in section.groups:
            groups.append(
                {
                    "label": group.label,
                    "totals": summary(group.totals),
                    "lifetime": summary(group.lifetime) if group.lifetime else None,
                    "url": reverse("admin:attempts_run_change", args=[group.label])
                    if section.key == "run"
                    else None,
                }
            )
        sections.append(
            {
                "key": section.key,
                "title": section.title,
                "groups": groups,
                "truncated": section.truncated,
            }
        )
    return {
        "totals": summary(report.totals),
        "sections": sections,
        "budget": usd(budget) if budget is not None else None,
        "single_run": single_run,
        "timezone": timezone.get_current_timezone_name(),
    }
