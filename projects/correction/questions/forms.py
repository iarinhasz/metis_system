"""Formulários do admin: escopo explícito e revisão otimista da Question."""

from typing import Any

from django import forms

from projects.correction.questions.criteria import METHODS
from projects.correction.questions.models import Question, TaxonomyNode


class TaxonomyChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: TaxonomyNode) -> str:
        return f"{obj.name} · {obj.level} · versão {obj.taxonomy_version[:12]}"


def taxonomy_choice() -> TaxonomyChoice:
    return TaxonomyChoice(
        queryset=TaxonomyNode.for_curation_selection(),
        required=False,
        label="Nó da taxonomia",
        empty_label="Question genérica",
        help_text="Escolha uma área, subárea ou tópico. Vazio cria a Question genérica.",
    )


class DraftQuestionForm(forms.Form):
    method = forms.ChoiceField(label="Método", choices=[(name, name) for name in METHODS])
    taxonomy_node = taxonomy_choice()


class QuestionForm(forms.ModelForm):  # type: ignore[type-arg]
    method = forms.ChoiceField(label="Método", choices=[(name, name) for name in METHODS])
    taxonomy_node = taxonomy_choice()
    revision = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Question
        fields = ("name", "method", "taxonomy_node", "is_generic")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["revision"].required = True
            self.initial["revision"] = self.instance.updated_at.isoformat()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if set(self.changed_data) - {"revision"}:
            # O ModelForm não deve testar unicidade como se o conteúdo editado já fosse aprovado.
            self.instance.validated, self.instance.active = False, False
        return cleaned
