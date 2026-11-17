"""O formato da resposta de cada chamada ao modelo.

Os campos viram o JSON schema que o modelo é obrigado a seguir (saída estruturada). Por isso
todos são obrigatórios e nada além deles é aceito.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScannedHeading(_Output):
    title: str = Field(description="O título como está no documento, com a numeração.")
    level: int = Field(ge=1, description="1 para seção, 2 para subseção, 3 para a subseção dela.")


class HeadingScan(_Output):
    """Resposta da chamada 1: o mapa do documento, sem o conteúdo."""

    title: str = Field(description="Título do artigo.")
    authors: tuple[str, ...] = Field(description="Nomes dos autores, na ordem do documento.")
    language: str = Field(description="Idioma do texto principal, em ISO 639-1 (pt, en, es).")
    headings: tuple[ScannedHeading, ...] = Field(
        description="Títulos das seções, na ordem em que aparecem."
    )


class SectionContent(_Output):
    """Resposta da chamada 2, feita uma vez por seção do mapa."""

    text: str = Field(description="O texto da seção, copiado literalmente do documento.")
    has_footnotes: bool = Field(description="Se a seção chama alguma nota de rodapé.")


class ParsedReference(_Output):
    raw: str = Field(description="A entrada inteira, copiada literalmente da lista.")
    marker: str | None = Field(description="A marca da entrada na lista, se houver: [3], 3. ou 3.")
    authors: tuple[str, ...] = Field(
        description="Os autores na ordem, como escritos na entrada ('Silva, A.' ou 'Ana Silva')."
    )
    title: str | None = Field(description="O título da obra citada.")
    year: str | None = Field(description="O ano, com o sufixo quando houver: 2020 ou 2020a.")
    venue: str | None = Field(
        description="Onde saiu: revista, conferência, editora ou repositório."
    )
    doi: str | None = Field(description="O DOI, sem o prefixo https://doi.org/.")
    arxiv_id: str | None = Field(
        description="O identificador do arXiv, quando houver (ex.: 1602.03218)."
    )


class ParsedReferences(_Output):
    """Resposta da chamada que separa a lista de referências em campos."""

    references: tuple[ParsedReference, ...]


class ScannedFigure(_Output):
    label: str = Field(description="O rótulo como está no documento: 'Figure 3', 'Tabela 2'.")
    kind: Literal["figure", "table"] = Field(
        description="figure para figura, gráfico, diagrama ou foto; table para tabela."
    )
    page: int = Field(ge=1, description="A página do PDF em que ela está; a primeira é a 1.")
    caption: str = Field(description="A legenda inteira, copiada literalmente, com o rótulo.")


class FigureScan(_Output):
    """Resposta da chamada que lista as figuras e as tabelas do artigo."""

    figures: tuple[ScannedFigure, ...]


class DescribedFigure(_Output):
    """Resposta da chamada que descreve uma figura ou tabela."""

    caption_start: str = Field(
        description="As primeiras palavras da legenda da figura descrita, copiadas do PDF."
    )
    figure_class: str = Field(
        description="A classe: gráfico de linhas, de barras, de dispersão, diagrama, fluxograma, "
        "foto, mapa, tabela…"
    )
    description: str = Field(description="O que a figura mostra, em poucas frases.")
    data_read: tuple[str, ...] = Field(
        description="O que dá para ler nela: eixos e unidades, valores, tendências."
    )
    supports_claims: bool | None = Field(
        description="Se a figura sustenta o que o texto afirma sobre ela; nulo se o texto não "
        "afirma nada sobre ela."
    )
    support_rationale: str = Field(description="Por que sustenta ou não, citando o que se vê.")
    issues: tuple[str, ...] = Field(
        description="Problemas: eixo sem unidade, legenda que não bate com o desenho, texto "
        "ilegível, escala enganosa. Vazio se não houver."
    )
    table_markdown: str | None = Field(
        description="Para tabela, o conteúdo dela em markdown; para figura, nulo."
    )
