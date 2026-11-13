"""Tarifas Standard pagas, em USD por milhão de tokens; fontes em docs/agents.md."""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from projects.correction.agents.specs import Provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPrice:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cached_usd_per_million: Decimal
    cache_write_multiplier: Decimal = Decimal(1)
    long_context_threshold: int | None = None
    long_input_multiplier: Decimal = Decimal(1)
    long_output_multiplier: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        values = (
            self.input_usd_per_million,
            self.output_usd_per_million,
            self.cached_usd_per_million,
            self.cache_write_multiplier,
            self.long_input_multiplier,
            self.long_output_multiplier,
        )
        if any(not value.is_finite() or value < 0 for value in values):
            raise ValueError("Preços e multiplicadores precisam ser finitos e não negativos.")
        if self.long_context_threshold is not None and self.long_context_threshold < 1:
            raise ValueError("O limite de contexto longo precisa ser positivo.")


def standard_prices(on: date) -> dict[tuple[Provider, str], ModelPrice]:
    """Tarifas conferidas em 12/11/2026; a promoção do Gemini termina em 31/12/2026."""
    google_flash = (
        ModelPrice(Decimal("0.75"), Decimal("3.75"), Decimal("0.075"))
        if on < date(2027, 1, 1)
        else ModelPrice(Decimal("1.50"), Decimal("7.50"), Decimal("0.15"))
    )
    return {
        (Provider.OPENAI, "gpt-5.6-terra"): ModelPrice(
            Decimal("2"),
            Decimal("12"),
            Decimal("0.2"),
            cache_write_multiplier=Decimal("1.25"),
            long_context_threshold=272_000,
            long_input_multiplier=Decimal(2),
            long_output_multiplier=Decimal("1.5"),
        ),
        (Provider.OPENAI, "gpt-5.6-luna"): ModelPrice(
            Decimal("0.2"),
            Decimal("1.2"),
            Decimal("0.02"),
            cache_write_multiplier=Decimal("1.25"),
            long_context_threshold=272_000,
            long_input_multiplier=Decimal(2),
            long_output_multiplier=Decimal("1.5"),
        ),
        (Provider.GOOGLE, "gemini-3.8-flash"): google_flash,
        (Provider.GOOGLE, "gemini-3.5-flash-lite"): ModelPrice(
            Decimal("0.3"), Decimal("2.5"), Decimal("0.03")
        ),
        # O E1 ainda usa esse id. A troca de rota anunciada para 01/12/2026 tem
        # as mesmas tarifas de texto, imagem e vídeo no 3.5 Flash-Lite.
        (Provider.GOOGLE, "gemini-2.5-flash"): ModelPrice(
            Decimal("0.3"), Decimal("2.5"), Decimal("0.03")
        ),
    }


class Pricing:
    def __init__(
        self,
        prices: dict[tuple[Provider, str], ModelPrice] | None = None,
        *,
        on: date | None = None,
    ) -> None:
        self._prices = dict(prices) if prices is not None else None
        self._on = on

    def cost(
        self,
        provider: Provider,
        model_id: str,
        *,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        cache_write_tokens: int = 0,
    ) -> Decimal | None:
        if min(input_tokens, output_tokens, cached_tokens, cache_write_tokens) < 0:
            raise ValueError("Contagens de tokens não podem ser negativas.")
        prices = (
            self._prices
            if self._prices is not None
            else standard_prices(self._on or datetime.now(UTC).date())
        )
        if (price := prices.get((provider, model_id))) is None:
            logger.warning("Preço não cadastrado: provedor=%s modelo=%s", provider, model_id)
            return None
        cached = min(cached_tokens, input_tokens)
        writes = min(cache_write_tokens, input_tokens - cached)
        uncached = input_tokens - cached - writes
        input_cost = (
            uncached + writes * price.cache_write_multiplier
        ) * price.input_usd_per_million + cached * price.cached_usd_per_million
        output_cost = output_tokens * price.output_usd_per_million
        if price.long_context_threshold is not None and input_tokens > price.long_context_threshold:
            input_cost *= price.long_input_multiplier
            output_cost *= price.long_output_multiplier
        return ((input_cost + output_cost) / Decimal(1_000_000)).quantize(
            Decimal("0.000000000001"), rounding=ROUND_HALF_UP
        )
