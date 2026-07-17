"""Provider protocol."""

from typing import Protocol

from promptbench_studio.domain.schemas import BenchmarkDefinition, ModelTarget, RunResult


class LLMProvider(Protocol):
    async def call(self, benchmark: BenchmarkDefinition, model: ModelTarget) -> RunResult: ...
