"""Schema mínimo do catálogo; os contratos de domínio entram em suas etapas."""

from pydantic import BaseModel, ConfigDict, Field


class PendingOutput(BaseModel):
    """Saída temporária para exercitar a fábrica sem antecipar contratos de M2–M5."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    summary: str = Field(min_length=1, examples=["Resposta sintética de desenvolvimento."])
