"""Gravação e consulta do uso dos modelos, sem guardar prompt nem resposta."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.agents.usage import LLMUsage
    from projects.correction.attempts.models import LLMCall


@dataclass(frozen=True)
class CostTotals:
    cost_usd: Decimal
    calls: int
    unpriced_calls: int
    failed_calls: int


@dataclass(frozen=True)
class CostGroup:
    label: str
    totals: CostTotals
    # Só grupos por run recebem o total histórico, independente dos filtros da lista.
    lifetime: CostTotals | None = None


@dataclass(frozen=True)
class CostSection:
    key: str
    title: str
    groups: tuple[CostGroup, ...]
    truncated: bool


@dataclass(frozen=True)
class CostReport:
    totals: CostTotals
    sections: tuple[CostSection, ...]


COST_GROUP_LIMIT = 100


def _aggregates() -> dict[str, Count | Sum]:
    return {
        "total_cost": Sum("cost_usd"),
        "calls": Count("pk"),
        "unpriced_calls": Count("pk", filter=Q(cost_usd__isnull=True)),
        "failed_calls": Count("pk", filter=Q(success=False)),
    }


def _totals(row: dict[str, Any]) -> CostTotals:
    return CostTotals(
        cost_usd=row["total_cost"] or Decimal(0),
        calls=row["calls"],
        unpriced_calls=row["unpriced_calls"],
        failed_calls=row["failed_calls"],
    )


def _groups(queryset: models.QuerySet[LLMCall], *fields: str) -> tuple[CostGroup, ...]:
    # Limite só de exibição; o resumo sempre soma todas as chamadas filtradas.
    rows = (
        queryset.order_by()
        .values(*fields)
        .annotate(**_aggregates())
        .order_by(*fields)[: COST_GROUP_LIMIT + 1]
    )
    return tuple(
        CostGroup(label=" / ".join(str(row[field]) for field in fields), totals=_totals(row))
        for row in rows
    )


class LLMCallManagement:
    """Herdado por `LLMCall`; cada execução, inclusive um retry, cria uma linha própria."""

    objects: ClassVar[models.Manager[LLMCall]]

    @classmethod
    def record_usage(cls, call: LLMUsage) -> LLMCall:
        return cls.objects.create(
            run_id=call.run_id,
            stage=call.stage,
            role=call.role,
            agent=call.agent,
            provider=call.provider,
            model=call.model_id,
            prompt_version=call.prompt_version,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            cached_tokens=call.cached_tokens,
            cache_write_tokens=call.cache_write_tokens,
            reasoning_tokens=call.reasoning_tokens,
            cost_usd=call.cost_usd,
            latency_ms=call.latency_ms,
            success=call.success,
            error=call.error or "",
        )

    @classmethod
    def for_run(cls, run_id: Any) -> list[LLMCall]:
        return list(cls.objects.filter(run_id=run_id).order_by("created_at", "id"))

    @classmethod
    def cost_report(
        cls, queryset: models.QuerySet[LLMCall] | None = None, *, run_id: Any = None
    ) -> CostReport:
        """Soma custos históricos, inclusive falhas, sem recalcular tarifas nem arredondar."""
        calls = queryset if queryset is not None else cls.objects.all()
        if run_id is not None:
            calls = calls.filter(run_id=run_id)
        totals = _totals(calls.aggregate(**_aggregates()))
        sections: list[CostSection] = []
        if run_id is None:
            runs = _groups(calls, "run_id")
            # Uma única consulta para todos os runs exibidos, sem N+1. Filtros de período,
            # papel ou modelo nunca escondem que o run já passou do orçamento.
            lifetime = {
                str(row["run_id"]): _totals(row)
                for row in cls.objects.filter(run_id__in=[group.label for group in runs])
                .order_by()
                .values("run_id")
                .annotate(**_aggregates())
            }
            runs = tuple(replace(group, lifetime=lifetime[group.label]) for group in runs)
            sections.append(
                CostSection("run", "Por run", runs[:COST_GROUP_LIMIT], len(runs) > COST_GROUP_LIMIT)
            )
        for key, title, fields in (
            ("stage", "Por estágio", ("stage",)),
            ("role", "Por papel", ("role",)),
            ("model", "Por provedor e modelo", ("provider", "model")),
            ("day", "Por dia", ("cost_day",)),
        ):
            source = (
                calls.annotate(
                    cost_day=TruncDate("created_at", tzinfo=timezone.get_current_timezone())
                )
                if key == "day"
                else calls
            )
            groups = _groups(source, *fields)
            sections.append(
                CostSection(key, title, groups[:COST_GROUP_LIMIT], len(groups) > COST_GROUP_LIMIT)
            )
        return CostReport(totals=totals, sections=tuple(sections))
