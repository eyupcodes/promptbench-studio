"""Shared Streamlit session state defaults."""

from decimal import Decimal
from typing import Any

import streamlit as st

from promptbench_studio.domain.schemas import ModelTarget
from promptbench_studio.services.persistence_service import load_history_sync

DEFAULT_MODELS = (
    ModelTarget(
        provider="demo",
        model_key="demo/fast",
        display_name="Demo Fast",
        input_price_per_million=Decimal("0"),
        output_price_per_million=Decimal("0"),
    ),
    ModelTarget(
        provider="demo",
        model_key="demo/balanced",
        display_name="Demo Balanced",
        input_price_per_million=Decimal("0"),
        output_price_per_million=Decimal("0"),
    ),
    ModelTarget(
        provider="demo",
        model_key="demo/quality",
        display_name="Demo Quality",
        input_price_per_million=Decimal("0"),
        output_price_per_million=Decimal("0"),
    ),
    ModelTarget(
        provider="openai",
        model_key="openai/gpt-4.1-mini",
        display_name="GPT-4.1 Mini",
        input_price_per_million=Decimal("0.40"),
        output_price_per_million=Decimal("1.60"),
    ),
    ModelTarget(
        provider="anthropic",
        model_key="anthropic/claude-haiku-4-5",
        display_name="Claude Haiku 4.5",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("5.00"),
    ),
    ModelTarget(
        provider="groq",
        model_key="groq/llama-3.3-70b-versatile",
        display_name="Llama 3.3 70B (Groq)",
        input_price_per_million=Decimal("0.59"),
        output_price_per_million=Decimal("0.79"),
    ),
)


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "models": DEFAULT_MODELS,
        "current_results": [],
        "current_benchmark": None,
        "current_evaluations": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "history" not in st.session_state:
        st.session_state.history = load_history_sync()
