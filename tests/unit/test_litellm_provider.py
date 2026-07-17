from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from promptbench_studio.config import Settings
from promptbench_studio.domain.schemas import BenchmarkDefinition, ModelTarget, RunStatus
from promptbench_studio.providers.litellm_provider import LiteLLMProvider


async def synthetic_stream() -> AsyncIterator[dict[str, Any]]:
    yield {
        "model": "synthetic/model",
        "choices": [{"delta": {"content": "forty"}, "finish_reason": None}],
    }
    yield {
        "model": "synthetic/model",
        "choices": [{"delta": {"content": " two"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


async def test_streaming_provider_normalizes_output_and_usage() -> None:
    calls: list[dict[str, Any]] = []

    async def completion(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        calls.append(kwargs)
        return synthetic_stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(name="Synthetic", user_prompt="Return forty two")
    model = ModelTarget(
        provider="synthetic",
        model_key="synthetic/model",
        display_name="Synthetic",
        input_price_per_million=Decimal("1"),
        output_price_per_million=Decimal("2"),
    )

    result = await provider.call(benchmark, model)

    assert result.status is RunStatus.SUCCESS
    assert result.output_text == "forty two"
    assert result.metrics.input_tokens == 3
    assert result.metrics.output_tokens == 2
    assert result.metrics.total_tokens == 5
    assert result.metrics.estimated_cost_usd == Decimal("0.000007")
    assert result.metrics.time_to_first_token_ms is not None
    assert calls[0]["stream"] is True
    assert calls[0]["stream_options"] == {"include_usage": True}


async def test_provider_returns_sanitized_error() -> None:
    attempts = 0

    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        nonlocal attempts
        attempts += 1
        raise ValueError("api_key=synthetic-secret")

    provider = LiteLLMProvider(
        settings=Settings(_env_file=None, OPENAI_API_KEY="synthetic-secret"),
        completion=completion,
    )
    benchmark = BenchmarkDefinition(name="Synthetic", user_prompt="Return 42")
    model = ModelTarget(
        provider="openai",
        model_key="openai/gpt-test",
        display_name="Synthetic",
    )

    result = await provider.call(benchmark, model)

    assert attempts == 1
    assert result.status is RunStatus.ERROR
    assert "synthetic-secret" not in (result.provider_error or "")


async def test_provider_estimates_tokens_when_usage_is_missing() -> None:
    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        async def stream() -> AsyncIterator[dict[str, Any]]:
            yield {"choices": [{"delta": {"content": "estimated output"}}]}

        return stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(name="Estimate", user_prompt="Estimate these tokens")
    model = ModelTarget(
        provider="synthetic",
        model_key="synthetic/model",
        display_name="Synthetic",
        input_price_per_million=Decimal("1"),
        output_price_per_million=Decimal("2"),
    )

    result = await provider.call(benchmark, model)

    assert result.metrics.input_tokens > 0
    assert result.metrics.output_tokens > 0
    assert result.metrics.total_tokens == (
        result.metrics.input_tokens + result.metrics.output_tokens
    )
    assert result.metrics.estimated_cost_usd is not None


async def test_provider_retries_timeout_and_reports_timeout() -> None:
    attempts = 0

    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("provider timed out")

    provider = LiteLLMProvider(
        settings=Settings(_env_file=None, max_retries=1),
        completion=completion,
    )
    benchmark = BenchmarkDefinition(name="Timeout", user_prompt="Return 42")
    model = ModelTarget(provider="synthetic", model_key="synthetic/model", display_name="Model")

    result = await provider.call(benchmark, model)

    assert attempts == 2
    assert result.status is RunStatus.TIMEOUT
    assert result.metrics.retry_count == 1
