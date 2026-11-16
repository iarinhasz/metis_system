"""Cliente de busca arXiv com parser de Atom."""

from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict

from projects.correction.scholarly.errors import ScholarlyClientError
from projects.correction.scholarly.http import DEFAULT_TIMEOUT_SECONDS, ScholarlyHTTPClient

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPEN_SEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class ArxivAuthor(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class ArxivEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    summary: str
    published: str
    updated: str
    authors: tuple[ArxivAuthor, ...]
    doi: str | None = None
    categories: tuple[str, ...] = ()


class ArxivSearch(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_results: int
    entries: tuple[ArxivEntry, ...]


class ArxivClient:
    """Consulta o endpoint público export.arxiv.org/api/query."""

    def __init__(
        self,
        *,
        base_url: str = "https://export.arxiv.org/api/query",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http: ScholarlyHTTPClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.http = http or ScholarlyHTTPClient("arxiv", timeout=timeout)

    def search(self, query: str, *, max_results: int = 10) -> ArxivSearch:
        if not query.strip() or not 1 <= max_results <= 100:
            raise ValueError("A busca exige texto e max_results entre 1 e 100.")
        response = self.http.get(
            self.base_url,
            params={"search_query": query, "start": 0, "max_results": max_results},
            headers={"Accept": "application/atom+xml"},
        )
        assert response is not None
        try:
            root = ElementTree.fromstring(response.body)
        except ElementTree.ParseError as exc:
            raise ScholarlyClientError("O arXiv devolveu XML Atom inválido.") from exc
        entries = tuple(self._entry(element) for element in root.findall(f"{ATOM}entry"))
        total = root.findtext(f"{OPEN_SEARCH}totalResults")
        try:
            total_results = int(total or "0")
        except ValueError as exc:
            raise ScholarlyClientError("O arXiv devolveu totalResults inválido.") from exc
        return ArxivSearch(total_results=total_results, entries=entries)

    @staticmethod
    def _entry(element: ElementTree.Element) -> ArxivEntry:
        def required(name: str) -> str:
            value = element.findtext(f"{ATOM}{name}")
            if not value:
                raise ScholarlyClientError(f"Entrada arXiv sem {name}.")
            return value.strip()

        authors = tuple(
            ArxivAuthor(name=(author.findtext(f"{ATOM}name") or "").strip())
            for author in element.findall(f"{ATOM}author")
        )
        doi = element.findtext(f"{ARXIV}doi")
        categories = tuple(
            category.attrib["term"]
            for category in element.findall(f"{ATOM}category")
            if "term" in category.attrib
        )
        entry_id = required("id")
        return ArxivEntry(
            id=entry_id,
            title=required("title"),
            summary=required("summary"),
            published=required("published"),
            updated=required("updated"),
            authors=authors,
            doi=doi.strip() if doi else None,
            categories=categories,
        )
