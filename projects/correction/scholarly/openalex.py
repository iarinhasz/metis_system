"""Leitura paginada da taxonomia pública do OpenAlex."""

import json
import time
from typing import Annotated
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.metis.config import settings
from projects.correction.scholarly.cache import normalize_doi
from projects.correction.scholarly.http import (
    DEFAULT_TIMEOUT_SECONDS,
    ScholarlyHTTPClient,
    json_payload,
)

Name = Annotated[str, Field(min_length=1, max_length=512, strict=True)]


class OpenAlexEntity(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: Annotated[str, Field(min_length=1, max_length=128, strict=True)]
    display_name: Name


class OpenAlexField(OpenAlexEntity):
    domain: OpenAlexEntity


class OpenAlexSubfield(OpenAlexField):
    field: OpenAlexEntity


class OpenAlexTopic(OpenAlexSubfield):
    subfield: OpenAlexEntity


class OpenAlexTaxonomy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    domains: tuple[OpenAlexEntity, ...] = ()
    fields: tuple[OpenAlexField, ...] = ()
    subfields: tuple[OpenAlexSubfield, ...] = ()
    topics: tuple[OpenAlexTopic, ...]


class PageMeta(BaseModel):
    count: Annotated[int, Field(gt=0, strict=True)]
    page: Annotated[int, Field(gt=0, strict=True)]
    per_page: Annotated[int, Field(gt=0, le=100, strict=True)]


class EntityPage[T: OpenAlexEntity](BaseModel):
    meta: PageMeta
    results: list[T]


TopicPage = EntityPage[OpenAlexTopic]


class OpenAlexClient:
    """Leitura dos quatro níveis, inclusive ramos sem topics, com paginação conferida."""

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "https://api.openalex.org",
        per_page: int = 100,
    ) -> None:
        if not 1 <= per_page <= 100:
            raise ValueError("O tamanho da página deve ficar entre 1 e 100.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.per_page = per_page

    def topics(self) -> tuple[OpenAlexTopic, ...]:
        return self._read("topics", TopicPage, "id,display_name,domain,field,subfield")

    def taxonomy(self) -> OpenAlexTaxonomy:
        domains = self._read("domains", EntityPage[OpenAlexEntity], "id,display_name")
        time.sleep(1)
        fields = self._read("fields", EntityPage[OpenAlexField], "id,display_name,domain")
        time.sleep(1)
        subfields = self._read(
            "subfields", EntityPage[OpenAlexSubfield], "id,display_name,domain,field"
        )
        time.sleep(1)
        return OpenAlexTaxonomy(
            domains=domains, fields=fields, subfields=subfields, topics=self.topics()
        )

    def _read[T: OpenAlexEntity](
        self, endpoint: str, page_type: type[EntityPage[T]], select: str
    ) -> tuple[T, ...]:
        entities: dict[str, T] = {}
        expected: int | None = None
        page = 1
        while True:
            params = {
                "page": str(page),
                "per_page": str(self.per_page),
                "sort": "id",
                "select": select,
            }
            if self.api_key:
                params["api_key"] = self.api_key
            request = Request(
                f"{self.base_url}/{endpoint}?{urlencode(params)}",
                headers={"Accept": "application/json", "User-Agent": "Metis-taxonomy/1"},
            )
            with urlopen(request, timeout=30) as response:
                result = page_type.model_validate(json.load(response))
            if result.meta.page != page or result.meta.per_page != self.per_page:
                raise ValueError("O OpenAlex devolveu uma página diferente da solicitada.")
            if expected is None:
                expected = result.meta.count
            if result.meta.count != expected or expected > 10_000:
                raise ValueError("A contagem do OpenAlex mudou ou excede a paginação suportada.")
            if not result.results or len(result.results) > self.per_page:
                raise ValueError("Página vazia ou inválida antes do fim da taxonomia.")
            for entity in result.results:
                if entity.id in entities:
                    raise ValueError("O OpenAlex repetiu um identificador entre páginas.")
                entities[entity.id] = entity
            if len(entities) == expected:
                return tuple(entities.values())
            if len(entities) > expected or len(result.results) < self.per_page:
                raise ValueError("A resposta do OpenAlex está incompleta ou tem contagem inválida.")
            page += 1
            time.sleep(1)


class OpenAlexLocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    landing_page_url: str | None = None
    pdf_url: str | None = None
    source: dict[str, object] | None = None


class OpenAlexWork(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    doi: str | None = None
    title: str | None = None
    publication_year: int | None = None
    is_retracted: bool = False
    abstract_inverted_index: dict[str, list[int]] | None = None
    open_access: dict[str, object] | None = None
    best_oa_location: OpenAlexLocation | None = None


class OpenAlexWorkSearch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    results: tuple[OpenAlexWork, ...]
    meta: dict[str, object] = Field(default_factory=dict)


class OpenAlexWorksClient:
    """Consulta obras sem alterar a API de taxonomia de `OpenAlexClient`."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openalex.org",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http: ScholarlyHTTPClient | None = None,
    ) -> None:
        self.api_key = settings.openalex_api_key if api_key is None else api_key
        self.base_url = base_url.rstrip("/")
        self.http = http or ScholarlyHTTPClient("openalex", timeout=timeout)

    def by_doi(self, doi: str) -> OpenAlexWork | None:
        normalized = normalize_doi(doi)
        params = {"api_key": self.api_key} if self.api_key else None
        response = self.http.get(
            f"{self.base_url}/works/https://doi.org/{quote(normalized, safe='/')}",
            params=params,
            doi=normalized,
            not_found_ok=True,
        )
        return None if response is None else OpenAlexWork.model_validate(json_payload(response))

    def search(self, query: str, *, per_page: int = 10) -> OpenAlexWorkSearch:
        if not query.strip() or not 1 <= per_page <= 100:
            raise ValueError("A busca exige texto e per_page entre 1 e 100.")
        params: dict[str, str | int] = {"search": query, "per-page": per_page}
        if self.api_key:
            params["api_key"] = self.api_key
        response = self.http.get(f"{self.base_url}/works", params=params)
        assert response is not None
        return OpenAlexWorkSearch.model_validate(json_payload(response))
