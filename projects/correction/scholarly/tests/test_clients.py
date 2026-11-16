"""Integração dos clientes com fixtures de respostas e HTTP local."""

import json
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

import pytest

from projects.correction.scholarly.arxiv import ArxivClient
from projects.correction.scholarly.cache import DOIResponseCache
from projects.correction.scholarly.crossref import CrossrefClient
from projects.correction.scholarly.errors import ScholarlyClientError
from projects.correction.scholarly.http import ScholarlyHTTPClient
from projects.correction.scholarly.openalex import (
    OpenAlexClient,
    OpenAlexTopic,
    OpenAlexWorksClient,
)
from projects.correction.scholarly.semantic_scholar import SemanticScholarClient
from projects.correction.scholarly.tests.http_stub import StubResponse, api_stub
from projects.correction.scholarly.tests.test_support import MemoryRedis
from projects.correction.scholarly.unpaywall import UnpaywallClient

FIXTURES = Path(__file__).parent / "fixtures"


class NoopLimiter:
    def acquire(self, provider: str, *, rate: float | None = None, capacity: int = 1) -> None:
        del provider, rate, capacity

    def permit(self, provider: str) -> AbstractContextManager[None]:
        del provider
        return nullcontext()


def client_http(provider: str, *, redis: MemoryRedis | None = None) -> ScholarlyHTTPClient:
    cache_client = redis or MemoryRedis()
    return ScholarlyHTTPClient(
        provider,
        limiter=NoopLimiter(),
        cache=DOIResponseCache(cache_client),
        redis_client=cache_client,
        sleeper=lambda delay: None,
    )


def recorded(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_crossref_parses_doi_and_bibliographic_search() -> None:
    with api_stub() as api:
        api.queue(StubResponse(recorded("crossref_work.json")))
        work = CrossrefClient(base_url=api.url, http=client_http("crossref")).by_doi(
            "10.1000/example"
        )
    assert work is not None
    assert work.doi == "10.1000/example"
    assert work.title == ("A recorded sample paper",)
    assert work.update_to[0]["type"] == "retraction"

    with api_stub() as api:
        api.queue(StubResponse(recorded("crossref_search.json")))
        results = CrossrefClient(base_url=api.url, http=client_http("crossref")).search("sample")
    assert results.total_results == 1
    assert results.items[0].doi == "10.1000/example"


def test_openalex_work_client_parses_retraction_and_search() -> None:
    with api_stub() as api:
        api.queue(StubResponse(recorded("openalex_work.json")))
        work = OpenAlexWorksClient(base_url=api.url, http=client_http("openalex")).by_doi(
            "10.1000/example"
        )
    assert work is not None
    assert work.is_retracted
    assert work.best_oa_location is not None
    assert work.best_oa_location.pdf_url == "https://example.org/paper.pdf"

    with api_stub() as api:
        api.queue(StubResponse(recorded("openalex_search.json")))
        results = OpenAlexWorksClient(base_url=api.url, http=client_http("openalex")).search(
            "sample"
        )
    assert len(results.results) == 1
    assert results.results[0].publication_year == 2024


def test_openalex_taxonomy_public_api_remains_available() -> None:
    topic = OpenAlexTopic.model_validate(
        {
            "id": "https://openalex.org/topics/1",
            "display_name": "Topic",
            "domain": {"id": "domain", "display_name": "Domain"},
            "field": {"id": "field", "display_name": "Field"},
            "subfield": {"id": "subfield", "display_name": "Subfield"},
        }
    )
    assert topic.display_name == "Topic"
    assert OpenAlexClient(base_url="http://127.0.0.1").base_url == "http://127.0.0.1"


def test_semantic_scholar_parses_doi_match_and_search_with_api_key() -> None:
    with api_stub() as api:
        api.queue(StubResponse(recorded("semantic_scholar_paper.json")))
        client = SemanticScholarClient(
            api_key="s2-test", base_url=api.url, http=client_http("semantic_scholar")
        )
        by_doi = client.by_doi("10.1000/example")
    assert by_doi is not None and by_doi.paper_id == "paper-123"
    assert (
        next(value for key, value in api.requests[0].headers.items() if key.lower() == "x-api-key")
        == "s2-test"
    )

    with api_stub() as api:
        api.queue(StubResponse(recorded("semantic_scholar_paper.json")))
        match = SemanticScholarClient(base_url=api.url, http=client_http("semantic_scholar")).match(
            "A recorded sample paper"
        )
    assert match is not None and match.title == "A recorded sample paper"

    with api_stub() as api:
        api.queue(StubResponse(recorded("semantic_scholar_search.json")))
        search = SemanticScholarClient(
            base_url=api.url, http=client_http("semantic_scholar")
        ).search("sample")
    assert search.total == 1 and search.data[0].year == 2024


def test_arxiv_parses_atom_fixture() -> None:
    with api_stub() as api:
        api.queue(
            StubResponse(
                recorded("arxiv_search.xml"), headers={"Content-Type": "application/atom+xml"}
            )
        )
        result = ArxivClient(base_url=api.url, http=client_http("arxiv")).search("sample")
    assert result.total_results == 1
    assert result.entries[0].doi == "10.1000/example"
    assert result.entries[0].authors[0].name == "Ada Lovelace"
    assert result.entries[0].categories == ("cs.CL",)


def test_unpaywall_parses_open_access_location() -> None:
    with api_stub() as api:
        api.queue(StubResponse(recorded("unpaywall_work.json")))
        work = UnpaywallClient(
            email="reader@example.org", base_url=api.url, http=client_http("unpaywall")
        ).by_doi("10.1000/example")
    assert work is not None and work.is_oa
    assert work.best_oa_location is not None
    assert work.best_oa_location.license == "cc-by"


def test_repeated_doi_in_different_forms_uses_one_http_request() -> None:
    redis = MemoryRedis()
    with api_stub() as api:
        api.queue(StubResponse(recorded("crossref_work.json")))
        client = CrossrefClient(base_url=api.url, http=client_http("crossref", redis=redis))
        first = client.by_doi("10.1000/Example")
        second = client.by_doi("https://doi.org/10.1000/EXAMPLE")

    assert first == second
    assert len(api.requests) == 1


def test_only_successful_responses_are_cached() -> None:
    redis = MemoryRedis()
    with api_stub() as api:
        api.queue(
            StubResponse(b'{"message":{}}', status=400),
            StubResponse(recorded("crossref_work.json")),
        )
        client = CrossrefClient(base_url=api.url, http=client_http("crossref", redis=redis))
        with pytest.raises(ScholarlyClientError):
            client.by_doi("10.1000/example")
        work = client.by_doi("10.1000/example")

    assert work is not None
    assert len(api.requests) == 2


def test_fixture_files_are_valid_json() -> None:
    for path in FIXTURES.glob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
