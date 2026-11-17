"""Chaves fechadas dos critérios compartilhadas pelos agentes e pelo método."""

from enum import StrEnum


class Criterion(StrEnum):
    ORIGINALITY = "originality"
    SOUNDNESS = "soundness"
    SUBSTANCE = "substance"
    CLARITY = "clarity"
    MEANINGFUL_COMPARISON = "meaningful_comparison"
    IMPACT = "impact"
    REPLICABILITY = "replicability"
