"""Security guards for provider configuration and errors."""

import ipaddress
import re
import socket
from urllib.parse import urlsplit

BEARER_PATTERN = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+")
KEY_PATTERN = re.compile(r"(?i)((?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s,;]+")
PROVIDER_KEY_PATTERN = re.compile(r"(?<![\w-])(?:sk-(?:proj-|ant-api\d{2}-)?|gsk_)[A-Za-z0-9_-]+")
URL_CREDENTIAL_PATTERN = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:@/]+:)[^\s@/]+(@)")


def redact_secrets(text: str, secrets: tuple[str, ...] = ()) -> str:
    sanitized = BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    sanitized = KEY_PATTERN.sub(r"\1[REDACTED]", sanitized)
    sanitized = PROVIDER_KEY_PATTERN.sub("[REDACTED]", sanitized)
    sanitized = URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]\2", sanitized)
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized


def validate_base_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Custom provider URL must use HTTPS and include a host")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Custom provider URL contains unsupported credentials or port")

    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as error:
        raise ValueError("Custom provider host could not be resolved") from error

    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Custom provider URL must resolve only to public addresses")
    return url
