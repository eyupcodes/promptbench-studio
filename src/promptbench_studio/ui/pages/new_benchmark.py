"""Benchmark creation page."""

import json

import streamlit as st

from promptbench_studio.config import get_settings
from promptbench_studio.domain.schemas import (
    BenchmarkDefinition,
    BenchmarkParameters,
    EvaluationConfig,
    ModelTarget,
    RunResult,
)
from promptbench_studio.providers.demo_provider import RoutingProvider
from promptbench_studio.providers.litellm_provider import LiteLLMProvider
from promptbench_studio.services.benchmark_service import run_benchmark_sync
from promptbench_studio.services.persistence_service import load_history_sync


def _run(benchmark: BenchmarkDefinition, selected_models: list[ModelTarget]) -> None:
    settings = get_settings()
    provider = RoutingProvider(LiteLLMProvider(settings))
    progress = st.progress(0, text="Preparing benchmark…")

    def update_progress(current: int, total: int, result: RunResult) -> None:
        progress.progress(current / total, text=f"Completed {current}/{total}: {result.model_key}")

    outcome = run_benchmark_sync(
        benchmark,
        selected_models,
        provider=provider,
        progress=update_progress,
        settings=settings,
    )
    st.session_state.current_benchmark = outcome.benchmark
    st.session_state.current_results = list(outcome.results)
    st.session_state.current_evaluations = list(outcome.evaluations)
    st.session_state.history = load_history_sync()


def render() -> None:
    st.title("New Benchmark")
    st.caption("Same prompts and parameters run against every selected model.")
    model_by_name = {model.display_name: model for model in st.session_state.models}

    with st.form("new-benchmark"):
        name = st.text_input("Test name", placeholder="Customer support tone comparison")
        description = st.text_area(
            "Description",
            placeholder="What decision should this test support?",
        )
        system_prompt = st.text_area("System prompt", height=120)
        user_prompt = st.text_area("User prompt", height=180)
        selected_names = st.multiselect(
            "Models",
            options=list(model_by_name),
            default=list(model_by_name)[:2],
            help="Select at least two models for useful comparison.",
        )
        left, right = st.columns(2)
        temperature = left.slider("Temperature", 0.0, 2.0, 0.0, 0.1)
        max_tokens = right.number_input("Max output tokens", 1, 131_072, 1_024)
        timeout = left.number_input("Timeout (seconds)", 1, 600, 60)
        repeat_count = right.number_input("Repeat count", 1, 20, 1)
        st.markdown("**Evaluation criteria**")
        required_phrases = st.text_input(
            "Required phrases",
            placeholder="comma, separated, phrases",
            help="Each phrase must appear in model output.",
        )
        forbidden_phrases = st.text_input(
            "Forbidden phrases",
            placeholder="comma, separated, phrases",
            help="Each phrase must be absent from model output.",
        )
        regex_patterns = st.text_area(
            "Regex patterns",
            placeholder="One regular expression per line",
            height=80,
        )
        min_words = left.number_input("Minimum words", 0, 100_000, 0)
        max_words = right.number_input("Maximum words (0 disables)", 0, 100_000, 0)
        json_schema_text = st.text_area(
            "Optional JSON Schema",
            placeholder='{"type":"object","properties":{...}}',
            height=120,
        )
        reference_answer = st.text_area("Optional reference answer", height=80)
        judge_model = st.text_input(
            "Optional judge model",
            placeholder="anthropic/claude-opus-4-8",
        )
        judge_criterion = st.text_area(
            "Optional judge criterion",
            placeholder="Score factual accuracy and instruction adherence.",
            height=80,
        )
        submitted = st.form_submit_button("Run benchmark", type="primary")

    if not submitted:
        return
    if not name.strip() or not user_prompt.strip():
        st.error("Test name and user prompt are required.")
        return
    if len(selected_names) < 2:
        st.error("Select at least two models.")
        return

    try:
        json_schema = json.loads(json_schema_text) if json_schema_text.strip() else None
    except json.JSONDecodeError as error:
        st.error(f"JSON Schema is invalid: {error.msg}")
        return
    try:
        evaluation = EvaluationConfig(
            required_phrases=tuple(
                phrase.strip() for phrase in required_phrases.split(",") if phrase.strip()
            ),
            forbidden_phrases=tuple(
                phrase.strip() for phrase in forbidden_phrases.split(",") if phrase.strip()
            ),
            regex_patterns=tuple(
                pattern.strip() for pattern in regex_patterns.splitlines() if pattern.strip()
            ),
            min_words=int(min_words) or None,
            max_words=int(max_words) or None,
            json_schema=json_schema,
            reference_answer=reference_answer.strip() or None,
            judge_model=judge_model.strip() or None,
            judge_criterion=judge_criterion.strip() or None,
        )
    except ValueError as error:
        st.error(f"Evaluation configuration is invalid: {error}")
        return
    benchmark = BenchmarkDefinition(
        name=name.strip(),
        description=description.strip(),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        parameters=BenchmarkParameters(
            temperature=temperature,
            max_output_tokens=int(max_tokens),
            timeout_seconds=float(timeout),
            repeat_count=int(repeat_count),
        ),
        evaluation=evaluation,
    )
    with st.status("Running selected models…", expanded=True) as status:
        _run(benchmark, [model_by_name[item] for item in selected_names])
        status.update(label="Benchmark finished", state="complete")
    st.success("Benchmark finished. Open Comparison to inspect results.")
