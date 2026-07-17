"""Comparison page."""

import pandas as pd
import streamlit as st

from promptbench_studio.services.export_service import export_csv, export_json, export_markdown
from promptbench_studio.services.report_service import build_comparison, select_best_model
from promptbench_studio.ui.charts import scatter_chart


def render() -> None:
    st.title("Comparison")
    results = st.session_state.current_results
    if not results:
        st.info("Run a benchmark first.")
        return

    st.header("Responses")
    columns = st.columns(min(len(results), 3))
    for index, result in enumerate(results):
        with columns[index % len(columns)]:
            st.markdown(f"**{result.model_key}**")
            status = result.status.value
            if status == "success":
                st.success("Success")
            else:
                st.error(f"{status.title()}: {result.provider_error or 'Unknown provider error'}")
            st.text_area(
                f"Response from {result.model_key}",
                value=result.output_text,
                height=220,
                disabled=True,
                key=f"response-{result.id}",
            )
            st.caption(
                f"Latency {result.metrics.latency_ms} ms · TTFT "
                f"{result.metrics.time_to_first_token_ms or 'n/a'} ms · "
                f"Tokens {result.metrics.total_tokens}"
            )

    evaluations = st.session_state.current_evaluations
    scores_by_run: dict[str, list[float]] = {}
    for evaluation in evaluations:
        if evaluation.score is not None:
            scores_by_run.setdefault(str(evaluation.run_id), []).append(evaluation.score)
    frame = build_comparison(results)
    quality_by_model = {
        result.model_key: sum(scores_by_run[str(result.id)]) / len(scores_by_run[str(result.id)])
        for result in results
        if scores_by_run.get(str(result.id))
    }
    frame["quality_score"] = pd.Series(
        [quality_by_model.get(result.model_key) for result in results],
        dtype="float64",
    )
    winner = select_best_model(results, quality_by_model)
    if winner is not None:
        st.success(
            f"Recommended model: {winner}. Highest measured quality; latency and cost break ties."
        )
    st.header("Metrics table")
    st.dataframe(frame, hide_index=True, use_container_width=True)
    if evaluations:
        st.subheader("Evaluation details")
        st.dataframe(
            [
                {
                    "Run ID": str(evaluation.run_id),
                    "Evaluator": evaluation.evaluator_type,
                    "Criterion": evaluation.criterion,
                    "Score": evaluation.score,
                    "Explanation": evaluation.explanation,
                }
                for evaluation in evaluations
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.header("Cost and latency trade-offs")
    st.caption(
        "Quality plots appear after evaluation scores are available. "
        "Metrics table remains source of truth."
    )
    if frame["quality_score"].notna().any():
        st.plotly_chart(
            scatter_chart(frame, "estimated_cost_usd", "Estimated cost (USD)"),
            use_container_width=True,
            key="cost-quality",
        )
        st.plotly_chart(
            scatter_chart(frame, "latency_ms", "Latency (ms)"),
            use_container_width=True,
            key="latency-quality",
        )
    else:
        st.info("Add evaluation scores to display cost-quality and latency-quality charts.")

    st.header("Export")
    csv_column, json_column, markdown_column = st.columns(3)
    csv_column.download_button(
        "Download CSV", export_csv(results), "promptbench-results.csv", "text/csv"
    )
    json_column.download_button(
        "Download JSON",
        export_json(results),
        "promptbench-results.json",
        "application/json",
    )
    markdown_column.download_button(
        "Download Markdown",
        export_markdown(results),
        "promptbench-report.md",
        "text/markdown",
    )
