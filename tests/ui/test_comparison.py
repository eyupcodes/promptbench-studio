from decimal import Decimal
from uuid import uuid4

import pytest
from streamlit.testing.v1 import AppTest

from promptbench_studio.domain.schemas import EvaluationResult, RunResult, RunStatus, UsageMetrics


@pytest.fixture
def results() -> list[RunResult]:
    test_id = uuid4()
    return [
        RunResult(
            test_id=test_id,
            model_id=uuid4(),
            model_key=model,
            output_text=f"Response from {model}",
            metrics=UsageMetrics(
                latency_ms=latency,
                estimated_cost_usd=cost,
                total_tokens=12,
            ),
            status=status,
            provider_error="Provider unavailable" if status is RunStatus.ERROR else None,
        )
        for model, latency, cost, status in (
            ("demo/quality", 50, None, RunStatus.SUCCESS),
            ("demo/fast", 10, Decimal("0"), RunStatus.SUCCESS),
            ("demo/failed", 1, None, RunStatus.ERROR),
        )
    ]


def comparison_app(
    results: list[RunResult], evaluations: list[EvaluationResult] | None = None
) -> AppTest:
    app = AppTest.from_string("from promptbench_studio.ui.pages.comparison import render\nrender()")
    app.session_state.current_results = results
    app.session_state.current_evaluations = evaluations or []
    return app.run(timeout=10)


def test_empty_comparison_shows_guidance_without_results_or_exports() -> None:
    app = comparison_app([])

    assert not app.exception
    assert app.info[0].value == "Run a benchmark first."
    assert not app.text_area
    assert not app.dataframe
    assert not app.get("download_button")
    assert not app.get("plotly_chart")


def test_unscored_comparison_preserves_responses_errors_and_unknown_cost(
    results: list[RunResult],
) -> None:
    app = comparison_app(results)

    assert not app.exception
    for result in results:
        response = app.text_area(key=f"response-{result.id}")
        assert response.value == f"Response from {result.model_key}"
        assert response.disabled
    assert app.error[0].value == "Error: Provider unavailable"
    frame = app.dataframe[0].value
    assert frame["model"].tolist() == ["demo/quality", "demo/fast", "demo/failed"]
    assert frame["status"].tolist() == ["success", "success", "error"]
    assert frame["latency_ms"].tolist() == [50, 10, 1]
    assert frame["total_tokens"].tolist() == [12, 12, 12]
    assert frame["estimated_cost_usd"].isna().tolist() == [True, False, True]
    assert frame.loc[1, "estimated_cost_usd"] == 0.0
    assert frame["quality_score"].isna().all()
    assert not any("Recommended model:" in item.value for item in app.success)
    assert not app.get("plotly_chart")
    assert [item.proto.label for item in app.get("download_button")] == [
        "Download CSV",
        "Download JSON",
        "Download Markdown",
    ]


def test_comparison_averages_numeric_scores_and_recommends_only_successful_models(
    results: list[RunResult],
) -> None:
    evaluations = [
        EvaluationResult(
            run_id=run_id,
            evaluator_type="rule",
            criterion=f"criterion-{index}",
            score=score,
            explanation="Evaluation detail",
        )
        for index, (run_id, score) in enumerate(
            (
                (results[0].id, 1.0),
                (results[0].id, 0.6),
                (results[0].id, None),
                (results[1].id, 0.6),
                (results[2].id, 1.0),
                (uuid4(), 1.0),
            )
        )
    ]
    app = comparison_app(results, evaluations)

    assert not app.exception
    assert app.dataframe[0].value["quality_score"].tolist() == pytest.approx([0.8, 0.6, 1.0])
    recommendations = [item.value for item in app.success if "Recommended model:" in item.value]
    assert len(recommendations) == 1
    assert recommendations[0].startswith("Recommended model: demo/quality.")
    details = app.dataframe[1].value
    assert details["Run ID"].tolist() == [str(item.run_id) for item in evaluations]
    assert details["Criterion"].tolist() == [f"criterion-{index}" for index in range(6)]
    assert details["Score"].isna().tolist() == [False, False, True, False, False, False]
    assert len(app.get("plotly_chart")) == 2


def test_comparison_with_only_unscored_evaluations_does_not_recommend_a_model(
    results: list[RunResult],
) -> None:
    evaluation = EvaluationResult(
        run_id=results[0].id,
        evaluator_type="judge",
        criterion="accuracy",
        score=None,
        explanation="Judge unavailable",
    )
    app = comparison_app(results, [evaluation])

    assert not app.exception
    assert app.dataframe[0].value["quality_score"].isna().all()
    assert app.dataframe[1].value.loc[0, "Explanation"] == "Judge unavailable"
    assert not any("Recommended model:" in item.value for item in app.success)
    assert not app.get("plotly_chart")
    assert app.info
