"""Cliente Semantic Scholar Graph API."""

from typing import Any
from urllib.parse import quote

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from projects.correction.metis.config import settings
from projects.correction.scholarly.cache import normalize_doi
from projects.correction.scholarly.http import (
    DEFAULT_TIMEOUT_SECONDS,
    ScholarlyHTTPClient,
    json_payload,
)

PAPER_FIELDS = "paperId,externalIds,title,abstract,year,authors,openAccessPdf,isRetracted"


class SemanticScholarPaper(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    paper_id: str | None = Field(default=None, validation_alias=AliasChoices("paperId", "paper_id"))
    external_ids: dict[str, Any] = Field(
        default_factory=dict, validation_alias=AliasChoices("externalIds", "external_ids")
    )
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    authors: tuple[dict[str, Any], ...] = ()
    open_access_pdf: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("openAccessPdf", "open_access_pdf")
    )
    is_retracted: bool | None = Field(
        default=None, validation_alias=AliasChoices("isRetracted", "is_retracted")
    )


class SemanticScholarSearch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    total: int | None = None
    data: tuple[SemanticScholarPaper, ...]


class SemanticScholarClient:
    """Consulta por DOI, correspondência bibliográfica e busca de artigos."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.semanticscholar.org/graph/v1",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http: ScholarlyHTTPClient | None = None,
    ) -> None:
        self.api_key = settings.semantic_scholar_api_key if api_key is None else api_key
        self.base_url = base_url.rstrip("/")
        self.http = http or ScholarlyHTTPClient("semantic_scholar", timeout=timeout)

    def by_doi(self, doi: str) -> SemanticScholarPaper | None:
        normalized = normalize_doi(doi)
        response = self.http.get(
            f"{self.base_url}/paper/DOI:{quote(normalized, safe='')}",
            params={"fields": PAPER_FIELDS},
            headers=self._headers(),
            doi=normalized,
            not_found_ok=True,
        )
        return (
            None
            if response is None
            else SemanticScholarPaper.model_validate(json_payload(response))
        )

    def match(self, query: str) -> SemanticScholarPaper | None:
        if not query.strip():
            raise ValueError("A correspondência exige texto.")
        response = self.http.get(
            f"{self.base_url}/paper/search/match",
            params={"query": query, "fields": PAPER_FIELDS},
            headers=self._headers(),
        )
        assert response is not None
        payload = json_payload(response)
        if not payload:
            return None
        return SemanticScholarPaper.model_validate(payload)

    def search(self, query: str, *, limit: int = 10) -> SemanticScholarSearch:
        if not query.strip() or not 1 <= limit <= 100:
            raise ValueError("A busca exige texto e limit entre 1 e 100.")
        return self._search(
            f"{self.base_url}/paper/search",
            {"query": query, "limit": limit, "fields": PAPER_FIELDS},
        )

    def _search(self, url: str, params: dict[str, str | int]) -> SemanticScholarSearch:
        response = self.http.get(url, params=params, headers=self._headers())
        assert response is not None
        payload = json_payload(response)
        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("A resposta do Semantic Scholar não contém data[].")
        return SemanticScholarSearch.model_validate(payload)

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}
