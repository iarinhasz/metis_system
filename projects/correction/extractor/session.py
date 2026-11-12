"""A conversa com o modelo sobre um documento, pelo Agno: cada pergunta leva o documento e
devolve a resposta já validada no schema pedido.

Sem retry aqui (o Agno vem com `retries=0`): uma falha vira erro passageiro, e quem tenta de
novo, com backoff, é o Celery (ver docs/orchestration.md).
"""

import logging
from collections.abc import Callable
from typing import Any, Final, Protocol

from agno.agent import Agent
from agno.media import File
from agno.models.google import Gemini
from agno.run.base import RunStatus
from pydantic import BaseModel

from projects.correction.extractor.config import DocumentConfig, InputStrategy
from projects.correction.extractor.errors import (
    InvalidModelAnswer,
    MissingModelKey,
    ModelUnavailable,
)
from projects.correction.extractor.pdf_text import read_pdf_text
from projects.correction.metis.config import settings

# O Gemini aceita até 20 MB por pedido; um PDF maior vai como texto.
INLINE_LIMIT_BYTES: Final = 18 * 1024 * 1024
ERROR_DETAIL_CHARS: Final = 200


class DocumentSession(Protocol):
    def ask[T: BaseModel](self, prompt: str, output: type[T], *, with_document: bool = True) -> T:
        """Pergunta sobre o documento e devolve a resposta já validada no schema pedido.
        Com `with_document=False`, o prompt vai sozinho (ele já traz o texto que importa)."""
        ...


type SessionOpener = Callable[[DocumentConfig, bytes], DocumentSession]


class AgnoSession:
    def __init__(
        self,
        config: DocumentConfig,
        pdf: bytes,
        *,
        client_params: dict[str, Any] | None = None,
    ) -> None:
        if not settings.gemini_key:
            raise MissingModelKey("Falta a GEMINI_KEY no .env.")
        self._model = Gemini(
            id=config.model,
            api_key=settings.gemini_key,
            temperature=0,
            # Mapear e copiar não pede raciocínio: sem thinking, a chamada sai mais rápida e barata.
            thinking_budget=0,
            timeout=settings.llm_timeout_seconds,
            client_params=client_params,
        )
        if config.strategy is InputStrategy.PDF and len(pdf) <= INLINE_LIMIT_BYTES:
            self._file: File | None = File(content=pdf, mime_type="application/pdf")
            self._text: str | None = None
        else:
            self._file, self._text = None, read_pdf_text(pdf)

    def ask[T: BaseModel](self, prompt: str, output: type[T], *, with_document: bool = True) -> T:
        agent = Agent(model=self._model, output_schema=output, telemetry=False)
        if not with_document:
            run = agent.run(prompt)
        elif self._file is not None:
            run = agent.run(prompt, files=[self._file])
        else:
            # O artigo vem primeiro, entre delimitadores, marcado como dado.
            run = agent.run(f"<artigo>\n{self._text}\n</artigo>\n\n{prompt}")

        if run.status != RunStatus.completed:
            detail = str(run.content or "")[:ERROR_DETAIL_CHARS]
            raise ModelUnavailable(f"O modelo {self._model.id} falhou: {detail}")
        if not isinstance(run.content, output):
            raise InvalidModelAnswer(
                f"Resposta do modelo vazia, cortada ou fora do schema {output.__name__}."
            )
        return run.content


class _OnlyErrors(logging.Filter):
    """O Agno registra em warning a resposta que não bateu com o schema, e ela traz texto do
    manuscrito, que não pode ir para o log. Só os erros passam. O filtro fica no logger, e não
    no nível, porque o Agno redefine o nível a cada execução."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR


logging.getLogger("agno").addFilter(_OnlyErrors())
