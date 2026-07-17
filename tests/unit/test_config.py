import pytest
from pydantic import ValidationError

from promptbench_studio.config import Settings


def test_settings_are_immutable() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(ValidationError):
        settings.max_retries = 5  # type: ignore[misc]


def test_settings_reject_invalid_concurrency() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_concurrency=0)


def test_secret_is_not_exposed_by_repr() -> None:
    settings = Settings(_env_file=None, OPENAI_API_KEY="synthetic-secret")

    assert "synthetic-secret" not in repr(settings)
