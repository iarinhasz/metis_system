"""Criação e leitura dos perfis de avaliação; a curadoria vem na etapa 2.6."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.db.models import Q

from projects.correction.questions.profile import QuestionSnapshot, RubricFieldSnapshot

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

    @classmethod
    def resolution_candidates(
        cls, *, method: str, taxonomy_version: str, codes: tuple[str, ...]
    ) -> list[QuestionSnapshot]:
        questions = (
            cls.objects.filter(method=method, validated=True, active=True)
            .filter(
                Q(is_generic=True)
                | Q(taxonomy_node__taxonomy_version=taxonomy_version, taxonomy_node__code__in=codes)
            )
            .select_related("taxonomy_node")
            .prefetch_related("rubric_fields")
        )
        return [
            QuestionSnapshot(
                id=question.pk,
                version=question.version,
                name=question.name,
                method=question.method,
                is_generic=question.is_generic,
                taxonomy_node_code=question.taxonomy_node.code if question.taxonomy_node else None,
                taxonomy_version=question.taxonomy_node.taxonomy_version
                if question.taxonomy_node
                else None,
                rubric_fields=tuple(
                    RubricFieldSnapshot(
                        id=field.pk,
                        key=field.key,
                        label=field.label,
                        rubric_text=field.rubric_text,
                        order=field.order,
                    )
                    for field in question.rubric_fields.all()
                ),
            )
            for question in questions
        ]
