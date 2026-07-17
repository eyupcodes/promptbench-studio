"""Immutable domain schemas."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from jsonschema import SchemaError, validators
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class BenchmarkParameters(FrozenModel):
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1, le=131_072)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    repeat_count: int = Field(default=1, ge=1, le=20)


class ModelTarget(FrozenModel):
    id: UUID = Field(default_factory=uuid4)
    provider: str = Field(min_length=1, max_length=50)
    model_key: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    base_url: str | None = None
    input_price_per_million: Decimal | None = Field(default=None, ge=0)
    output_price_per_million: Decimal | None = Field(default=None, ge=0)
    context_window: int | None = Field(default=None, gt=0)
    active: bool = True


class EvaluationConfig(FrozenModel):
    required_phrases: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()
    regex_patterns: tuple[str, ...] = ()
    min_words: int | None = Field(default=None, ge=0)
    max_words: int | None = Field(default=None, ge=1)
    json_schema: dict[str, Any] | None = None
    reference_answer: str | None = None
    judge_model: str | None = None
    judge_criterion: str | None = None

    @field_validator("regex_patterns")
    @classmethod
    def validate_regex_patterns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        import re

        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"Invalid regular expression: {pattern}") from error
        return value

    @field_validator("json_schema")
    @classmethod
    def validate_json_schema(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        try:
            validators.validator_for(value).check_schema(value)
        except SchemaError as error:
            raise ValueError(f"Invalid JSON Schema: {error.message}") from error
        return value

    @field_validator("max_words")
    @classmethod
    def validate_word_range(cls, value: int | None, info: Any) -> int | None:
        minimum = info.data.get("min_words")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("max_words must be greater than or equal to min_words")
        return value


class BenchmarkDefinition(FrozenModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    system_prompt: str = Field(default="", max_length=100_000)
    user_prompt: str = Field(min_length=1, max_length=100_000)
    parameters: BenchmarkParameters = Field(default_factory=BenchmarkParameters)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageMetrics(FrozenModel):
    latency_ms: int = Field(ge=0)
    time_to_first_token_ms: int | None = Field(default=None, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)
    characters: int = Field(default=0, ge=0)
    words: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)


class RunResult(FrozenModel):
    id: UUID = Field(default_factory=uuid4)
    test_id: UUID
    model_id: UUID
    model_key: str
    output_text: str = ""
    metrics: UsageMetrics
    status: RunStatus
    finish_reason: str | None = None
    provider_error: str | None = None
    schema_valid: bool | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationResult(FrozenModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    evaluator_type: str
    criterion: str
    score: float | None = Field(default=None, ge=0, le=1)
    explanation: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HistoryEntry(FrozenModel):
    benchmark: BenchmarkDefinition
    results: tuple[RunResult, ...]
    evaluations: tuple[EvaluationResult, ...] = ()
