"""Leitura, gravação e transições da curadoria, com bloqueio da Question."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from projects.correction.questions.criteria import get_method
from projects.correction.questions.curation_errors import CurationConflict, CurationError
from projects.correction.questions.profile import QuestionSnapshot, RubricFieldSnapshot

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.agents.schemas.curation import DraftQuestion
    from projects.correction.questions.models import Question, TaxonomyNode


class QuestionManagement:
    objects: ClassVar[models.Manager[Question]]

    @classmethod
    @transaction.atomic
    def store_initial_drafts(
        cls,
        items: tuple[tuple[DraftQuestion, TaxonomyNode | None], ...],
        *,
        method: str,
    ) -> tuple[tuple[Question, bool], ...]:
        # Serializa o bootstrap mesmo quando o escopo genérico ainda não tem linha.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [0x4D455449535145])
        results = []
        for draft, node in items:
            existing = (
                cls.objects.filter(method=method, taxonomy_node=node, is_generic=node is None)
                .order_by("created_at", "pk")
                .first()
            )
            results.append(
                (existing, False)
                if existing is not None
                else (cls.store_draft(draft, method=method, taxonomy_node=node), True)
            )
        return tuple(results)

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
    def get_by_id(cls, question_id: Any) -> Question:
        return cls.objects.select_related("taxonomy_node").get(pk=question_id)

    @classmethod
    def for_curation(cls) -> list[Question]:
        return list(cls.objects.select_related("taxonomy_node").order_by("created_at", "pk"))

    @classmethod
    def lock_for_curation(cls, question_id: Any) -> Question:
        return cls.objects.select_for_update().get(pk=question_id)

    @classmethod
    @transaction.atomic
    def store_draft(
        cls,
        draft: DraftQuestion,
        *,
        method: str,
        taxonomy_node: TaxonomyNode | None,
    ) -> Question:
        from projects.correction.questions.models import RubricField

        get_method(method)
        question = cls.create(
            name=draft.name.strip(),
            method=method,
            taxonomy_node=taxonomy_node,
            is_generic=taxonomy_node is None,
            validated=False,
            active=False,
        )
        for order, field in enumerate(draft.rubric_fields):
            RubricField.create(
                question=question,
                key=field.key,
                label=field.label.strip(),
                rubric_text=field.rubric_text,
                order=order,
            )
        return question

    @staticmethod
    def invalidate_curation(question: Question) -> None:
        """Chamado com a Question travada; editar tira a rubrica da resolução."""
        question.validated = False
        question.active = False
        question.updated_at = timezone.now()
        question.save(update_fields=["validated", "active", "updated_at"])

    @classmethod
    @transaction.atomic
    def save_curation(cls, question: Question, *, revision: str | None = None) -> None:
        get_method(question.method)
        question.name = question.name.strip()
        if not question.name:
            raise CurationError("Informe um nome para a Question.")
        fields = ("name", "method", "taxonomy_node_id", "is_generic")
        if question._state.adding:
            question.validated, question.active, question.version = False, False, 1
            question.full_clean()
            question.save()
            return
        current = cls.lock_for_curation(question.pk)
        if revision is not None and current.updated_at.isoformat() != revision:
            raise CurationConflict("A Question mudou enquanto você editava. Recarregue a página.")
        changed = any(getattr(question, field) != getattr(current, field) for field in fields)
        for field in fields:
            setattr(current, field, getattr(question, field))
        if changed:
            current.validated, current.active = False, False
            current.updated_at = timezone.now()
            current.full_clean()
            current.save(update_fields=[*fields, "validated", "active", "updated_at"])
        question.validated, question.active = current.validated, current.active
        question.version, question.updated_at = current.version, current.updated_at

    @classmethod
    def validate_for_use(cls, question_id: Any) -> Question:
        try:
            with transaction.atomic():
                question = cls.lock_for_curation(question_id)
                get_method(question.method)
                fields = list(question.rubric_fields.all())
                if not fields or any(
                    not field.label.strip() or not field.rubric_text.strip() for field in fields
                ):
                    raise CurationError("Inclua e revise pelo menos um campo de rubrica não vazio.")
                question.validated = True
                question.version += 1
                question.updated_at = timezone.now()
                question.full_clean()
                question.save(update_fields=["validated", "version", "updated_at"])
                return question
        except (ValidationError, IntegrityError) as exc:
            raise CurationConflict(
                "Já existe uma Question validada e ativa neste escopo e método."
            ) from exc

    @classmethod
    def set_active(cls, question_id: Any, active: bool) -> Question:
        try:
            with transaction.atomic():
                question = cls.lock_for_curation(question_id)
                if active and not question.validated:
                    raise CurationError("Valide a Question antes de ativá-la.")
                if active:
                    get_method(question.method)
                question.active = active
                question.updated_at = timezone.now()
                question.full_clean()
                question.save(update_fields=["active", "updated_at"])
                return question
        except (ValidationError, IntegrityError) as exc:
            raise CurationConflict(
                "Já existe uma Question validada e ativa neste escopo e método."
            ) from exc

    @classmethod
    @transaction.atomic(savepoint=False)
    def resolution_candidates(
        cls, *, method: str, taxonomy_version: str, codes: tuple[str, ...]
    ) -> list[QuestionSnapshot]:
        questions = (
            cls.objects.filter(method=method, validated=True, active=True)
            .filter(
                Q(is_generic=True)
                | Q(taxonomy_node__taxonomy_version=taxonomy_version, taxonomy_node__code__in=codes)
            )
            .select_for_update(of=("self",))
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
