"""Custo por milhão de tokens; a tabela inicial de produção entra na etapa 1.4."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from projects.correction.agents.specs import Provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPrice:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cached_usd_per_million: Decimal


class Pricing:
    def __init__(self, prices: dict[tuple[Provider, str], ModelPrice] | None = None) -> None:
        self._prices = dict(prices or {})

    def cost(
        self,
        provider: Provider,
        model_id: str,
        *,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
    ) -> Decimal | None:
        if (price := self._prices.get((provider, model_id))) is None:
            logger.warning("Preço não cadastrado: provedor=%s modelo=%s", provider, model_id)
            return None
        uncached = max(0, input_tokens - cached_tokens)
        cached = min(cached_tokens, input_tokens)
        return (
            uncached * price.input_usd_per_million
            + output_tokens * price.output_usd_per_million
            + cached * price.cached_usd_per_million
        ) / Decimal(1_000_000)
