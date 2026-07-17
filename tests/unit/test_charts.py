import pandas as pd

from promptbench_studio.ui.charts import DARK_COLORS, LIGHT_COLORS, scatter_chart


def comparison_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model": "synthetic/a",
                "estimated_cost_usd": 0.001,
                "latency_ms": 10,
                "quality_score": 0.9,
            },
            {
                "model": "synthetic/b",
                "estimated_cost_usd": 0.002,
                "latency_ms": 20,
                "quality_score": 0.8,
            },
        ]
    )


def test_scatter_chart_has_labels_symbols_and_accessible_palette() -> None:
    figure = scatter_chart(comparison_frame(), "latency_ms", "Latency (ms)")

    assert figure.layout.xaxis.title.text == "Latency (ms)"
    assert figure.layout.yaxis.title.text == "Quality score (0-1)"
    assert len(figure.data) == 2
    assert all(trace.marker.symbol is not None for trace in figure.data)
    assert len(LIGHT_COLORS) == len(DARK_COLORS) == 4
