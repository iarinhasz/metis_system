"""Criação e leitura dos perfis de avaliação; a curadoria vem na etapa 2.6."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.questions.models import Question, TaxonomyNode


class QuestionManagement:
    objects: ClassVar[models.Manager[Question]]

    @classmethod
    def create(
        cls,
        *,
        name: str,
        method: str,
        taxonomy_node: TaxonomyNode | None = None,
        is_generic: bool = False,
        validated: bool = False,
        active: bool = True,
    ) -> Question:
        question = cls.objects.model(
            name=name,
            method=method,
            taxonomy_node=taxonomy_node,
            is_generic=is_generic,
            validated=validated,
            active=active,
        )
        question.full_clean()
        question.save()
        return question
