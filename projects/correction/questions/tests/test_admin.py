"""Ninguém altera a taxonomia pelo admin, nem por POST direto."""

from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

from projects.correction.questions.management.commands.load_taxonomy import read_topics
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomySnapshot

pytestmark = pytest.mark.django_db


def test_taxonomy_admin_only_allows_reading(admin_client: Client, taxonomy_file: Path) -> None:
    snapshot = TaxonomySnapshot.from_topics(read_topics(taxonomy_file))
    TaxonomyNode.import_snapshot(snapshot)
    node = TaxonomyNode.for_version(snapshot.version)[0]
    detail = reverse("admin:questions_taxonomynode_change", args=[node.pk])
    assert admin_client.get(reverse("admin:questions_taxonomynode_changelist")).status_code == 200
    assert admin_client.get(detail).status_code == 200
    assert admin_client.post(detail, {"name": "Alterado"}).status_code == 403
    assert admin_client.get(reverse("admin:questions_taxonomynode_add")).status_code == 403
    assert (
        admin_client.post(
            reverse("admin:questions_taxonomynode_delete", args=[node.pk])
        ).status_code
        == 403
    )
    assert TaxonomyNode.for_version(snapshot.version)[0].name == node.name
