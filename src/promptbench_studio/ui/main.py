"""PromptBench Studio Streamlit entrypoint."""

import streamlit as st

from promptbench_studio.ui.pages import comparison, dashboard, history, new_benchmark, settings
from promptbench_studio.ui.state import initialize_state


def run() -> None:
    st.set_page_config(
        page_title="PromptBench Studio",
        page_icon="PB",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_state()
    navigation = st.navigation(
        [
            st.Page(
                dashboard.render,
                title="Dashboard",
                icon=":material/dashboard:",
                url_path="dashboard",
                default=True,
            ),
            st.Page(
                new_benchmark.render,
                title="New Benchmark",
                icon=":material/add_chart:",
                url_path="new-benchmark",
            ),
            st.Page(
                comparison.render,
                title="Comparison",
                icon=":material/compare:",
                url_path="comparison",
            ),
            st.Page(
                history.render,
                title="History",
                icon=":material/history:",
                url_path="history",
            ),
            st.Page(
                settings.render,
                title="Settings",
                icon=":material/settings:",
                url_path="settings",
            ),
        ]
    )
    navigation.run()


if __name__ == "__main__":
    run()
