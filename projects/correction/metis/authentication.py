"""Autenticação por bearer token para a API interna."""

import hmac

from django.http import HttpRequest
from ninja.security import HttpBearer

from projects.correction.metis.config import settings


class ServiceBearerAuth(HttpBearer):
    """Valida o token do serviço sem comparação sensível a tempo."""

    def authenticate(self, request: HttpRequest, token: str) -> bool:
        configured_token = settings.api_token
        if not configured_token:
            return False
        return hmac.compare_digest(token.encode("utf-8"), configured_token.encode("utf-8"))


class DenyAllAuth(HttpBearer):
    """Autenticação padrão fechada para rotas sem política explícita."""

    def authenticate(self, request: HttpRequest, token: str) -> None:
        return None
