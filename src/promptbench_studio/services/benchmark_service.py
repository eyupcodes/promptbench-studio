"""Application service coordinating benchmark execution and persistence."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from pydantic import Field

from promptbench_studio.benchmark.runner import BenchmarkRunner, ProgressCallback
from promptbench_studio.config import Settings, get_settings
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    EvaluationConfig,
    EvaluationResult,
    FrozenModel,
    ModelTarget,
    RunResult,
)
from promptbench_studio.providers.base import LLMProvider
from promptbench_studio.providers.litellm_provider import LiteLLMProvider
from promptbench_studio.services.evaluation_service import evaluate_results
from promptbench_studio.services.persistence_service import save_benchmark

Evaluator = Callable[
    [Sequence[RunResult], EvaluationConfig],
    Awaitable[list[EvaluationResult]],
]
Persister = Callable[
    [
        BenchmarkDefinition,
        Sequence[ModelTarget],
        Sequence[RunResult],
        Sequence[EvaluationResult],
        Settings,
    ],
    Awaitable[None],
]


class BenchmarkOutcome(FrozenModel):
    benchmark: BenchmarkDefinition
    models: tuple[ModelTarget, ...]
    results: tuple[RunResult, ...]
    evaluations: tuple[EvaluationResult, ...] = Field(default_factory=tuple)


async def run_benchmark(
    benchmark: BenchmarkDefinition,
    models: Sequence[ModelTarget],
    *,
    provider: LLMProvider | None = None,
    evaluator: Evaluator = evaluate_results,
    persister: Persister = save_benchmark,
    progress: ProgressCallback | None = None,
    settings: Settings | None = None,
) -> BenchmarkOutcome:
    runtime = settings or get_settings()
    selected_models = tuple(models)
    targets = selected_models * benchmark.parameters.repeat_count
    runner = BenchmarkRunner(provider or LiteLLMProvider(runtime), runtime.max_concurrency)
    results = await runner.run(benchmark, targets, progress)
    evaluations = await evaluator(results, benchmark.evaluation)
    await persister(benchmark, selected_models, results, evaluations, runtime)
    return BenchmarkOutcome(
        benchmark=benchmark,
        models=selected_models,
        results=tuple(results),
        evaluations=tuple(evaluations),
    )


def run_benchmark_sync(
    benchmark: BenchmarkDefinition,
    models: Sequence[ModelTarget],
    *,
    provider: LLMProvider | None = None,
    evaluator: Evaluator = evaluate_results,
    persister: Persister = save_benchmark,
    progress: ProgressCallback | None = None,
    settings: Settings | None = None,
) -> BenchmarkOutcome:
    return asyncio.run(
        run_benchmark(
            benchmark,
            models,
            provider=provider,
            evaluator=evaluator,
            persister=persister,
            progress=progress,
            settings=settings,
        )
    )
