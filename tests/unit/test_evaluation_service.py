from typing import Any
from uuid import uuid4

from promptbench_studio.domain.schemas import (
    EvaluationConfig,
    RunResult,
    RunStatus,
    UsageMetrics,
)
from promptbench_studio.services.evaluation_service import evaluate_results


def make_result() -> RunResult:
    return RunResult(
        test_id=uuid4(),
        model_id=uuid4(),
        model_key="synthetic/model",
        output_text="The answer is 42",
        metrics=UsageMetrics(latency_ms=1),
        status=RunStatus.SUCCESS,
    )


async def test_evaluate_results_runs_rules_and_judge() -> None:
    async def completion(**_kwargs: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"content": '{"score": 0.9, "explanation": "Accurate"}'}}]}

    evaluations = await evaluate_results(
        [make_result()],
        EvaluationConfig(
            required_phrases=("42",),
            judge_model="synthetic/judge",
            judge_criterion="Accuracy",
        ),
        completion,
    )

    assert [evaluation.evaluator_type for evaluation in evaluations] == [
        "required_phrase",
        "llm_judge",
    ]
    assert evaluations[-1].score == 0.9


async def test_evaluate_results_accepts_empty_configuration() -> None:
    assert await evaluate_results([make_result()], EvaluationConfig()) == []


async def test_evaluate_results_skips_failed_runs() -> None:
    failed = make_result().model_copy(update={"status": RunStatus.ERROR})

    assert await evaluate_results([failed], EvaluationConfig(required_phrases=("42",))) == []


def test_evaluate_results_sync_runs_without_active_event_loop() -> None:
    from promptbench_studio.services.evaluation_service import evaluate_results_sync

    evaluations = evaluate_results_sync([make_result()], EvaluationConfig(required_phrases=("42",)))

    assert evaluations[0].score == 1
