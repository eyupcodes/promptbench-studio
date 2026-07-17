"""Provider-independent cost calculation."""

from decimal import Decimal

MILLION = Decimal(1_000_000)


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: Decimal | None,
    output_price_per_million: Decimal | None,
) -> Decimal | None:
    if input_price_per_million is None or output_price_per_million is None:
        return None
    input_cost = Decimal(input_tokens) * input_price_per_million / MILLION
    output_cost = Decimal(output_tokens) * output_price_per_million / MILLION
    return input_cost + output_cost
