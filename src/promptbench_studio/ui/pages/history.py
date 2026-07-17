"""Benchmark history page."""

import streamlit as st


def render() -> None:
    st.title("History")
    history = st.session_state.history
    if not history:
        st.info("No saved benchmark runs yet.")
        return

    query = st.text_input("Filter benchmarks", placeholder="Search name or description")
    normalized_query = query.casefold().strip()
    filtered = [
        item
        for item in history
        if not normalized_query
        or normalized_query in item.benchmark.name.casefold()
        or normalized_query in item.benchmark.description.casefold()
    ]
    if not filtered:
        st.info("No benchmark runs match this filter.")
        return

    for item in filtered:
        benchmark = item.benchmark
        results = item.results
        with st.expander(f"{benchmark.name} · {benchmark.created_at:%Y-%m-%d %H:%M UTC}"):
            st.write(benchmark.description or "No description")
            st.write(f"Models: {', '.join(result.model_key for result in results)}")
            if st.button("Open comparison", key=f"history-{benchmark.id}"):
                st.session_state.current_benchmark = benchmark
                st.session_state.current_results = results
                st.session_state.current_evaluations = item.evaluations
                st.success("Selected. Open Comparison from navigation.")
