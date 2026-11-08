"""Composição da API Ninja com autenticação fechada por padrão."""

from django.http import HttpRequest
from ninja import NinjaAPI, Status

from projects.correction.attempts.api import router as attempts_router
from projects.correction.metis.authentication import DenyAllAuth
from projects.correction.metis.config import settings
from projects.correction.queries.health import database_is_available

api = NinjaAPI(
    title="Metis API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    auth=DenyAllAuth(),
)
api.add_router("/api/", attempts_router)


@api.get("/health/", auth=None, response={200: dict[str, str], 503: dict[str, str]})
def health(request: HttpRequest) -> Status[dict[str, str]]:
    """Healthcheck do container: responde 503 quando o banco não atende."""
    del request
    if not database_is_available():
        return Status(503, {"status": "unavailable"})
    return Status(200, {"status": "ok"})
