"""As configs de cada tipo de documento. Hoje o Metis avalia um só: o artigo científico.

As seções obrigatórias são as que o gate de qualidade exige (abstract e referências). O papel
das demais (introdução, método, resultados…) é dado pelo E2, nos papéis das seções, e não aqui.
"""

from typing import Final

from projects.correction.extractor.config import (
    DocumentConfig,
    InputStrategy,
    Provider,
    SectionDefinition,
)
from projects.correction.extractor.prompts import load_prompt

ARTICLE_CONFIG: Final = DocumentConfig(
    name="scientific_article",
    # O PDF vai inteiro: artigo em duas colunas, com tabelas e fórmulas, se perde no texto puro.
    strategy=InputStrategy.PDF,
    provider=Provider.GOOGLE,
    model="gemini-2.5-flash",
    scan_prompt=load_prompt("scan_headings"),
    extraction_prompt=load_prompt("extract_section"),
    references_prompt=load_prompt("parse_references"),
    required_sections=(
        SectionDefinition(key="abstract", labels=("Abstract", "Resumo", "Resumen")),
        SectionDefinition(
            key="references",
            labels=(
                "References",
                "Referências",
                "Referências bibliográficas",
                "Referencias",
                "Bibliografia",
                "Bibliography",
                "Literature Cited",
                "Works Cited",
            ),
        ),
    ),
)
