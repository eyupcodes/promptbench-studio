from streamlit.testing.v1 import AppTest


def test_dashboard_loads_without_exception() -> None:
    app = AppTest.from_file("src/promptbench_studio/ui/main.py")
    app.run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "PromptBench Studio"
