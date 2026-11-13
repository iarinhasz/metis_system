"""Admin do domínio: leitura da auditoria e as ações do gate e do reprocessamento."""

from typing import Any
from uuid import UUID

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Model
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import URLPattern, path, reverse

from projects.correction.attempts.models import Article, Attempt, LLMCall, Run, RunEvent
from projects.correction.attempts.status import RECOVERABLE, HumanDecision, RunStatus
from projects.correction.pipeline.services import decide_run, recover_run
from projects.correction.queries.attempts.run import RunConflict

RUN_ACTIONS = {
    "continue": "Continuar avaliação",
    "close": "Encerrar",
    "recover": "Reprocessar",
}


class ReadOnlyModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Impede alterações manuais que contornariam os Managements de `queries/attempts/`."""

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
    """Página do run com os botões do gate (continuar, encerrar) e do reprocessamento."""

    list_display = ("id", "attempt", "status", "stage", "version", "created_at")
    list_filter = ("status", "stage")
    search_fields = ("id", "attempt__article__external_id")

    def get_urls(self) -> list[URLPattern]:
        action = path(
            "<path:object_id>/acao/",
            self.admin_site.admin_view(self.run_action_view),
            name="attempts_run_action",
        )
        return [action, *super().get_urls()]

    def can_act(self, request: HttpRequest) -> bool:
        """As ações exigem a permissão de alterar o Run, não só a de ver."""
        return admin.ModelAdmin.has_change_permission(self, request)

    def action_panel(self, request: HttpRequest, run: Run | None) -> dict[str, Any] | None:
        """O bloco de ações do topo da página, quando o run está num estado que tem ação."""
        if run is None or not self.can_act(request):
            return None
        status = RunStatus(run.status)
        if status == RunStatus.WAITING_HUMAN_REVIEW:
            return {
                "title": "Revisão humana",
                "help": "O E3 apontou risco alto. Continuar retoma a avaliação a partir do E4; "
                "encerrar fecha o run sem avaliar.",
                "actions": [
                    ("continue", RUN_ACTIONS["continue"], "default"),
                    ("close", RUN_ACTIONS["close"], ""),
                ],
            }
        if status in RECOVERABLE:
            return {
                "title": "Reprocessamento",
                "help": f"O estágio {run.stage} parou em {run.status}. Reprocessar roda esse "
                "estágio de novo, sem refazer os anteriores.",
                "actions": [("recover", RUN_ACTIONS["recover"], "default")],
            }
        return None

    def render_change_form(
        self,
        request: HttpRequest,
        context: dict[str, Any],
        add: bool = False,
        change: bool = False,
        form_url: str = "",
        obj: Run | None = None,
    ) -> HttpResponse:
        context["run_panel"] = self.action_panel(request, obj)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def run_action_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not self.can_act(request):
            raise PermissionDenied
        try:
            run_id = UUID(object_id)
        except ValueError as exc:
            raise Http404("Run não encontrado.") from exc

        action = request.POST.get("action", "")
        actor = f"admin:{request.user.get_username()}"
        change_url = reverse("admin:attempts_run_change", args=[object_id])
        try:
            if action == "continue":
                run = decide_run(run_id, HumanDecision.CONTINUE, actor=actor)
            elif action == "close":
                run = decide_run(run_id, HumanDecision.CLOSE, actor=actor)
            elif action == "recover":
                run = recover_run(run_id, actor=actor)
            else:
                self.message_user(request, "Ação desconhecida.", messages.ERROR)
                return redirect(change_url)
        except Run.DoesNotExist as exc:
            raise Http404("Run não encontrado.") from exc
        except RunConflict as exc:
            self.message_user(request, str(exc), messages.ERROR)
        else:
            self.message_user(
                request, f"{RUN_ACTIONS[action]}: o run está em {run.status}.", messages.SUCCESS
            )
        return redirect(change_url)


@admin.register(RunEvent)
class RunEventAdmin(ReadOnlyModelAdmin):
    list_display = ("run", "event_type", "from_status", "to_status", "actor", "created_at")
    list_filter = ("event_type", "actor")
    search_fields = ("run__id", "event_key", "task_id")


@admin.register(LLMCall)
class LLMCallAdmin(ReadOnlyModelAdmin):
    list_display = (
        "run", "stage", "role", "agent", "provider", "model", "input_tokens", "output_tokens",
        "cached_tokens", "cost_usd", "latency_ms", "success", "created_at",
    )
    list_filter = ("stage", "role", "provider", "model", "success", "created_at")
    search_fields = ("run__id", "model", "agent", "prompt_version")
    list_select_related = ("run",)
    actions = None

    def has_change_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False
