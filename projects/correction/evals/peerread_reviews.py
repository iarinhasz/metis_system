"""Extrai somente os escores numéricos de arquivos brutos de pareceres PeerRead."""

import json
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from projects.correction.agents.schemas.criteria import Criterion

_FIELDS: dict[str, Criterion] = {
    "originality": Criterion.ORIGINALITY,
    "soundness_correctness": Criterion.SOUNDNESS,
    "soundness": Criterion.SOUNDNESS,
    "substance": Criterion.SUBSTANCE,
    "clarity": Criterion.CLARITY,
    "meaningful_comparison": Criterion.MEANINGFUL_COMPARISON,
    "impact": Criterion.IMPACT,
    "replicability": Criterion.REPLICABILITY,
}


def _is_meta_review(value: Any) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes"}


def _numeric_score(value: Any) -> int | None:
    text = str(value).strip()
    return int(text) if len(text) == 1 and text in "12345" else None


def read_peerread_scores(path: Path) -> dict[Criterion, int]:
    """Agrega a mediana inteira por critério, sem reter os comentários dos revisores."""
    data = json.loads(path.read_text(encoding="utf-8"))
    reviews = data.get("reviews")
    if reviews is None and isinstance(data.get("metadata"), dict):
        reviews = data["metadata"].get("reviews")
    if not isinstance(reviews, list):
        raise ValueError(f"{path.name}: o arquivo não tem a lista PeerRead de reviews.")

    collected: dict[Criterion, list[int]] = {criterion: [] for criterion in Criterion}
    for review in reviews:
        if not isinstance(review, dict) or _is_meta_review(review.get("is_meta_review", False)):
            continue
        fields = {str(name).casefold(): value for name, value in review.items()}
        per_review: dict[Criterion, int] = {}
        for source_field, criterion in _FIELDS.items():
            score = _numeric_score(fields.get(source_field))
            if score is not None and criterion not in per_review:
                per_review[criterion] = score
        for criterion, score in per_review.items():
            collected[criterion].append(score)

    aggregated: dict[Criterion, int] = {}
    for criterion, scores in collected.items():
        if scores:
            median = Decimal(str(statistics.median(scores)))
            aggregated[criterion] = int(median.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return aggregated
