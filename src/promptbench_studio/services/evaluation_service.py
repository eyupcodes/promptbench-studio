"""Run configured evaluations for benchmark results."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import litellm

from promptbench_studio.domain.schemas import (
    EvaluationConfig,
    EvaluationResult,
    RunResult,
)
from promptbench_studio.evaluation.engine import evaluate_deterministic
from promptbench_studio.evaluation.judge import LLMJudgeEvaluator

Completion = Callable[..., Awaitable[Any]]


async def evaluate_results(
    results: Sequence[RunResult],
    config: EvaluationConfig,
    judge_completion: Completion | None = None,
) -> list[EvaluationResult]:
    evaluations: list[EvaluationResult] = []
    for result in results:
        if result.status.value != "success":
            continue
        evaluations.extend(evaluate_deterministic(result, config))
        if config.judge_model and config.judge_criterion:
            judge = LLMJudgeEvaluator(judge_completion or litellm.acompletion)
            evaluations.append(
                await judge.evaluate(
                    run_id=result.id,
                    judge_model=config.judge_model,
                    criterion=config.judge_criterion,
                    candidate=result.output_text,
                    reference_answer=config.reference_answer,
                )
            )
    return evaluations


def evaluate_results_sync(
    results: Sequence[RunResult],
    config: EvaluationConfig,
) -> list[EvaluationResult]:
    return asyncio.run(evaluate_results(results, config))
