"""Admin somente leitura para os registros de auditoria do domínio."""

from django.contrib import admin
from django.db.models import Model
from django.http import HttpRequest

from projects.correction.attempts.models import Article, Attempt, Run, RunEvent


class ReadOnlyModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Impede alterações manuais que contornariam os Managements de `queries/`."""

    def get_readonly_fields(
        self, request: HttpRequest, obj: Model | None = None
    ) -> tuple[str, ...]:
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return obj is not None and super().has_view_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False


@admin.register(Article)
class ArticleAdmin(ReadOnlyModelAdmin):
    list_display = ("external_id", "title", "created_at")
    search_fields = ("external_id", "title")


@admin.register(Attempt)
class AttemptAdmin(ReadOnlyModelAdmin):
    list_display = ("article", "attempt_number", "sha256", "size_bytes", "created_at")
    list_filter = ("created_at",)
    search_fields = ("article__external_id", "sha256", "original_filename")


@admin.register(Run)
class RunAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "attempt", "status", "stage", "version", "created_at")
    list_filter = ("status", "stage")
    search_fields = ("id", "attempt__article__external_id")


@admin.register(RunEvent)
class RunEventAdmin(ReadOnlyModelAdmin):
    list_display = ("run", "event_type", "from_status", "to_status", "actor", "created_at")
    list_filter = ("event_type", "actor")
    search_fields = ("run__id", "event_key", "task_id")
