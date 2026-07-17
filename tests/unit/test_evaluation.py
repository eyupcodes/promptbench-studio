import time
from uuid import uuid4

from promptbench_studio.domain.schemas import (
    EvaluationConfig,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.evaluation.engine import evaluate_deterministic
from promptbench_studio.evaluation.rules import evaluate_rules
from promptbench_studio.evaluation.schema_validator import evaluate_json_schema


def test_rule_evaluation_scores_each_criterion() -> None:
    config = EvaluationConfig(
        required_phrases=("answer",),
        forbidden_phrases=("secret",),
        regex_patterns=(r"\b42\b",),
        min_words=2,
        max_words=5,
    )

    results = evaluate_rules(uuid4(), "The answer is 42", config)

    assert results
    assert all(result.score == 1 for result in results)


def test_regex_evaluation_times_out_catastrophic_backtracking() -> None:
    config = EvaluationConfig(regex_patterns=(r"(a+)+$",))
    started = time.perf_counter()

    results = evaluate_rules(uuid4(), "a" * 100_000 + "b", config)

    assert time.perf_counter() - started < 1
    assert results[0].score == 0
    assert "timed out" in results[0].explanation.lower()


def test_json_schema_evaluation_rejects_invalid_payload() -> None:
    result = evaluate_json_schema(
        uuid4(),
        '{"answer": "wrong type"}',
        {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        },
    )

    assert result.score == 0
    assert "not of type" in result.explanation


def test_deterministic_engine_includes_successful_schema_check() -> None:
    run = RunResult(
        test_id=uuid4(),
        model_id=uuid4(),
        model_key="synthetic/model",
        output_text='{"answer": 42}',
        metrics=UsageMetrics(latency_ms=1),
        status=RunStatus.SUCCESS,
    )
    config = EvaluationConfig(
        required_phrases=("answer",),
        json_schema={
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        },
    )

    results = evaluate_deterministic(run, config)

    assert len(results) == 2
    assert all(result.score == 1 for result in results)
