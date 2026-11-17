"""Carga real no PostgreSQL: dry-run, repetição, versões e falha sem escrita parcial."""

import json
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DataError
from pydantic import TypeAdapter

from projects.correction.extractor.tests.http_stub import StubResponse, StubServer
from projects.correction.questions.management.commands import load_taxonomy
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomyLevel, TaxonomySnapshot
from projects.correction.scholarly.openalex import OpenAlexClient, OpenAlexTopic

pytestmark = pytest.mark.django_db


def load(path: Path, *, execute: bool = False) -> str:
    stdout = StringIO()
    call_command("load_taxonomy", file=path, execute=execute, stdout=stdout)
    return stdout.getvalue()


def test_dry_run_makes_no_queries_or_writes(
    taxonomy_file: Path, django_assert_num_queries: Any
) -> None:
    with django_assert_num_queries(0):
        output = load(taxonomy_file)
    assert "Dry-run" in output and "taxonomy_version:" in output
    assert "topic: 4" in output
    assert TaxonomyNode.count() == 0


def test_execute_stores_four_levels_with_uuid7_and_same_version(
    taxonomy_file: Path, recorded_topics: list[dict[str, Any]]
) -> None:
    snapshot = TaxonomySnapshot.from_topics(
        tuple(TypeAdapter(list[OpenAlexTopic]).validate_python(recorded_topics))
    )
    output = load(taxonomy_file, execute=True)
    nodes = TaxonomyNode.for_version(snapshot.version)
    assert len(nodes) == 15
    assert snapshot.version in output
    assert {node.level for node in nodes} == set(TaxonomyLevel)
    for node in nodes:
        assert node.pk.version == 7
        node.full_clean()
        if node.level == TaxonomyLevel.DOMAIN:
            assert node.parent is None
        else:
            assert node.parent is not None
            assert node.parent.taxonomy_version == node.taxonomy_version


def test_repeated_load_keeps_ids_and_timestamps(taxonomy_file: Path) -> None:
    output = load(taxonomy_file, execute=True)
    version = output.splitlines()[0].split(": ")[1]
    before = [(node.pk, node.updated_at) for node in TaxonomyNode.for_version(version)]
    load(taxonomy_file, execute=True)
    assert TaxonomyNode.count() == len(before)
    assert [(node.pk, node.updated_at) for node in TaxonomyNode.for_version(version)] == before


def test_changed_content_creates_a_new_snapshot_without_overwriting_old_nodes(
    taxonomy_file: Path, recorded_topics: list[dict[str, Any]]
) -> None:
    original_output = load(taxonomy_file, execute=True)
    original_version = original_output.splitlines()[0].split(": ")[1]
    before = [(node.pk, node.name) for node in TaxonomyNode.for_version(original_version)]
    recorded_topics[0]["display_name"] = "Nome atualizado"
    taxonomy_file.write_text(json.dumps(recorded_topics), encoding="utf-8")
    changed_output = load(taxonomy_file, execute=True)
    assert original_output != changed_output
    assert TaxonomyNode.count() == 30
    assert [(node.pk, node.name) for node in TaxonomyNode.for_version(original_version)] == before


@pytest.mark.parametrize("fault", ["parent", "missing", "id", "duplicate", "empty", "json"])
def test_invalid_input_does_not_store_part_of_the_tree(
    taxonomy_file: Path, recorded_topics: list[dict[str, Any]], fault: str
) -> None:
    match fault:
        case "parent":
            recorded_topics[1]["domain"]["display_name"] = "Outro domínio"
        case "missing":
            del recorded_topics[1]["subfield"]
        case "id":
            recorded_topics[1]["field"]["id"] = "https://example.com/fields/31"
        case "duplicate":
            recorded_topics.append(recorded_topics[0])
        case "empty":
            recorded_topics.clear()
    taxonomy_file.write_text(
        "{bad json" if fault == "json" else json.dumps(recorded_topics), encoding="utf-8"
    )
    with pytest.raises(CommandError, match="nenhuma escrita"):
        load(taxonomy_file, execute=True)
    assert TaxonomyNode.count() == 0


def test_a_single_page_cannot_silently_be_imported_as_the_whole_taxonomy() -> None:
    path = Path(__file__).parent / "data" / "openalex_topics.json"
    with pytest.raises(CommandError, match="incompleta"):
        load(path, execute=True)
    assert TaxonomyNode.count() == 0


