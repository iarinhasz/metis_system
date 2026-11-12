"""Tipagem do que o extractor precisa saber para dividir um tipo de documento.

Uma `DocumentConfig` diz como o documento vai ao modelo, qual modelo usar, os prompts das duas
chamadas (varredura dos títulos e extração do conteúdo) e as seções que o extractor procura pelo
nome. Os passos do extractor só leem a config; nada de tipo de documento fica espalhado no código.
"""

import re
import unicodedata
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

KEY_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")
# Marcadores do prompt da chamada 2, que é feita uma vez por seção do mapa: a seção pedida, onde
# ela termina (o título seguinte) e a instrução sobre as notas de rodapé.
TITLE_MARKER: Final = "<<title>>"
END_MARKER: Final = "<<end>>"
FOOTNOTES_MARKER: Final = "<<footnotes>>"
EXTRACTION_MARKERS: Final = (TITLE_MARKER, END_MARKER, FOOTNOTES_MARKER)
# Onde o texto da seção de referências entra no prompt que a separa em campos.
REFERENCES_MARKER: Final = "<<references>>"


class Provider(StrEnum):
    """Quem atende as chamadas. Um provedor novo entra junto com a implementação dele."""

    GOOGLE = "google"


class InputStrategy(StrEnum):
    """Como o documento vai ao modelo."""

    # Extrai o texto do PDF aqui e manda só o texto: mais barato, mas perde o layout.
    TEXT = "text"
    # Manda o PDF: o modelo lê colunas, tabelas e figuras como o leitor vê.
    PDF = "pdf"


class SectionDefinition(BaseModel):
    """Uma seção que o extractor procura pelo nome do título."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chave estável no resultado (`abstract`, `references`), em snake_case.
    key: str
    # Grafias aceitas para o título, em português e em inglês.
    labels: tuple[str, ...] = Field(min_length=1)

    @field_validator("key")
    @classmethod
    def _key_is_snake_case(cls, value: str) -> str:
        if not KEY_PATTERN.match(value):
            raise ValueError(f"key precisa ser snake_case: {value!r}")
        return value

    @field_validator("labels")
    @classmethod
    def _labels_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not label.strip() for label in value):
            raise ValueError("label vazio")
        return value


class DocumentConfig(BaseModel):
    """O que o extractor precisa saber de um tipo de documento."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    strategy: InputStrategy
    provider: Provider
    model: str
    # Chamada 1: só os títulos das seções, na ordem do documento.
    scan_prompt: str
    # Chamada 2, uma por seção mapeada na chamada 1: o texto daquela seção.
    extraction_prompt: str
    # Chamada que separa a lista de referências em campos (só com o texto, sem o PDF).
    references_prompt: str
    # Sem uma delas, o documento não pode ser avaliado e é rejeitado.
    required_sections: tuple[SectionDefinition, ...] = ()
    # Procuradas pelo nome quando existem; a falta não rejeita o documento.
    optional_sections: tuple[SectionDefinition, ...] = ()
    # True: o texto das notas de rodapé e as marcas que as chamam ficam fora das seções, e a
    # resposta só diz se a seção tinha nota. False: as notas vêm no fim da seção que as chama.
    ignore_footnotes: bool = True
    # Quantas chamadas da etapa 2 rodam ao mesmo tempo.
    max_parallel_calls: int = Field(default=4, ge=1)
    # Conferência de cada seção contra o texto do PDF (ver coverage.py). Abaixo de um dos
    # limites, a chamada daquela seção é refeita, com uma dica do que deu errado.
    # Cobertura: fração da prosa do PDF que veio na resposta (o modelo pulou texto?).
    min_coverage: float = Field(default=0.8, ge=0, le=1)
    # Fidelidade: fração da resposta que está na seção no PDF (trouxe texto de outra seção?).
    min_fidelity: float = Field(default=0.8, ge=0, le=1)
    # Quantas vezes refazer a chamada de uma seção reprovada; fica a melhor resposta.
    check_retries: int = Field(default=1, ge=0)

    @field_validator("name", "model", "scan_prompt", "extraction_prompt", "references_prompt")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("valor vazio")
        return value

    @field_validator("extraction_prompt")
    @classmethod
    def _extraction_prompt_has_the_markers(cls, value: str) -> str:
        for marker in EXTRACTION_MARKERS:
            if marker not in value:
                raise ValueError(f"extraction_prompt precisa do marcador {marker}")
        return value

    @field_validator("references_prompt")
    @classmethod
    def _references_prompt_has_the_marker(cls, value: str) -> str:
        if REFERENCES_MARKER not in value:
            raise ValueError(f"references_prompt precisa do marcador {REFERENCES_MARKER}")
        return value

    @model_validator(mode="after")
    def _sections_do_not_collide(self) -> DocumentConfig:
        keys = [definition.key for definition in self.all_sections]
        repeated_keys = sorted({key for key in keys if keys.count(key) > 1})
        if repeated_keys:
            raise ValueError(f"chaves repetidas entre as seções: {repeated_keys}")

        owner: dict[str, str] = {}
        for definition in self.all_sections:
            for label in definition.labels:
                normalized = normalize_label(label)
                if owner.setdefault(normalized, definition.key) != definition.key:
                    raise ValueError(
                        f"o título {label!r} aparece em {owner[normalized]!r} e em "
                        f"{definition.key!r}: não daria para saber a qual seção ele pertence"
                    )
        return self

    @property
    def all_sections(self) -> tuple[SectionDefinition, ...]:
        return self.required_sections + self.optional_sections


def normalize_label(label: str) -> str:
    """Forma de comparar títulos: sem acento, sem caixa e com os espaços normalizados."""
    decomposed = unicodedata.normalize("NFKD", label)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.casefold().split())
