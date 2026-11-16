"""Tarifas por provedor e modelo, cache e mudanças de faixa e vigência."""

import logging
from datetime import date
from decimal import Decimal

import pytest

from projects.correction.agents.pricing import ModelPrice, Pricing, standard_prices
from projects.correction.agents.specs import Provider
from projects.correction.metis.config import MetisSettings


def test_catalog_covers_all_development_roles_and_extraction() -> None:
    prices = standard_prices(date(2026, 11, 12))
    for spec in MetisSettings(_env_file=None).model_specs.values():
        assert (spec.provider, spec.model_id) in prices
    assert (Provider.GOOGLE, "gemini-3.6-flash") in prices
    assert (Provider.GOOGLE, "gemini-2.5-flash") in prices  # registros anteriores


def test_cache_is_charged_once_at_its_own_rate() -> None:
    assert Pricing().cost(
        Provider.OPENAI,
        "gpt-5.6-terra",
        input_tokens=100_000,
        output_tokens=1_000,
        cached_tokens=25_000,
    ) == Decimal("0.167")


def test_cache_writes_use_the_published_multiplier() -> None:
    assert Pricing().cost(
        Provider.OPENAI,
        "gpt-5.6-terra",
        input_tokens=100,
        output_tokens=10,
        cached_tokens=20,
        cache_write_tokens=40,
    ) == Decimal("0.000304")


@pytest.mark.parametrize(("tokens", "expected"), [(272_000, "0.5452"), (272_001, "1.089804")])
def test_long_context_changes_the_rate_for_the_entire_request(tokens: int, expected: str) -> None:
    assert Pricing().cost(
        Provider.OPENAI,
        "gpt-5.6-terra",
        input_tokens=tokens,
        output_tokens=100,
        cached_tokens=0,
    ) == Decimal(expected)


@pytest.mark.parametrize(("on", "expected"), [(date(2026, 12, 31), "4.5"), (date(2027, 1, 1), "9")])
def test_google_introductory_price_expires(on: date, expected: str) -> None:
    assert Pricing(on=on).cost(
        Provider.GOOGLE,
        "gemini-3.8-flash",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cached_tokens=0,
    ) == Decimal(expected)


def test_cache_counts_are_clamped_to_input_without_negative_costs() -> None:
    assert Pricing().cost(
        Provider.OPENAI,
        "gpt-5.6-luna",
        input_tokens=10,
        output_tokens=0,
        cached_tokens=100,
        cache_write_tokens=100,
    ) == Decimal("0.0000002")


def test_unknown_price_is_null_and_warns_without_guessing(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="projects.correction.agents.pricing"):
        cost = Pricing().cost(
            Provider.OPENAI,
            "modelo-desconhecido",
            input_tokens=20,
            output_tokens=5,
            cached_tokens=4,
        )
    assert cost is None
    assert "Preço não cadastrado" in caplog.text and "modelo-desconhecido" in caplog.text


def test_an_explicit_empty_table_does_not_fall_back_to_standard_prices() -> None:
    assert (
        Pricing({}).cost(
            Provider.GOOGLE,
            "gemini-3.8-flash",
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
        )
        is None
    )


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity"])
def test_invalid_prices_fail_before_any_call(value: str) -> None:
    with pytest.raises(ValueError):
        ModelPrice(Decimal(value), Decimal(1), Decimal(1))


def test_negative_token_counts_are_rejected() -> None:
    with pytest.raises(ValueError, match="negativas"):
        Pricing().cost(
            Provider.GOOGLE,
            "gemini-3.8-flash",
            input_tokens=-1,
            output_tokens=0,
            cached_tokens=0,
        )
