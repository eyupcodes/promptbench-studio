"""Provider settings guidance page."""

import streamlit as st


def render() -> None:
    st.title("Settings")
    st.warning("Provider credentials are read from environment variables and never stored here.")
    st.code(
        "OPENAI_API_KEY=\nANTHROPIC_API_KEY=\nGROQ_API_KEY=",
        language="bash",
    )
    st.subheader("Configured models")
    st.dataframe(
        [
            {
                "Provider": model.provider,
                "Model": model.model_key,
                "Display name": model.display_name,
                "Input $/1M": model.input_price_per_million,
                "Output $/1M": model.output_price_per_million,
            }
            for model in st.session_state.models
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Edit `.env` for credentials. Restart app after changing environment values.")
