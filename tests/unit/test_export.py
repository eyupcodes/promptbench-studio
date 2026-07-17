import csv
import io
from decimal import Decimal
from uuid import uuid4

from promptbench_studio.domain.schemas import RunResult, RunStatus, UsageMetrics
from promptbench_studio.services.export_service import export_csv, export_json, export_markdown


def result_with_output(output: str) -> RunResult:
    return RunResult(
        test_id=uuid4(),
        model_id=uuid4(),
        model_key="synthetic/model",
        output_text=output,
        metrics=UsageMetrics(
            latency_ms=10,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            estimated_cost_usd=Decimal("0.001"),
            characters=len(output),
            words=1,
        ),
        status=RunStatus.SUCCESS,
    )


def test_csv_export_neutralizes_formula_injection() -> None:
    for output in (
        "=HYPERLINK('bad')",
        "+SUM(1,1)",
        "-1+1",
        "@SUM(1,1)",
        "\t=SUM(1,1)",
        "\r=SUM(1,1)",
    ):
        exported = export_csv([result_with_output(output)])
        row = next(csv.DictReader(io.StringIO(exported)))

        assert row["output_text"] == f"'{output}"


def test_empty_csv_export_returns_empty_string() -> None:
    assert export_csv([]) == ""


def test_json_and_markdown_exports_escape_content() -> None:
    result = result_with_output("<script>alert(1)</script>\n```\ninjected heading")

    assert "api_key" not in export_json([result])
    markdown = export_markdown([result])
    assert "<script>" not in markdown
    assert "````text" in markdown
    assert markdown.endswith("````\n")
