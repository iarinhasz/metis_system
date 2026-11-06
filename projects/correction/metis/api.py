"""Composição da API Ninja com autenticação fechada por padrão."""

from django.http import HttpRequest
from ninja import NinjaAPI

from projects.correction.attempts.api import health_check
from projects.correction.attempts.api import router as attempts_router
from projects.correction.metis.authentication import DenyAllAuth
from projects.correction.metis.config import settings

api = NinjaAPI(
    title="Metis API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    auth=DenyAllAuth(),
)
api.add_router("/api/", attempts_router)


@api.get("/health/", auth=None)
def health(request: HttpRequest) -> tuple[int, dict[str, str]]:
    del request
    return health_check()
