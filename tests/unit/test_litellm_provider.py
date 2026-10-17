from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import pytest

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


class StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


def make_model(key: str = "synthetic/model", base_url: str | None = None) -> ModelTarget:
    return ModelTarget(provider="synthetic", model_key=key, display_name="Model", base_url=base_url)


async def test_provider_retries_rate_limit_then_succeeds() -> None:
    attempts = 0

    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise StatusError(429)
        return synthetic_stream()

    provider = LiteLLMProvider(
        settings=Settings(_env_file=None, max_retries=2), completion=completion
    )
    benchmark = BenchmarkDefinition(name="Retry", user_prompt="Return 42")

    result = await provider.call(benchmark, make_model())

    assert attempts == 2
    assert result.status is RunStatus.SUCCESS
    assert result.metrics.retry_count == 1


@pytest.mark.parametrize(("status_code", "expected_attempts"), [(503, 2), (400, 1), (404, 1)])
async def test_provider_retries_only_server_errors(
    status_code: int, expected_attempts: int
) -> None:
    attempts = 0

    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        nonlocal attempts
        attempts += 1
        raise StatusError(status_code)

    provider = LiteLLMProvider(
        settings=Settings(_env_file=None, max_retries=1), completion=completion
    )
    benchmark = BenchmarkDefinition(name="Status", user_prompt="Return 42")

    result = await provider.call(benchmark, make_model())

    assert attempts == expected_attempts
    assert result.status is RunStatus.ERROR
    assert result.provider_error == f"status {status_code}"


@pytest.mark.parametrize(
    ("model_key", "sends_temperature"),
    [("openai/gpt-test", True), ("anthropic/claude-sonnet-5-test", False)],
)
async def test_temperature_is_omitted_for_models_that_reject_it(
    model_key: str, sends_temperature: bool
) -> None:
    calls: list[dict[str, Any]] = []

    async def completion(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        calls.append(kwargs)
        return synthetic_stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(name="Temp", user_prompt="Return 42")

    await provider.call(benchmark, make_model(model_key))

    assert ("temperature" in calls[0]) is sends_temperature


async def test_system_prompt_is_sent_as_first_message() -> None:
    calls: list[dict[str, Any]] = []

    async def completion(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        calls.append(kwargs)
        return synthetic_stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(
        name="System", system_prompt="Be terse.", user_prompt="Return 42"
    )

    await provider.call(benchmark, make_model())

    assert calls[0]["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "Return 42"},
    ]


async def test_invalid_custom_base_url_fails_before_calling_provider() -> None:
    calls = 0

    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return synthetic_stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(name="Url", user_prompt="Return 42")

    result = await provider.call(benchmark, make_model(base_url="http://169.254.169.254/v1"))

    assert calls == 0
    assert result.status is RunStatus.ERROR
    assert "HTTPS" in (result.provider_error or "")


async def test_stream_ignores_chunks_without_choices_or_text_content() -> None:
    async def completion(**_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        async def stream() -> AsyncIterator[dict[str, Any]]:
            yield {"choices": []}
            yield {"choices": [{"delta": {"content": None}}]}
            yield {"choices": [{"delta": {"content": ["not", "text"]}}]}
            yield {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}

        return stream()

    provider = LiteLLMProvider(settings=Settings(_env_file=None), completion=completion)
    benchmark = BenchmarkDefinition(name="Chunks", user_prompt="Return ok")

    result = await provider.call(benchmark, make_model())

    assert result.status is RunStatus.SUCCESS
    assert result.output_text == "ok"
    assert result.finish_reason == "stop"
