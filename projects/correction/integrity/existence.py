"""Classificação de existência e consistência dos metadados bibliográficos."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from projects.correction.agents.factory import AgentFactory
from projects.correction.extractor.contract import DocumentReference
from projects.correction.integrity.resolution import ReferenceResolution
from projects.correction.pipeline.errors import InvalidEvaluationOutput

ExistenceStatus = Literal["ok", "metadata_mismatch", "not_found"]


class ReferenceAdjudication(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ExistenceStatus
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    rationale: str = Field(min_length=1, max_length=4000)


class ReferenceExistence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_id: str
    status: ExistenceStatus
    resolution: ReferenceResolution
    adjudicated: bool = False
    rationale: str = ""


class _Runner(Protocol):
    def run(self, payload: str) -> object: ...


Adjudicator = Callable[[DocumentReference, ReferenceResolution], ReferenceAdjudication]


def check_reference_existence(
    references: Sequence[DocumentReference],
    resolutions: Sequence[ReferenceResolution],
    *,
    factory: AgentFactory | None = None,
    adjudicator: Adjudicator | None = None,
) -> tuple[ReferenceExistence, ...]:
    """Adjudica somente resultados que não puderam ser aceitos automaticamente."""
    resolution_by_id = {item.reference_id: item for item in resolutions}
    if set(resolution_by_id) != {item.id for item in references}:
        raise ValueError("As referências e as resoluções devem corresponder exatamente.")

    def judge(reference: DocumentReference, result: ReferenceResolution) -> ReferenceAdjudication:
        if adjudicator is not None:
            return adjudicator(reference, result)
        if factory is None:
            raise ValueError("Uma fábrica ou adjudicador é necessário para casos duvidosos.")
        runner = factory.reference_adjudicator(output_schema=ReferenceAdjudication)
        output = runner.run(
            "Determine se a referência é real usando somente os dados fornecidos. "
            "Não infira uma correspondência sem evidência.\n"
            f"Referência original: {reference.raw}\n"
            f"Estado da resolução: {result.status}\n"
            f"Metadados encontrados: {result.model_dump(mode='json')!r}"
        )
        content = getattr(output, "content", None)
        if not getattr(output, "valid", False) or not isinstance(content, ReferenceAdjudication):
            raise InvalidEvaluationOutput("O adjudicador de referências devolveu saída inválida.")
        return content

    outcomes: list[ReferenceExistence] = []
    for reference in references:
        resolution = resolution_by_id[reference.id]
        if resolution.status == "ok":
            outcomes.append(
                ReferenceExistence(
                    reference_id=reference.id,
                    status="ok",
                    resolution=resolution,
                    rationale="Correspondência aceita pela cascata de provedores.",
                )
            )
            continue
        decision = judge(reference, resolution)
        outcomes.append(
            ReferenceExistence(
                reference_id=reference.id,
                status=decision.status,
                resolution=resolution,
                adjudicated=True,
                rationale=decision.rationale,
            )
        )
    return tuple(outcomes)
