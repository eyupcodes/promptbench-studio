"""JSON Schema output evaluator."""

import json
from typing import Any
from uuid import UUID

from jsonschema import validators
from jsonschema.exceptions import ValidationError, best_match

from promptbench_studio.domain.schemas import EvaluationResult

CRITERION = "Output matches JSON Schema"
MAX_EXPLANATION_CHARS = 300


def _json_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _explain(error: ValidationError) -> str:
    """One line with the failing path and reason, without the schema or full output."""
    text = f"{_json_path(error)}: {' '.join(error.message.split())}"
    if len(text) > MAX_EXPLANATION_CHARS:
        text = text[: MAX_EXPLANATION_CHARS - 3] + "..."
    return text


def _failure(run_id: UUID, explanation: str) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        evaluator_type="json_schema",
        criterion=CRITERION,
        score=0,
        explanation=explanation,
    )


def evaluate_json_schema(run_id: UUID, output: str, schema: dict[str, Any]) -> EvaluationResult:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        return _failure(
            run_id, f"Invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})"
        )
    validator = validators.validator_for(schema)(schema)
    failure = best_match(validator.iter_errors(payload))
    if failure is not None:
        return _failure(run_id, _explain(failure))
    return EvaluationResult(
        run_id=run_id,
        evaluator_type="json_schema",
        criterion=CRITERION,
        score=1,
        explanation="Passed",
    )