def test_catalog_preserves_subfields_without_topics(tmp_path: Path) -> None:
    path = Path(__file__).parent / "data" / "openalex_catalog.json"
    output = load(path, execute=True)
    version = output.splitlines()[0].split(": ")[1]
    nodes = {node.code: node for node in TaxonomyNode.for_version(version)}
    orphan = nodes["https://openalex.org/subfields/1502"]
    assert orphan.name == "Bioengineering"
    assert orphan.parent is not None and orphan.parent.code == "https://openalex.org/fields/15"
    assert not any(node.parent_id == orphan.pk for node in nodes.values())


def test_database_failure_rolls_back_parents_inserted_earlier(taxonomy_file: Path) -> None:
    snapshot = TaxonomySnapshot.from_topics(load_taxonomy.read_topics(taxonomy_file))
    # Força uma rejeição real do PostgreSQL no segundo nível, depois de inserir os domains.
    invalid = replace(
        snapshot,
        entries=tuple(
            replace(entry, name="x" * 513) if entry.level == TaxonomyLevel.FIELD else entry
            for entry in snapshot.entries
        ),
    )
    with pytest.raises(DataError):
        TaxonomyNode.import_snapshot(invalid)
    assert TaxonomyNode.count() == 0


@pytest.mark.parametrize("fault", ["empty", "duplicate", "count", "page", "short"])
def test_inconsistent_http_pagination_is_rejected(
    recorded_topics: list[dict[str, Any]], fault: str
) -> None:
    second: dict[str, Any] = {
        "meta": {"count": 4, "page": 2, "per_page": 2},
        "results": recorded_topics[2:],
    }
    match fault:
        case "empty":
            second["results"] = []
        case "duplicate":
            second["results"] = recorded_topics[:2]
        case "count":
            second["meta"]["count"] = 5
        case "page":
            second["meta"]["page"] = 1
        case "short":
            second["results"] = recorded_topics[2:3]
    server = StubServer()
    server.queue(
        StubResponse.json(
            {"meta": {"count": 4, "page": 1, "per_page": 2}, "results": recorded_topics[:2]}
        ),
        StubResponse.json(second),
    )
    server.start()
    try:
        with pytest.raises(ValueError):
            OpenAlexClient(base_url=server.url, per_page=2).topics()
    finally:
        server.stop()


@pytest.mark.parametrize("status", [200, 401, 429, 503])
def test_command_replays_http_pages_or_aborts_without_writes(
    recorded_catalog: dict[str, Any], monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    server = StubServer()
    # Reconstitui os endpoints com os mesmos objetos gravados, incluindo o ramo sem topic.
    domains = {}
    fields = {}
    subfields = {}
    for topic in recorded_catalog["topics"]:
        domains[topic["domain"]["id"]] = topic["domain"]
        fields[topic["field"]["id"]] = topic["field"] | {"domain": topic["domain"]}
        subfields[topic["subfield"]["id"]] = topic["subfield"] | {
            "domain": topic["domain"],
            "field": topic["field"],
        }
    for subfield in recorded_catalog["subfields"]:
        domains[subfield["domain"]["id"]] = subfield["domain"]
        fields[subfield["field"]["id"]] = subfield["field"] | {"domain": subfield["domain"]}
        subfields[subfield["id"]] = subfield
    endpoints = {
        "domains": list(domains.values()),
        "fields": list(fields.values()),
        "subfields": list(subfields.values()),
        "topics": recorded_catalog["topics"],
    }
    for endpoint, rows in endpoints.items():
        for offset in range(0, len(rows), 2):
            page = offset // 2 + 1
            server.queue(
                StubResponse.json(
                    {
                        "meta": {"count": len(rows), "page": page, "per_page": 2},
                        "results": rows[offset : offset + 2],
                    },
                    status=status if endpoint == "topics" and page == 2 else 200,
                )
            )

    def client(*, api_key: str) -> OpenAlexClient:
        return OpenAlexClient(api_key=api_key, base_url=server.url, per_page=2)

    monkeypatch.setattr(load_taxonomy, "OpenAlexClient", client)
    monkeypatch.setattr("projects.correction.scholarly.openalex.time.sleep", lambda _: None)
    server.start()
    try:
        if status == 200:
            call_command("load_taxonomy", execute=True, stdout=StringIO())
            assert TaxonomyNode.count() == 17
        else:
            with pytest.raises(CommandError, match=f"HTTP {status}"):
                call_command("load_taxonomy", execute=True, stdout=StringIO())
            assert TaxonomyNode.count() == 0
        assert len(server.requests) == 10
        assert "page=2" in server.requests[-1].path
        assert {request.path.split("?")[0] for request in server.requests} == {
            "/domains",
            "/fields",
            "/subfields",
            "/topics",
        }
    finally:
        server.stop()
