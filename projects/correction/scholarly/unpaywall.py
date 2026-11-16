"""Cliente Unpaywall para localizar versões Open Access por DOI."""

from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.metis.config import settings
from projects.correction.scholarly.cache import normalize_doi
from projects.correction.scholarly.http import (
    DEFAULT_TIMEOUT_SECONDS,
    ScholarlyHTTPClient,
    json_payload,
)


class UnpaywallLocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    url: str | None = None
    url_for_pdf: str | None = None
    host_type: str | None = None
    license: str | None = None
    version: str | None = None
    is_best: bool = False


class UnpaywallWork(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    doi: str
    is_oa: bool = Field(validation_alias="is_oa")
    best_oa_location: UnpaywallLocation | None = None
    oa_locations: tuple[UnpaywallLocation, ...] = ()
    title: str | None = None
    year: int | None = None


class UnpaywallClient:
    """Consulta os metadados de acesso aberto do Unpaywall."""

    def __init__(
        self,
        *,
        email: str | None = None,
        base_url: str = "https://api.unpaywall.org/v2",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http: ScholarlyHTTPClient | None = None,
    ) -> None:
        self.email = settings.unpaywall_email if email is None else email
        self.base_url = base_url.rstrip("/")
        self.http = http or ScholarlyHTTPClient("unpaywall", timeout=timeout)

    def by_doi(self, doi: str) -> UnpaywallWork | None:
        normalized = normalize_doi(doi)
        if not self.email:
            raise ValueError("Unpaywall exige METIS_UNPAYWALL_EMAIL.")
        response = self.http.get(
            f"{self.base_url}/{quote(normalized, safe='')}",
            params={"email": self.email},
            doi=normalized,
            not_found_ok=True,
        )
        return None if response is None else UnpaywallWork.model_validate(json_payload(response))
