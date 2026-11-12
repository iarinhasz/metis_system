"""O formato da resposta de cada chamada ao modelo.

Os campos viram o JSON schema que o modelo é obrigado a seguir (saída estruturada). Por isso
todos são obrigatórios e nada além deles é aceito.
"""

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
