from promptbench_studio.domain.schemas import BenchmarkDefinition, ModelTarget, RunStatus
from promptbench_studio.providers.demo_provider import DemoProvider, RoutingProvider


async def test_demo_provider_returns_repeatable_success_without_credentials() -> None:
    benchmark = BenchmarkDefinition(name="Demo", user_prompt="Explain caching")
    model = ModelTarget(
        provider="demo",
        model_key="demo/balanced",
        display_name="Demo Balanced",
    )

    first = await DemoProvider().call(benchmark, model)
    second = await DemoProvider().call(benchmark, model)

    assert first.status is RunStatus.SUCCESS
    assert first.output_text == second.output_text
    assert first.metrics.total_tokens > 0
    assert first.metrics.estimated_cost_usd == 0
    assert first.model_id == model.id


async def test_routing_provider_routes_demo_and_live_models() -> None:
    benchmark = BenchmarkDefinition(name="Routing", user_prompt="Return 42")
    live_model = ModelTarget(provider="live", model_key="live/model", display_name="Live")
    demo_model = ModelTarget(provider="demo", model_key="demo/fast", display_name="Demo")
    live_provider = DemoProvider()
    router = RoutingProvider(live_provider)

    demo_result = await router.call(benchmark, demo_model)
    live_result = await router.call(benchmark, live_model)

    assert demo_result.raw_response["provider"] == "demo"
    assert live_result.model_key == "live/model"
