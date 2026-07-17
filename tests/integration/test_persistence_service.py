from decimal import Decimal
from pathlib import Path

from promptbench_studio.config import Settings
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    EvaluationResult,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.services.persistence_service import load_history, save_benchmark


async def test_benchmark_history_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'history.db'}",
    )
    benchmark = BenchmarkDefinition(name="Persistent benchmark", user_prompt="Return 42")
    model = ModelTarget(
        provider="synthetic",
        model_key="synthetic/model",
        display_name="Synthetic model",
        input_price_per_million=Decimal("1"),
        output_price_per_million=Decimal("2"),
    )
    result = RunResult(
        test_id=benchmark.id,
        model_id=model.id,
        model_key=model.model_key,
        output_text="42",
        metrics=UsageMetrics(
            latency_ms=10,
            time_to_first_token_ms=2,
            input_tokens=2,
            output_tokens=1,
            total_tokens=3,
            estimated_cost_usd=Decimal("0.000004"),
            characters=2,
            words=1,
        ),
        status=RunStatus.SUCCESS,
    )

    evaluation = EvaluationResult(
        run_id=result.id,
        evaluator_type="exact",
        criterion="Answer is 42",
        score=1,
        explanation="Passed",
    )

    await save_benchmark(benchmark, [model], [result], [evaluation], settings)
    history = await load_history(settings=settings)

    assert len(history) == 1
    assert history[0].benchmark.name == "Persistent benchmark"
    assert history[0].results[0].output_text == "42"
    assert history[0].results[0].metrics.estimated_cost_usd == Decimal("0.0000040000")
    assert history[0].evaluations[0].score == 1
