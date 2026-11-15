"""O meta-revisor escreve narrativa referenciada; notas não fazem parte de sua saída."""

from pydantic import Field

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import Output, Text


class MetaPoint(Output):
    text: Text
    criterion_keys: tuple[Criterion, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class MetaReview(Output):
    strengths: tuple[MetaPoint, ...] = ()
    weaknesses: tuple[MetaPoint, ...] = ()
    suggestions: tuple[MetaPoint, ...] = ()
