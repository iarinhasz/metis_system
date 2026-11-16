"""Erros tipados dos clientes de APIs acadêmicas."""

from projects.correction.pipeline.errors import TransientStageError


class ScholarlyError(Exception):
    """Falha permanente ou resposta inválida de uma API acadêmica."""


class ScholarlyClientError(ScholarlyError):
    """Resposta HTTP não transitória ou payload inválido."""


class ScholarlyTransientError(ScholarlyError, TransientStageError):
    """Falha de rede ou resposta transitória após as tentativas do cliente."""
