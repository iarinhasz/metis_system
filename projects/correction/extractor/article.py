"""O artigo dividido em seções: o que o extractor entrega."""

from pydantic import BaseModel, ConfigDict


class ExtractedSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    level: int
    parent_id: str | None
    key: str | None
    text: str
    has_footnotes: bool
    # Conferência contra o texto do PDF (ver coverage.py); None quando não deu para verificar.
    # Cobertura abaixo do min_coverage da config: pode faltar texto.
    coverage: float | None
    # Fidelidade abaixo do min_fidelity: pode haver texto que não é desta seção.
    fidelity: float | None


class ExtractedArticle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    authors: tuple[str, ...]
    language: str
    # Quem dividiu o artigo (provedor/modelo), para saber de onde veio cada versão.
    model: str
    sections: tuple[ExtractedSection, ...]

    @property
    def has_footnotes(self) -> bool:
        return any(section.has_footnotes for section in self.sections)

    def section(self, key: str) -> ExtractedSection | None:
        return next((section for section in self.sections if section.key == key), None)
