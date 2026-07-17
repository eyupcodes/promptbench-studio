from decimal import Decimal

import pytest
from pydantic import ValidationError

from promptbench_studio.domain.schemas import BenchmarkParameters, EvaluationConfig, ModelTarget


def test_benchmark_parameters_are_immutable() -> None:
    parameters = BenchmarkParameters()

    with pytest.raises(ValidationError):
        parameters.temperature = 1  # type: ignore[misc]


def test_model_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        ModelTarget(
            provider="test",
            model_key="test/model",
            display_name="Test",
            input_price_per_million=Decimal("-1"),
        )


def test_evaluation_rejects_inverted_word_range() -> None:
    with pytest.raises(ValidationError):
        EvaluationConfig(min_words=10, max_words=5)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("regex_patterns", ("[",)),
        ("json_schema", {"type": "not-a-json-schema-type"}),
    ],
)
def test_evaluation_rejects_invalid_patterns_and_schemas(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        EvaluationConfig.model_validate({field: value})
