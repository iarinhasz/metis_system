"""A mesma falha passageira que o pipeline já reconhece para retry."""

from projects.correction.pipeline.errors import LLMUnavailable as LLMUnavailable


class MissingProviderKey(ValueError):
    """A criação de um cliente exige a chave explícita do provedor."""
