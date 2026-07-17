from decimal import Decimal

from promptbench_studio.benchmark.pricing import calculate_cost


def test_calculate_cost_uses_per_million_prices() -> None:
    cost = calculate_cost(
        input_tokens=1_000,
        output_tokens=500,
        input_price_per_million=Decimal("2"),
        output_price_per_million=Decimal("8"),
    )

    assert cost == Decimal("0.006")


def test_calculate_cost_is_unknown_without_prices() -> None:
    assert calculate_cost(10, 10, None, None) is None
