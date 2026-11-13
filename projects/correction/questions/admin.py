"""Taxonomia de leitura e curadoria explícita de Questions e rubricas."""

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, models
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import URLPattern, path, reverse

from projects.correction.agents.errors import LLMUnavailable, MissingProviderKey
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus
from projects.correction.questions.curation import draft_question
from projects.correction.questions.curation_errors import CurationError
from projects.correction.questions.forms import DraftQuestionForm, QuestionForm, RubricCheckForm
from projects.correction.questions.models import Question, RubricField, TaxonomyNode
from projects.correction.questions.rubric_check import start_rubric_check


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


class RubricFieldInline(admin.TabularInline):  # type: ignore[type-arg]
    model = RubricField
    fields = ("key", "label", "rubric_text", "order")
    extra = 0
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 5, "cols": 70})}
    }


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    form = QuestionForm
    inlines = (RubricFieldInline,)
    list_display = (
        "name",
        "method",
        "taxonomy_node",
        "is_generic",
        "validated",
        "active",
        "version",
    )
    list_filter = ("method", "is_generic", "validated", "active", "taxonomy_node__taxonomy_version")
    list_select_related = ("taxonomy_node",)
    search_fields = ("name", "taxonomy_node__name", "taxonomy_node__code")
    readonly_fields = ("validated", "active", "version", "created_at", "updated_at")
    fields = (
        "name",
        "method",
        "taxonomy_node",
        "is_generic",
        "validated",
        "active",
        "version",
        "revision",
        "created_at",
        "updated_at",
    )
    actions = (
        "draft_selected",
        "validate_selected",
        "activate_selected",
        "deactivate_selected",
        "rubric_check_selected",
    )
    change_list_template = "admin/questions/question/change_list.html"
    change_form_template = "admin/questions/question/change_form.html"

    def has_delete_permission(self, request: HttpRequest, obj: Question | None = None) -> bool:
        return False

    def get_urls(self) -> list[URLPattern]:
        return [
            path(
                "<uuid:question_id>/rubric-check/",
                self.admin_site.admin_view(self.rubric_check_view),
                name="questions_question_rubric_check",
            ),
            path(
                "<uuid:question_id>/rubric-check/<uuid:batch_id>/",
                self.admin_site.admin_view(self.rubric_check_results_view),
                name="questions_question_rubric_check_results",
            ),
            path(
                "draft/",
                self.admin_site.admin_view(self.draft_view),
                name="questions_question_draft",
            ),
            *super().get_urls(),
        ]

    def has_rubric_check_permission(self, request: HttpRequest) -> bool:
        return self.has_change_permission(request) and all(
            request.user.has_perm(perm)
            for perm in (
                "attempts.add_run",
                "attempts.view_attempt",
                "attempts.view_run",
                "evaluation.view_finalreport",
            )
        )

    @admin.action(description="Rodar rubric check", permissions=["rubric_check"])
    def rubric_check_selected(
        self, request: HttpRequest, queryset: models.QuerySet[Question]
    ) -> HttpResponse | None:
        selected = list(queryset[:2])
        if len(selected) != 1:
            self.message_user(request, "Selecione um rascunho para testar.", messages.ERROR)
            return None
        return redirect("admin:questions_question_rubric_check", selected[0].pk)

    @staticmethod
    def _rubric_check_question(question_id: UUID) -> Question:
        try:
            return Question.get_by_id(question_id)
        except Question.DoesNotExist as exc:
            raise Http404("Question não encontrada.") from exc

    def rubric_check_view(self, request: HttpRequest, question_id: UUID) -> HttpResponse:
        if not self.has_rubric_check_permission(request):
            raise PermissionDenied
        question = self._rubric_check_question(question_id)
        if not self.has_change_permission(request, question):
            raise PermissionDenied
        form = RubricCheckForm(
            request.POST if request.method == "POST" else None,
            initial={"revision": question.updated_at.isoformat(), "batch_id": uuid4()},
        )
        if request.method == "POST" and form.is_valid():
            try:
                batch = start_rubric_check(
                    question.pk,
                    attempt_ids=tuple(attempt.pk for attempt in form.cleaned_data["attempts"]),
                    revision=form.cleaned_data["revision"],
                    batch_id=form.cleaned_data["batch_id"],
                    actor=f"admin:{request.user.get_username()}",
                )
            except CurationError as exc:
                form.add_error(None, str(exc))
            else:
                if batch.created:
                    self.log_change(
                        request,
                        question,
                        f"Rubric check {batch.id}: {len(batch.runs)} runs internos.",
                    )
                return redirect(
                    "admin:questions_question_rubric_check_results", question.pk, batch.id
                )
        return TemplateResponse(
            request,
            "admin/questions/question/rubric_check.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Rodar rubric check",
                "question": question,
                "form": form,
            },
        )

    def rubric_check_results_view(
        self, request: HttpRequest, question_id: UUID, batch_id: UUID
    ) -> HttpResponse:
        if not all(
            request.user.has_perm(perm)
            for perm in (
                "attempts.view_attempt",
                "attempts.view_run",
                "evaluation.view_finalreport",
            )
        ):
            raise PermissionDenied
        question = self._rubric_check_question(question_id)
        if not self.has_view_permission(request, question):
            raise PermissionDenied
        runs = Run.rubric_check_batch(question.pk, batch_id)
        if not runs:
            raise Http404("Lote de rubric check não encontrado para esta Question.")
        return TemplateResponse(
            request,
            "admin/questions/question/rubric_check_results.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Resultados do rubric check",
                "question": question,
                "batch_id": batch_id,
                "frozen_question": runs[0].config_snapshot["question"],
                "results": [
                    {
                        "run": run,
                        "report": run.final_report
                        if run.status == RunStatus.DONE and hasattr(run, "final_report")
                        else None,
                        "run_url": reverse("admin:attempts_run_change", args=[run.pk]),
                    }
                    for run in runs
                ],
            },
        )

    def draft_view(self, request: HttpRequest) -> HttpResponse:
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = DraftQuestionForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            node = form.cleaned_data["taxonomy_node"]
            try:
                question = draft_question(
                    method=form.cleaned_data["method"], taxonomy_node_id=node.pk if node else None
                )
            except (CurationError, LLMUnavailable, MissingProviderKey) as exc:
                form.add_error(None, str(exc))
            else:
                self.log_addition(
                    request, question, "Rascunho criado pelo agente para revisão humana."
                )
                self.message_user(
                    request, "Rascunho criado. Revise a rubrica, valide e ative.", messages.SUCCESS
                )
                return redirect("admin:questions_question_change", question.pk)
        return TemplateResponse(
            request,
            "admin/questions/question/draft.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Rascunhar Question",
                "form": form,
            },
        )

    @admin.action(description="Rascunhar Question", permissions=["add"])
    def draft_selected(self, request: HttpRequest, queryset: models.QuerySet[Question]) -> None:
        selected = list(queryset[:2])
        if len(selected) != 1:
            self.message_user(
                request,
                "Selecione uma Question para rascunhar outra no mesmo escopo.",
                messages.ERROR,
            )
            return
        source = selected[0]
        try:
            question = draft_question(
                method=source.method, taxonomy_node_id=source.taxonomy_node_id
            )
        except (CurationError, LLMUnavailable, MissingProviderKey) as exc:
            self.message_user(request, str(exc), messages.ERROR)
        else:
            self.log_addition(request, question, f"Rascunho no escopo de {source.pk}.")
            self.message_user(
                request,
                f"Rascunho criado: {question.name}. Revise antes de validar.",
                messages.SUCCESS,
            )

    def _curate(
        self,
        request: HttpRequest,
        queryset: models.QuerySet[Question],
        operation: Callable[[UUID], Question],
        description: str,
    ) -> None:
        for selected in queryset:
            try:
                question = operation(selected.pk)
            except CurationError as exc:
                self.message_user(request, f"{selected.name}: {exc}", messages.ERROR)
            else:
                self.log_change(request, question, description)
                self.message_user(
                    request,
                    f"{question.name}: {description} (versão {question.version}).",
                    messages.SUCCESS,
                )

    @admin.action(description="Validar", permissions=["change"])
    def validate_selected(self, request: HttpRequest, queryset: models.QuerySet[Question]) -> None:
        self._curate(request, queryset, Question.validate_for_use, "Validação registrada")

    @admin.action(description="Ativar", permissions=["change"])
    def activate_selected(self, request: HttpRequest, queryset: models.QuerySet[Question]) -> None:
        self._curate(
            request, queryset, lambda pk: Question.set_active(pk, True), "Question ativada"
        )

    @admin.action(description="Desativar", permissions=["change"])
    def deactivate_selected(
        self, request: HttpRequest, queryset: models.QuerySet[Question]
    ) -> None:
        self._curate(
            request, queryset, lambda pk: Question.set_active(pk, False), "Question desativada"
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: Question,
        form: forms.ModelForm[Question],
        change: bool,
    ) -> None:
        Question.save_curation(obj, revision=form.cleaned_data.get("revision") if change else None)

    def save_formset(
        self,
        request: HttpRequest,
        form: forms.ModelForm[Question],
        formset: Any,
        change: bool,
    ) -> None:
        fields = formset.save(commit=False)
        for deleted in formset.deleted_objects:
            RubricField.delete_curation(deleted.pk, question_id=form.instance.pk)
        for field in fields:
            RubricField.save_curation(field)
        formset.save_m2m()

    def changeform_view(
        self,
        request: HttpRequest,
        object_id: str | None = None,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        extra_context = {
            **(extra_context or {}),
            "can_rubric_check": self.has_rubric_check_permission(request),
        }
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except (CurationError, ValidationError) as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return redirect(request.path)
        except IntegrityError:
            self.message_user(
                request,
                "Conflito ao salvar. Recarregue a página e revise os campos.",
                messages.ERROR,
            )
            return redirect(request.path)
