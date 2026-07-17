"""Dashboard page."""

from collections import Counter
from decimal import Decimal

import streamlit as st

from promptbench_studio.domain.schemas import HistoryEntry, RunResult


def _all_results(history: list[HistoryEntry], current: list[RunResult]) -> list[RunResult]:
    persisted = [result for entry in history for result in entry.results]
    return persisted or current


def render() -> None:
    st.title("PromptBench Studio")
    st.caption("Compare LLM quality, latency, token use, and estimated cost.")

    history = st.session_state.history
    current_results = st.session_state.current_results
    results = _all_results(history, current_results)
    successful = sum(result.status.value == "success" for result in results)
    failed = len(results) - successful
    total_cost = sum(
        (result.metrics.estimated_cost_usd or Decimal(0) for result in results),
        start=Decimal(0),
    )
    usage = Counter(result.model_key for result in results)
    most_used = usage.most_common(1)[0][0] if usage else "No data"
    success_rate = successful / len(results) if results else 0
    columns = st.columns(4)
    columns[0].metric("Benchmark tests", len(history))
    columns[1].metric("Total model runs", len(results))
    columns[2].metric("Success rate", f"{success_rate:.0%}", f"{failed} failed")
    columns[3].metric("Estimated total cost", f"${total_cost:.6f}")
    st.caption(f"Most used model: {most_used}")

    if history:
        st.subheader("Recent benchmarks")
        st.dataframe(
            [
                {
                    "Test": entry.benchmark.name,
                    "Created": entry.benchmark.created_at,
                    "Runs": len(entry.results),
                    "Successful": sum(result.status.value == "success" for result in entry.results),
                }
                for entry in history[:5]
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Start here")
    st.write(
        "Create a benchmark, select two or more provider models, then review responses "
        "and metrics in Comparison. Live calls require provider keys in `.env`."
    )
    if not results:
        st.info("No benchmark results yet. Open New Benchmark to run the first comparison.")
