"""JSON Schema output evaluator."""

import json
from typing import Any
from uuid import UUID

from jsonschema import ValidationError, validate

from promptbench_studio.domain.schemas import EvaluationResult


def evaluate_json_schema(run_id: UUID, output: str, schema: dict[str, Any]) -> EvaluationResult:
    try:
        payload = json.loads(output)
        validate(payload, schema)
    except (json.JSONDecodeError, ValidationError) as error:
        return EvaluationResult(
            run_id=run_id,
            evaluator_type="json_schema",
            criterion="Output matches JSON Schema",
            score=0,
            explanation=str(error),
        )
    return EvaluationResult(
        run_id=run_id,
        evaluator_type="json_schema",
        criterion="Output matches JSON Schema",
        score=1,
        explanation="Passed",
    )
