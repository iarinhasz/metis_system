"""Auditoria somente de leitura: notas e relatórios não são editados no admin."""

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.http import HttpRequest

from projects.correction.evaluation.models import FinalReport, JudgeVerdict, ReviewRound

if TYPE_CHECKING:
    _ModelAdmin = admin.ModelAdmin[Any]
else:
    _ModelAdmin = admin.ModelAdmin


class ReadOnlyAdmin(_ModelAdmin):
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(ReviewRound)
class ReviewRoundAdmin(ReadOnlyAdmin):
    list_display = ("run", "evaluator_slot", "round_number", "mode", "ready")
    list_filter = ("mode", "evaluator_slot", "ready")
    list_select_related = ("run",)


@admin.register(JudgeVerdict)
class JudgeVerdictAdmin(ReadOnlyAdmin):
    list_display = ("round", "item_type", "item_key", "verdict", "source")
    list_filter = ("verdict", "source")
    list_select_related = ("round",)


@admin.register(FinalReport)
class FinalReportAdmin(ReadOnlyAdmin):
    list_display = ("run", "recommendation", "total_score", "agreement", "created_at")
    list_select_related = ("run",)
