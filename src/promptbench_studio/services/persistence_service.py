"""SQLite persistence boundary for Streamlit workflows."""

import asyncio
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from promptbench_studio.config import Settings, get_settings
from promptbench_studio.db.models import (
    BenchmarkRunRecord,
    BenchmarkTestRecord,
    EvaluationRecord,
    ModelRecord,
    ProviderRecord,
)
from promptbench_studio.db.session import create_engine, create_session_factory, initialize_database
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    BenchmarkParameters,
    EvaluationConfig,
    EvaluationResult,
    HistoryEntry,
    ModelTarget,
    RunResult,
    RunStatus,
    UsageMetrics,
)


def _model_key(model: ModelTarget) -> str:
    return f"{model.provider}:{model.model_key}"


async def save_benchmark(
    benchmark: BenchmarkDefinition,
    models: Sequence[ModelTarget],
    results: Sequence[RunResult],
    evaluations: Sequence[EvaluationResult] = (),
    settings: Settings | None = None,
) -> None:
    runtime = settings or get_settings()
    engine = create_engine(runtime.database_url)
    await initialize_database(engine)
    factory = create_session_factory(engine)
    try:
        async with factory.begin() as session:
            model_records: dict[UUID, ModelRecord] = {}
            for model in models:
                provider = await session.scalar(
                    select(ProviderRecord).where(ProviderRecord.name == model.provider)
                )
                if provider is None:
                    provider = ProviderRecord(name=model.provider, base_url=model.base_url)
                    session.add(provider)
                    await session.flush()

                existing_model = await session.scalar(
                    select(ModelRecord).where(ModelRecord.model_key == _model_key(model))
                )
                if existing_model is None:
                    existing_model = ModelRecord(
                        id=str(model.id),
                        provider_id=provider.id,
                        model_key=_model_key(model),
                        display_name=model.display_name,
                        input_price=model.input_price_per_million,
                        output_price=model.output_price_per_million,
                        context_window=model.context_window,
                        active=model.active,
                    )
                    session.add(existing_model)
                    await session.flush()
                model_records[model.id] = existing_model

            test_record = BenchmarkTestRecord(
                id=str(benchmark.id),
                name=benchmark.name,
                description=benchmark.description,
                system_prompt=benchmark.system_prompt,
                user_prompt=benchmark.user_prompt,
                parameters_json=benchmark.parameters.model_dump(mode="json"),
                evaluation_config=benchmark.evaluation.model_dump(mode="json"),
                created_at=benchmark.created_at,
            )
            session.add(test_record)
            await session.flush()
            for result in results:
                model_record = model_records[result.model_id]
                metrics = result.metrics
                session.add(
                    BenchmarkRunRecord(
                        id=str(result.id),
                        test_id=test_record.id,
                        model_id=model_record.id,
                        output_text=result.output_text,
                        raw_response=result.raw_response,
                        input_tokens=metrics.input_tokens,
                        output_tokens=metrics.output_tokens,
                        total_tokens=metrics.total_tokens,
                        cost_usd=metrics.estimated_cost_usd,
                        latency_ms=metrics.latency_ms,
                        time_to_first_token_ms=metrics.time_to_first_token_ms,
                        finish_reason=result.finish_reason,
                        retry_count=metrics.retry_count,
                        status=result.status.value,
                        provider_error=result.provider_error,
                        schema_valid=result.schema_valid,
                        created_at=result.created_at,
                    )
                )
            for evaluation in evaluations:
                session.add(
                    EvaluationRecord(
                        id=str(evaluation.id),
                        run_id=str(evaluation.run_id),
                        evaluator_type=evaluation.evaluator_type,
                        criterion=evaluation.criterion,
                        score=evaluation.score,
                        explanation=evaluation.explanation,
                        created_at=evaluation.created_at,
                    )
                )
    finally:
        await engine.dispose()


async def load_history(
    limit: int = 100,
    settings: Settings | None = None,
) -> list[HistoryEntry]:
    runtime = settings or get_settings()
    engine = create_engine(runtime.database_url)
    await initialize_database(engine)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            records = await session.scalars(
                select(BenchmarkTestRecord)
                .options(
                    selectinload(BenchmarkTestRecord.runs).selectinload(BenchmarkRunRecord.model),
                    selectinload(BenchmarkTestRecord.runs).selectinload(
                        BenchmarkRunRecord.evaluations
                    ),
                )
                .order_by(BenchmarkTestRecord.created_at.desc())
                .limit(limit)
            )
            return [_history_entry(record) for record in records]
    finally:
        await engine.dispose()


def _history_entry(record: BenchmarkTestRecord) -> HistoryEntry:
    benchmark = BenchmarkDefinition(
        id=UUID(record.id),
        name=record.name,
        description=record.description,
        system_prompt=record.system_prompt,
        user_prompt=record.user_prompt,
        parameters=BenchmarkParameters.model_validate(record.parameters_json),
        evaluation=EvaluationConfig.model_validate(record.evaluation_config),
        created_at=record.created_at,
    )
    ordered_runs = sorted(record.runs, key=lambda item: item.created_at)
    results = tuple(_run_result(run) for run in ordered_runs)
    evaluations = tuple(
        _evaluation_result(evaluation)
        for run in ordered_runs
        for evaluation in sorted(run.evaluations, key=lambda item: item.created_at)
    )
    return HistoryEntry(benchmark=benchmark, results=results, evaluations=evaluations)


def _evaluation_result(record: EvaluationRecord) -> EvaluationResult:
    return EvaluationResult(
        id=UUID(record.id),
        run_id=UUID(record.run_id),
        evaluator_type=record.evaluator_type,
        criterion=record.criterion,
        score=record.score,
        explanation=record.explanation,
        created_at=record.created_at,
    )


def _run_result(record: BenchmarkRunRecord) -> RunResult:
    model_key = record.model.model_key.split(":", 1)[-1]
    output = record.output_text
    return RunResult(
        id=UUID(record.id),
        test_id=UUID(record.test_id),
        model_id=UUID(record.model_id),
        model_key=model_key,
        output_text=output,
        metrics=UsageMetrics(
            latency_ms=record.latency_ms,
            time_to_first_token_ms=record.time_to_first_token_ms,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
            estimated_cost_usd=record.cost_usd,
            characters=len(output),
            words=len(output.split()),
            retry_count=record.retry_count,
        ),
        status=RunStatus(record.status),
        finish_reason=record.finish_reason,
        provider_error=record.provider_error,
        schema_valid=record.schema_valid,
        raw_response=record.raw_response,
        created_at=record.created_at,
    )


def save_benchmark_sync(
    benchmark: BenchmarkDefinition,
    models: Sequence[ModelTarget],
    results: Sequence[RunResult],
    evaluations: Sequence[EvaluationResult] = (),
) -> None:
    asyncio.run(save_benchmark(benchmark, models, results, evaluations))


def load_history_sync() -> list[HistoryEntry]:
    return asyncio.run(load_history())
