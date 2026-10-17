from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "src/promptbench_studio/ui/main.py"


def test_dashboard_loads_without_exception() -> None:
    app = AppTest.from_file(str(APP_PATH))
    app.run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "PromptBench Studio"
