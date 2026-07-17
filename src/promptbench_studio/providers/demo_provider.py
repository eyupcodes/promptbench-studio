"""Credential-free deterministic provider for local demos."""

import asyncio
from decimal import Decimal

from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.providers.base import LLMProvider

DEMO_RESPONSES = {
    "demo/fast": (
        "Concise response: use measured evidence, then choose simplest model that meets task."
    ),
    "demo/balanced": (
        "Balanced response: compare instruction adherence, latency, token use, and estimated cost. "
        "Validate important outputs with deterministic checks before relying on a model score."
    ),
    "demo/quality": (
        "Detailed response: define task criteria, run identical prompts with fixed parameters, "
        "inspect failures independently, and compare quality against latency and cost. "
        "Repeat runs when consistency matters and keep benchmark history for regression analysis."
    ),
}


class DemoProvider:
    """Return stable synthetic results without network access or credentials."""

    async def call(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult:
        await asyncio.sleep(0)
        output = DEMO_RESPONSES.get(model.model_key, DEMO_RESPONSES["demo/balanced"])
        input_tokens = _estimate_tokens(benchmark.system_prompt + benchmark.user_prompt)
        output_tokens = _estimate_tokens(output)
        latency_ms = {"demo/fast": 180, "demo/balanced": 420, "demo/quality": 760}.get(
            model.model_key, 420
        )
        return RunResult(
            test_id=benchmark.id,
            model_id=model.id,
            model_key=model.model_key,
            output_text=output,
            metrics=UsageMetrics(
                latency_ms=latency_ms,
                time_to_first_token_ms=max(1, latency_ms // 4),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_cost_usd=Decimal(0),
                characters=len(output),
                words=len(output.split()),
            ),
            status=RunStatus.SUCCESS,
            finish_reason="stop",
            raw_response={"provider": "demo", "synthetic": True},
        )


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


class RoutingProvider:
    """Route demo models locally and all other models to live provider."""

    def __init__(
        self, live_provider: LLMProvider, demo_provider: LLMProvider | None = None
    ) -> None:
        self._live_provider = live_provider
        self._demo_provider = demo_provider or DemoProvider()

    async def call(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult:
        provider = self._demo_provider if model.provider == "demo" else self._live_provider
        return await provider.call(benchmark, model)
