"""Safe in-memory benchmark exports."""

import csv
import html
import io
import json
from collections.abc import Sequence
from typing import Any

from promptbench_studio.domain.schemas import RunResult

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _row(result: RunResult) -> dict[str, Any]:
    metrics = result.metrics
    return {
        "run_id": str(result.id),
        "model": result.model_key,
        "status": result.status.value,
        "output_text": result.output_text,
        "latency_ms": metrics.latency_ms,
        "time_to_first_token_ms": metrics.time_to_first_token_ms,
        "input_tokens": metrics.input_tokens,
        "output_tokens": metrics.output_tokens,
        "total_tokens": metrics.total_tokens,
        "estimated_cost_usd": (
            str(metrics.estimated_cost_usd) if metrics.estimated_cost_usd is not None else None
        ),
        "provider_error": result.provider_error,
    }


def _safe_csv_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def export_csv(results: Sequence[RunResult]) -> str:
    rows = [
        {key: _safe_csv_cell(value) for key, value in _row(result).items()} for result in results
    ]
    if not rows:
        return ""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def export_json(results: Sequence[RunResult]) -> str:
    return json.dumps([_row(result) for result in results], ensure_ascii=False, indent=2)


def export_markdown(results: Sequence[RunResult]) -> str:
    lines = ["# PromptBench Studio Report", ""]
    for result in results:
        output = html.escape(result.output_text)
        fence = "`" * max(4, _longest_backtick_run(output) + 1)
        lines.extend(
            [
                f"## {html.escape(result.model_key)}",
                "",
                f"- Status: {html.escape(result.status.value)}",
                f"- Latency: {result.metrics.latency_ms} ms",
                "",
                f"{fence}text",
                output,
                fence,
                "",
            ]
        )
    return "\n".join(lines)


def _longest_backtick_run(text: str) -> int:
    longest = current = 0
    for character in text:
        current = current + 1 if character == "`" else 0
        longest = max(longest, current)
    return longest
