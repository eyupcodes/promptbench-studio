"""Concurrent benchmark runner."""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable, Sequence

from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.providers.base import LLMProvider
from promptbench_studio.providers.security import redact_secrets

ProgressCallback = Callable[[int, int, RunResult], Awaitable[None] | None]
LOGGER = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(self, provider: LLMProvider, max_concurrency: int = 5) -> None:
        self._provider = provider
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(
        self,
        benchmark: BenchmarkDefinition,
        models: Sequence[ModelTarget],
        on_progress: ProgressCallback | None = None,
    ) -> list[RunResult]:
        total = len(models)
        completed = 0
        results_by_index: dict[int, RunResult] = {}

        async def run_indexed(index: int, model: ModelTarget) -> None:
            nonlocal completed
            result = await self._run_one(benchmark, model)
            results_by_index[index] = result
            completed += 1
            if on_progress is not None:
                try:
                    callback_result = on_progress(completed, total, result)
                    if inspect.isawaitable(callback_result):
                        await callback_result
                except Exception:
                    LOGGER.exception("Benchmark progress callback failed")

        await asyncio.gather(*(run_indexed(index, model) for index, model in enumerate(models)))
        return [results_by_index[index] for index in range(total)]

    async def _run_one(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult:
        async with self._semaphore:
            try:
                return await self._provider.call(benchmark, model)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                return RunResult(
                    test_id=benchmark.id,
                    model_id=model.id,
                    model_key=model.model_key,
                    metrics=UsageMetrics(latency_ms=0),
                    status=RunStatus.ERROR,
                    provider_error=redact_secrets(str(error)),
                )
