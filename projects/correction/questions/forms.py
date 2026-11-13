"""Formulários do admin: escopo explícito e revisão otimista da Question."""

from typing import Any

from django import forms

from projects.correction.attempts.models import Attempt
from projects.correction.extractor.attempt_extraction import extraction_version
from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.questions.criteria import METHODS
from projects.correction.questions.models import Question, TaxonomyNode
from projects.correction.questions.rubric_check import MAX_SAMPLE_ATTEMPTS


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


class AttemptChoice(forms.ModelMultipleChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Attempt) -> str:
        return f"{obj.article.external_id} · attempt {obj.attempt_number} · {obj.original_filename}"


class RubricCheckForm(forms.Form):
    attempts = AttemptChoice(
        queryset=Attempt.for_rubric_check_selection(""),
        label="Attempts de amostra",
        help_text=f"Selecione de 1 a {MAX_SAMPLE_ATTEMPTS} attempts com extração em cache.",
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )
    revision = forms.CharField(widget=forms.HiddenInput)
    batch_id = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = self.fields["attempts"]
        assert isinstance(field, forms.ModelMultipleChoiceField)
        field.queryset = Attempt.for_rubric_check_selection(extraction_version(ARTICLE_CONFIG))

    def clean_attempts(self) -> Any:
        attempts = self.cleaned_data["attempts"]
        if len(attempts) > MAX_SAMPLE_ATTEMPTS:
            raise forms.ValidationError(f"Escolha no máximo {MAX_SAMPLE_ATTEMPTS} attempts.")
        return attempts
