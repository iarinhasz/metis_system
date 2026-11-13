"""Criação e leitura dos campos da rubrica, com o texto original preservado."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import transaction
from django.utils import timezone

from projects.correction.questions.curation_errors import CurationError

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.questions.models import Question, RubricField


class RubricFieldManagement:
    objects: ClassVar[models.Manager[RubricField]]

    @classmethod
    def create(
        cls, *, question: Question, key: str, label: str, rubric_text: str, order: int = 0
    ) -> RubricField:
        field = cls.objects.model(
            question=question, key=key, label=label, rubric_text=rubric_text, order=order
        )
        field.full_clean()
        field.save()
        return field

    @classmethod
    def for_question(cls, question: Question) -> list[RubricField]:
        return list(cls.objects.filter(question=question).order_by("order", "id"))

    @classmethod
    @transaction.atomic
    def save_curation(cls, field: RubricField) -> None:
        from projects.correction.questions.models import Question

        question = Question.lock_for_curation(field.question_id)
        if not field.key.strip() or not field.label.strip() or not field.rubric_text.strip():
            raise CurationError("Chave, rótulo e texto da rubrica não podem ser vazios.")
        if not field._state.adding:
            current = cls.objects.get(pk=field.pk, question=question)
            if all(
                getattr(current, name) == getattr(field, name)
                for name in (
                    "key",
                    "label",
                    "rubric_text",
                    "order",
                )
            ):
                return
        field.full_clean()
        field.updated_at = timezone.now()
        field.save()
        Question.invalidate_curation(question)

    @classmethod
    @transaction.atomic
    def delete_curation(cls, field_id: Any, *, question_id: Any) -> None:
        from projects.correction.questions.models import Question

        question = Question.lock_for_curation(question_id)
        field = cls.objects.get(pk=field_id, question=question)
        field.delete()
        Question.invalidate_curation(question)
