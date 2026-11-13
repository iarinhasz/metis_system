"""O rascunho contextualiza critérios fixos; não altera a escala nem os pesos."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from projects.correction.agents.schemas.criteria import Criterion


class DraftRubric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    key: Criterion
    label: str = Field(min_length=1, max_length=255)
    rubric_text: str = Field(min_length=1, max_length=20_000)


EXAMPLE_RUBRICS = [
    {"key": key.value, "label": key.value, "rubric_text": "Contexto do domínio para este critério."}
    for key in Criterion
]


class DraftQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1, max_length=255, examples=["Perfil de avaliação da área"])
    rubric_fields: tuple[DraftRubric, ...] = Field(
        min_length=7, max_length=7, examples=[EXAMPLE_RUBRICS]
    )

    @model_validator(mode="after")
    def complete_rubric(self) -> DraftQuestion:
        if not self.name.strip() or any(
            not field.label.strip() or not field.rubric_text.strip() for field in self.rubric_fields
        ):
            raise ValueError("Nome, rótulos e textos da rubrica não podem ser vazios.")
        if {field.key for field in self.rubric_fields} != set(Criterion):
            raise ValueError("O rascunho deve contextualizar uma vez cada critério.")
        return self
