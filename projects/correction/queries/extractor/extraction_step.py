"""Consultas e gravação de ExtractionStep (as respostas do modelo guardadas durante o E1)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import connection

if TYPE_CHECKING:
    from django.db import models

    from projects.correction.extractor.models import ExtractionStep


class ExtractionStepManagement:
    """Herdado por `ExtractionStep`. Uso: `ExtractionStep.stored(sha256, version)`."""

    objects: ClassVar[models.Manager[ExtractionStep]]

    @classmethod
    def stored(cls, sha256: str, version: str) -> dict[str, Any]:
        """As respostas guardadas daquele PDF e daquela versão do extractor, pela chave."""
        rows = cls.objects.filter(sha256=sha256, version=version).values_list("key", "answer")
        return dict(rows)

    @classmethod
    def store(cls, sha256: str, version: str, key: str, answer: Any) -> None:
        """Guarda a resposta de um passo; se a chave já está guardada, fica a que está.

        Roda nas threads das chamadas em paralelo. O Django abre uma conexão por thread e não
        a fecha sozinho: fora da thread principal, ela é fechada aqui."""
        try:
            cls.objects.get_or_create(
                sha256=sha256, version=version, key=key, defaults={"answer": answer}
            )
        finally:
            if threading.current_thread() is not threading.main_thread():
                connection.close()

    @classmethod
    def forget(cls, sha256: str, version: str) -> None:
        cls.objects.filter(sha256=sha256, version=version).delete()
