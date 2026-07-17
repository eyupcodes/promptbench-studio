from collections.abc import Sequence
from typing import Any

from promptbench_studio.config import Settings
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    EvaluationConfig,
    EvaluationResult,
    ModelTarget,
    RunResult,
)
from promptbench_studio.providers.demo_provider import DemoProvider
from promptbench_studio.services.benchmark_service import run_benchmark, run_benchmark_sync


async def test_run_benchmark_repeats_targets_reports_progress_and_persists() -> None:
    benchmark = BenchmarkDefinition(
        name="Service",
        user_prompt="Return a useful answer",
        parameters={"repeat_count": 2},
        evaluation=EvaluationConfig(required_phrases=("response",)),
    )
    models = [
        ModelTarget(provider="demo", model_key="demo/fast", display_name="Fast"),
        ModelTarget(provider="demo", model_key="demo/quality", display_name="Quality"),
    ]
    progress: list[tuple[int, int, str]] = []
    persisted: list[tuple[BenchmarkDefinition, Sequence[ModelTarget], Sequence[RunResult]]] = []

    async def persist(
        saved_benchmark: BenchmarkDefinition,
        saved_models: Sequence[ModelTarget],
        results: Sequence[RunResult],
        _evaluations: Sequence[EvaluationResult],
        _settings: Settings,
    ) -> None:
        persisted.append((saved_benchmark, saved_models, results))

    outcome = await run_benchmark(
        benchmark,
        models,
        provider=DemoProvider(),
        settings=Settings(_env_file=None),
        progress=lambda current, total, result: progress.append((current, total, result.model_key)),
        persister=persist,
    )

    assert len(outcome.results) == 4
    assert len(outcome.evaluations) == 4
    assert sorted(current for current, _, _ in progress) == [1, 2, 3, 4]
    assert all(total == 4 for _, total, _ in progress)
    assert persisted[0][0] == benchmark
    assert tuple(persisted[0][1]) == tuple(models)
    assert len(persisted[0][2]) == 4


def test_run_benchmark_sync_returns_outcome() -> None:
    benchmark = BenchmarkDefinition(name="Sync", user_prompt="Return 42")
    model = ModelTarget(provider="demo", model_key="demo/fast", display_name="Fast")

    async def persist(*_args: Any, **_kwargs: Any) -> None:
        return None

    outcome = run_benchmark_sync(
        benchmark,
        [model],
        provider=DemoProvider(),
        settings=Settings(_env_file=None),
        persister=persist,
    )

    assert outcome.benchmark == benchmark
    assert outcome.models == (model,)
    assert len(outcome.results) == 1
