"""Taxonomia versionada e contexto de avaliação por área."""

from django.core.exceptions import ValidationError
from django.db import models

from projects.correction.attempts.models import TimeStampModel
from projects.correction.queries.questions.question import QuestionManagement
from projects.correction.queries.questions.rubric_field import RubricFieldManagement
from projects.correction.queries.questions.taxonomy_node import TaxonomyNodeManagement
from projects.correction.questions.taxonomy import TaxonomyLevel, canonical_code


class TaxonomyNode(TaxonomyNodeManagement, TimeStampModel):
    code = models.CharField(max_length=128)
    level = models.CharField(
        max_length=8, choices=[(level.value, level.value) for level in TaxonomyLevel]
    )
    name = models.CharField(max_length=512)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    taxonomy_version = models.CharField(max_length=64, db_index=True)

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "taxonomy_version"], name="taxonomy_code_version_uniq"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(level="domain", parent__isnull=True)
                    | models.Q(level__in=["field", "subfield", "topic"], parent__isnull=False)
                ),
                name="taxonomy_level_parent_valid",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        try:
            level = TaxonomyLevel(self.level)
            canonical_code(self.code, level)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if level == TaxonomyLevel.DOMAIN:
            if self.parent_id is not None:
                raise ValidationError("Um domain não pode ter pai.")
        elif self.parent is None:
            raise ValidationError("Este nível exige um pai.")
        elif (
            self.parent.level != list(TaxonomyLevel)[list(TaxonomyLevel).index(level) - 1]
            or self.parent.taxonomy_version != self.taxonomy_version
        ):
            raise ValidationError("O pai deve ser do nível anterior e da mesma versão.")

    def __str__(self) -> str:
        return f"{self.name} ({self.level})"


class Question(QuestionManagement, TimeStampModel):
    taxonomy_node = models.ForeignKey(
        TaxonomyNode, on_delete=models.PROTECT, null=True, blank=True, related_name="questions"
    )
    is_generic = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    method = models.SlugField(max_length=64)
    validated = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_generic=True, taxonomy_node__isnull=True)
                    | models.Q(is_generic=False, taxonomy_node__isnull=False)
                ),
                name="question_generic_node_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1), name="question_version_positive"
            ),
            models.UniqueConstraint(
                fields=["taxonomy_node", "method"],
                condition=models.Q(validated=True, active=True),
                name="question_active_node_method_uniq",
            ),
            models.UniqueConstraint(
                fields=["method"],
                condition=models.Q(is_generic=True, validated=True, active=True),
                name="question_active_generic_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class RubricField(RubricFieldManagement, TimeStampModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="rubric_fields")
    key = models.SlugField(max_length=64)
    label = models.CharField(max_length=255)
    rubric_text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "key"], name="rubric_question_key_uniq")
        ]

    def __str__(self) -> str:
        return self.label
