"""Comparison reporting helpers."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from promptbench_studio.domain.schemas import RunResult, RunStatus


def build_comparison(results: Sequence[RunResult]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in results:
        metrics = result.metrics
        rows.append(
            {
                "model": result.model_key,
                "status": result.status.value,
                "latency_ms": metrics.latency_ms,
                "time_to_first_token_ms": metrics.time_to_first_token_ms,
                "input_tokens": metrics.input_tokens,
                "output_tokens": metrics.output_tokens,
                "total_tokens": metrics.total_tokens,
                "estimated_cost_usd": (
                    float(metrics.estimated_cost_usd)
                    if metrics.estimated_cost_usd is not None
                    else None
                ),
                "characters": metrics.characters,
                "words": metrics.words,
            }
        )
    return pd.DataFrame(rows)


def select_best_model(
    results: Sequence[RunResult], quality_scores: Mapping[str, float]
) -> str | None:
    scored = [
        result
        for result in results
        if result.status is RunStatus.SUCCESS and result.model_key in quality_scores
    ]
    if not scored:
        return None
    ranked = sorted(
        scored,
        key=lambda result: (
            -quality_scores[result.model_key],
            result.metrics.latency_ms,
            result.metrics.estimated_cost_usd is None,
            result.metrics.estimated_cost_usd or 0,
        ),
    )
    return ranked[0].model_key
