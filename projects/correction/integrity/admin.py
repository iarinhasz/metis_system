"""Admin do E3: o relatório de integridade de cada run, só leitura, com os achados."""

from django.contrib import admin
from django.http import HttpRequest

from projects.correction.attempts.admin import ReadOnlyModelAdmin
from projects.correction.integrity.models import IntegrityFinding, IntegrityReport


class IntegrityFindingInline(admin.TabularInline):  # type: ignore[type-arg]
    model = IntegrityFinding
    fields = ("position", "severity", "kind", "message", "evidence")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False


@admin.register(IntegrityReport)
class IntegrityReportAdmin(ReadOnlyModelAdmin):
    list_display = ("run", "risk", "rules_version", "created_at")
    list_filter = ("risk",)
    inlines = (IntegrityFindingInline,)
