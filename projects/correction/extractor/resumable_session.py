"""A sessão que retoma: guarda no banco cada resposta do modelo e, no retry do estágio, devolve
as já guardadas sem chamar o modelo de novo.

O retry segue o mesmo caminho da primeira vez, porque cada prompt depende só das respostas
anteriores: o mapa dá os prompts das seções, os textos dão o das referências, a lista dá os das
descrições. Ele só chama o modelo a partir de onde parou.

A chave de cada resposta é o hash do prompt, do schema pedido e de `with_document`. O sha256
do PDF e a versão do extractor (config e prompts) separam um artigo e uma versão das outras.
"""

import hashlib
import json
import logging
from functools import cache

from pydantic import BaseModel

from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.models import ExtractionStep
from projects.correction.extractor.session import DocumentSession, SessionOpener

logger = logging.getLogger(__name__)


class ResumableSession:
    def __init__(self, session: DocumentSession, sha256: str, version: str) -> None:
        self._session = session
        self._sha256, self._version = sha256, version
        # Lidas uma vez, na thread principal: as threads das chamadas só leem da memória.
        self._stored = ExtractionStep.stored(sha256, version)
        if self._stored:
            logger.info(
                "Extração %s retomada com %d respostas guardadas.", sha256[:12], len(self._stored)
            )

    def ask[T: BaseModel](self, prompt: str, output: type[T], *, with_document: bool = True) -> T:
        key = step_key(prompt, output, with_document=with_document)
        if (stored := self._stored.get(key)) is not None:
            return output.model_validate(stored)
        answer = self._session.ask(prompt, output, with_document=with_document)
        ExtractionStep.store(self._sha256, self._version, key, answer.model_dump(mode="json"))
        return answer


def resumable(opener: SessionOpener, sha256: str, version: str) -> SessionOpener:
    """O mesmo opener, com a sessão que guarda e retoma as respostas daquele PDF."""

    def open_session(config: DocumentConfig, pdf: bytes) -> DocumentSession:
        return ResumableSession(opener(config, pdf), sha256, version)

    return open_session


def step_key(prompt: str, output: type[BaseModel], *, with_document: bool) -> str:
    payload = "\n".join((_schema(output), str(with_document), prompt))
    return hashlib.sha256(payload.encode()).hexdigest()


@cache
def _schema(output: type[BaseModel]) -> str:
    """O schema entra na chave: mudar um schema no código não reaproveita a resposta antiga."""
    return json.dumps(output.model_json_schema(), sort_keys=True)
