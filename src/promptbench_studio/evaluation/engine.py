"""Evaluation orchestration."""

from promptbench_studio.domain.schemas import EvaluationConfig, EvaluationResult, RunResult
from promptbench_studio.evaluation.rules import evaluate_rules
from promptbench_studio.evaluation.schema_validator import evaluate_json_schema


def evaluate_deterministic(run: RunResult, config: EvaluationConfig) -> list[EvaluationResult]:
    results = evaluate_rules(run.id, run.output_text, config)
    if config.json_schema is not None:
        results.append(evaluate_json_schema(run.id, run.output_text, config.json_schema))
    return results
