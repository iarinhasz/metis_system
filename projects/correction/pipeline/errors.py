"""Erros que um estágio levanta para dizer ao pipeline como tratar a falha."""

from typing import ClassVar

from projects.correction.attempts.status import RunStatus


class StageError(Exception):
    """Base dos erros de estágio; cada subclasse define o status em que o run termina."""

    failure_status: ClassVar[RunStatus]


class TransientStageError(StageError):
    """Falha passageira de serviço externo (GROBID, Crossref): retry com backoff."""

    failure_status = RunStatus.ERROR_EXTERNAL


class LLMUnavailable(TransientStageError):
    """Provedor de LLM indisponível (429, 5xx, timeout): retry com backoff."""

    failure_status = RunStatus.ERROR_LLM


class InvalidEvaluationOutput(LLMUnavailable):
    """Saída do avaliador fora do schema ou incompatível com a seção solicitada."""


class InvalidSubmission(StageError):
    """O PDF não pode ser avaliado (sem texto, sem abstract, criptografado). Sem retry."""

    failure_status = RunStatus.REJECTED_INVALID_SUBMISSION


class SetupRequired(StageError):
    """Falta configuração para seguir (ex.: nenhuma Question disponível). Sem retry."""

    failure_status = RunStatus.WAITING_SETUP
