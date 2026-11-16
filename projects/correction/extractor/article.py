"""O artigo dividido em seções: o que o extractor entrega."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from projects.correction.extractor.contract import HiddenTextFinding


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


class Reference(BaseModel):
    """Uma entrada da lista de referências: como o autor escreveu (`raw`) e já separada."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    raw: str
    marker: str | None
    authors: tuple[str, ...]
    title: str | None
    year: str | None
    venue: str | None
    doi: str | None
    arxiv_id: str | None


class Citation(BaseModel):
    """Uma chamada no texto de uma seção. `start` e `end` são offsets do `marker` no texto da
    seção; `reference_id` é None quando nenhuma entrada da lista (ou mais de uma) corresponde."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: str | None
    marker: str
    sentence: str
    section_id: str
    start: int
    end: int


class FigureDescription(BaseModel):
    """O que o modelo leu numa figura ou tabela (1.8). Não tem como conferir contra o PDF."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    figure_class: str
    description: str
    data_read: tuple[str, ...]
    # Nulo quando o texto não afirma nada sobre a figura.
    supports_claims: bool | None
    support_rationale: str
    issues: tuple[str, ...]
    table_markdown: str | None


class Figure(BaseModel):
    """Uma figura ou tabela, com a legenda conferida contra o texto do PDF."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: Literal["figure", "table"]
    label: str
    # O número do rótulo ("3", "A.1"), que liga as chamadas no texto à figura.
    number: str | None
    page: int
    caption: str
    # Fração da legenda que está no texto do PDF; None quando não deu para verificar.
    fidelity: float | None
    # Nula antes da 1.8, com `describe_figures` desligado ou quando a chamada falhou.
    description: FigureDescription | None = None


class FigureMention(BaseModel):
    """Uma chamada a uma figura ou tabela no texto de uma seção ("Fig. 3", "Tabela 2"),
    com offsets no texto da seção; `figure_id` é None quando o rótulo não está na lista."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    figure_id: str | None
    marker: str
    sentence: str
    section_id: str
    start: int
    end: int


class ExtractedArticle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    authors: tuple[str, ...]
    language: str
    # Quem dividiu o artigo (provedor/modelo), para saber de onde veio cada versão.
    model: str
    sections: tuple[ExtractedSection, ...]
    # Vazias nas extrações feitas antes da 1.10.
    references: tuple[Reference, ...] = ()
    citations: tuple[Citation, ...] = ()
    # Vazias nas extrações feitas antes da 1.6.
    figures: tuple[Figure, ...] = ()
    figure_mentions: tuple[FigureMention, ...] = ()
    hidden_text_findings: tuple[HiddenTextFinding, ...] = ()

    @property
    def has_footnotes(self) -> bool:
        return any(section.has_footnotes for section in self.sections)

    def section(self, key: str) -> ExtractedSection | None:
        return next((section for section in self.sections if section.key == key), None)
