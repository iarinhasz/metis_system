"""Falhas do extractor, já na forma que o pipeline entende (retry, rejeição ou erro)."""

from projects.correction.pipeline.errors import InvalidSubmission, LLMUnavailable, SetupRequired


class ModelUnavailable(LLMUnavailable):
    """A chamada ao modelo falhou (fora do ar, sem cota, timeout): o estágio tenta de novo."""


class InvalidModelAnswer(LLMUnavailable):
    """Resposta vazia, cortada ou fora do schema: o estágio tenta de novo."""


class MissingModelKey(SetupRequired):
    """Falta a chave do provedor no .env."""


class UnreadablePdf(InvalidSubmission):
    """O PDF não abre ou não tem texto."""


class MissingRequiredSections(InvalidSubmission):
    """O documento não tem uma seção obrigatória (ex.: abstract ou referências)."""
