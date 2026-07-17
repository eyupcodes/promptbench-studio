"""LiteLLM streaming adapter."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, cast

import litellm
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from promptbench_studio.benchmark.pricing import calculate_cost
from promptbench_studio.config import Settings, get_settings
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.providers.security import redact_secrets, validate_base_url

Completion = Callable[..., Awaitable[Any]]


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _content_from_chunk(chunk: Any) -> str:
    choices = _value(chunk, "choices", [])
    if not choices:
        return ""
    delta = _value(choices[0], "delta", {})
    content = _value(delta, "content", "")
    return content if isinstance(content, str) else ""


def _finish_reason(chunk: Any) -> str | None:
    choices = _value(chunk, "choices", [])
    if not choices:
        return None
    value = _value(choices[0], "finish_reason")
    return str(value) if value is not None else None


def _usage_from_chunk(chunk: Any) -> dict[str, int]:
    usage = _value(chunk, "usage")
    if usage is None:
        return {}
    prompt = int(_value(usage, "prompt_tokens", 0) or 0)
    completion = int(_value(usage, "completion_tokens", 0) or 0)
    total = int(_value(usage, "total_tokens", prompt + completion) or 0)
    return {"input_tokens": prompt, "output_tokens": completion, "total_tokens": total}


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _is_retryable(error: BaseException) -> bool:
    if isinstance(error, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
        return True
    status_code = getattr(error, "status_code", None)
    if status_code == 429 or (isinstance(status_code, int) and status_code >= 500):
        return True
    return type(error).__name__ in {
        "APIConnectionError",
        "InternalServerError",
        "RateLimitError",
        "ServiceUnavailableError",
    }


class LiteLLMProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        completion: Completion | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._completion = completion or cast(Completion, litellm.acompletion)

    async def call(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult:
        started = time.perf_counter()
        attempts = 0
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._settings.max_retries + 1),
                wait=wait_exponential(multiplier=0.5, max=8),
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    attempts = attempt.retry_state.attempt_number
                    return await self._stream(benchmark, model, started, attempts - 1)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            is_timeout = isinstance(error, (TimeoutError, asyncio.TimeoutError))
            return RunResult(
                test_id=benchmark.id,
                model_id=model.id,
                model_key=model.model_key,
                metrics=UsageMetrics(
                    latency_ms=elapsed_ms,
                    retry_count=max(0, attempts - 1),
                ),
                status=RunStatus.TIMEOUT if is_timeout else RunStatus.ERROR,
                provider_error=redact_secrets(str(error), self._secret_values()),
            )
        raise RuntimeError("Retry loop exited without a result")

    async def _stream(
        self,
        benchmark: BenchmarkDefinition,
        model: ModelTarget,
        started: float,
        retry_count: int,
    ) -> RunResult:
        response = await self._completion(**self._request_kwargs(benchmark, model))
        stream = cast(AsyncIterator[Any], response)
        parts: list[str] = []
        usage: dict[str, int] = {}
        first_token_ms: int | None = None
        finish_reason: str | None = None
        response_model = model.model_key

        async for chunk in stream:
            content = _content_from_chunk(chunk)
            if content:
                if first_token_ms is None:
                    first_token_ms = round((time.perf_counter() - started) * 1000)
                parts.append(content)
            chunk_usage = _usage_from_chunk(chunk)
            if chunk_usage:
                usage = chunk_usage
            finish_reason = _finish_reason(chunk) or finish_reason
            response_model = str(_value(chunk, "model", response_model))

        output = "".join(parts)
        latency_ms = round((time.perf_counter() - started) * 1000)
        input_tokens = usage.get("input_tokens") or _estimate_tokens(
            benchmark.system_prompt + benchmark.user_prompt
        )
        output_tokens = usage.get("output_tokens") or _estimate_tokens(output)
        total_tokens = usage.get("total_tokens") or input_tokens + output_tokens
        cost = calculate_cost(
            input_tokens,
            output_tokens,
            model.input_price_per_million,
            model.output_price_per_million,
        )
        return RunResult(
            test_id=benchmark.id,
            model_id=model.id,
            model_key=model.model_key,
            output_text=output,
            metrics=UsageMetrics(
                latency_ms=latency_ms,
                time_to_first_token_ms=first_token_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
                characters=len(output),
                words=len(output.split()),
                retry_count=retry_count,
            ),
            status=RunStatus.SUCCESS,
            finish_reason=finish_reason,
            raw_response={"model": response_model, "usage": usage},
        )

    def _request_kwargs(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if benchmark.system_prompt:
            messages.append({"role": "system", "content": benchmark.system_prompt})
        messages.append({"role": "user", "content": benchmark.user_prompt})
        kwargs: dict[str, Any] = {
            "model": model.model_key,
            "messages": messages,
            "max_tokens": benchmark.parameters.max_output_tokens,
            "timeout": benchmark.parameters.timeout_seconds,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self._supports_temperature(model.model_key):
            kwargs["temperature"] = benchmark.parameters.temperature
        if model.base_url:
            kwargs["base_url"] = validate_base_url(model.base_url)
        return kwargs

    @staticmethod
    def _supports_temperature(model_key: str) -> bool:
        unsupported = (
            "claude-fable-5",
            "claude-opus-4-7",
            "claude-opus-4-8",
            "claude-sonnet-5",
        )
        return not any(name in model_key for name in unsupported)

    def _secret_values(self) -> tuple[str, ...]:
        values = (
            self._settings.openai_api_key,
            self._settings.anthropic_api_key,
            self._settings.groq_api_key,
        )
        return tuple(value.get_secret_value() for value in values if value is not None)
