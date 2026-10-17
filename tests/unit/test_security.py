import socket

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


def resolve_to(monkeypatch: pytest.MonkeyPatch, *addresses: str) -> None:
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", (address, 0)) for address in addresses],
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@api.example.com/v1",
        "https://user@api.example.com/v1",
        "https://api.example.com:8443/v1",
        "https:///v1",
    ],
)
def test_rejects_credentials_ports_and_missing_host(url: str) -> None:
    with pytest.raises(ValueError, match=r"HTTPS|credentials or port"):
        validate_base_url(url)


def test_accepts_explicit_default_port(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve_to(monkeypatch, "93.184.216.34")

    assert validate_base_url("https://api.example.com:443/v1") == "https://api.example.com:443/v1"


def test_rejects_unresolvable_host(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise socket.gaierror("no such host")

    monkeypatch.setattr("socket.getaddrinfo", fail)

    with pytest.raises(ValueError, match="could not be resolved"):
        validate_base_url("https://missing.example.com/v1")


@pytest.mark.parametrize("address", ["10.0.0.5", "192.168.1.10", "127.0.0.1", "::1", "fd00::1"])
def test_rejects_hostname_resolving_to_non_public_address(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    resolve_to(monkeypatch, address)

    with pytest.raises(ValueError, match="public addresses"):
        validate_base_url("https://internal.example.com/v1")


def test_rejects_hostname_with_any_non_public_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve_to(monkeypatch, "93.184.216.34", "10.0.0.5")

    with pytest.raises(ValueError, match="public addresses"):
        validate_base_url("https://rebind.example.com/v1")


def test_rejects_hostname_with_no_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve_to(monkeypatch)

    with pytest.raises(ValueError, match="public addresses"):
        validate_base_url("https://empty.example.com/v1")


def test_redacts_token_and_secret_assignments() -> None:
    sanitized = redact_secrets("token: abc123; secret=hunter2, API-KEY = k-999")

    assert "abc123" not in sanitized
    assert "hunter2" not in sanitized
    assert "k-999" not in sanitized
    assert sanitized.count("[REDACTED]") == 3


def test_redaction_keeps_unrelated_text_and_skips_empty_secrets() -> None:
    assert redact_secrets("rate limit exceeded", secrets=("",)) == "rate limit exceeded"
