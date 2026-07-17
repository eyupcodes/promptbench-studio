import pytest

from promptbench_studio.providers.security import redact_secrets, validate_base_url


def test_redacts_known_secret_and_bearer_token() -> None:
    text = "api_key=synthetic-secret Authorization: Bearer abc.def"

    sanitized = redact_secrets(text, secrets=("synthetic-secret",))

    assert "synthetic-secret" not in sanitized
    assert "abc.def" not in sanitized


def test_redacts_common_provider_key_prefixes() -> None:
    text = "Provider failed with sk-proj-abc123 and sk-ant-api03-def456 and gsk_xyz789"

    sanitized = redact_secrets(text)

    assert "abc123" not in sanitized
    assert "def456" not in sanitized
    assert "xyz789" not in sanitized
    assert sanitized.count("[REDACTED]") == 3


def test_redacts_url_credentials() -> None:
    sanitized = redact_secrets("https://client:super-secret@example.com/v1")

    assert "super-secret" not in sanitized
    assert "[REDACTED]" in sanitized


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com",
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
    ],
)
def test_rejects_unsafe_base_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_base_url(url)


def test_accepts_public_https_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    assert validate_base_url("https://api.example.com/v1") == "https://api.example.com/v1"
