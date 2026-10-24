from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from promptbench_studio.domain.schemas import BenchmarkParameters, EvaluationConfig, ModelTarget
from promptbench_studio.ui.pages import new_benchmark


@pytest.fixture
def models() -> list[ModelTarget]:
    return [
        ModelTarget(provider="demo", model_key=f"demo/{name}", display_name=name.title())
        for name in ("fast", "balanced", "quality")
    ]


@pytest.fixture
def run_benchmark(monkeypatch: pytest.MonkeyPatch) -> Mock:
    runner = Mock()
    monkeypatch.setattr(new_benchmark, "_run", runner)
    return runner


@pytest.fixture
def benchmark_app(models: list[ModelTarget], run_benchmark: Mock) -> AppTest:
    app = AppTest.from_string(
        "from promptbench_studio.ui.pages.new_benchmark import render\nrender()"
    )
    app.session_state.models = models
    app.run()

    assert not app.exception
    assert app.title[0].value == "New Benchmark"
    run_benchmark.assert_not_called()
    app.text_input[0].set_value("Support comparison")
    next(item for item in app.text_area if item.label == "User prompt").set_value("Help me choose.")
    return app


@pytest.mark.parametrize(
    ("widget_type", "label", "value", "expected_error"),
    [
        ("text_input", "Test name", " \t ", "Test name and user prompt are required."),
        ("text_area", "User prompt", " \n ", "Test name and user prompt are required."),
        ("multiselect", "Models", [], "Select at least two models."),
        ("multiselect", "Models", ["Fast"], "Select at least two models."),
        ("text_area", "Optional JSON Schema", "{", "JSON Schema is invalid:"),
        (
            "text_area",
            "Optional JSON Schema",
            '{"type": "not-a-type"}',
            "Evaluation configuration is invalid:",
        ),
        ("text_area", "Regex patterns", "[", "Evaluation configuration is invalid:"),
    ],
)
def test_invalid_form_does_not_run_benchmark(
    benchmark_app: AppTest,
    run_benchmark: Mock,
    widget_type: str,
    label: str,
    value: object,
    expected_error: str,
) -> None:
    widget = next(item for item in getattr(benchmark_app, widget_type) if item.label == label)
    widget.set_value(value)
    benchmark_app.button[0].click().run()

    assert not benchmark_app.exception
    assert benchmark_app.error[0].value.startswith(expected_error)
    assert not benchmark_app.success
    run_benchmark.assert_not_called()


def test_inverted_word_limits_do_not_run_benchmark(
    benchmark_app: AppTest, run_benchmark: Mock
) -> None:
    next(item for item in benchmark_app.number_input if item.label == "Minimum words").set_value(10)
    next(
        item for item in benchmark_app.number_input if item.label == "Maximum words (0 disables)"
    ).set_value(5)
    benchmark_app.button[0].click().run()

    assert not benchmark_app.exception
    assert "max_words must be greater than or equal to min_words" in benchmark_app.error[0].value
    assert not benchmark_app.success
    run_benchmark.assert_not_called()


@pytest.mark.parametrize("customize", [False, True])
def test_valid_form_passes_configuration_and_selected_models_to_runner(
    benchmark_app: AppTest, run_benchmark: Mock, models: list[ModelTarget], customize: bool
) -> None:
    app = benchmark_app
    app.text_input[0].set_value("  Support comparison  ")
    app.multiselect[0].set_value(["Quality", "Fast"])
    if customize:
        text_inputs = {
            "Required phrases": " response, , evidence ",
            "Forbidden phrases": " guess, , hallucination ",
            "Optional judge model": " synthetic/judge ",
        }
        text_areas = {
            "Description": "  Compare support answers.  ",
            "System prompt": "  Be helpful.  ",
            "Regex patterns": "  \\p{L}+  \n\n response ",
            "Optional JSON Schema": '{"type": "object"}',
            "Optional reference answer": "  Reference response  ",
            "Optional judge criterion": "  Accuracy  ",
        }
        numbers = {
            "Max output tokens": 256,
            "Timeout (seconds)": 30,
            "Repeat count": 2,
            "Minimum words": 5,
            "Maximum words (0 disables)": 50,
        }
        for item in app.text_input:
            if item.label in text_inputs:
                item.set_value(text_inputs[item.label])
        for item in app.text_area:
            if item.label in text_areas:
                item.set_value(text_areas[item.label])
        for item in app.number_input:
            if item.label in numbers:
                item.set_value(numbers[item.label])
        app.slider[0].set_value(0.7)

    app.button[0].click().run()

    assert not app.exception
    assert not app.error
    assert app.success[0].value == "Benchmark finished. Open Comparison to inspect results."
    run_benchmark.assert_called_once()
    benchmark, selected_models = run_benchmark.call_args.args
    assert selected_models == [models[2], models[0]]
    assert benchmark.name == "Support comparison"
    assert benchmark.user_prompt == "Help me choose."
    if customize:
        assert benchmark.description == "Compare support answers."
        assert benchmark.system_prompt == "  Be helpful.  "
        assert benchmark.parameters == BenchmarkParameters(
            temperature=0.7, max_output_tokens=256, timeout_seconds=30, repeat_count=2
        )
        assert benchmark.evaluation == EvaluationConfig(
            required_phrases=("response", "evidence"),
            forbidden_phrases=("guess", "hallucination"),
            regex_patterns=(r"\p{L}+", "response"),
            min_words=5,
            max_words=50,
            json_schema={"type": "object"},
            reference_answer="Reference response",
            judge_model="synthetic/judge",
            judge_criterion="Accuracy",
        )
    else:
        assert benchmark.description == ""
        assert benchmark.system_prompt == ""
        assert benchmark.parameters == BenchmarkParameters()
        assert benchmark.evaluation == EvaluationConfig()
