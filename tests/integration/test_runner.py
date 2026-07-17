import asyncio
from decimal import Decimal
from uuid import uuid4

from promptbench_studio.benchmark.runner import BenchmarkRunner
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)


class SyntheticProvider:
    async def call(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult:
        await asyncio.sleep(0.01)
        if model.model_key == "synthetic/fail":
            raise RuntimeError("synthetic failure")
        if model.model_key == "synthetic/leak":
            raise RuntimeError("Provider rejected sk-proj-abc123")
        return RunResult(
            test_id=benchmark.id,
            model_id=model.id,
            model_key=model.model_key,
            output_text="42",
            metrics=UsageMetrics(
                latency_ms=10,
                time_to_first_token_ms=2,
                input_tokens=3,
                output_tokens=1,
                total_tokens=4,
                estimated_cost_usd=Decimal("0.0001"),
                characters=2,
                words=1,
            ),
            status=RunStatus.SUCCESS,
        )


async def test_runner_isolates_model_failures() -> None:
    benchmark = BenchmarkDefinition(name="Synthetic", user_prompt="Return 42")
    models = [
        ModelTarget(id=uuid4(), provider="synthetic", model_key=key, display_name=key)
        for key in ("synthetic/a", "synthetic/fail", "synthetic/b")
    ]

    results = await BenchmarkRunner(SyntheticProvider(), max_concurrency=2).run(benchmark, models)

    assert len(results) == 3
    assert [result.status for result in results].count(RunStatus.SUCCESS) == 2
    assert [result.status for result in results].count(RunStatus.ERROR) == 1


async def test_runner_redacts_provider_keys_from_fallback_errors() -> None:
    benchmark = BenchmarkDefinition(name="Synthetic", user_prompt="Return 42")
    model = ModelTarget(
        id=uuid4(),
        provider="synthetic",
        model_key="synthetic/leak",
        display_name="synthetic/leak",
    )

    result = (await BenchmarkRunner(SyntheticProvider()).run(benchmark, [model]))[0]

    assert result.status is RunStatus.ERROR
    assert result.provider_error == "Provider rejected [REDACTED]"


async def test_runner_preserves_results_when_progress_callback_fails() -> None:
    benchmark = BenchmarkDefinition(name="Synthetic", user_prompt="Return 42")
    models = [
        ModelTarget(id=uuid4(), provider="synthetic", model_key=key, display_name=key)
        for key in ("synthetic/a", "synthetic/b")
    ]

    def failing_progress(_completed: int, _total: int, _result: RunResult) -> None:
        raise RuntimeError("progress renderer unavailable")

    results = await BenchmarkRunner(SyntheticProvider(), max_concurrency=2).run(
        benchmark,
        models,
        failing_progress,
    )

    assert len(results) == 2
    assert all(result.status is RunStatus.SUCCESS for result in results)
