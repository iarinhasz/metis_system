"""Criação e leitura dos campos da rubrica, com o texto original preservado."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

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
