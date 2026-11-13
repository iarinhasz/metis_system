"""A taxonomia importada é somente de leitura, inclusive em POST direto."""

from django.contrib import admin
from django.http import HttpRequest

from projects.correction.questions.models import TaxonomyNode


@admin.register(TaxonomyNode)
class TaxonomyNodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "code", "level", "parent", "taxonomy_version")
    list_filter = ("level", "taxonomy_version")
    search_fields = ("name", "code", "parent__name")
    list_select_related = ("parent",)
    readonly_fields = (
        "id",
        "code",
        "level",
        "name",
        "parent",
        "taxonomy_version",
        "created_at",
        "updated_at",
    )
    actions = None

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: TaxonomyNode | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: TaxonomyNode | None = None) -> bool:
        return False
