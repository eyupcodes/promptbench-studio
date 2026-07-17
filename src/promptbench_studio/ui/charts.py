"""Accessible Plotly comparison charts."""

from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

LIGHT_COLORS = ("#2a78d6", "#008300", "#e87ba4", "#eda100")
DARK_COLORS = ("#3987e5", "#008300", "#d55181", "#c98500")


def _theme() -> tuple[str, str, str, tuple[str, ...]]:
    is_dark = getattr(st.context, "theme", None) == "dark"
    if is_dark:
        return "#1a1a19", "#ffffff", "#2c2c2a", DARK_COLORS
    return "#fcfcfb", "#0b0b0b", "#e1e0d9", LIGHT_COLORS


def scatter_chart(
    frame: pd.DataFrame,
    x: Literal["estimated_cost_usd", "latency_ms"],
    x_label: str,
) -> go.Figure:
    surface, text, grid, colors = _theme()
    clean = frame.dropna(subset=[x, "quality_score"]).copy()
    figure = px.scatter(
        clean,
        x=x,
        y="quality_score",
        color="model",
        symbol="model",
        text="model",
        color_discrete_sequence=list(colors),
        labels={
            x: x_label,
            "quality_score": "Quality score (0-1)",
            "model": "Model",
        },
        hover_data={"model": True, x: ":.6f", "quality_score": ":.2f"},
    )
    figure.update_traces(
        marker={"size": 10, "line": {"width": 2, "color": surface}},
        textposition="top center",
    )
    figure.update_layout(
        paper_bgcolor=surface,
        plot_bgcolor=surface,
        font={"color": text, "family": "system-ui, Segoe UI, sans-serif"},
        legend={"title": {"text": "Model"}, "orientation": "h", "y": -0.25},
        margin={"l": 20, "r": 20, "t": 20, "b": 90},
        hovermode="closest",
    )
    figure.update_xaxes(gridcolor=grid, zeroline=False)
    figure.update_yaxes(gridcolor=grid, range=[0, 1.05], zeroline=False)
    return figure
