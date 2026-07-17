from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from promptbench_studio.db.models import (
    Base,
    BenchmarkRunRecord,
    BenchmarkTestRecord,
    EvaluationRecord,
    ModelRecord,
    ProviderRecord,
)
from promptbench_studio.db.session import (
    create_engine,
    create_session_factory,
    initialize_database,
    session_scope,
)
from promptbench_studio.repositories.repositories import (
    BenchmarkRepository,
    EvaluationRepository,
    ModelRepository,
    ProviderRepository,
)


async def test_provider_and_benchmark_round_trip() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        provider = await ProviderRepository(session).create(ProviderRecord(name="synthetic"))
        benchmark = await BenchmarkRepository(session).create_test(
            BenchmarkTestRecord(
                name="Synthetic benchmark",
                user_prompt="Return 42",
                parameters_json={"temperature": 0},
                evaluation_config={},
            )
        )
        await session.commit()

        assert provider.id
        assert await BenchmarkRepository(session).get_test(benchmark.id) is benchmark

    await engine.dispose()


async def test_all_repositories_list_and_get_records() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await initialize_database(engine)
    factory = create_session_factory(engine)

    async with factory() as session:
        providers = ProviderRepository(session)
        models = ModelRepository(session)
        benchmarks = BenchmarkRepository(session)
        evaluations = EvaluationRepository(session)

        provider = await providers.create(ProviderRecord(name="enabled-provider"))
        await providers.create(ProviderRecord(name="disabled-provider", enabled=False))
        model = await models.create(
            ModelRecord(
                provider_id=provider.id,
                model_key="synthetic/model",
                display_name="Synthetic model",
                input_price=Decimal("1"),
                output_price=Decimal("2"),
            )
        )
        await models.create(
            ModelRecord(
                provider_id=provider.id,
                model_key="synthetic/inactive",
                display_name="Inactive model",
                active=False,
            )
        )
        benchmark = await benchmarks.create_test(
            BenchmarkTestRecord(
                name="Repository coverage",
                user_prompt="Return 42",
                parameters_json={},
                evaluation_config={},
            )
        )
        run = await benchmarks.create_run(
            BenchmarkRunRecord(
                test_id=benchmark.id,
                model_id=model.id,
                output_text="42",
                input_tokens=2,
                output_tokens=1,
                total_tokens=3,
                latency_ms=10,
                status="success",
            )
        )
        evaluation = await evaluations.create(
            EvaluationRecord(
                run_id=run.id,
                evaluator_type="exact",
                criterion="Answer is 42",
                score=1,
                explanation="Passed",
            )
        )
        await session.commit()

        assert [item.name for item in await providers.list_enabled()] == ["enabled-provider"]
        assert [item.model_key for item in await models.list_active()] == ["synthetic/model"]
        assert await models.get(model.id) is model
        assert [item.id for item in await benchmarks.list_tests()] == [benchmark.id]
        assert [item.id for item in await benchmarks.list_runs(benchmark.id)] == [run.id]
        assert [item.id for item in await evaluations.list_for_run(run.id)] == [evaluation.id]

    await engine.dispose()


async def test_session_scope_commits_and_rolls_back() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await initialize_database(engine)
    factory = create_session_factory(engine)

    async for session in session_scope(factory):
        session.add(ProviderRecord(name="committed"))

    async with factory() as session:
        enabled = await ProviderRepository(session).list_enabled()
        assert [provider.name for provider in enabled] == ["committed"]

    try:
        async for session in session_scope(factory):
            session.add(ProviderRecord(name="rolled-back"))
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    async with factory() as session:
        enabled = await ProviderRepository(session).list_enabled()
        assert [provider.name for provider in enabled] == ["committed"]

    await engine.dispose()
