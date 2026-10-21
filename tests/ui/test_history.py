from datetime import UTC, datetime
from uuid import uuid4

import pytest
from streamlit.testing.v1 import AppTest

from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    EvaluationResult,
    HistoryEntry,
    RunResult,
    RunStatus,
    UsageMetrics,
)


@pytest.fixture
def saved_history() -> list[HistoryEntry]:
    entries = []
    for name, description in (
        ("Straße summary", "Summarize a travel guide"),
        ("Code review", "Check JSON validation"),
    ):
        benchmark = BenchmarkDefinition(
            name=name,
            description=description,
            user_prompt="Review this example.",
            created_at=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
        )
        result = RunResult(
            test_id=benchmark.id,
            model_id=uuid4(),
            model_key=f"demo/{len(entries)}",
            output_text=f"Output for {name}",
            metrics=UsageMetrics(latency_ms=10),
            status=RunStatus.SUCCESS,
        )
        evaluations = (
            (
                EvaluationResult(
                    run_id=result.id,
                    evaluator_type="rule",
                    criterion="required_phrase",
                    score=1.0,
                    explanation="Required phrase found.",
                ),
            )
            if not entries
            else ()
        )
        entries.append(
            HistoryEntry(benchmark=benchmark, results=(result,), evaluations=evaluations)
        )
    return entries


def history_app(entries: list[HistoryEntry]) -> AppTest:
    app = AppTest.from_string("from promptbench_studio.ui.pages.history import render\nrender()")
    app.session_state.history = entries
    return app


def test_empty_history_shows_guidance_without_controls() -> None:
    app = history_app([]).run()

    assert not app.exception
    assert app.title[0].value == "History"
    assert app.info[0].value == "No saved benchmark runs yet."
    assert not app.text_input
    assert not app.button


@pytest.mark.parametrize(
    ("query", "expected_names"),
    [
        ("  STRASSE  ", ["Straße summary"]),
        (" SUMMARY ", ["Straße summary"]),
        ("  json  ", ["Code review"]),
        (" \t ", ["Straße summary", "Code review"]),
    ],
)
def test_history_filters_names_and_descriptions(
    saved_history: list[HistoryEntry], query: str, expected_names: list[str]
) -> None:
    app = history_app(saved_history).run()
    app.text_input[0].set_value(query).run()

    assert not app.exception
    assert [item.label.split(" · ")[0] for item in app.expander] == expected_names
    assert len(app.button) == len(expected_names)
    assert not app.info


def test_history_filter_can_recover_from_no_matches(saved_history: list[HistoryEntry]) -> None:
    app = history_app(saved_history).run()
    app.text_input[0].set_value("missing benchmark").run()

    assert not app.exception
    assert app.info[0].value == "No benchmark runs match this filter."
    assert not app.expander
    assert not app.button

    app.text_input[0].set_value("").run()

    assert not app.exception
    assert len(app.expander) == len(saved_history)
    assert not app.info


@pytest.mark.parametrize("selected_index", [0, 1])
def test_open_comparison_replaces_previous_selection(
    saved_history: list[HistoryEntry], selected_index: int
) -> None:
    selected = saved_history[selected_index]
    previous = saved_history[1 - selected_index]
    app = history_app(saved_history)
    app.session_state.current_benchmark = previous.benchmark
    app.session_state.current_results = previous.results
    app.session_state.current_evaluations = previous.evaluations
    app.run()

    app.button(key=f"history-{selected.benchmark.id}").click().run()

    assert not app.exception
    assert app.session_state.current_benchmark == selected.benchmark
    assert app.session_state.current_results == selected.results
    assert app.session_state.current_evaluations == selected.evaluations
    assert app.success[0].value == "Selected. Open Comparison from navigation."
    assert app.session_state.history == saved_history
