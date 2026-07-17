"""Focused SQLAlchemy repositories."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from promptbench_studio.db.models import (
    BenchmarkRunRecord,
    BenchmarkTestRecord,
    EvaluationRecord,
    ModelRecord,
    ProviderRecord,
)


class ProviderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: ProviderRecord) -> ProviderRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_enabled(self) -> Sequence[ProviderRecord]:
        result = await self._session.scalars(
            select(ProviderRecord)
            .where(ProviderRecord.enabled.is_(True))
            .order_by(ProviderRecord.name)
        )
        return result.all()


class ModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: ModelRecord) -> ModelRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_active(self) -> Sequence[ModelRecord]:
        result = await self._session.scalars(
            select(ModelRecord)
            .where(ModelRecord.active.is_(True))
            .order_by(ModelRecord.display_name)
        )
        return result.all()

    async def get(self, model_id: str) -> ModelRecord | None:
        return await self._session.get(ModelRecord, model_id)


class BenchmarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_test(self, record: BenchmarkTestRecord) -> BenchmarkTestRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_test(self, test_id: str) -> BenchmarkTestRecord | None:
        return await self._session.get(BenchmarkTestRecord, test_id)

    async def list_tests(self, limit: int = 100) -> Sequence[BenchmarkTestRecord]:
        result = await self._session.scalars(
            select(BenchmarkTestRecord).order_by(BenchmarkTestRecord.created_at.desc()).limit(limit)
        )
        return result.all()

    async def create_run(self, record: BenchmarkRunRecord) -> BenchmarkRunRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_runs(self, test_id: str) -> Sequence[BenchmarkRunRecord]:
        result = await self._session.scalars(
            select(BenchmarkRunRecord)
            .where(BenchmarkRunRecord.test_id == test_id)
            .order_by(BenchmarkRunRecord.created_at)
        )
        return result.all()


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: EvaluationRecord) -> EvaluationRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_for_run(self, run_id: str) -> Sequence[EvaluationRecord]:
        result = await self._session.scalars(
            select(EvaluationRecord)
            .where(EvaluationRecord.run_id == run_id)
            .order_by(EvaluationRecord.created_at)
        )
        return result.all()
