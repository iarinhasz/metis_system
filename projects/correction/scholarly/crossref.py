"""Cliente Crossref para metadados bibliográficos e eventos de retratação."""

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


class CrossrefWork(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    doi: str = Field(validation_alias=AliasChoices("DOI", "doi"))
    title: tuple[str, ...] = ()
    author: tuple[dict[str, Any], ...] = ()
    published: dict[str, Any] | None = None
    abstract: str | None = None
    update_to: tuple[dict[str, Any], ...] = Field(
        default=(), validation_alias=AliasChoices("update-to", "update_to")
    )
    updated_by: tuple[dict[str, Any], ...] = Field(
        default=(), validation_alias=AliasChoices("updated-by", "updated_by")
    )


class CrossrefWorks(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    items: tuple[CrossrefWork, ...]
    total_results: int = Field(validation_alias=AliasChoices("total-results", "total_results"))


class CrossrefClient:
    """Consulta obras pelo DOI ou por string bibliográfica."""

    def __init__(
        self,
        *,
        mailto: str | None = None,
        base_url: str = "https://api.crossref.org",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http: ScholarlyHTTPClient | None = None,
    ) -> None:
        self.mailto = settings.crossref_mailto if mailto is None else mailto
        self.base_url = base_url.rstrip("/")
        self.http = http or ScholarlyHTTPClient("crossref", timeout=timeout)

    def by_doi(self, doi: str) -> CrossrefWork | None:
        normalized = normalize_doi(doi)
        response = self.http.get(
            f"{self.base_url}/works/{quote(normalized, safe='/')}",
            params={"mailto": self.mailto} if self.mailto else None,
            doi=normalized,
            not_found_ok=True,
        )
        if response is None:
            return None
        message = json_payload(response).get("message")
        if not isinstance(message, dict):
            raise ValueError("A resposta do Crossref não contém message.")
        return CrossrefWork.model_validate(message)

    def search(self, query: str, *, rows: int = 10) -> CrossrefWorks:
        if not query.strip() or rows < 1:
            raise ValueError("A busca exige texto e rows positivo.")
        params: dict[str, str | int] = {"query.bibliographic": query, "rows": rows}
        if self.mailto:
            params["mailto"] = self.mailto
        response = self.http.get(f"{self.base_url}/works", params=params)
        assert response is not None
        message = json_payload(response).get("message")
        if not isinstance(message, dict):
            raise ValueError("A resposta do Crossref não contém message.")
        return CrossrefWorks.model_validate(message)
