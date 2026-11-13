"""Carga atômica e consultas da árvore versionada."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.db import transaction

from projects.correction.questions.taxonomy import TaxonomyLevel

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.questions.models import TaxonomyNode
    from projects.correction.questions.taxonomy import TaxonomySnapshot


class TaxonomyNodeManagement:
    objects: ClassVar[models.Manager[TaxonomyNode]]

    @classmethod
    @transaction.atomic
    def import_snapshot(cls, snapshot: TaxonomySnapshot) -> None:
        """Insere pais antes dos filhos; repetir a mesma versão preserva os UUIDs."""
        parents: dict[str, TaxonomyNode] = {}
        for level in TaxonomyLevel:
            entries = [entry for entry in snapshot.entries if entry.level == level]
            cls.objects.bulk_create(
                [
                    cls.objects.model(
                        code=entry.code,
                        level=entry.level,
                        name=entry.name,
                        parent=parents[entry.parent_code] if entry.parent_code else None,
                        taxonomy_version=snapshot.version,
                    )
                    for entry in entries
                ],
                ignore_conflicts=True,
                batch_size=1000,
            )
            parents.update(
                (node.code, node)
                for node in cls.objects.filter(taxonomy_version=snapshot.version, level=level)
            )

    @classmethod
    def for_version(cls, version: str) -> list[TaxonomyNode]:
        return list(
            cls.objects.filter(taxonomy_version=version).select_related("parent").order_by("code")
        )

    @classmethod
    def count(cls) -> int:
        return cls.objects.count()

    @classmethod
    def latest_version(cls) -> str | None:
        return (
            cls.objects.filter(level=TaxonomyLevel.DOMAIN)
            .order_by("-created_at", "-pk")
            .values_list("taxonomy_version", flat=True)
            .first()
        )

    @classmethod
    def fields_for_profiling(cls, version: str) -> list[TaxonomyNode]:
        return list(
            cls.objects.filter(
                taxonomy_version=version,
                level=TaxonomyLevel.FIELD,
                parent__level=TaxonomyLevel.DOMAIN,
                parent__taxonomy_version=version,
            )
            .select_related("parent")
            .order_by("code")
        )

    @classmethod
    def topics_for_field(cls, version: str, field_code: str) -> list[TaxonomyNode]:
        return list(
            cls.objects.filter(
                taxonomy_version=version,
                level=TaxonomyLevel.TOPIC,
                parent__level=TaxonomyLevel.SUBFIELD,
                parent__taxonomy_version=version,
                parent__parent__level=TaxonomyLevel.FIELD,
                parent__parent__taxonomy_version=version,
                parent__parent__code=field_code,
            )
            .select_related("parent")
            .order_by("code")
        )

    @classmethod
    def path_for_topic(cls, version: str, topic_code: str) -> tuple[TaxonomyNode, ...]:
        topic = (
            cls.objects.filter(
                taxonomy_version=version,
                code=topic_code,
                level=TaxonomyLevel.TOPIC,
                parent__level=TaxonomyLevel.SUBFIELD,
                parent__taxonomy_version=version,
                parent__parent__level=TaxonomyLevel.FIELD,
                parent__parent__taxonomy_version=version,
                parent__parent__parent__level=TaxonomyLevel.DOMAIN,
                parent__parent__parent__taxonomy_version=version,
            )
            .select_related("parent__parent__parent")
            .first()
        )
        if topic is None or topic.parent is None:
            return ()
        subfield = topic.parent
        field = subfield.parent
        assert field is not None and field.parent is not None
        return field.parent, field, subfield, topic
