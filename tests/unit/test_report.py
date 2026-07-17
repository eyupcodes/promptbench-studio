from decimal import Decimal
from uuid import uuid4

from promptbench_studio.domain.schemas import RunResult, RunStatus, UsageMetrics
from promptbench_studio.services.report_service import build_comparison, select_best_model


def make_result(model: str, latency: int, cost: str | None) -> RunResult:
    return RunResult(
        test_id=uuid4(),
        model_id=uuid4(),
        model_key=model,
        output_text="42",
        metrics=UsageMetrics(
            latency_ms=latency,
            input_tokens=2,
            output_tokens=1,
            total_tokens=3,
            estimated_cost_usd=Decimal(cost) if cost else None,
            characters=2,
            words=1,
        ),
        status=RunStatus.SUCCESS,
    )


def test_build_comparison_preserves_unknown_cost() -> None:
    frame = build_comparison([make_result("a", 10, None)])

    assert frame.loc[0, "estimated_cost_usd"] is None


def test_select_best_model_returns_none_without_success() -> None:
    failed = make_result("failed", 1, None).model_copy(update={"status": RunStatus.ERROR})

    assert select_best_model([failed], {}) is None


def test_select_best_model_uses_score_then_latency() -> None:
    results = [make_result("slow", 50, "0.1"), make_result("fast", 10, "0.2")]

    winner = select_best_model(results, {"slow": 0.9, "fast": 0.9})

    assert winner == "fast"


def test_select_best_model_requires_quality_evidence() -> None:
    results = [make_result("fast", 10, "0.2")]

    assert select_best_model(results, {}) is None


def test_select_best_model_ignores_unscored_models() -> None:
    results = [make_result("unscored", 1, "0.001"), make_result("scored", 50, "0.2")]

    assert select_best_model(results, {"scored": 0.8}) == "scored"
