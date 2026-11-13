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
