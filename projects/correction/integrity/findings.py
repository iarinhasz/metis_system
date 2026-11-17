"""O que o E3 encontra: cada achado tem um tipo, uma gravidade, uma mensagem e a evidência."""

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, JsonValue


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


SEVERITY_ORDER: Final = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2}


class FindingKind(StrEnum):
    # Fase 0: o texto escondido que o E1 achou no PDF (1.7).
    HIDDEN_INSTRUCTION = "hidden_instruction"
    HIDDEN_TEXT = "hidden_text"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: FindingKind
    severity: Severity
    # Sem texto do manuscrito: a mensagem vai para o relatório final.
    message: str
    # O que mostrar lado a lado no gate: o trecho do artigo e, quando há, a fonte.
    evidence: dict[str, JsonValue] = {}
